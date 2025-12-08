# Architecture Documentation

This document describes the architecture, design decisions, and system components of the AI Cover Letter Generator.

## Table of Contents
- [System Overview](#system-overview)
- [Architecture Diagram](#architecture-diagram)
- [Core Components](#core-components)
- [Data Flow](#data-flow)
- [Design Decisions](#design-decisions)
- [Technology Stack](#technology-stack)
- [Performance Characteristics](#performance-characteristics)

## System Overview

The AI Cover Letter Generator is a **Retrieval-Augmented Generation (RAG)** application that creates personalized cover letters by:
1. Storing user's professional background in a vector database
2. Retrieving relevant context based on job requirements
3. Using LLMs to generate tailored cover letters

### Key Characteristics
- **Architecture Pattern**: RAG (Retrieval-Augmented Generation)
- **Deployment**: CLI application (local execution)
- **Data Storage**: Local ChromaDB vector database
- **LLM Providers**: OpenAI (GPT-4o), Anthropic (Claude), Groq (Llama)

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERACTION                         │
│                     (CLI Interface - cli.py)                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                    DATA PREPARATION LAYER                        │
│                    (prepare_data.py)                             │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│  │   PDF/DOCX   │  │   LinkedIn   │  │     JSON     │            │
│  │   Extractor  │  │   CSV Parser │  │    Parser    │            │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘            │
│         │                  │                  │                  │
│         └──────────────────┼──────────────────┘                  │
│                            ↓                                     │
│                   ┌─────────────────┐                            │
│                   │  Text Chunking  │                            │
│                   │  (Smart Split)  │                            │
│                   └────────┬────────┘                            │
│                            │                                     │
│                            ↓                                     │
│                   ┌─────────────────┐                            │
│                   │   Embedding     │                            │
│                   │   Generation    │                            │
│                   │  (all-MiniLM)   │                            │
│                   └────────┬────────┘                            │
└────────────────────────────┼─────────────────────────────────────┘
                             │
                             ↓
                    ┌─────────────────┐
                    │   ChromaDB      │
                    │ Vector Database │
                    │  (Persistent)   │
                    └────────┬────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                    GENERATION PIPELINE                          │
│                    (generator.py)                               │
│                                                                 │
│  Step 1: Job Analysis                                           │
│  ┌────────────────────────────────────────────────┐             │
│  │  Groq + Llama 4 Maverick                       │             │
│  │  - Extract requirements & priorities           │             │
│  │  - Classify job level (IC/Manager/Director)    │             │
│  │  - Identify key technologies                   │             │
│  └────────────────┬───────────────────────────────┘             │
│                   │                                             │
│  Step 2: Multi-Stage Retrieval                                  │
│  ┌────────────────┴───────────────────────────────┐             │
│  │  Query 1: General job requirements             │             │
│  │  Query 2: High-priority requirements           │             │
│  │  Query 3: Technologies & technical skills      │             │
│  └────────────────┬───────────────────────────────┘             │
│                   │                                             │
│  Step 3: Intelligent Scoring                                    │
│  ┌────────────────┴───────────────────────────────┐             │
│  │  - Embedding similarity (base score)           │             │
│  │  - Source type boost (achievements > resume)   │             │
│  │  - Recency boost (year-based)                  │             │
│  │  - Metrics boost (%, team sizes)               │             │
│  │  - Role-specific boosts (leadership/technical) │             │
│  │  - Technology match boost                      │             │
│  └────────────────┬───────────────────────────────┘             │
│                   │                                             │
│  Step 4: Context Assembly                                       │
│  ┌────────────────┴───────────────────────────────┐             │
│  │  - Top-scored documents (diversity-aware)      │             │
│  │  - Limited to 15,000 chars                     │             │
│  │  - Source diversity (max 3 per source)         │             │
│  └────────────────┬───────────────────────────────┘             │
│                   │                                             │
│  Step 5: Two-Stage LLM Generation                               │
│  ┌────────────────┴───────────────────────────────┐             │
│  │  Stage 1: Draft Generation                     │             │
│  │  ┌──────────────────────────────────────┐      │             │
│  │  │ GPT-4o / Claude Opus 4               │      │             │
│  │  │ Input: System prompt + Context +     │      │             │
│  │  │        Job description               │      │             │
│  │  └──────────────┬───────────────────────┘      │             │
│  │                 │                              │             │
│  │                 ↓                              │             │
│  │  Stage 2: Critique & Refinement                │             │
│  │  ┌──────────────────────────────────────┐      │             │
│  │  │ Same LLM                             │      │             │
│  │  │ Input: Draft + Critique prompt       │      │             │
│  │  └──────────────┬───────────────────────┘      │             │
│  └─────────────────┼──────────────────────────────┘             │
└────────────────────┼─────────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│                    OUTPUT GENERATION                            │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │     PDF      │  │     DOCX     │  │  Signature   │           │
│  │  Generator   │  │  Generator   │  │  Validator   │           │
│  │ (ReportLab)  │  │(python-docx) │  │ (AI Vision)  │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Data Preparation Layer (`prepare_data.py`)

**Purpose:** Process user documents into searchable vector embeddings

**Key Functions:**
- `extract_text_from_pdf()` - Extract text from PDF files
- `extract_text_from_docx()` - Extract text from Word documents
- `chunk_text()` - Split text into semantic chunks
- `process_data_directory()` - Main orchestration function

**Design Decisions:**
- **Chunk Size: 600 characters** (with 100 char overlap)
  - *Rationale:* Balances context vs. precision. Small enough to isolate individual achievements, large enough to maintain context.
- **Paragraph-Aware Splitting**
  - *Rationale:* Preserves semantic boundaries, avoids mid-sentence splits
- **Metadata Injection**
  - *Rationale:* Enriches chunks with source, company, year for better retrieval

**Processing Flow:**
```
PDF/DOCX → Text Extraction → Metadata Extraction (filename parsing)
→ Chunking (paragraph-aware) → Embedding (384-dim vectors)
→ ChromaDB Storage
```

### 2. Vector Database (`chromadb`)

**Configuration:**
- **Embedding Model:** `all-MiniLM-L6-v2` (384 dimensions)
- **Similarity Metric:** Cosine distance
- **Storage:** Persistent local storage in `chroma_db/`

**Why ChromaDB?**
- ✅ Lightweight, no server required
- ✅ Persistent storage
- ✅ Built-in embedding support
- ✅ Fast for small-to-medium datasets (<10k documents)

**Metadata Schema:**
```python
{
    "source": str,        # File path
    "type": str,          # pdf, docx, csv, json
    "chunk_index": int,   # Position in original document
    "total_chunks": int,  # Total chunks from document
    "company": str,       # Extracted company name
    "year": str          # Extracted year
}
```

### 3. Job Analysis (`analysis.py`)

**Purpose:** Extract structured requirements from job postings

**LLM Used:** Groq + Llama 4 Maverick (fast, free)

**Output Schema:**
```python
@dataclass
class JobAnalysis:
    level: JobLevel          # IC_SENIOR, MANAGER, SENIOR_MANAGER, DIRECTOR_VP
    job_type: JobType        # STARTUP, ENTERPRISE, PRODUCT, INFRASTRUCTURE
    requirements: List[JobRequirement]
    key_technologies: List[str]
    team_size_mentioned: bool
```

**Why Groq?**
- ✅ Fast inference (<2 seconds)
- ✅ Free tier generous
- ✅ Good structured output

### 4. Intelligent Scoring (`scoring.py`)

**Purpose:** Rank retrieved documents by relevance

**Scoring Formula:**
```python
total_score = (
    base_similarity_score +           # Embedding distance (0-20)
    source_boost +                    # Achievements: +15, Resume: +10
    recency_boost +                   # Last 2 years: +12, 3-5 years: +8
    metrics_boost +                   # Percentages: +10, Team sizes: +8
    role_specific_boost +             # Leadership/Technical terms: +8-12
    technology_match_boost +          # Per matching tech: +7
    process_improvement_boost         # Optimization terms: +6
)
```

**Why Multi-Factor Scoring?**
- Pure embedding similarity misses important signals
- Recent work is more relevant
- Metrics provide concrete proof
- Role-specific language matters (manager vs IC)

### 5. Cover Letter Generator (`generator.py`)

**Purpose:** Orchestrate RAG pipeline and LLM generation

**LLM Options:**
1. **GPT-4o** (default)
   - Cost: ~$0.01-0.02 per letter
   - Quality: Excellent
   - Speed: ~10 seconds

2. **Claude Opus 4**
   - Cost: ~$0.10-0.15 per letter
   - Quality: Maximum reasoning
   - Speed: ~15 seconds

**Generation Strategy:**
1. **Stage 1: Draft**
   - Input: System prompt + Retrieved context + Job description
   - Temperature: 0.7 (balanced creativity)
   - Max tokens: 1500

2. **Stage 2: Critique & Refine**
   - Input: Draft + Critique prompt
   - Purpose: Check tone, leadership emphasis, specificity
   - Temperature: 0.5 (more focused)

**Why Two-Stage?**
- Single-stage often misses subtle requirements
- Critique stage improves tone and emphasis
- Self-reflection improves quality

### 6. Meta-Learning System

**Components:**
- `feedback_tracker.py` - Track user feedback patterns
- `system_improver.py` - Suggest prompt improvements

**Workflow:**
```
User Feedback → Categorize (leadership/technical/tone/length)
→ Detect Patterns (threshold: 3 occurrences)
→ Generate Improvement Suggestions
→ Show Diff → Apply if Approved
```

**Why Meta-Learning?**
- System improves based on actual usage
- Reduces repetitive feedback
- Personalizes to user's style over time

### 7. Output Generation

**PDF Generation (`pdf_generator_template.py`):**
- Library: ReportLab
- Template: Professional business letter format
- Features: Contact header, proper margins, page breaks

**DOCX Generation (`docx_generator.py`):**
- Library: python-docx
- Features: Standard formatting, easy editing

**Signature Validation (`signature_validator.py`):**
- AI Vision: Groq + Llama 3.2 Vision
- Purpose: Detect cut-off signatures on PDFs
- Action: Automatically prompt for shorter version

## Data Flow

### 1. Initial Setup Flow
```
User Documents → Data Preparation → Embeddings → ChromaDB
                                                      ↓
                                              [Persistent Storage]
```

### 2. Cover Letter Generation Flow
```
Job Posting URL/Text
    ↓
Job Parser (Playwright) → Clean Job Description
    ↓
Job Analyzer (Groq) → JobAnalysis
    ↓
Multi-Query Retrieval → Scored Documents
    ↓
Context Assembly (Top N, Diversity-Aware)
    ↓
LLM Generation (2-Stage) → Draft Cover Letter
    ↓
User Feedback Loop → Revision (optional, iterative)
    ↓
PDF + DOCX Generation → Signature Validation
    ↓
Saved to Output Directory
```

### 3. Feedback Loop Flow
```
User Provides Feedback → Categorize
    ↓
Track in feedback_history.json
    ↓
Pattern Detection (3+ similar feedback)
    ↓
Generate System Prompt Improvement
    ↓
Show Diff → User Approval → Update Prompt
    ↓
Clear Feedback History for Category
```

## Design Decisions

### Why RAG Instead of Fine-Tuning?

| Aspect | RAG | Fine-Tuning |
|--------|-----|-------------|
| **Data Requirements** | Works with small datasets | Requires thousands of examples |
| **Update Speed** | Instant (add new docs) | Hours/days to retrain |
| **Cost** | Low ($0.01/letter) | High (training costs) |
| **Transparency** | Can see what was retrieved | Black box |
| **Maintenance** | Easy | Complex |

**Decision:** RAG is superior for this use case.

### Why Local Vector DB vs. Cloud?

**Options Considered:**
- Pinecone (cloud vector DB)
- Weaviate (cloud/self-hosted)
- ChromaDB (local)

**Decision:** ChromaDB local
- ✅ No API costs
- ✅ Data privacy (documents stay local)
- ✅ Fast for small datasets
- ✅ No internet required after setup

### Why Two-Stage Generation?

**Single-Stage Issues:**
- Often too generic
- Misses tone requirements
- Inconsistent quality

**Two-Stage Benefits:**
- +15% quality improvement (subjective testing)
- Better alignment with job requirements
- Catches formatting issues

**Cost:** +50% API cost, but worth it for quality

### Why Multiple LLM Providers?

**Purpose:** Different use cases, different models

| Model | Use Case | Why |
|-------|----------|-----|
| Groq (Llama 4) | Job analysis | Fast, free, structured output |
| Groq (Llama 3.2 Vision) | Signature validation | Fast, vision capable |
| GPT-4o | Cover letter gen (default) | Best quality/cost ratio |
| Claude Opus 4 | Premium generation | Maximum reasoning |

**Decision:** Use the right tool for each job.

## Technology Stack

### Core Dependencies

**Vector Search & ML:**
- `chromadb` - Vector database
- `sentence-transformers` - Embeddings
- `torch` - ML backend

**LLM Providers:**
- `openai` - GPT-4o
- `anthropic` - Claude
- `groq` - Llama models (fast inference)

**Document Processing:**
- `pypdf` - PDF reading
- `python-docx` - DOCX reading/writing
- `reportlab` - PDF generation
- `pdf2image` + `Pillow` - Image processing for validation

**Web Scraping:**
- `playwright` - JavaScript-enabled scraping
- `beautifulsoup4` - HTML parsing
- `requests` - HTTP requests

**CLI & UX:**
- `prompt_toolkit` - Enhanced CLI input
- `pyperclip` - Cross-platform clipboard

**Configuration:**
- `python-dotenv` - Environment variables
- `pydantic` - Data validation

### Development Dependencies

**Testing:**
- `pytest` - Test framework
- `pytest-cov` - Coverage reporting
- `pytest-asyncio` - Async testing

**Code Quality:**
- `black` - Code formatting
- `ruff` - Fast linting
- `mypy` - Type checking
- `bandit` - Security scanning

**Workflow:**
- `pre-commit` - Git hooks

## Performance Characteristics

### Latency Breakdown

**Initial Setup (prepare-data):**
- Process 50 documents: ~30-60 seconds
- Embedding generation: ~0.5s per document
- One-time cost

**Cover Letter Generation:**
```
Job Analysis:        1-2s   (Groq, fast)
Vector Retrieval:    0.1s   (local, <1ms per query)
Document Scoring:    0.05s  (pure Python)
LLM Generation:      8-12s  (GPT-4o) or 12-18s (Claude)
PDF Generation:      0.2s   (ReportLab)
Signature Validation: 2-3s  (Vision model)
─────────────────────────────
Total:               12-20s per letter
```

### Throughput

**Single-threaded:**
- ~3-5 cover letters per minute
- Limited by LLM API rate limits

**Batch Generation:**
- Not currently supported
- Could add with async/concurrent requests

### Resource Usage

**Memory:**
- Embedding model: ~500MB (loaded once)
- ChromaDB: ~50-100MB (for typical dataset)
- Peak usage: ~1GB

**Disk:**
- ChromaDB: ~10-50MB (depends on document count)
- Embeddings: ~1KB per chunk
- Total: <100MB for typical usage

**Network:**
- LLM API calls: ~5-20KB per request
- Job URL parsing: ~50-500KB per page

### Scalability Limits

**Current Limitations:**
- Document count: Works well up to ~10,000 documents
- Concurrent users: CLI is single-user
- Vector search: Linear scan (acceptable for small datasets)

**If Scaling Needed:**
1. Switch to cloud vector DB (Pinecone, Weaviate)
2. Add caching layer (Redis)
3. Implement batch processing
4. Move to web service architecture

## Error Handling Strategy

**Graceful Degradation:**
- Missing optional dependencies → Feature disabled with warning
- API failures → Retry with exponential backoff
- Empty search results → Fallback to generic generation

**User-Facing Errors:**
- Clear, actionable error messages
- Validation on startup (API keys, required files)
- Helpful suggestions in error messages

## Security Considerations

**Data Privacy:**
- All documents stored locally
- No data sent to third parties (except LLM APIs for generation)
- API keys in `.env` (gitignored)

**API Key Management:**
- Never hardcoded
- Read from environment variables
- Validated on startup

**Input Validation:**
- User feedback sanitized (prevent prompt injection)
- File paths validated
- URL parsing sandboxed

## Future Architecture Considerations

**Potential Improvements:**
1. **Web Interface** - Flask/FastAPI + React frontend
2. **Database** - PostgreSQL for job tracking, application history
3. **Caching** - Redis for frequently accessed data
4. **Async** - Concurrent LLM calls for faster batch processing
5. **Monitoring** - Prometheus metrics, Grafana dashboards

**Backward Compatibility:**
- CLI will remain primary interface
- New features should degrade gracefully
- Maintain simple deployment (single command)

---

*Last Updated: 2024*
*Document Version: 1.0*
