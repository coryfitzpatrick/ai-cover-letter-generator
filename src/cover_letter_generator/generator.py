"""Core cover letter generation logic with RAG and LLM integration."""

import os
from pathlib import Path

# Disable warnings and telemetry BEFORE importing libraries
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY_DISABLED"] = "True"

import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv
from groq import Groq
from sentence_transformers import SentenceTransformer

# Load environment variables
load_dotenv()


class CoverLetterGenerator:
    """Generate cover letters using RAG and LLM.

    This class uses Retrieval-Augmented Generation (RAG) to create personalized
    cover letters by retrieving relevant context from a vector database and
    generating content using Groq's Llama 3.3 70B model.
    """

    # Model configuration constants
    MODEL_NAME = "llama-3.3-70b-versatile"
    TEMPERATURE = 0.7
    MAX_TOKENS = 1000
    TOP_P = 0.9

    # RAG configuration constants
    DEFAULT_N_RESULTS = 40  # Increased to ensure all leadership details are captured, even if embedded in longer chunks
    DISTANCE_THRESHOLD = 2.0  # Slightly relaxed to include more potentially relevant content
    MAX_CONTEXT_CHARS = 15000

    def __init__(self, system_prompt_path: str = None):
        """Initialize the cover letter generator.

        Args:
            system_prompt_path: Path to system prompt template file
        """
        print("Initializing cover letter generator...")

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

        # Initialize Groq client
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")

        self.groq_client = Groq(api_key=api_key)

        # Load system prompt
        if system_prompt_path is None:
            system_prompt_path = Path(__file__).parent.parent.parent / "system_prompt.txt"
        else:
            system_prompt_path = Path(system_prompt_path)

        if not system_prompt_path.exists():
            raise FileNotFoundError(f"System prompt not found at {system_prompt_path}")

        with open(system_prompt_path, 'r') as f:
            self.system_prompt_template = f.read()

        print("✓ Generator initialized successfully\n")

    def get_relevant_context(
        self, job_description: str, n_results: int = None
    ) -> str:
        """Retrieve relevant context from the vector database.

        Args:
            job_description: The job description to match against
            n_results: Number of results to retrieve (default from class constant)

        Returns:
            Combined context string
        """
        if n_results is None:
            n_results = self.DEFAULT_N_RESULTS

        # Normalize the query
        normalized_query = job_description.replace("'", "").strip()

        # Generate query embedding
        query_embedding = self.model.encode([normalized_query])[0]

        # Query the collection
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()], n_results=n_results
        )

        # Filter results by distance threshold
        contexts = []
        total_chars = 0

        if results["documents"] and results["distances"]:
            # Prioritize Achievements and Resume documents
            sorted_results = sorted(
                zip(
                    results["documents"][0],
                    results["distances"][0],
                    results["metadatas"][0],
                ),
                key=lambda x: (
                    0 if "achievements" in x[2].get("source", "").lower() else
                    1 if "resume" in x[2].get("source", "").lower() else 2,
                    x[1],  # Then sort by distance
                ),
            )

            for doc, distance, metadata in sorted_results:
                if distance <= self.DISTANCE_THRESHOLD:
                    source = metadata.get("source", "Unknown")
                    context_entry = f"[Source: {source}]\n{doc}"

                    # Check if adding this would exceed our limit
                    if total_chars + len(context_entry) > self.MAX_CONTEXT_CHARS:
                        break

                    contexts.append(context_entry)
                    total_chars += len(context_entry)

        if not contexts:
            return "No specific relevant information found. Use general knowledge about professional experience."

        return "\n\n---\n\n".join(contexts)

    def generate_cover_letter_stream(
        self,
        job_description: str,
        company_name: str = None,
        job_title: str = None,
    ):
        """Generate a cover letter with streaming output.

        Args:
            job_description: The job description/posting
            company_name: The company name
            job_title: The job title

        Yields:
            Chunks of the generated cover letter
        """
        print("Retrieving relevant context from knowledge base...")
        context = self.get_relevant_context(job_description)

        print("Generating cover letter...\n")
        print("-" * 80)

        # Format the system prompt
        system_prompt = self.system_prompt_template.format(
            context=context,
            job_description=job_description,
            company_name=company_name or "[Company Name]",
            job_title=job_title or "[Job Title]"
        )

        # Query Groq with streaming
        try:
            stream = self.groq_client.chat.completions.create(
                model=self.MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "Please write the cover letter now. Remember to explicitly reference specific job requirements in each paragraph and show how the experience matches what they're asking for. Make the connections obvious."},
                ],
                temperature=self.TEMPERATURE,
                max_tokens=self.MAX_TOKENS,
                top_p=self.TOP_P,
                stream=True,
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            raise RuntimeError(f"Error generating cover letter: {e}") from e

    def revise_cover_letter_stream(
        self,
        original_cover_letter: str,
        feedback: str,
        job_description: str,
        company_name: str = None,
        job_title: str = None
    ):
        """Revise a cover letter based on user feedback with streaming output.

        Args:
            original_cover_letter: The original generated cover letter
            feedback: User's feedback for revision
            job_description: The original job description
            company_name: The company name
            job_title: The job title

        Yields:
            Chunks of the revised cover letter
        """
        print("Retrieving relevant context from knowledge base...")
        context = self.get_relevant_context(job_description)

        print("Revising cover letter based on your feedback...\n")
        print("-" * 80)

        # Format the system prompt
        system_prompt = self.system_prompt_template.format(
            context=context,
            job_description=job_description,
            company_name=company_name or "[Company Name]",
            job_title=job_title or "[Job Title]"
        )

        # Create messages with the original letter and feedback
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": "Please write the cover letter now."
            },
            {
                "role": "assistant",
                "content": original_cover_letter
            },
            {
                "role": "user",
                "content": f"Please revise the cover letter based on this feedback:\n\n{feedback}\n\nProvide the complete revised cover letter (not just the changes)."
            }
        ]

        # Query Groq with streaming
        try:
            stream = self.groq_client.chat.completions.create(
                model=self.MODEL_NAME,
                messages=messages,
                temperature=self.TEMPERATURE,
                max_tokens=self.MAX_TOKENS,
                top_p=self.TOP_P,
                stream=True,
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            raise RuntimeError(f"Error revising cover letter: {e}") from e
