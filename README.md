# Cover Letter Generator

An AI-powered cover letter generator that uses Retrieval-Augmented Generation (RAG) to create personalized cover letters based on your professional background and job descriptions.

## Features

- **RAG-based Generation**: Uses vector embeddings to retrieve relevant information from your professional documents
- **LinkedIn Integration**: Automatically processes LinkedIn CSV exports (profile, recommendations)
- **JSON Data Support**: Processes JSON files containing professional information
- **Google Drive Sync**: Optional Google Drive storage for data files with automatic sync
- **Iterative Feedback Loop**: Provide feedback and refine cover letters until perfect
- **Customizable System Prompts**: Easily modify the generation behavior and output style
- **Streaming Output**: See the cover letter being generated in real-time
- **Template-based PDF Output**: Uses your custom PDF template with professional formatting
- **Smart Organization**: Automatically creates folders named "{Company} - {Job Title}" for each application
- **iCloud Sync**: Saves to iCloud Documents/Cover Letters for access across all your Apple devices
- **CLI Interface**: Simple command-line interface for quick generation
- **Multi-format Input**: Processes PDFs and CSV files from your professional background

## Tech Stack

- **LLM**: Groq with Llama 3.3 70B Versatile (fast, high-quality, excellent instruction following)
- **Vector Database**: ChromaDB for storing and retrieving document embeddings
- **Embeddings**: Sentence Transformers (all-MiniLM-L6-v2)
- **PDF Processing**: PyPDF2 for extracting text from documents
- **Python**: 3.11+

## Installation

1. Clone the repository:
```bash
cd cover-letter-ai-gen
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the package in development mode:
```bash
pip install -e .
```

4. Set up your environment variables:
```bash
cp .env.example .env
```

5. Edit `.env` and add your configuration:
```bash
GROQ_API_KEY=your_groq_api_key_here
USER_NAME=Your Full Name
```

Get your Groq API key from: https://console.groq.com/keys (free tier available)

The `USER_NAME` will be used for your cover letter filenames (e.g., "John Smith Cover Letter.pdf")

6. **Create your personalized system prompt** (Required):

```bash
cp system_prompt_example.txt system_prompt.txt
```

**Important:** You MUST edit `system_prompt.txt` and replace all instances of `{YOUR NAME}` with your actual name:

- Find: `{YOUR NAME}`
- Replace with: Your actual name (e.g., "John Smith")
- Save the file

The `system_prompt.txt` file controls how your cover letters are generated. It's your personal configuration and is **not tracked in git** (only `system_prompt_example.txt` is version controlled as a template).

**Example:**
```
# Before (in system_prompt.txt)
CONTEXT ABOUT {YOUR NAME} (ONLY SOURCE OF TRUTH):

# After (in your system_prompt.txt)
CONTEXT ABOUT John Smith (ONLY SOURCE OF TRUTH):
```

Use Find & Replace in your editor to update all occurrences at once.

## Usage

### Step 1: Prepare Your Data

**Option A: Use Google Drive (Recommended)**

Store your documents in Google Drive to keep them out of git and sync across devices:

1. Run the setup script:
   ```bash
   ./setup_google_drive.sh
   ```

2. Follow the prompts to move your data to Google Drive

3. See [DATA_SETUP.md](DATA_SETUP.md) for detailed instructions

**Option B: Use Local Storage**

Place your professional documents in the `data/` directory:
- **PDFs**: Resume, achievements document, interview questions/answers
- **LinkedIn CSVs**: Profile.csv, Recommendations_Received.csv
- **JSON files**: Any structured professional data

Then run the data preparation script:

```bash
prepare-data
```

This will:
- Extract text from all PDF files in your data directory (local or Google Drive)
- Split the text into chunks
- Generate embeddings
- Store everything in a ChromaDB vector database

### Step 2: Generate Cover Letters

Run the CLI tool:

```bash
cover-letter-cli
```

The tool will:
1. Prompt you to enter the company name and job title
2. Prompt you to paste the job description (press Ctrl+D when done)
3. Retrieve relevant information from your knowledge base
4. Generate a personalized cover letter with streaming output
5. Allow you to provide feedback for revisions or save the PDF directly

#### Example Usage:

```bash
$ cover-letter-cli

================================================================================
Cover Letter Generator
================================================================================

This tool generates personalized cover letters based on job descriptions.

Instructions:
  1. Enter the company name and job title
  2. Paste the job description (press Ctrl+D when done)
  3. The cover letter will be generated and displayed

Type 'quit' or 'exit' to exit the program.
================================================================================

Initializing cover letter generator...
Loading embedding model...
Connecting to ChromaDB...
✓ Generator initialized successfully

--------------------------------------------------------------------------------
Company Name: Circle
Job Title: Software Engineering Manager

Paste the job description below (press Ctrl+D when done):
[Paste your job description here]
[Press Ctrl+D]

Retrieving relevant context from knowledge base...
Generating cover letter...

--------------------------------------------------------------------------------
[Cover letter will appear here in real-time]
--------------------------------------------------------------------------------

Options:
  (1) Provide feedback for revision
  (2) Save this version
  (3) Start over with new job description
  (4) Exit

What would you like to do? [2]: 1

Describe the changes you'd like to see in the cover letter.
(Be specific: e.g., 'Add more about my leadership experience',
 'Make the tone more formal', 'Emphasize technical skills')

Your feedback (press Ctrl+D when done):
Add more specific metrics about the unit test improvements at J&J
[Press Ctrl+D]

Retrieving relevant context from knowledge base...
Revising cover letter based on your feedback...
--------------------------------------------------------------------------------
[Revised cover letter appears here in real-time]
--------------------------------------------------------------------------------

Options:
  (1) Provide feedback for revision
  (2) Save this version
  (3) Start over with new job description
  (4) Exit

What would you like to do? [2]: 2

✓ Cover letter saved to: ~/Library/Mobile Documents/com~apple~CloudDocs/Documents/Cover Letters/Circle - Software Engineering Manager/{Your Name} Cover Letter.pdf
```

### Iterative Feedback Loop

After generating a cover letter, you can provide feedback to refine it:

**Option 1: Provide feedback for revision**
- Give specific instructions for changes
- Examples:
  - "Add more about my leadership experience at Fitbit"
  - "Make the tone more formal"
  - "Emphasize my technical skills with Java and microservices"
  - "Include specific metrics about the unit test improvements"
- The AI will revise the entire cover letter based on your feedback
- You can iterate multiple times until you're satisfied

**Option 2: Save this version**
- Immediately saves the current version as PDF (no format selection needed)

**Option 3: Start over with new job description**
- Clears the current cover letter and prompts for a new job description

**Option 4: Exit**
- Exits the program

### PDF Output

The tool generates professional PDF cover letters using your custom template with your contact information formatted at the top. When you choose to save a cover letter, it's automatically saved as a PDF in the organized folder structure.

The PDF will include:
- Your name and contact information header
- Professional formatting with proper spacing
- Clickable links for email, LinkedIn, and portfolio
- Current date
- Clean, readable layout optimized for ATS systems

### File Organization

Cover letters are automatically organized into folders by company and job title:

```
~/Library/Mobile Documents/com~apple~CloudDocs/Documents/Cover Letters/
└── Circle - Software Engineering Manager/
    └── {Your Name} Cover Letter.pdf
```

**Folder Structure:**
- Each application gets its own folder: `{Company Name} - {Job Title}`
- Files are consistently named: `{Your Name} Cover Letter.pdf`
- Automatically saved to your iCloud `Documents/Cover Letters` folder
- Syncs across all your Apple devices via iCloud

This organization makes it easy to:
- Find cover letters by company and position
- Keep all application materials together
- Access from any Apple device via iCloud sync

## Customization

### User Name Configuration

Your name is used for cover letter filenames. Set it in `.env`:

```bash
USER_NAME=Your Full Name
```

This will generate files like "{Your Full Name} Cover Letter.pdf"

### Modifying the System Prompt

The system prompt controls how cover letters are generated.

**Initial Setup (Required):**
1. Copy the example template:
   ```bash
   cp system_prompt_example.txt system_prompt.txt
   ```

2. **Replace `{YOUR NAME}` with your actual name:**
   - Open `system_prompt.txt` in your editor
   - Use Find & Replace to change all instances of `{YOUR NAME}` to your actual name
   - Example: `{YOUR NAME}` → `John Smith`
   - This appears in multiple places throughout the file

3. Customize the prompt further if desired (optional)

**Important:**
- `system_prompt.txt` is YOUR personal configuration file
- It is **NOT tracked in git** (already in `.gitignore`)
- Only `system_prompt_example.txt` is version controlled as a template
- Never commit your personal `system_prompt.txt` to version control

**Customization Options:**

Edit `system_prompt.txt` to customize:

- Tone and style
- Structure and format
- What to emphasize
- Length and detail level
- Company-specific context

**Template Variables:**

The prompt uses these variables:

**Automatically filled by the system:**
- `{context}`: Relevant information retrieved from your documents
- `{job_description}`: The job posting you provide
- `{company_name}`: The company you're applying to
- `{job_title}`: The position you're applying for

**Must be manually replaced during setup:**
- `{YOUR NAME}`: Replace with your actual name (e.g., "John Smith") throughout the entire `system_prompt.txt` file

### Adding More Documents

You can add multiple types of professional documents to enhance your cover letters:

**PDF Files**: Place PDFs (resume, achievements, interview prep docs) in your data directory
**LinkedIn CSV Exports**: Export your LinkedIn data and add CSV files to your data directory
  - Profile.csv (professional summary, headline)
  - Recommendations_Received.csv (recommendations from colleagues)
**JSON Files**: Add JSON files containing structured professional information

After adding new files, run `prepare-data` again to update the knowledge base. The system automatically:
- Processes all PDFs, CSVs, and JSON files
- Excludes template folders from data processing
- Updates the vector database with new content

### Adjusting RAG Parameters

In `src/cover_letter_generator/generator.py`, you can modify:

- `DEFAULT_N_RESULTS`: Number of document chunks to retrieve (default: 40)
- `DISTANCE_THRESHOLD`: Maximum distance for relevant results (default: 2.0)
- `TEMPERATURE`: LLM creativity level (default: 0.7)
- `MAX_TOKENS`: Maximum response length (default: 1000)
- `MAX_CONTEXT_CHARS`: Maximum context characters sent to LLM (default: 15000)

### Using a Different LLM

Currently using **Groq with Llama 3.3 70B Versatile** (fast, high-quality, excellent for complex instructions).

To use a different Groq model, change the `MODEL_NAME` constant in `generator.py`:
- `llama-3.3-70b-versatile` (current - best quality and instruction following)
- `llama-3.1-70b-versatile` (previous generation, still excellent)
- `mixtral-8x7b-32768` (faster, larger context window)

To switch to a different LLM provider, you'll need to:
1. Update the imports in `generator.py`
2. Modify the client initialization in `__init__`
3. Update the API calls in `generate_cover_letter_stream` and `revise_cover_letter_stream`
4. Update the `.env` file with the appropriate API key

## Project Structure

```
cover-letter-ai-gen/
├── data/                          # Your professional documents (optional, can use Google Drive)
│   ├── *.pdf                      # PDF files (resume, achievements, etc.)
│   ├── *.csv                      # LinkedIn CSV exports
│   ├── *.json                     # JSON data files
│   ├── template/                  # PDF template folder (excluded from data processing)
│   │   └── Cover Letter_ AI Template.pdf
│   └── chroma_db/                 # Vector database (auto-generated)
├── src/
│   └── cover_letter_generator/
│       ├── __init__.py
│       ├── prepare_data.py        # Data processing (PDFs, CSVs, JSONs)
│       ├── generator.py           # Core RAG + LLM logic
│       ├── cli.py                 # Command-line interface
│       ├── pdf_generator.py       # Basic PDF generation
│       ├── pdf_generator_template.py  # Template-based PDF generation
│       └── utils.py               # Utility functions
├── system_prompt_example.txt      # System prompt template (example)
├── system_prompt.txt              # Your personalized system prompt (not in git)
├── setup_google_drive.sh          # Google Drive setup script
├── DATA_SETUP.md                  # Google Drive setup guide
├── FILE_ORGANIZATION.md           # File organization guide
├── pyproject.toml                 # Project configuration
├── .env                           # Environment variables (not in git)
├── .env.example                   # Example environment variables
└── README.md                      # This file
```

## How It Works

1. **Data Preparation**:
   - PDFs are read and text is extracted
   - LinkedIn CSV files are parsed (profile data, recommendations)
   - JSON files are processed (structured professional data)
   - Text is split into overlapping chunks (1000 chars with 200 char overlap)
   - Each chunk is embedded using Sentence Transformers (all-MiniLM-L6-v2)
   - Embeddings and metadata are stored in ChromaDB vector database
   - Template folder is automatically excluded from processing

2. **Cover Letter Generation**:
   - User provides a job description
   - Job description is embedded
   - Similar chunks are retrieved from ChromaDB (vector similarity search)
   - Retrieved context + job description are formatted into a prompt
   - Groq's Llama 3.3 70B generates the cover letter
   - Results are streamed to the user in real-time

## Troubleshooting

### "ChromaDB not found" error
Run `prepare-data` to create the vector database first.

### "GROQ_API_KEY not found" error
Make sure you've created a `.env` file and added your Groq API key from https://console.groq.com/keys

### Poor quality cover letters
- Add more detailed documents to the `data/` directory
- Modify the system prompt to be more specific
- Adjust the `temperature` parameter for more/less creativity
- Increase `n_results` to retrieve more context

### "No relevant context found"
- Your documents may not contain information relevant to the job
- Try lowering the `distance_threshold` in `generator.py`
- Add more comprehensive documents to your knowledge base

## License

MIT License - feel free to use and modify for your own job search!

## Contributing

This is a personal project, but suggestions and improvements are welcome. Feel free to open issues or submit pull requests.
