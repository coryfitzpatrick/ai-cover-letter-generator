#!/usr/bin/env python3
"""Performance profiling script for the cover letter generator.

This script profiles various components to identify performance bottlenecks
and measure latency across the generation pipeline.

Usage:
    python scripts/profile_performance.py [--full] [--output results.json]
"""

import argparse
import json
import time
from pathlib import Path
from typing import Dict, List, Any
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def measure_time(func, *args, **kwargs):
    """Measure execution time of a function.

    Args:
        func: Function to measure
        *args: Positional arguments to func
        **kwargs: Keyword arguments to func

    Returns:
        Tuple of (result, elapsed_time_ms)
    """
    start = time.perf_counter()
    result = func(*args, **kwargs)
    elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
    return result, elapsed


def profile_embedding_generation():
    """Profile embedding generation speed."""
    print("\n📊 Profiling Embedding Generation...")

    try:
        from sentence_transformers import SentenceTransformer

        # Load model (one-time cost)
        _, load_time = measure_time(
            SentenceTransformer,
            "all-MiniLM-L6-v2"
        )

        model = SentenceTransformer("all-MiniLM-L6-v2")

        # Test documents of various sizes
        test_docs = {
            "short": "Led team of 5 engineers.",
            "medium": "Led team of 5 engineers to improve deployment speed by 40% through CI/CD improvements.",
            "long": "Led team of 5 engineers to improve deployment speed by 40% through CI/CD improvements. Implemented automated testing, containerization with Docker, and Kubernetes orchestration. Reduced deployment time from 2 hours to 15 minutes. Mentored junior engineers and conducted code reviews." * 3
        }

        results = {
            "model_load_time_ms": round(load_time, 2),
            "encoding_times": {}
        }

        for doc_type, text in test_docs.items():
            _, encode_time = measure_time(
                model.encode,
                text
            )
            results["encoding_times"][doc_type] = {
                "time_ms": round(encode_time, 2),
                "length": len(text)
            }
            print(f"  {doc_type}: {encode_time:.2f}ms ({len(text)} chars)")

        # Batch encoding
        batch_texts = [test_docs["medium"]] * 10
        _, batch_time = measure_time(
            model.encode,
            batch_texts
        )
        results["batch_10_docs_ms"] = round(batch_time, 2)
        print(f"  Batch (10 docs): {batch_time:.2f}ms ({batch_time/10:.2f}ms per doc)")

        return results

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return {"error": str(e)}


def profile_text_chunking():
    """Profile text chunking performance."""
    print("\n📊 Profiling Text Chunking...")

    try:
        from cover_letter_generator.prepare_data import chunk_text

        # Test documents
        short_text = "This is a short document. " * 10
        medium_text = "This is a medium document with multiple paragraphs.\n\n" * 50
        long_text = "This is a long document with extensive content.\n\n" * 200

        results = {}

        for doc_type, text in [("short", short_text), ("medium", medium_text), ("long", long_text)]:
            chunks, chunk_time = measure_time(
                chunk_text,
                text,
                chunk_size=600,
                overlap=100
            )
            results[doc_type] = {
                "time_ms": round(chunk_time, 2),
                "text_length": len(text),
                "num_chunks": len(chunks),
                "time_per_chunk_ms": round(chunk_time / max(len(chunks), 1), 2)
            }
            print(f"  {doc_type}: {chunk_time:.2f}ms ({len(chunks)} chunks, {chunk_time/max(len(chunks), 1):.2f}ms per chunk)")

        return results

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return {"error": str(e)}


def profile_vector_search():
    """Profile vector database search performance."""
    print("\n📊 Profiling Vector Search...")

    try:
        import chromadb
        from chromadb.config import Settings
        from sentence_transformers import SentenceTransformer
        import tempfile
        import shutil

        # Create temporary ChromaDB
        temp_dir = Path(tempfile.mkdtemp())

        try:
            client = chromadb.Client(Settings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=str(temp_dir)
            ))

            collection = client.create_collection(name="test_profile")

            # Add test documents
            model = SentenceTransformer("all-MiniLM-L6-v2")

            num_docs_list = [10, 50, 100, 500]
            results = {}

            for num_docs in num_docs_list:
                # Generate test documents
                docs = [f"Test document {i} about software engineering and leadership." for i in range(num_docs)]
                embeddings = model.encode(docs).tolist()
                ids = [f"doc_{i}" for i in range(num_docs)]
                metadatas = [{"source": f"test_{i}.pdf"} for i in range(num_docs)]

                # Add to collection
                _, add_time = measure_time(
                    collection.add,
                    documents=docs,
                    embeddings=embeddings,
                    ids=ids,
                    metadatas=metadatas
                )

                # Search
                query = "software engineering leadership team"
                query_embedding = model.encode(query).tolist()

                _, search_time = measure_time(
                    collection.query,
                    query_embeddings=[query_embedding],
                    n_results=10
                )

                results[f"{num_docs}_docs"] = {
                    "add_time_ms": round(add_time, 2),
                    "search_time_ms": round(search_time, 2),
                    "time_per_doc_add_ms": round(add_time / num_docs, 2)
                }

                print(f"  {num_docs} docs: Add={add_time:.2f}ms, Search={search_time:.2f}ms")

                # Clear for next test
                client.delete_collection(name="test_profile")
                collection = client.create_collection(name="test_profile")

            return results

        finally:
            # Cleanup
            shutil.rmtree(temp_dir)

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return {"error": str(e)}


def profile_document_scoring():
    """Profile document scoring performance."""
    print("\n📊 Profiling Document Scoring...")

    try:
        from cover_letter_generator.scoring import score_document
        from cover_letter_generator.analysis import JobAnalysis, JobLevel, JobType, JobRequirement

        # Create test job analysis
        job_analysis = JobAnalysis(
            level=JobLevel.MANAGER,
            job_type=JobType.PRODUCT,
            requirements=[
                JobRequirement(category="leadership", description="Team leadership", priority=1),
                JobRequirement(category="technical", description="System design", priority=2),
            ],
            key_technologies=["Python", "AWS", "Kubernetes"],
            team_size_mentioned=True
        )

        # Test documents
        test_docs = [
            "Led team of 8 engineers, improving deployment by 50% using Python and Kubernetes.",
            "Implemented AWS infrastructure with 99.9% uptime.",
            "Conducted performance reviews and hiring for engineering team.",
            "Built microservices architecture in Python.",
        ]

        metadatas = [
            {"source": "achievements.pdf", "company": "techcorp", "year": "2024"},
            {"source": "resume.pdf", "company": "startup", "year": "2023"},
            {"source": "recommendations.pdf", "company": "bigco", "year": "2022"},
            {"source": "resume.pdf", "company": "unknown", "year": "2020"},
        ]

        distances = [0.3, 0.5, 0.7, 0.9]

        results = {
            "scores": [],
            "total_time_ms": 0,
            "avg_time_per_doc_ms": 0
        }

        total_time = 0
        for doc, metadata, distance in zip(test_docs, metadatas, distances):
            score, score_time = measure_time(
                score_document,
                doc,
                metadata,
                job_analysis,
                distance
            )
            total_time += score_time
            results["scores"].append({
                "score": round(score, 2),
                "time_ms": round(score_time, 4)
            })

        results["total_time_ms"] = round(total_time, 2)
        results["avg_time_per_doc_ms"] = round(total_time / len(test_docs), 4)

        print(f"  Total: {total_time:.2f}ms for {len(test_docs)} docs")
        print(f"  Average: {total_time/len(test_docs):.4f}ms per doc")

        return results

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return {"error": str(e)}


def profile_full_pipeline():
    """Profile the full generation pipeline (requires API keys)."""
    print("\n📊 Profiling Full Pipeline...")
    print("  ⚠️  Note: This requires valid API keys and will make actual API calls")

    # This would profile the full end-to-end generation
    # Skipping for now as it requires API keys and costs money

    return {
        "note": "Full pipeline profiling requires API keys",
        "estimated_steps": {
            "job_analysis": "1-2s (Groq)",
            "vector_retrieval": "0.1s",
            "document_scoring": "0.05s",
            "llm_generation_draft": "8-12s (GPT-4o)",
            "llm_generation_refine": "6-10s (GPT-4o)",
            "pdf_generation": "0.2s",
            "total_estimated": "15-25s"
        }
    }


def main():
    """Main profiling function."""
    parser = argparse.ArgumentParser(description="Profile cover letter generator performance")
    parser.add_argument("--full", action="store_true", help="Run full pipeline profiling (requires API keys)")
    parser.add_argument("--output", type=str, help="Output JSON file for results")

    args = parser.parse_args()

    print("=" * 60)
    print("  Cover Letter Generator - Performance Profiling")
    print("=" * 60)

    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "components": {}
    }

    # Run profiling
    results["components"]["embedding_generation"] = profile_embedding_generation()
    results["components"]["text_chunking"] = profile_text_chunking()
    results["components"]["vector_search"] = profile_vector_search()
    results["components"]["document_scoring"] = profile_document_scoring()

    if args.full:
        results["components"]["full_pipeline"] = profile_full_pipeline()

    # Summary
    print("\n" + "=" * 60)
    print("  Summary")
    print("=" * 60)
    print("\n🎯 Key Metrics:")

    # Extract key metrics
    if "embedding_generation" in results["components"]:
        emb = results["components"]["embedding_generation"]
        if "model_load_time_ms" in emb:
            print(f"  • Model load time: {emb['model_load_time_ms']}ms")
        if "encoding_times" in emb and "medium" in emb["encoding_times"]:
            print(f"  • Single doc encoding: {emb['encoding_times']['medium']['time_ms']}ms")

    if "vector_search" in results["components"]:
        search = results["components"]["vector_search"]
        if "100_docs" in search:
            print(f"  • Vector search (100 docs): {search['100_docs']['search_time_ms']}ms")

    if "document_scoring" in results["components"]:
        scoring = results["components"]["document_scoring"]
        if "avg_time_per_doc_ms" in scoring:
            print(f"  • Document scoring: {scoring['avg_time_per_doc_ms']}ms per doc")

    # Save results
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(json.dumps(results, indent=2))
        print(f"\n💾 Results saved to: {output_path}")

    print("\n✅ Profiling complete!")


if __name__ == "__main__":
    main()
