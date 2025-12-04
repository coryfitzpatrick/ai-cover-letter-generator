"""Core cover letter generation logic with RAG and LLM integration."""

import os
from pathlib import Path

# Disable warnings and telemetry BEFORE importing libraries
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY_DISABLED"] = "True"

import chromadb
import openai
from anthropic import Anthropic
from chromadb.config import Settings
from docx import Document
from dotenv import load_dotenv
from groq import Groq
from sentence_transformers import SentenceTransformer

from .analysis import JobAnalysis, JobLevel, analyze_job_posting
from .scoring import score_document
from .utils import suppress_telemetry_errors

# Load environment variables
load_dotenv()

# Suppress ChromaDB telemetry errors
suppress_telemetry_errors()


class CoverLetterGenerator:
    """Generate cover letters using RAG and Claude.

    This class uses Retrieval-Augmented Generation (RAG) to create personalized
    cover letters by retrieving relevant context from a vector database and
    generating content using Claude (Sonnet 4.5 or Opus 4) with two-stage generation.

    Groq is used for fast job analysis only.
    """

    # Groq model for job analysis (fast and free)
    GROQ_MODEL = "meta-llama/llama-4-maverick-17b-128e-instruct"

    # Available models
    AVAILABLE_MODELS = {
        "gpt-4o": "gpt-4o",
        "opus": "claude-3-opus-20240229",
        "opus-4": "claude-3-opus-20240229",
    }

    # RAG configuration constants
    DEFAULT_N_RESULTS = 40  # Initial candidates retrieved from vector DB
    DISTANCE_THRESHOLD = 2.0  # Maximum embedding distance (0-2 scale, lower = more similar)
    MAX_CONTEXT_CHARS = 15000  # Maximum characters in context sent to LLM

    # Multi-stage retrieval configuration
    EXTENDED_N_RESULTS = 60  # Retrieve more results initially for better selection after scoring
    PRIORITY_REQUIREMENTS_TO_QUERY = 3  # Top N priority requirements to query separately
    PRIORITY_REQ_RESULTS = 15  # Results per priority requirement query
    TECHNOLOGIES_TO_QUERY = 5  # Top N technologies to query separately
    TECHNOLOGY_RESULTS = 10  # Results per technology query
    MAX_CHUNKS_PER_SOURCE = 8  # Limit chunks from same source for diversity

    def __init__(self, system_prompt_path: str = None, model_name: str = None):
        """Initialize the cover letter generator.

        Args:
            system_prompt_path: Path to system prompt template file
            model_name: Model to use. Options: "gpt-4o" (default), "opus".
                         Can also use environment variable LLM_MODEL.
        """
        print("Initializing cover letter generator...")

        # Determine which model to use
        model_selection = model_name or os.getenv("LLM_MODEL", "gpt-4o")
        self.model_name = self.AVAILABLE_MODELS.get(
            model_selection.lower(),
            self.AVAILABLE_MODELS["gpt-4o"]
        )

        # Display which model is being used
        if "gpt-4o" in self.model_name:
            display_name = "GPT-4o"
        elif "opus" in self.model_name:
            display_name = "Claude Opus 4"
        else:
            display_name = self.model_name
            
        print(f"Using {display_name} for cover letter generation")

        # Load embedding model
        print("Loading embedding model...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

        # Setup ChromaDB
        # Allow custom data directory via environment variable
        data_dir_env = os.getenv("DATA_DIR")
        if data_dir_env:
            # Remove quotes if present and expand ~ to home directory
            data_dir_env = data_dir_env.strip('"').strip("'")
            data_dir = Path(data_dir_env).expanduser().resolve()
        else:
            data_dir = Path(__file__).parent.parent.parent / "data"

        chroma_dir = data_dir / "chroma_db"

        if not chroma_dir.exists():
            raise FileNotFoundError(
                f"ChromaDB not found at {chroma_dir}. "
                "Please run 'prepare-data' first to create the database."
            )

        print("Connecting to ChromaDB...")
        self.client = chromadb.PersistentClient(
            path=str(chroma_dir),
            settings=Settings(anonymized_telemetry=False)
        )

        try:
            self.collection = self.client.get_collection(name="cover_letter_context")
        except Exception as e:
            raise FileNotFoundError(
                f"Collection 'cover_letter_context' not found. "
                f"Please run 'prepare-data' first. Error: {e}"
            )

        # Initialize Groq client (for job analysis only)
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        self.groq_client = Groq(api_key=groq_api_key)

        # Initialize LLM clients
        self.openai_client = None
        self.claude_client = None

        if "gpt" in self.model_name:
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                raise ValueError("OPENAI_API_KEY not found in environment variables")
            self.openai_client = openai.Client(api_key=openai_api_key)
        else:
            anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
            if not anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
            self.claude_client = Anthropic(api_key=anthropic_api_key)

        # Cost tracking
        self.total_cost = 0.0
        self.api_calls = []

        # Load system prompt
        # Load system prompt
        if system_prompt_path is None:
            # Check DATA_DIR first
            data_dir_env = os.getenv("DATA_DIR")
            if data_dir_env:
                data_dir_clean = data_dir_env.strip('"').strip("'")
                data_dir = Path(data_dir_clean).expanduser().resolve()
                drive_prompt_path = data_dir / "system_prompt" / "system_prompt.txt"
                
                if drive_prompt_path.exists():
                    system_prompt_path = drive_prompt_path
                    print(f"✓ Loaded system prompt from {drive_prompt_path}")
            
            # Fallback to local default if not found in Drive
            if system_prompt_path is None:
                system_prompt_path = Path(__file__).parent.parent.parent / "prompts" / "system_prompt.txt"
        else:
            system_prompt_path = Path(system_prompt_path)

        if not system_prompt_path.exists():
            raise FileNotFoundError(f"System prompt not found at {system_prompt_path}")

        with open(system_prompt_path, 'r') as f:
            self.system_prompt_template = f.read()

        print("✓ Generator initialized successfully\n")
        
        # Initialize project root
        self.project_root = Path(__file__).parent.parent.parent

    def _prepare_system_prompt(
        self,
        context: str,
        job_description: str,
        company_name: str,
        job_title: str,
        job_analysis_summary: str = ""
    ) -> str:
        """Prepare the system prompt with all context filled in."""
        # Load Leadership Philosophy
        leadership_philosophy = self._load_leadership_philosophy()

        # Format the prompt
        return self.system_prompt_template.format(
            context=context,
            job_description=job_description,
            company_name=company_name or "[Company Name]",
            job_title=job_title or "[Job Title]",
            job_analysis=job_analysis_summary,
            leadership_philosophy=leadership_philosophy
        )

    def _call_llm(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 2500,
        temperature: float = 0.3
    ) -> tuple[str, float]:
        """Call the appropriate LLM based on configuration."""
        if "gpt" in self.model_name:
            response = self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            content = response.choices[0].message.content
            cost = self._track_api_cost(
                self.model_name,
                response.usage.prompt_tokens,
                response.usage.completion_tokens
            )
        else:
            response = self.claude_client.messages.create(
                model=self.model_name,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )
            content = response.content[0].text
            cost = self._track_api_cost(
                self.model_name,
                response.usage.input_tokens,
                response.usage.output_tokens
            )
        
        return content, cost

    def _load_leadership_philosophy(self) -> str:
        """Load leadership philosophy from Google Drive or local file."""
        leadership_philosophy = ""
        
        # Resolve DATA_DIR
        data_dir_env = os.getenv("DATA_DIR")
        if data_dir_env:
            data_dir_clean = data_dir_env.strip('"').strip("'")
            data_dir = Path(data_dir_clean).expanduser().resolve()
            
            # Check for DOCX first
            philosophy_docx = data_dir / "Leadership Philosophy.docx"
            if philosophy_docx.exists():
                try:
                    doc = Document(str(philosophy_docx))
                    leadership_philosophy = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
                    print(f"✓ Loaded leadership philosophy from {philosophy_docx.name}")
                except Exception as e:
                    print(f"Warning: Failed to read philosophy DOCX: {e}")

        # Fallback to local txt if not found in Drive (or if DATA_DIR not set)
        if not leadership_philosophy:
            philosophy_path = self.project_root / "leadership_philosophy.txt"
            if philosophy_path.exists():
                with open(philosophy_path, 'r') as f:
                    leadership_philosophy = f.read()
                print("✓ Loaded leadership philosophy from local file")
                
        return leadership_philosophy

    def analyze_job_posting(self, job_description: str, job_title: str = None) -> JobAnalysis:
        """Analyze job posting to extract requirements and classify job type.

        Args:
            job_description: The job description text
            job_title: Optional job title for context

        Returns:
            JobAnalysis object with requirements and classification
        """
        return analyze_job_posting(
            self.groq_client,
            self.GROQ_MODEL,
            job_description,
            job_title
        )

    def get_relevant_context(
        self, 
        job_description: str, 
        n_results: int = None, 
        job_title: str = None,
        job_analysis: JobAnalysis = None
    ) -> str:
        """Retrieve relevant context from the vector database using intelligent multi-stage retrieval.

        Args:
            job_description: The job description to match against
            n_results: Number of results to retrieve (default from class constant)
            job_title: Optional job title for better analysis
            job_analysis: Optional pre-computed job analysis to avoid re-running it

        Returns:
            Combined context string optimized for the specific job
        """
        # Step 1: Analyze the job posting (if not already provided)
        if job_analysis is None:
            job_analysis = self.analyze_job_posting(job_description, job_title)

        # Step 2: Determine context allocation based on job type and level
        max_context_chars = self.MAX_CONTEXT_CHARS
        if job_analysis.level in [JobLevel.SENIOR_MANAGER, JobLevel.DIRECTOR_VP]:
            # Senior roles need more context for comprehensive experience
            max_context_chars = int(self.MAX_CONTEXT_CHARS * 1.3)
        elif job_analysis.level == JobLevel.IC_SENIOR:
            # IC roles can be more focused
            max_context_chars = int(self.MAX_CONTEXT_CHARS * 0.9)

        # Adjust retrieval count based on analysis
        if n_results is None:
            # Retrieve more results initially so we can score and filter
            n_results = self.EXTENDED_N_RESULTS

        print(f"Retrieving top {n_results} candidates from knowledge base...")

        # Step 3: Multi-stage targeted retrieval
        all_retrieved_docs = []
        seen_docs = set()  # Track unique documents to avoid duplicates

        # Query 1: General job description match
        normalized_query = job_description.replace("'", "").strip()
        query_embedding = self.model.encode([normalized_query])[0]
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=n_results
        )

        if results["documents"] and results["distances"]:
            for doc, distance, metadata in zip(
                results["documents"][0],
                results["distances"][0],
                results["metadatas"][0]
            ):
                doc_hash = hash(doc[:100])  # Use first 100 chars as fingerprint
                if doc_hash not in seen_docs:
                    seen_docs.add(doc_hash)
                    all_retrieved_docs.append((doc, distance, metadata))

        # Query 2: Targeted queries for high-priority requirements
        priority_requirements = [r for r in job_analysis.requirements if r.priority == 1]
        for req in priority_requirements[:self.PRIORITY_REQUIREMENTS_TO_QUERY]:
            req_embedding = self.model.encode([req.description])[0]
            req_results = self.collection.query(
                query_embeddings=[req_embedding.tolist()],
                n_results=self.PRIORITY_REQ_RESULTS
            )

            if req_results["documents"] and req_results["distances"]:
                for doc, distance, metadata in zip(
                    req_results["documents"][0],
                    req_results["distances"][0],
                    req_results["metadatas"][0]
                ):
                    doc_hash = hash(doc[:100])
                    if doc_hash not in seen_docs:
                        seen_docs.add(doc_hash)
                        # Boost these results since they match specific requirements
                        all_retrieved_docs.append((doc, distance * 0.8, metadata))

        # Query 3: Technology-specific queries if technologies mentioned
        for tech in job_analysis.key_technologies[:self.TECHNOLOGIES_TO_QUERY]:
            tech_query = f"experience with {tech}"
            tech_embedding = self.model.encode([tech_query])[0]
            tech_results = self.collection.query(
                query_embeddings=[tech_embedding.tolist()],
                n_results=self.TECHNOLOGY_RESULTS
            )

            if tech_results["documents"] and tech_results["distances"]:
                for doc, distance, metadata in zip(
                    tech_results["documents"][0],
                    tech_results["distances"][0],
                    tech_results["metadatas"][0]
                ):
                    doc_hash = hash(doc[:100])
                    if doc_hash not in seen_docs and tech.lower() in doc.lower():
                        seen_docs.add(doc_hash)
                        all_retrieved_docs.append((doc, distance * 0.85, metadata))

        print(f"Retrieved {len(all_retrieved_docs)} unique documents across all queries")

        # Step 4: Score and rank all retrieved documents
        print("Scoring and ranking documents...")
        scored_docs = []
        for doc, distance, metadata in all_retrieved_docs:
            if distance <= self.DISTANCE_THRESHOLD:
                score = score_document(doc, metadata, job_analysis, distance)
                scored_docs.append((doc, distance, metadata, score))

        # Sort by score (highest first)
        scored_docs.sort(key=lambda x: x[3], reverse=True)

        print("Selected top documents (score threshold applied)")

        # Debug: Show top 5 scoring documents
        if scored_docs:
            print("\n  Top 5 highest-scoring documents:")
            for i, (doc, distance, metadata, score) in enumerate(scored_docs[:5]):
                source = metadata.get("source", "Unknown")
                preview = doc[:80].replace('\n', ' ')
                print(f"    {i+1}. Score: {score:.1f} | Source: {source}")
                print(f"       Preview: {preview}...")
            print()

        # Step 5: Build context string with best documents
        contexts = []
        total_chars = 0

        # Ensure diversity in sources
        source_counts = {}

        for doc, distance, metadata, score in scored_docs:
            source = metadata.get("source", "Unknown")

            # Track source diversity
            source_counts[source] = source_counts.get(source, 0) + 1
            if source_counts[source] > self.MAX_CHUNKS_PER_SOURCE:
                continue  # Skip if too many from same source

            context_entry = f"[Source: {source}]\n{doc}"

            # Check if adding this would exceed our limit
            if total_chars + len(context_entry) > max_context_chars:
                break

            contexts.append(context_entry)
            total_chars += len(context_entry)

        print(f"Final context: {len(contexts)} documents, {total_chars} characters")

        if not contexts:
            return "No specific relevant information found. Use general knowledge about professional experience."

        return "\n\n---\n\n".join(contexts)

    def _track_api_cost(self, model: str, input_tokens: int, output_tokens: int):
        """Track API costs for transparency.

        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
        """
        # Claude pricing (as of 2025)
        # Reference: https://www.anthropic.com/pricing

        if "opus" in model or "claude-3-opus" in model:
            # Claude Opus 4 - Maximum power
            input_cost = (input_tokens / 1_000_000) * 15.00   # $15 per million input tokens
            output_cost = (output_tokens / 1_000_000) * 75.00  # $75 per million output tokens
        elif "gpt-4o" in model:
            # GPT-4o - High quality, lower cost
            input_cost = (input_tokens / 1_000_000) * 2.50    # $2.50 per million input tokens
            output_cost = (output_tokens / 1_000_000) * 10.00   # $10.00 per million output tokens
        elif "sonnet" in model or "claude-3-5-sonnet" in model:
            # Claude Sonnet 3.5 - Fast and cost-effective
            input_cost = (input_tokens / 1_000_000) * 3.00   # $3 per million input tokens
            output_cost = (output_tokens / 1_000_000) * 15.00  # $15 per million output tokens
        else:
            # Unknown model
            print(f"Warning: Unknown model '{model}' - cost tracking may be inaccurate")
            input_cost = 0
            output_cost = 0

        total_cost = input_cost + output_cost
        self.total_cost += total_cost

        call_info = {
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "cost": total_cost
        }
        self.api_calls.append(call_info)

        return total_cost

    def get_cost_summary(self) -> dict:
        """Get summary of API costs.

        Returns:
            Dictionary with cost information
        """
        return {
            "total_cost": self.total_cost,
            "total_calls": len(self.api_calls),
            "calls": self.api_calls
        }

    def generate_cover_letter(
        self,
        job_description: str,
        company_name: str = None,
        job_title: str = None,
        custom_context: str = None,
    ) -> tuple[str, dict]:
        """Generate cover letter using Claude with two-stage refinement process.

        Stage 1: Generate initial draft
        Stage 2: Self-critique and refine for maximum impact

        Args:
            job_description: The job description/posting
            company_name: The company name
            job_title: The job title
            custom_context: Optional custom context specific to this job application
                           (e.g., relevant experience not in resume, domain knowledge)

        Returns:
            Tuple of (final_cover_letter, cost_info)
        """
        print("=" * 80)
        print("STAGE 1: ANALYZING JOB & GENERATING INITIAL DRAFT")
        print("=" * 80)

        # Job analysis (using Groq - fast and free)
        print("\nAnalyzing job requirements with Groq...")
        job_analysis = self.analyze_job_posting(job_description, job_title)

        # Get relevant context
        # Get relevant context
        print("\nRetrieving relevant context from knowledge base...")
        context = self.get_relevant_context(
            job_description, 
            job_title=job_title,
            job_analysis=job_analysis
        )

        # Append custom context if provided
        if custom_context:
            print(f"✓ Adding custom context ({len(custom_context)} characters)")
            context += f"\n\n---\n\n**ADDITIONAL CONTEXT FOR THIS JOB:**\n{custom_context}"

        # Build job analysis summary
        analysis_summary = f"""JOB LEVEL: {job_analysis.level.value.upper().replace('_', ' ')}
JOB TYPE: {job_analysis.job_type.value.upper()}
KEY REQUIREMENTS: {len(job_analysis.requirements)} identified"""

        if job_analysis.key_technologies:
            analysis_summary += f"\nTECHNOLOGIES: {', '.join(job_analysis.key_technologies[:8])}"

        priority_reqs = sorted([r for r in job_analysis.requirements], key=lambda x: x.priority)[:3]
        if priority_reqs:
            analysis_summary += "\n\nTOP PRIORITY REQUIREMENTS:"
            for i, req in enumerate(priority_reqs, 1):
                analysis_summary += f"\n{i}. [{req.category.upper()}] {req.description}"

        # Prepare system prompt
        system_prompt = self._prepare_system_prompt(
            context=context,
            job_description=job_description,
            company_name=company_name,
            job_title=job_title,
            job_analysis_summary=analysis_summary
        )

        # [NEW] Context Pre-processing Layer
        # Rewrite the context if a custom prompt is provided
        print("Preprocessing context...")
        managerial_context = self._preprocess_context(context)
        
        # Stage 1: Generate initial draft
        print(f"Generating initial draft with {self.model_name}...")
        
        try:
            initial_draft, draft_cost = self._call_llm(
                system_prompt=system_prompt,
                user_message=f"CONTEXT:\n{managerial_context}\n\nJOB DESCRIPTION:\n{job_description}\n\nWrite an interview-worthy cover letter for this job.",
                max_tokens=2500,
                temperature=0.3
            )

            print(f"✓ Initial draft generated (cost: ${draft_cost:.4f})")

        except Exception as e:
            raise RuntimeError(f"Error generating initial draft: {e}") from e


        print("\n" + "=" * 80)
        print("STAGE 2: SELF-CRITIQUE & REFINEMENT")
        print("=" * 80)

        # Stage 2: Light polish and refinement
        critique_prompt_path = self.project_root / "prompts" / "critique_prompt.txt"
        if not critique_prompt_path.exists():
            raise FileNotFoundError(f"Critique prompt file not found at {critique_prompt_path}")
            
        with open(critique_prompt_path, 'r') as f:
            critique_template = f.read()

        critique_prompt = critique_template.format(
            company_name=company_name,
            initial_draft=initial_draft,
            job_description=job_description[:2000]  # Truncate JD to avoid context limits
        )

        print(f"\n{self.model_name} is critiquing and refining the draft...")

        try:
            full_response, refinement_cost = self._call_llm(
                system_prompt="You are a helpful assistant.",
                user_message=critique_prompt,
                max_tokens=2500,
                temperature=0.3
            )

            print(f"✓ Refinement complete (cost: ${refinement_cost:.4f})")

            # Extract refined version
            if "REFINED VERSION:" in full_response:
                refined_letter = full_response.split("REFINED VERSION:")[1].strip()
            else:
                # If format not followed, use the whole response
                refined_letter = full_response

            # Extract notes for display
            notes = ""
            if "NOTES:" in full_response:
                notes_part = full_response.split("REFINED VERSION:")[0]
                if "NOTES:" in notes_part:
                    notes = notes_part.split("NOTES:")[1].strip()

            if notes:
                print("\nRefinement Notes:")
                print("-" * 80)
                print(notes)

        except Exception as e:
            raise RuntimeError(f"Error refining cover letter: {e}") from e

        total_cost = draft_cost + refinement_cost

        print("\n" + "=" * 80)
        print("✓ GENERATION COMPLETE")
        print(f"  Total Cost: ${total_cost:.4f}")
        print(f"  Session Total: ${self.total_cost:.4f}")
        print("=" * 80)

        cost_info = {
            "draft_cost": draft_cost,
            "refinement_cost": refinement_cost,
            "total_cost": total_cost,
            "session_total": self.total_cost
        }

        return refined_letter, cost_info

    def revise_cover_letter(
        self,
        current_version: str,
        feedback: str,
        job_description: str,
        company_name: str = None,
        job_title: str = None,
        custom_context: str = None,
    ) -> tuple[str, dict]:
        """Revise cover letter with Claude based on user feedback.

        Args:
            current_version: The current cover letter to revise
            feedback: User's feedback for what to change
            job_description: The job description
            company_name: Company name
            job_title: Job title
            custom_context: Optional custom context specific to this job

        Returns:
            Tuple of (revised_letter, cost_info)
        """
        print("\n" + "=" * 80)
        print(f"REVISING WITH {self.model_name.upper()}")
        print("=" * 80)
        print(f"\nUser feedback: {feedback}")

        # Get context (use cached if available)
        context = self.get_relevant_context(job_description, job_title=job_title)

        # Append custom context if provided
        if custom_context:
            context += f"\n\n---\n\n**ADDITIONAL CONTEXT FOR THIS JOB:**\n{custom_context}"

        # Prepare system prompt
        system_prompt = self._prepare_system_prompt(
            context=context,
            job_description=job_description,
            company_name=company_name,
            job_title=job_title,
            job_analysis_summary=""  # Not needed for revisions
        )

        # Create revision prompt
        revision_prompt = f"""Here is the current cover letter:

{current_version}

The user has requested the following changes:
{feedback}

Please revise the cover letter to incorporate this feedback while maintaining:
- All the core principles (impact, specificity, authenticity)
- Accurate information from the context (no fabrication)
- Natural flow and compelling narrative
- Professional tone appropriate for the role

Write the complete revised cover letter."""

        try:
            print("\nGenerating revision...")
            
            revised_letter, revision_cost = self._call_llm(
                system_prompt=system_prompt,
                user_message=revision_prompt,
                max_tokens=2000,
                temperature=0.3
            )

            print(f"✓ Revision complete (cost: ${revision_cost:.4f})")

        except Exception as e:
            raise RuntimeError(f"Error generating revision: {e}") from e

        print("=" * 80)

        cost_info = {
            "revision_cost": revision_cost,
            "session_total": self.total_cost
        }

        return revised_letter, cost_info

    def revise_cover_letter_stream(
        self,
        current_letter: str,
        user_feedback: str,
        job_description: str,
        company_name: str = None,
        job_title: str = None,
        custom_context: str = None,
    ):
        """Revise cover letter with Claude in streaming mode (yields chunks as they arrive).

        Args:
            current_letter: The current cover letter to revise
            user_feedback: User's feedback for what to change
            job_description: The job description
            company_name: Company name
            job_title: Job title
            custom_context: Optional custom context specific to this job

        Yields:
            str: Chunks of the revised cover letter as they're generated
        """
        # Get context (use cached if available)
        context = self.get_relevant_context(job_description, job_title=job_title)

        # Append custom context if provided
        if custom_context:
            context += f"\n\n---\n\n**ADDITIONAL CONTEXT FOR THIS JOB:**\n{custom_context}"

        # Load Claude system prompt
        system_prompt_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 'prompts', 'system_prompt.txt'
        )

        with open(system_prompt_path, 'r') as f:
            system_prompt_template = f.read()

        # Load Leadership Philosophy
        leadership_philosophy = self._load_leadership_philosophy()

        # Fill in the template
        system_prompt = system_prompt_template.format(
            company_name=company_name or "[Company Name]",
            job_title=job_title or "[Job Title]",
            context=context,
            job_description=job_description,
            job_analysis="",  # Not needed for revisions
            leadership_philosophy=leadership_philosophy
        )

        # Create revision prompt
        revision_prompt_path = self.project_root / "prompts" / "revision_prompt.txt"
        if revision_prompt_path.exists():
            with open(revision_prompt_path, 'r') as f:
                revision_template = f.read()
        else:
            raise FileNotFoundError(f"Revision prompt file not found at {revision_prompt_path}")

        revision_prompt = revision_template.format(
            current_letter=current_letter,
            user_feedback=user_feedback
        )

        try:
            # Stream response
            if "gpt" in self.model_name:
                stream = self.openai_client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": revision_prompt}
                    ],
                    temperature=0.3,
                    max_tokens=2000,
                    stream=True
                )
                
                full_content = []
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_content.append(content)
                        yield content
                
                # OpenAI doesn't return usage in stream chunks easily, so we estimate or skip
                # For simplicity in this hybrid implementation, we'll skip exact cost tracking for stream
                # or estimate based on length
                full_text = "".join(full_content)
                # Rough estimation: 1 token ~= 4 chars
                output_tokens = len(full_text) // 4
                input_tokens = len(system_prompt) // 4 + len(revision_prompt) // 4
                
                self._track_api_cost(
                    self.model_name,
                    input_tokens,
                    output_tokens
                )
                
            else:
                with self.claude_client.messages.stream(
                    model=self.model_name,
                    max_tokens=2000,
                    temperature=0.3,
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": revision_prompt}
                    ]
                ) as stream:
                    for text in stream.text_stream:
                        yield text

                    # Track cost after streaming is complete
                    final_message = stream.get_final_message()
                    self._track_api_cost(
                        self.model_name,
                        final_message.usage.input_tokens,
                        final_message.usage.output_tokens
                    )

        except Exception as e:
            raise RuntimeError(f"Error streaming revision: {e}") from e

    def _preprocess_context(self, context_str: str) -> str:
        """
        Pre-process context string if a custom prompt exists.
        
        Args:
            context_str: Original context string
            
        Returns:
            Processed context string.
        """
        managerial_prompt_path = self.project_root / "managerial_prompt.txt"
        
        if not managerial_prompt_path.exists():
            # If the secret prompt file doesn't exist (e.g. public repo), skip translation
            return context_str

        try:
            with open(managerial_prompt_path, 'r') as f:
                translation_prompt = f.read()
            
            # Use Groq for speed, or LLM for quality.
            if "gpt" in self.model_name:
                response = self.openai_client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "user", "content": translation_prompt.format(context=context_str[:6000])}
                    ],
                    temperature=0.5,
                    max_tokens=2000
                )
                return response.choices[0].message.content
            else:
                response = self.claude_client.messages.create(
                    model=self.model_name,
                    max_tokens=2000,
                    temperature=0.5,
                    messages=[
                        {"role": "user", "content": translation_prompt.format(context=context_str[:6000])} # Truncate to be safe
                    ]
                )
                return response.content[0].text
        except Exception as e:
            print(f"Warning: Managerial translation failed ({e}). Using original context.")
            return context_str
