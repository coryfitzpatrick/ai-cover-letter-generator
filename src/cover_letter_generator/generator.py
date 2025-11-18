"""Core cover letter generation logic with RAG and LLM integration."""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum

# Disable warnings and telemetry BEFORE importing libraries
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY_DISABLED"] = "True"

import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv
from groq import Groq
from anthropic import Anthropic
from sentence_transformers import SentenceTransformer

# Load environment variables
load_dotenv()

# Suppress ChromaDB telemetry errors
from .utils import suppress_telemetry_errors
suppress_telemetry_errors()


class JobLevel(Enum):
    """Job level classification."""
    IC_SENIOR = "ic_senior"  # Senior IC roles
    MANAGER = "manager"  # Engineering Manager
    SENIOR_MANAGER = "senior_manager"  # Senior Manager / Director
    DIRECTOR_VP = "director_vp"  # Director / VP / Executive


class JobType(Enum):
    """Job type classification."""
    STARTUP = "startup"
    ENTERPRISE = "enterprise"
    PRODUCT = "product"
    INFRASTRUCTURE = "infrastructure"


@dataclass
class JobRequirement:
    """Represents a key requirement from job description."""
    category: str  # "leadership", "technical", "domain", "cultural"
    description: str
    priority: int  # 1 = highest priority


@dataclass
class JobAnalysis:
    """Analysis of job posting requirements."""
    level: JobLevel
    job_type: JobType
    requirements: List[JobRequirement]
    key_technologies: List[str]
    team_size_mentioned: bool


class CoverLetterGenerator:
    """Generate cover letters using RAG and Claude.

    This class uses Retrieval-Augmented Generation (RAG) to create personalized
    cover letters by retrieving relevant context from a vector database and
    generating content using Claude (Sonnet 4.5 or Opus 4) with two-stage generation.

    Groq is used for fast job analysis only.
    """

    # Groq model for job analysis (fast and free)
    GROQ_MODEL = "meta-llama/llama-4-maverick-17b-128e-instruct"

    # Available Claude models
    CLAUDE_MODELS = {
        "sonnet": "claude-sonnet-4-5-20250929",
        "sonnet-4.5": "claude-sonnet-4-5-20250929",
        "opus": "claude-opus-4-20250514",
        "opus-4": "claude-opus-4-20250514",
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

    # Scoring boost values
    ACHIEVEMENT_SOURCE_BOOST = 15
    RESUME_SOURCE_BOOST = 10
    RECOMMENDATION_BOOST = 8
    RECENT_COMPANY_BOOST = 12  # J&J (most recent)
    PREVIOUS_COMPANY_BOOST = 8  # Fitbit+Google
    PERCENTAGE_METRIC_BOOST = 10
    TEAM_SIZE_METRIC_BOOST = 8
    LEADERSHIP_TERM_BOOST = 5
    TECHNICAL_TERM_BOOST = 5
    TECHNOLOGY_MATCH_BOOST = 7
    PROCESS_IMPROVEMENT_BOOST = 6

    def __init__(self, system_prompt_path: str = None, claude_model: str = None):
        """Initialize the cover letter generator.

        Args:
            system_prompt_path: Path to system prompt template file
            claude_model: Claude model to use. Options: "sonnet" (default), "opus".
                         Can also use environment variable CLAUDE_MODEL.
        """
        print("Initializing cover letter generator...")

        # Determine which Claude model to use
        model_selection = claude_model or os.getenv("CLAUDE_MODEL", "sonnet")
        self.claude_model = self.CLAUDE_MODELS.get(
            model_selection.lower(),
            self.CLAUDE_MODELS["sonnet"]
        )

        # Display which model is being used
        model_name = "Claude Opus 4" if "opus" in self.claude_model else "Claude Sonnet 4.5"
        print(f"Using {model_name} for cover letter generation")

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

        # Initialize Claude client (for cover letter generation)
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        if not anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

        self.claude_client = Anthropic(api_key=anthropic_api_key)

        # Cost tracking
        self.total_cost = 0.0
        self.api_calls = []

        # Load system prompt
        if system_prompt_path is None:
            system_prompt_path = Path(__file__).parent.parent.parent / "system_prompt_claude.txt"
        else:
            system_prompt_path = Path(system_prompt_path)

        if not system_prompt_path.exists():
            raise FileNotFoundError(f"System prompt not found at {system_prompt_path}")

        with open(system_prompt_path, 'r') as f:
            self.system_prompt_template = f.read()

        print("✓ Generator initialized successfully\n")

    def analyze_job_posting(self, job_description: str, job_title: str = None) -> JobAnalysis:
        """Analyze job posting to extract requirements and classify job type.

        Args:
            job_description: The job description text
            job_title: Optional job title for context

        Returns:
            JobAnalysis object with requirements and classification
        """
        print("Analyzing job requirements...")

        # Prepare analysis prompt
        prompt = f"""Analyze this job posting and extract key information.

Job Title: {job_title or "Not specified"}

Job Description:
{job_description[:4000]}

Extract:
1. Job Level (IC_SENIOR, MANAGER, SENIOR_MANAGER, DIRECTOR_VP)
2. Job Type (STARTUP, ENTERPRISE, PRODUCT, INFRASTRUCTURE)
3. Top 5-7 key requirements categorized as:
   - leadership (team management, mentorship, cross-functional work)
   - technical (specific technologies, architectures, systems)
   - domain (industry knowledge, specific domains like healthcare, fintech)
   - cultural (values, work style, team culture)
4. Specific technologies mentioned (programming languages, tools, platforms)
5. Whether team size is mentioned

Respond in this EXACT format:

LEVEL: [one of: IC_SENIOR, MANAGER, SENIOR_MANAGER, DIRECTOR_VP]
TYPE: [one of: STARTUP, ENTERPRISE, PRODUCT, INFRASTRUCTURE]
REQUIREMENTS:
1. [category]: [description] (priority: [1-3])
2. [category]: [description] (priority: [1-3])
...
TECHNOLOGIES: [comma-separated list, or "none" if none mentioned]
TEAM_SIZE_MENTIONED: [yes/no]

Example:
LEVEL: MANAGER
TYPE: PRODUCT
REQUIREMENTS:
1. leadership: Lead team of 8-12 engineers (priority: 1)
2. technical: Experience with React and Java microservices (priority: 1)
3. leadership: Drive process improvements and best practices (priority: 2)
4. cultural: Build psychologically safe team environments (priority: 2)
5. domain: Experience in healthcare or regulated industries (priority: 3)
TECHNOLOGIES: React, Java, Docker, Kubernetes, AWS
TEAM_SIZE_MENTIONED: yes
"""

        try:
            response = self.groq_client.chat.completions.create(
                model=self.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": "You are a precise job posting analyzer. Extract requirements exactly as requested."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000,
            )

            result = response.choices[0].message.content.strip()

            # Parse the response
            level_match = re.search(r'LEVEL:\s*(\w+)', result, re.IGNORECASE)
            type_match = re.search(r'TYPE:\s*(\w+)', result, re.IGNORECASE)
            requirements_match = re.search(r'REQUIREMENTS:\s*\n(.*?)(?=TECHNOLOGIES:|$)', result, re.IGNORECASE | re.DOTALL)
            tech_match = re.search(r'TECHNOLOGIES:\s*(.+?)(?:\n|$)', result, re.IGNORECASE)
            team_size_match = re.search(r'TEAM_SIZE_MENTIONED:\s*(\w+)', result, re.IGNORECASE)

            # Parse level
            level_str = level_match.group(1).upper() if level_match else "MANAGER"
            level = JobLevel[level_str] if level_str in JobLevel.__members__ else JobLevel.MANAGER

            # Parse type
            type_str = type_match.group(1).upper() if type_match else "ENTERPRISE"
            job_type = JobType[type_str] if type_str in JobType.__members__ else JobType.ENTERPRISE

            # Parse requirements
            requirements = []
            if requirements_match:
                req_text = requirements_match.group(1)
                req_lines = re.findall(r'\d+\.\s*(\w+):\s*(.+?)\s*\(priority:\s*(\d+)\)', req_text, re.IGNORECASE)
                for category, description, priority in req_lines:
                    requirements.append(JobRequirement(
                        category=category.lower(),
                        description=description.strip(),
                        priority=int(priority)
                    ))

            # Parse technologies
            key_technologies = []
            if tech_match:
                tech_str = tech_match.group(1).strip()
                if tech_str.lower() != "none":
                    key_technologies = [t.strip() for t in tech_str.split(',')]

            # Parse team size mention
            team_size_mentioned = False
            if team_size_match:
                team_size_mentioned = team_size_match.group(1).lower() == "yes"

            analysis = JobAnalysis(
                level=level,
                job_type=job_type,
                requirements=requirements,
                key_technologies=key_technologies,
                team_size_mentioned=team_size_mentioned
            )

            print(f"  Level: {level.value}")
            print(f"  Type: {job_type.value}")
            print(f"  Requirements: {len(requirements)} key requirements identified")
            print(f"  Technologies: {', '.join(key_technologies) if key_technologies else 'None specific'}")

            return analysis

        except Exception as e:
            print(f"Warning: Could not analyze job posting: {e}")
            # Return default analysis
            return JobAnalysis(
                level=JobLevel.MANAGER,
                job_type=JobType.ENTERPRISE,
                requirements=[],
                key_technologies=[],
                team_size_mentioned=False
            )

    def score_document(self, doc: str, metadata: dict, job_analysis: JobAnalysis, distance: float) -> float:
        """Score a document's relevance based on multiple factors.

        Args:
            doc: Document text
            metadata: Document metadata
            job_analysis: Analyzed job requirements
            distance: Embedding distance from query

        Returns:
            Relevance score (higher is better)
        """
        score = 0.0
        doc_lower = doc.lower()
        source = metadata.get("source", "").lower()

        # Base score from embedding similarity (invert distance, normalize)
        # Distance typically ranges 0-2, so we invert it
        similarity_score = max(0, 2.0 - distance) * 10  # Scale to 0-20 range
        score += similarity_score

        # Boost for achievements document (usually most relevant)
        if "achievement" in source:
            score += self.ACHIEVEMENT_SOURCE_BOOST

        # Boost for resume (comprehensive info)
        if "resume" in source or "cv" in source:
            score += self.RESUME_SOURCE_BOOST

        # Boost for recommendations (leadership philosophy, soft skills)
        if "recommendation" in source:
            score += self.RECOMMENDATION_BOOST

        # Recency boost - J&J is most recent
        if "johnson" in doc_lower or "j&j" in doc_lower:
            score += self.RECENT_COMPANY_BOOST
        elif "fitbit" in doc_lower or "google" in doc_lower:
            score += self.PREVIOUS_COMPANY_BOOST

        # Boost for metrics/numbers (concrete achievements)
        if re.search(r'\d+%', doc):  # Percentages
            score += self.PERCENTAGE_METRIC_BOOST
        if re.search(r'\d+\s+(?:person|people|engineer|member)', doc_lower):  # Team sizes
            score += self.TEAM_SIZE_METRIC_BOOST

        # Leadership indicators boost (especially for manager+ roles)
        if job_analysis.level in [JobLevel.MANAGER, JobLevel.SENIOR_MANAGER, JobLevel.DIRECTOR_VP]:
            leadership_terms = [
                'led team', 'managed', 'mentored', 'coordinated',
                'cross-functional', 'leadership', 'guided', 'coached'
            ]
            for term in leadership_terms:
                if term in doc_lower:
                    score += self.LEADERSHIP_TERM_BOOST
                    break  # Only boost once

        # Technical depth boost for IC roles
        if job_analysis.level == JobLevel.IC_SENIOR:
            tech_terms = [
                'architected', 'designed', 'implemented', 'built',
                'migrated', 'optimized', 'developed'
            ]
            for term in tech_terms:
                if term in doc_lower:
                    score += self.TECHNICAL_TERM_BOOST
                    break

        # Technology match boost
        for tech in job_analysis.key_technologies:
            if tech.lower() in doc_lower:
                score += self.TECHNOLOGY_MATCH_BOOST

        # Process improvement boost (valuable across all roles)
        process_terms = ['reduced', 'improved', 'increased', 'optimized', 'streamlined']
        for term in process_terms:
            if term in doc_lower:
                score += self.PROCESS_IMPROVEMENT_BOOST
                break

        return score

    def get_relevant_context(
        self, job_description: str, n_results: int = None, job_title: str = None
    ) -> str:
        """Retrieve relevant context from the vector database using intelligent multi-stage retrieval.

        Args:
            job_description: The job description to match against
            n_results: Number of results to retrieve (default from class constant)
            job_title: Optional job title for better analysis

        Returns:
            Combined context string optimized for the specific job
        """
        # Step 1: Analyze the job posting
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
                score = self.score_document(doc, metadata, job_analysis, distance)
                scored_docs.append((doc, distance, metadata, score))

        # Sort by score (highest first)
        scored_docs.sort(key=lambda x: x[3], reverse=True)

        print(f"Selected top documents (score threshold applied)")

        # Debug: Show top 5 scoring documents
        if scored_docs:
            print(f"\n  Top 5 highest-scoring documents:")
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

        if "opus-4" in model or "claude-opus-4" in model:
            # Claude Opus 4 - Maximum power
            input_cost = (input_tokens / 1_000_000) * 15.00   # $15 per million input tokens
            output_cost = (output_tokens / 1_000_000) * 75.00  # $75 per million output tokens
        elif "sonnet-4" in model or "claude-sonnet-4" in model or "claude-3-5-sonnet" in model:
            # Claude Sonnet 4.5 and 3.5 - Fast and cost-effective
            input_cost = (input_tokens / 1_000_000) * 5.00   # $5 per million input tokens (updated from $3)
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

    def generate_cover_letter_claude_two_stage(
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
        print("\nRetrieving relevant context from knowledge base...")
        context = self.get_relevant_context(job_description, job_title=job_title)

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

        # Load Claude system prompt
        claude_prompt_path = Path(__file__).parent.parent.parent / "system_prompt_claude.txt"
        if not claude_prompt_path.exists():
            raise FileNotFoundError(f"Claude system prompt not found at {claude_prompt_path}")

        with open(claude_prompt_path, 'r') as f:
            claude_prompt_template = f.read()

        # Format the prompt
        system_prompt = claude_prompt_template.format(
            context=context,
            job_description=job_description,
            company_name=company_name or "[Company Name]",
            job_title=job_title or "[Job Title]",
            job_analysis=analysis_summary
        )

        model_name = "Claude Opus 4" if "opus" in self.claude_model else "Claude Sonnet 4.5"
        print(f"\nGenerating initial draft with {model_name}...")

        # Generate initial draft
        try:
            response = self.claude_client.messages.create(
                model=self.claude_model,
                max_tokens=2000,
                temperature=0.7,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": "Write an interview-worthy cover letter for this job."}
                ]
            )

            initial_draft = response.content[0].text
            draft_cost = self._track_api_cost(
                self.claude_model,
                response.usage.input_tokens,
                response.usage.output_tokens
            )

            print(f"✓ Initial draft generated (cost: ${draft_cost:.4f})")

        except Exception as e:
            raise RuntimeError(f"Error generating initial draft: {e}") from e

        print("\n" + "=" * 80)
        print("STAGE 2: SELF-CRITIQUE & REFINEMENT")
        print("=" * 80)

        # Stage 2: Light polish and refinement
        critique_prompt = f"""You are a cover letter expert doing a final polish on this draft for an engineering leadership role.

TARGET COMPANY: {company_name}

INITIAL DRAFT:
{initial_draft}

JOB DESCRIPTION:
{job_description[:2000]}

This draft is already strong. Your job is to do a light polish, NOT a major rewrite. Preserve the voice, energy, and natural flow. Ensure the tone is conversational and authentic, not aggressive or sales-y. Only make changes if there are clear issues:

**Check for:**
- **CRITICAL - Company name:** Does the letter use "{company_name}" consistently? If the job description mentions product names, subsidiaries, or legal entities (e.g., "Aisle Planner Pro", "Fullsteam Operations LLC"), ensure the letter uses ONLY "{company_name}". Replace any incorrect company/product names with "{company_name}".
- **Achievement fit:** Do the achievements selected actually match what THIS job needs? Or did you default to verification time/process improvement when they need team scaling/technical architecture?
- **Quantifiable metrics:** Does EVERY achievement include a specific number, percentage, or scale metric? No vague statements like "improved performance" - must be "reduced latency by 45%"
- **Strong closing:** Is the closing assertive with a clear call-to-action? Or is it passive ("thank you for your consideration")?
- **Values alignment:** If the job description mentions company values, mission, or culture, does the letter connect to these?
- **Competitive positioning:** Does the letter show why this candidate is uniquely qualified compared to typical applicants?
- **Problem-solution framing:** Does each achievement start with a PROBLEM, show LEADERSHIP in solving it, prove RESULTS, and make the CONNECTION to the company's challenges? Or is it just listing qualifications?
- **Leadership demonstration:** Are leadership abilities demonstrated through stories, not claimed? ("When faced with X, I led Y, achieving Z" vs "I have experience in X")
- **Connection to their challenges:** Does the letter explicitly show HOW the candidate's experience solves THEIR specific problems?
- Any fabricated facts not from the context?
- Any repeated achievements or information?
- Any em dashes (—) or double hyphens (--)? Replace with commas or separate sentences
- Any awkward phrasing that disrupts flow?
- Any generic statements that could be more specific?
- Does this letter feel unique to THIS job, or could it be sent to any company?
- Does this candidate feel like a MUST-HAVE problem-solver, or just another applicant with credentials?
- **Tone check:** Is the opening too aggressive/sales-y? Does it start with "Your team needs..." or "I understand exactly..."? If so, make it more conversational and genuine.
- **Language check:** Are there overly bold claims like "exactly what's needed" or "I'm confident I can deliver"? Soften to "could be valuable" or "I'm excited to explore."
- **Rhetorical questions:** Are there gimmicky rhetorical questions like "The result?" or "The impact?"? Replace with direct statements like "We reduced..." or natural transitions like "Through this work..."

**DO NOT:**
- Rewrite sentences that are already working well
- Remove personality or natural voice
- Over-edit for the sake of editing
- Make it sound more formal or template-like
- Force different achievements if the current ones are actually the best fit

If the draft is strong and achievements match their needs well, make minimal changes. If there are no real issues, the refined version can be very similar to the original.

Respond with:
1. **NOTES**: Brief notes on what you changed (if anything)
2. **REFINED VERSION**: The polished cover letter

Format:
NOTES:
[what you changed and why, or "Minimal changes - draft was strong"]

REFINED VERSION:
[polished cover letter]
"""

        print("\nClaude is critiquing and refining the draft...")

        try:
            refinement_response = self.claude_client.messages.create(
                model=self.claude_model,
                max_tokens=2500,
                temperature=0.7,
                messages=[
                    {"role": "user", "content": critique_prompt}
                ]
            )

            full_response = refinement_response.content[0].text
            refinement_cost = self._track_api_cost(
                self.claude_model,
                refinement_response.usage.input_tokens,
                refinement_response.usage.output_tokens
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
        print(f"✓ GENERATION COMPLETE")
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

    def revise_cover_letter_claude(
        self,
        current_letter: str,
        user_feedback: str,
        job_description: str,
        company_name: str = None,
        job_title: str = None,
        custom_context: str = None,
    ) -> tuple[str, dict]:
        """Revise cover letter with Claude based on user feedback.

        Args:
            current_letter: The current cover letter to revise
            user_feedback: User's feedback for what to change
            job_description: The job description
            company_name: Company name
            job_title: Job title
            custom_context: Optional custom context specific to this job

        Returns:
            Tuple of (revised_letter, cost_info)
        """
        print("\n" + "=" * 80)
        print("REVISING WITH CLAUDE SONNET 4.5")
        print("=" * 80)
        print(f"\nUser feedback: {user_feedback}")

        # Get context (use cached if available)
        context = self.get_relevant_context(job_description, job_title=job_title)

        # Append custom context if provided
        if custom_context:
            context += f"\n\n---\n\n**ADDITIONAL CONTEXT FOR THIS JOB:**\n{custom_context}"

        # Load Claude system prompt
        system_prompt_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 'system_prompt_claude.txt'
        )

        with open(system_prompt_path, 'r') as f:
            system_prompt_template = f.read()

        # Fill in the template
        system_prompt = system_prompt_template.format(
            company_name=company_name or "[Company Name]",
            job_title=job_title or "[Job Title]",
            context=context,
            job_description=job_description,
            job_analysis=""  # Not needed for revisions
        )

        # Create revision prompt
        revision_prompt = f"""Here is the current cover letter:

{current_letter}

The user has requested the following changes:
{user_feedback}

Please revise the cover letter to incorporate this feedback while maintaining:
- All the core principles (impact, specificity, authenticity)
- Accurate information from the context (no fabrication)
- Natural flow and compelling narrative
- Professional tone appropriate for the role

Write the complete revised cover letter."""

        try:
            print("\nGenerating revision...")
            response = self.claude_client.messages.create(
                model=self.claude_model,
                max_tokens=2000,
                temperature=0.7,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": revision_prompt}
                ]
            )

            revised_letter = response.content[0].text
            revision_cost = self._track_api_cost(
                self.claude_model,
                response.usage.input_tokens,
                response.usage.output_tokens
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
            os.path.dirname(__file__), '..', '..', 'system_prompt_claude.txt'
        )

        with open(system_prompt_path, 'r') as f:
            system_prompt_template = f.read()

        # Fill in the template
        system_prompt = system_prompt_template.format(
            company_name=company_name or "[Company Name]",
            job_title=job_title or "[Job Title]",
            context=context,
            job_description=job_description,
            job_analysis=""  # Not needed for revisions
        )

        # Create revision prompt
        revision_prompt = f"""Here is the current cover letter:

{current_letter}

The user has requested the following changes:
{user_feedback}

Please revise the cover letter to incorporate this feedback while maintaining:
- All the core principles (impact, specificity, authenticity)
- Accurate information from the context (no fabrication)
- Natural flow and compelling narrative
- Professional tone appropriate for the role

Write the complete revised cover letter."""

        try:
            # Stream response from Claude
            with self.claude_client.messages.stream(
                model=self.claude_model,
                max_tokens=2000,
                temperature=0.7,
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
                    self.claude_model,
                    final_message.usage.input_tokens,
                    final_message.usage.output_tokens
                )

        except Exception as e:
            raise RuntimeError(f"Error streaming revision: {e}") from e
