# Cover Letter Generator

[![CI](https://github.com/YOUR_USERNAME/ai-cover-letter-generator/workflows/CI/badge.svg)](https://github.com/YOUR_USERNAME/ai-cover-letter-generator/actions)
[![codecov](https://codecov.io/gh/YOUR_USERNAME/ai-cover-letter-generator/branch/main/graph/badge.svg)](https://codecov.io/gh/YOUR_USERNAME/ai-cover-letter-generator)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An AI-powered cover letter generator that uses Retrieval-Augmented Generation (RAG) to create personalized cover letters based on your professional background and job descriptions.

## Features

- **GPT-4o Generation**: High-quality, cost-effective generation (default)
- **Claude Opus Support**: Option to use Claude Opus for maximum reasoning power
- **RAG-based Generation**: Uses vector embeddings to retrieve relevant information from your professional documents
- **LinkedIn Integration**: Automatically processes LinkedIn CSV exports (profile, recommendations)
- **JSON Data Support**: Processes JSON files containing professional information
- **Google Drive Sync**: Optional Google Drive storage for data files with automatic sync
- **Iterative Feedback Loop**: Provide feedback and refine cover letters until perfect
- **Meta-Learning System**: Detects feedback patterns and suggests permanent improvements to the system prompt
- **Customizable System Prompts**: Easily modify the generation behavior and output style
- **Template-based Output**: Generates both PDF and DOCX files with professional formatting
- **Smart Organization**: Automatically creates folders named "{Company} - {Job Title} - {Date}" for each application
- **iCloud Sync**: Saves to iCloud Documents/Cover Letters for access across all your Apple devices
- **CLI Interface**: Simple command-line interface for quick generation
- **Multi-format Input**: Processes PDFs and CSV files from your professional background
- **URL Job Parsing**: Paste a job posting URL and automatically extract company, title, and description using AI
- **AI Signature Validation**: Claude vision-powered detection of cut-off signatures with automatic regeneration

## Tech Stack

- **Primary LLM**: GPT-4o (default) or Claude Opus 4
- **Signature Validation**: Llama 3.2 Vision (via Groq)
- **Job Analysis**: Groq with Llama 4 Maverick (fast, free job requirement extraction)
- **Vector Database**: ChromaDB for storing and retrieving document embeddings
- **Embeddings**: Sentence Transformers (all-MiniLM-L6-v2)
- **PDF/DOCX Generation**: ReportLab and python-docx with custom templates
- **Web Scraping**: BeautifulSoup4, Requests, and Playwright for job posting URLs
- **Signature Validation**: Claude AI Vision for detecting cut-off signatures
- **Python**: 3.11+

## Installation

1. Clone the repository:
```bash
cd cover-letter-ai-gen
```

2. **(Optional) Install system dependencies for signature validation:**

If you want to use the AI-powered signature validation feature, install poppler:

**macOS:**
```bash
brew install poppler
```

**Ubuntu/Debian:**
```bash
sudo apt-get install poppler-utils
```

**Windows:**
Download from: http://blog.alivate.com.au/poppler-windows/

> **Note:** Signature validation is optional. If poppler or the Anthropic API key is not available, the tool will skip validation and still save PDFs normally.

3. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

> **Note:** Use `python3` if `python` doesn't work on your system.

4. Verify the virtual environment is activated:
```bash
which pip  # Should show: /path/to/your/project/venv/bin/pip
```

5. Install the package in development mode:
```bash
pip install -e .
```

6. Set up your environment variables:
```bash
cp .env.example .env
```

7. Edit `.env` and add your configuration:
```bash
# Required
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GROQ_API_KEY=your_groq_api_key_here
USER_NAME=Your Full Name
```

**Required API Keys:**
- **OPENAI_API_KEY**: Get from https://platform.openai.com/api-keys (for GPT-4o generation)
- **GROQ_API_KEY**: Get from https://console.groq.com/keys (free tier available, used for job analysis and signature validation)
- **ANTHROPIC_API_KEY**: Get from https://console.anthropic.com/ (Optional - only for Claude Opus generation)
- **USER_NAME**: Your full name used for cover letter filenames (e.g., "John Smith Cover Letter.pdf")

8. **Create your personalized system prompt** (Required):

```bash
cp prompts/system_prompt.txt.example prompts/system_prompt.txt
```

**Important:** You MUST edit `system_prompt.txt` and replace all instances of `{YOUR NAME}` with your actual name:

- Find: `{YOUR NAME}`
- Replace with: Your actual name (e.g., "John Smith")
- Save the file

The `prompts/system_prompt.txt` file controls how your cover letters are generated. It's your personal configuration and is **not tracked in git** (only `prompts/system_prompt.txt.example` is version controlled as a template).

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
1. Ask if you want to provide a URL or enter details manually
2. If URL: Automatically extract company name, job title, and description from the webpage
3. If manual: Prompt for company name, job title, and job description
4. Retrieve relevant information from your knowledge base
5. Generate a personalized cover letter with streaming output
6. Allow you to provide feedback for revisions or save the PDF directly

#### Example Usage:

```bash
$ cover-letter-cli

================================================================================
Cover Letter Generator
================================================================================

This tool generates personalized cover letters based on job descriptions.

Instructions:
  1. Paste a job posting URL OR enter details manually
  2. The cover letter will be generated and displayed
  3. Provide feedback or save the final version

Type 'quit' or 'exit' to exit the program.
================================================================================

================================================================================
Which AI model would you like to use?
================================================================================

Available models:
  (1) GPT-4o [Default]
      - Best quality, cost-effective
      - Cost: ~$0.01-0.02 per cover letter
  (2) Claude Opus 4
      - Maximum reasoning power
      - Cost: ~$0.10-0.15 per cover letter (expensive)

Choice [1]: 1

Initializing cover letter generator...
Loading embedding model...
Connecting to ChromaDB...
✓ Generator initialized successfully

--------------------------------------------------------------------------------
How would you like to provide the job posting?
  (1) Paste a URL to the job posting
  (2) Enter details manually

Choice [1]: 1

Job Posting URL: https://jobs.lever.co/circle/abc123

Fetching job posting from URL...
Extracting text from webpage...
Analyzing job posting with AI (extracted 5234 characters)...
✓ Successfully parsed job posting:
  Company: Circle
  Title: Software Engineering Manager
  Description length: 3421 characters

================================================================================
EXTRACTED JOB DETAILS
================================================================================
Company: Circle
Title: Software Engineering Manager
Description length: 3421 characters

Are these details correct? (y/n) [y]: y

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
Add more about my leadership experience
[Press Ctrl+D]

Analyzing your feedback to make it more specific and actionable...

================================================================================
FEEDBACK ENHANCEMENT SUGGESTION
================================================================================

Your original feedback:
  "Add more about my leadership experience"

Enhanced suggestion:
  "Add specific examples of your leadership at Johnson & Johnson, particularly
  how you led the QA team and mentored engineers. Include the metric about
  improving unit test coverage from 30% to 95% and connect it to the job's
  requirement for technical leadership."

Which feedback would you like to use?
  (1) Use enhanced suggestion (recommended)
  (2) Use my original feedback
  (3) Cancel revision

Choice [1]: 1

Using enhanced feedback...
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

### URL Job Parsing

The tool can automatically extract job details from most job posting URLs:

**Supported platforms:**
- Lever (jobs.lever.co)
- Greenhouse (boards.greenhouse.io)
- LinkedIn Jobs
- Indeed
- Company career pages
- Most other job boards

**How it works:**
1. Paste the URL to any job posting
2. The tool fetches the webpage content
3. AI extracts the company name, job title, and full description
4. Review the extracted details with the **full description displayed**
5. Choose to:
   - Use as-is
   - Edit individual fields (company, title, or description)
   - View the complete description
   - Switch to manual entry

**Benefits:**
- Saves time - no need to copy/paste job descriptions
- Ensures complete context - captures the full posting
- Reduces errors - no manual transcription mistakes
- Works with most job boards automatically
- Granular control - edit individual fields without starting over
- Transparent - see the full description before accepting

**Example:**
```
Job Posting URL: https://jobs.lever.co/company/position-id

Fetching job posting from URL...
✓ Successfully parsed job posting:
  Company: Acme Corp
  Title: Senior Software Engineer
  Description length: 2847 characters

================================================================================
EXTRACTED JOB DETAILS
================================================================================

Company Name: Acme Corp
Job Title: Senior Software Engineer

Job Description (2847 characters):
--------------------------------------------------------------------------------
We are looking for a Senior Software Engineer to join our platform team...
[Full description shown here - first 2000 characters if longer]
--------------------------------------------------------------------------------

What would you like to do?
  (1) Use these details as-is
  (2) Edit company name
  (3) Edit job title
  (4) Edit description
  (5) View full description
  (6) Start over - enter all details manually

Choice [1]: 1

✓ Using extracted details
```

**Editing fields:**
- **Option 2-4**: Edit individual fields if extraction wasn't perfect
- **Option 5**: View the complete description (useful for long postings)
- **Option 6**: Switch to manual entry if extraction completely failed

**Example - Editing a field:**
```
Choice [1]: 2

Current Company Name: Acme Corp
Enter new Company Name (or press Enter to keep current): Acme Corporation

✓ Updated company name

What would you like to do?
  (1) Use these details as-is
  ...
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

### AI Feedback Enhancement

When you provide feedback for a revision, the AI automatically analyzes and enhances your feedback to make it more specific and actionable:

**How it works:**
1. You provide feedback (e.g., "Add more about leadership")
2. AI analyzes your feedback, the current cover letter, and the job description
3. AI suggests an enhanced version with specific, actionable improvements
4. You choose which version to use:
   - Enhanced suggestion (recommended) - More specific and actionable
   - Your original feedback - Stick with what you said
   - Cancel revision - Go back without changes

**Example:**

```
Your feedback: Add more about my leadership experience

Analyzing your feedback to make it more specific and actionable...

================================================================================
FEEDBACK ENHANCEMENT SUGGESTION
================================================================================

Your original feedback:
  "Add more about my leadership experience"

Enhanced suggestion:
  "Add specific examples of your leadership experience, particularly your work
  leading the Quality Assurance team at Johnson & Johnson. Emphasize how you
  improved unit test coverage from 30% to 95% and mentored junior engineers.
  Connect these experiences to the job's requirement for team leadership and
  technical mentorship."

Which feedback would you like to use?
  (1) Use enhanced suggestion (recommended)
  (2) Use my original feedback
  (3) Cancel revision

Choice [1]: 1

Using enhanced feedback...
Revising cover letter based on your feedback...
```

**Benefits:**
- **More specific revisions**: Turns vague feedback into concrete actions
- **Better results**: Enhanced feedback leads to more targeted improvements
- **Saves time**: No need to think through every detail yourself
- **Context-aware**: Considers both the job requirements and your background
- **You're in control**: Always option to use your original feedback

### Meta-Learning System

The tool learns from your feedback patterns and suggests permanent improvements to the system prompt:

**How it works:**
1. Every time you provide feedback, it's tracked and categorized (e.g., "leadership", "technical_depth", "tone")
2. When you give similar feedback 3+ times, the system detects the pattern
3. AI analyzes the pattern and suggests a permanent modification to `system_prompt.txt`
4. You review the proposed change (with diff)
5. If approved, the system prompt is updated automatically
6. Future cover letters automatically incorporate this improvement

**Example Workflow:**

```
[After providing feedback about leadership for the 3rd time]

================================================================================
💡 SYSTEM IMPROVEMENT SUGGESTION
================================================================================

I've noticed you've given similar feedback 3 times:
Category: Leadership

Examples:
  - "Add more about my leadership experience"
  - "Emphasize leadership and team management"
  - "Include leadership examples from J&J"

Analyzing patterns to suggest a permanent system improvement...

================================================================================
PROPOSED SYSTEM PROMPT UPDATE
================================================================================

Explanation: Add explicit instruction to prominently feature leadership experience
in the opening paragraphs with specific examples and metrics.

This would modify your system_prompt.txt file to automatically
address this feedback pattern in future cover letters.

Changes that would be made:
--------------------------------------------------------------------------------
+
+# AUTO-GENERATED IMPROVEMENT (based on user feedback patterns)
+When generating cover letters, prominently feature leadership experience and
+team management skills in the opening paragraphs. Include specific examples
+of leading teams, mentoring others, and measurable impacts on team performance.
+Reference concrete metrics when available (e.g., team size, productivity gains,
+quality improvements).
+
--------------------------------------------------------------------------------

Would you like to apply this permanent improvement?
  (y) Yes, update the system prompt
  (n) No, keep asking me each time
  (v) View full diff

Choice [n]: y

✓ System prompt updated successfully!
✓ Future cover letters will automatically incorporate this improvement.
✓ Cleared 3 feedback entries for 'leadership' category.
```

**Benefits:**
- 🎓 **System learns from you**: Gets better over time based on your preferences
- ⚡ **Permanent improvements**: No need to repeat the same feedback
- 🔍 **Transparent**: Shows exactly what will change before applying
- 🎛️ **You're in control**: Review and approve all changes
- 💾 **Safe**: Creates backups before modifying files
- 📊 **Pattern detection**: Identifies trends across multiple sessions

**Categories tracked:**
- **Leadership**: Team management, mentoring, delegation
- **Technical depth**: Technologies, architectures, coding skills
- **Tone**: Formality, professionalism, voice
- **Length**: Conciseness, brevity
- **Specificity**: Examples, metrics, details

**Files modified:**
- `system_prompt.txt` - Your personalized system prompt
- `.feedback_history.json` - Tracks feedback patterns (automatically managed)
- `system_prompt.txt.backup` - Backup created before each change

### PDF Output

The tool generates professional PDF cover letters using your custom template with your contact information formatted at the top. When you choose to save a cover letter, it's automatically saved as a PDF in the organized folder structure.

The PDF will include:
- Your name and contact information header
- Professional formatting with proper spacing
- Clickable links for email, LinkedIn, and portfolio
- Current date
- Clean, readable layout optimized for ATS systems

### Signature Validation (Optional)

If you have the Anthropic API key configured and poppler installed, the tool automatically validates that your signature is visible and not cut off in the PDF:

**How it works:**
1. After saving the PDF, the tool converts it to an image
2. Claude's vision AI analyzes the image to check if the signature is fully visible
3. If the signature appears cut off, you'll see a warning with options:
   - Automatically regenerate a shorter version
   - Keep the current version

**Example workflow:**
```
✓ Cover letter saved to: ~/Documents/Cover Letters/...

Validating signature visibility...
⚠ Warning: The signature appears to be cut off or not fully visible.
Details: Text is too long and signature is partially cut off at bottom

Would you like to regenerate a shorter version?
  (1) Yes, regenerate with shorter content
  (2) No, keep the current version

Choice [1]: 1

Regenerating with request to shorten content...
[Shortened cover letter appears here]
✓ Signature validation passed
```

**Setup:**
- Install poppler: `brew install poppler` (macOS) or `sudo apt-get install poppler-utils` (Linux)
- Set `ANTHROPIC_API_KEY` in your `.env` file
- If either is missing, validation is gracefully skipped

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
   cp prompts/system_prompt.txt.example prompts/system_prompt.txt
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
- Only `system_prompt.txt.example` is version controlled as a template
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

The tool supports **GPT-4o** (default) and **Claude Opus 4**.

To switch models, simply select your preference when running the CLI:
1. **GPT-4o**: Best balance of quality and cost (~$0.015/letter)
2. **Claude Opus 4**: Maximum reasoning capability (~$0.10/letter)

To add other models, you would need to modify `src/cover_letter_generator/generator.py` and `cli.py`.

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
│       ├── ui_components.py       # Reusable UI components for CLI
│       ├── pdf_generator.py       # Basic PDF generation
│       ├── pdf_generator_template.py  # Template-based PDF generation
│       ├── signature_validator.py # AI-powered signature validation
│       ├── job_parser.py          # URL job posting parser
│       ├── feedback_tracker.py    # Feedback pattern tracking
│       ├── system_improver.py     # System prompt improvement suggester
│       └── utils.py               # Utility functions
├── prompts/                       # Prompt templates and configuration
│   ├── system_prompt.txt.example      # System prompt template (example)
│   └── system_prompt.txt              # Your personalized system prompt (not in git)
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

## Advanced Configuration

### Custom Prompts
You can customize the behavior of the generator by creating local prompt files in the `prompts/` directory. These files are gitignored to protect your personal strategies.

- **`prompts/critique_prompt.txt`**: Customize the refinement instructions used in the second stage of generation.

### Context Preprocessing Hook (Advanced)
For advanced users who want to transform retrieved context before it's used in the cover letter, you can create a `managerial_prompt.txt` file in the project root. This file should contain a prompt template with a `{context}` placeholder.

**Use Case:** Transform technical achievements into management-focused language, or reframe context for specific types of roles.

**Example `managerial_prompt.txt`:**
```
Transform the following technical achievements into management-focused language,
emphasizing leadership impact, team growth, and strategic value:

{context}

Provide the transformed version maintaining all facts but reframing for a management audience.
```

**Note:** This is an optional, advanced feature. The context preprocessing adds a small additional cost (~$0.01 per letter) and processing time. If the file doesn't exist, the original context is used directly.

### Logging Configuration
The application includes a comprehensive logging system for debugging and monitoring. Configure logging via environment variables:

```bash
# In your .env file
LOG_LEVEL=INFO          # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE=/path/to/app.log   # Optional: write logs to file
VERBOSE=true            # Set to true for detailed debug output
```

**Log Levels:**
- `DEBUG`: Detailed information for debugging
- `INFO`: General informational messages (default)
- `WARNING`: Warning messages for potential issues
- `ERROR`: Error messages for failures
- `CRITICAL`: Critical errors that may stop execution

**Example usage:**
```bash
# Enable debug logging to file
export LOG_LEVEL=DEBUG
export LOG_FILE=~/.cover-letter-generator/debug.log

# Run with verbose output
export VERBOSE=true
cover-letter-cli
```

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

### Signature validation not working
**Symptoms:** Validation is skipped or you see warnings about missing dependencies

**Solutions:**
- Install poppler: `brew install poppler` (macOS) or `sudo apt-get install poppler-utils` (Linux)
- Set `GROQ_API_KEY` in your `.env` file (get from https://console.groq.com/keys)
- Verify poppler is installed: `which pdftoppm` should show a path
- The tool will work fine without signature validation - it's an optional feature

### URL parsing not working
**Symptoms:** "Could not parse job posting from URL" or incorrect details extracted

**Solutions:**
- Some job boards require login or have anti-scraping measures
- Try copying the URL from an incognito/private browser window
- As a fallback, choose option (2) to enter details manually
- The tool will prompt you to enter manually if URL parsing fails
- Works best with: Lever, Greenhouse, company career pages, LinkedIn (public postings)

### pip not working in virtual environment
**Symptoms:** `pip not found` or commands installing to system Python instead of venv

**Solution:**
```bash
# Remove broken venv
rm -rf venv

# Create new venv
python3 -m venv venv

# Activate it
source venv/bin/activate

# Verify it's working (should show path inside your project)
which pip

# Reinstall dependencies
pip install -e .
```

## License

MIT License - feel free to use and modify for your own job search!

## Contributing

This is a personal project, but suggestions and improvements are welcome. Feel free to open issues or submit pull requests.
