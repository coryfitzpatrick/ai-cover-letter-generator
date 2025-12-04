"""Prepare training data and load it into ChromaDB vector database."""

import csv
import json
import os
import re
import shutil
from pathlib import Path
from typing import List, Tuple

# Disable warnings and telemetry BEFORE importing libraries
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY_DISABLED"] = "True"

import chromadb
from chromadb.config import Settings
from docx import Document
from dotenv import load_dotenv
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

from .utils import suppress_telemetry_errors

# Load environment variables from project root
_env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)

# Suppress ChromaDB telemetry errors
suppress_telemetry_errors()

# Chunking configuration
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_OVERLAP = 200

# Embedding model
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text content from a PDF file.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Extracted text content
    """
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
        return ""


def extract_text_from_docx(docx_path: str) -> str:
    """Extract text content from a DOCX file (Word document or exported Google Doc).

    Args:
        docx_path: Path to the DOCX file

    Returns:
        Extracted text content
    """
    try:
        doc = Document(docx_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"

        # Also extract text from tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    text += cell.text + "\n"

        return text.strip()
    except Exception as e:
        print(f"Error reading {docx_path}: {e}")
        return ""


def chunk_text(
    text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_OVERLAP
) -> List[str]:
    """Split text into overlapping chunks.

    Args:
        text: Text to split
        chunk_size: Size of each chunk in characters
        overlap: Number of overlapping characters between chunks

    Returns:
        List of text chunks
    """
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]

        # Try to break at a sentence or word boundary
        if end < text_length:
            # Look for sentence endings
            last_period = chunk.rfind('.')
            last_newline = chunk.rfind('\n')
            break_point = max(last_period, last_newline)

            if break_point > chunk_size * 0.5:  # Only break if we're past halfway
                chunk = chunk[:break_point + 1]
                end = start + break_point + 1

        chunks.append(chunk.strip())
        start = end - overlap

    return [c for c in chunks if c]  # Filter empty chunks


def process_linkedin_profile_csv(csv_path: str) -> List[Tuple[str, dict]]:
    """Extract profile information from LinkedIn Profile.csv.

    Args:
        csv_path: Path to the Profile.csv file

    Returns:
        List of tuples (text, metadata)
    """
    results = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Extract the summary/headline
                if row.get('Summary'):
                    results.append((
                        f"PROFESSIONAL SUMMARY:\n{row['Summary']}",
                        {
                            "source": "LinkedIn Profile",
                            "type": "profile_summary",
                            "name": f"{row.get('First Name', '')} {row.get('Last Name', '')}".strip()
                        }
                    ))

                if row.get('Headline'):
                    results.append((
                        f"PROFESSIONAL HEADLINE: {row['Headline']}",
                        {
                            "source": "LinkedIn Profile",
                            "type": "headline",
                            "name": f"{row.get('First Name', '')} {row.get('Last Name', '')}".strip()
                        }
                    ))
    except Exception as e:
        print(f"  Error reading Profile.csv: {e}")

    return results


def process_linkedin_recommendations_csv(csv_path: str) -> List[Tuple[str, dict]]:
    """Extract recommendations from LinkedIn Recommendations CSV.

    Args:
        csv_path: Path to the recommendations CSV file

    Returns:
        List of tuples (text, metadata)
    """
    results = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('Text') and row.get('Status') == 'VISIBLE':
                    recommender = f"{row.get('First Name', '')} {row.get('Last Name', '')}".strip()
                    company = row.get('Company', 'Unknown')
                    job_title = row.get('Job Title', 'Unknown')

                    # Format the recommendation with context
                    text = (
                        f"RECOMMENDATION from {recommender} "
                        f"({job_title} at {company}):\n\n"
                        f"{row['Text']}"
                    )

                    results.append((
                        text,
                        {
                            "source": "LinkedIn Recommendation",
                            "type": "recommendation",
                            "recommender": recommender,
                            "company": company,
                            "title": job_title
                        }
                    ))
    except Exception as e:
        print(f"  Error reading recommendations CSV: {e}")

    return results


def process_csv_files(data_dir: Path) -> List[Tuple[str, dict]]:
    """Process all LinkedIn CSV files in the data directory.

    Args:
        data_dir: Path to the data directory

    Returns:
        List of tuples (text, metadata)
    """
    results = []

    # Look for CSV files in the data directory and subdirectories (exclude template folder)
    csv_files = [
        f for f in data_dir.glob("**/*.csv")
        if "template" not in str(f).lower()
    ]

    if not csv_files:
        return results

    print("\nScanning for LinkedIn CSV files...")

    for csv_file in csv_files:
        file_name = csv_file.name.lower()

        if 'profile' in file_name:
            print(f"\nProcessing {csv_file.name}...")
            profile_data = process_linkedin_profile_csv(str(csv_file))
            results.extend(profile_data)
            print(f"  Extracted {len(profile_data)} profile entries")

        elif 'recommendation' in file_name and 'received' in file_name:
            print(f"\nProcessing {csv_file.name}...")
            recommendations = process_linkedin_recommendations_csv(str(csv_file))
            results.extend(recommendations)
            print(f"  Extracted {len(recommendations)} recommendations")

    return results


def process_json_files(data_dir: Path) -> List[Tuple[str, dict]]:
    """Process JSON files in the data directory.

    Args:
        data_dir: Path to the data directory

    Returns:
        List of tuples (text, metadata)
    """
    results = []

    # Look for JSON files in the data directory and subdirectories (exclude template folder)
    json_files = [
        f for f in data_dir.glob("**/*.json")
        if "template" not in str(f).lower()
    ]

    if not json_files:
        return results

    print("\nScanning for JSON files...")

    for json_file in json_files:
        # Skip contact_info.json (it's configuration, not data)
        if json_file.name == "contact_info.json":
            continue

        print(f"\nProcessing {json_file.name}...")
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Handle different JSON structures
            if isinstance(data, dict):
                # Convert dict to text entries
                for key, value in data.items():
                    if isinstance(value, (str, int, float, bool)):
                        text = f"{key}: {value}"
                        results.append((
                            text,
                            {
                                "source": json_file.name,
                                "type": "json",
                                "key": key
                            }
                        ))
                    elif isinstance(value, dict):
                        # Nested dict - convert to formatted text
                        text = f"{key}:\n" + "\n".join(
                            f"  {k}: {v}" for k, v in value.items()
                            if isinstance(v, (str, int, float, bool))
                        )
                        if text.strip():
                            results.append((
                                text,
                                {
                                    "source": json_file.name,
                                    "type": "json",
                                    "key": key
                                }
                            ))
                    elif isinstance(value, list):
                        # List of items
                        for i, item in enumerate(value):
                            if isinstance(item, str):
                                results.append((
                                    f"{key} [{i+1}]: {item}",
                                    {
                                        "source": json_file.name,
                                        "type": "json",
                                        "key": key,
                                        "index": i
                                    }
                                ))
                            elif isinstance(item, dict):
                                # List of objects
                                text = f"{key} [{i+1}]:\n" + "\n".join(
                                    f"  {k}: {v}" for k, v in item.items()
                                    if isinstance(v, (str, int, float, bool))
                                )
                                if text.strip():
                                    results.append((
                                        text,
                                        {
                                            "source": json_file.name,
                                            "type": "json",
                                            "key": key,
                                            "index": i
                                        }
                                    ))

            elif isinstance(data, list):
                # Top-level list
                for i, item in enumerate(data):
                    if isinstance(item, str):
                        results.append((
                            item,
                            {
                                "source": json_file.name,
                                "type": "json",
                                "index": i
                            }
                        ))
                    elif isinstance(item, dict):
                        text = "\n".join(
                            f"{k}: {v}" for k, v in item.items()
                            if isinstance(v, (str, int, float, bool))
                        )
                        if text.strip():
                            results.append((
                                text,
                                {
                                    "source": json_file.name,
                                    "type": "json",
                                    "index": i
                                }
                            ))

            print(f"  Extracted {len([r for r in results if r[1]['source'] == json_file.name])} entries")

        except json.JSONDecodeError as e:
            print(f"  Error parsing JSON: {e}")
        except Exception as e:
            print(f"  Error reading {json_file.name}: {e}")

    return results


def main():
    """Main function to prepare data and load into ChromaDB."""
    print("Starting data preparation...")

    # Initialize the embedding model
    print("Loading embedding model...")
    model = SentenceTransformer(EMBEDDING_MODEL)

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

    # Delete entire chroma_db folder if it exists to clean up old data
    if chroma_dir.exists():
        print(f"Removing old ChromaDB at {chroma_dir}...")
        shutil.rmtree(chroma_dir)
        print("✓ Old database deleted")

    print(f"Initializing ChromaDB at {chroma_dir}...")
    client = chromadb.PersistentClient(
        path=str(chroma_dir),
        settings=Settings(anonymized_telemetry=False)
    )

    # Create new collection
    collection = client.create_collection(
        name="cover_letter_context",
        metadata={"description": "Context for cover letter generation"}
    )

    # Process all PDF files in the data directory and subdirectories
    documents = []
    metadatas = []
    ids = []

    print(f"\nScanning {data_dir} and subdirectories for PDF files...")
    # Get all PDFs but exclude the template folder
    pdf_files = [
        f for f in data_dir.glob("**/*.pdf")
        if "template" not in str(f).lower()
    ]

    doc_id = 0
    if not pdf_files:
        print("No PDF files found in data directory!")
    else:
        for pdf_file in pdf_files:
            print(f"\nProcessing {pdf_file.name}...")
            text = extract_text_from_pdf(str(pdf_file))

            if not text:
                print("  Skipped (empty or error)")
                continue

            # Smart Metadata Extraction from Filename
            # Try to infer company and year from filename (e.g., "2024_Johnson_Performance.pdf")
            filename_lower = pdf_file.name.lower()
            inferred_company = "unknown"
            inferred_year = "unknown"

            # Check for known companies (expand this list based on user's history)
            known_companies = [
                "johnson", "j&j", "fitbit", "google", "amazon", "microsoft", "startup"
            ]
            for company in known_companies:
                if company in filename_lower:
                    inferred_company = company
                    break
            
            # Check for year (2010-2030)
            year_match = re.search(r'20[12]\d', filename_lower)
            if year_match:
                inferred_year = year_match.group(0)

            # Chunk the text
            chunks = chunk_text(text)
            print(f"  Created {len(chunks)} chunks "
                  f"(Company: {inferred_company}, Year: {inferred_year})")

            # Add each chunk as a document
            for i, chunk in enumerate(chunks):
                documents.append(chunk)
                # Use relative path from data_dir for source
                relative_path = pdf_file.relative_to(data_dir)
                metadatas.append({
                    "source": str(relative_path),
                    "type": "pdf",
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "company": inferred_company,
                    "year": inferred_year
                })
                ids.append(f"doc_{doc_id}")
                doc_id += 1

    # Process DOCX files (Word documents and exported Google Docs)
    print(f"\nScanning {data_dir} and subdirectories for DOCX files...")
    docx_files = [
        f for f in data_dir.glob("**/*.docx")
        if "template" not in str(f).lower() and not f.name.startswith("~$")  # Exclude temp files
    ]

    if not docx_files:
        print("No DOCX files found in data directory!")
    else:
        for docx_file in docx_files:
            print(f"\nProcessing {docx_file.name}...")
            text = extract_text_from_docx(str(docx_file))

            if not text:
                print("  Skipped (empty or error)")
                continue

            # Smart Metadata Extraction from Filename
            filename_lower = docx_file.name.lower()
            inferred_company = "unknown"
            inferred_year = "unknown"

            known_companies = [
                "johnson", "j&j", "fitbit", "google", "amazon", "microsoft", "startup"
            ]
            for company in known_companies:
                if company in filename_lower:
                    inferred_company = company
                    break
            
            year_match = re.search(r'20[12]\d', filename_lower)
            if year_match:
                inferred_year = year_match.group(0)

            # Chunk the text
            chunks = chunk_text(text)
            print(f"  Created {len(chunks)} chunks "
                  f"(Company: {inferred_company}, Year: {inferred_year})")

            # Add each chunk as a document
            for i, chunk in enumerate(chunks):
                documents.append(chunk)
                # Use relative path from data_dir for source
                relative_path = docx_file.relative_to(data_dir)
                metadatas.append({
                    "source": str(relative_path),
                    "type": "docx",
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "company": inferred_company,
                    "year": inferred_year
                })
                ids.append(f"doc_{doc_id}")
                doc_id += 1

    # Process LinkedIn CSV files
    csv_data = process_csv_files(data_dir)

    if csv_data:
        for text, metadata in csv_data:
            documents.append(text)
            metadatas.append(metadata)
            ids.append(f"doc_{len(documents) - 1}")

    # Process JSON files
    json_data = process_json_files(data_dir)

    if json_data:
        for text, metadata in json_data:
            documents.append(text)
            metadatas.append(metadata)
            ids.append(f"doc_{len(documents) - 1}")

    if not documents:
        print("\nNo documents to process!")
        return

    # Generate embeddings and add to collection
    print(f"\nGenerating embeddings for {len(documents)} document chunks...")
    embeddings = model.encode(documents, show_progress_bar=True)

    print("Adding documents to ChromaDB...")
    collection.add(
        embeddings=embeddings.tolist(),
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )

    # Count file types
    pdf_count = len(pdf_files) if pdf_files else 0
    docx_count = len(docx_files) if docx_files else 0
    csv_count = len([
        m for m in metadatas 
        if m.get('type') in ['profile_summary', 'headline', 'recommendation']
    ])

    print(f"\n✓ Successfully processed {pdf_count} PDF files")
    if docx_count > 0:
        print(f"✓ Successfully processed {docx_count} DOCX files (Word/Google Docs)")
    if csv_count > 0:
        print(f"✓ Processed {csv_count} LinkedIn entries (profile + recommendations)")
    print(f"✓ Created {len(documents)} total document chunks")
    print(f"✓ Database saved at: {chroma_dir}")


if __name__ == "__main__":
    main()
