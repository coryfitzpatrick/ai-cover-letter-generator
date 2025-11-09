# Data Directory Setup Guide

This guide explains how to store your personal documents (resume, achievements, etc.) in Google Drive instead of the local `data/` folder.

## Benefits of Using Google Drive

- **Privacy**: Keep personal documents out of git repositories
- **Backup**: Automatic cloud backup
- **Sync**: Access from multiple devices
- **Organization**: Keep all your professional documents in one place

## Setup Instructions

### Step 1: Install Google Drive

If you haven't already, install Google Drive for Desktop:
- Download from: https://www.google.com/drive/download/
- Sign in with your Google account ({youremail}@gmail.com)

### Step 2: Create Your Data Folder in Google Drive

1. Open Google Drive on your computer
2. Navigate to "My Drive"
3. Create a folder called `AI Data` (or use your existing one)
4. Inside `AI Data`, place your files:

**Files** (place directly in `AI Data/`):
- Resume (e.g., `Cory Fitzpatrick Resume.pdf`)
- Achievements document (e.g., `Achievements.pdf` or `Achievements.docx`)
- Interview questions/answers (e.g., `Interview_Questions_and_Answers.pdf`)
- Google Docs (exported as `.docx` files)
- Any other professional documents
  - LinkedIn_Profile.csv
  - Recommendations_Received.csv
  - Recommendations_Given.csv
  - Website_Data.json
```

The system will automatically:
- Extract text from all PDF files
- Extract text from all DOCX files (Word documents and exported Google Docs)
- Process LinkedIn_Profile.csv for your professional summary and headline
- Process Recommendations_Received.csv for testimonials from colleagues
- Process Website_Data.json for relevant info

**Note:** To export Google Docs as DOCX:
1. Open the Google Doc in Google Drive
2. Click File → Download → Microsoft Word (.docx)
3. Save the .docx file in your `AI Data` folder

### Step 3: Find Your Google Drive Path

Google Drive is typically located at:
- **macOS**: `~/Library/CloudStorage/GoogleDrive-{youremail}@gmail.com/My Drive/`
- **Windows**: `G:\My Drive\` or `C:\Users\{username}\Google Drive\`

For your setup, it should be:
```
~/Library/CloudStorage/GoogleDrive-{youremail}@gmail.com/My Drive/AI Data
```

To verify, open Terminal and run:
```bash
ls ~/Library/CloudStorage/
```

Look for a folder starting with `GoogleDrive-`.

### Step 4: Configure the Application

1. Open your `.env` file in the project root:
   ```bash
   nano .env
   ```

2. Add the DATA_DIR line with your Google Drive path:
   ```bash
   # Your Groq API key
   GROQ_API_KEY=your_api_key_here

   # Point to Google Drive
   DATA_DIR=~/Library/CloudStorage/GoogleDrive-{youremail}@gmail.com/My Drive/AI Data
   ```

3. Save and close the file (Ctrl+X, then Y, then Enter)

### Step 5: Move Your Existing Data

Move your current data to Google Drive:

```bash
# Create the Google Drive folder if it doesn't exist
mkdir -p ~/Library/CloudStorage/GoogleDrive-{youremail}@gmail.com/My\ Drive/AI\ Data

# Copy your PDFs to Google Drive
cp /Users/cory/Projects/cover-letter-ai-gen/data/*.pdf ~/Library/CloudStorage/GoogleDrive-{youremail}@gmail.com/My\ Drive/AI\ Data/

# Copy LinkedIn data if you have it
cp -r /Users/cory/Projects/cover-letter-ai-gen/data/linkedin-export-* ~/Library/CloudStorage/GoogleDrive-{youremail}@gmail.com/My\ Drive/AI\ Data/
```

**Note**: Don't move the `chroma_db` folder yet! See step 6.

### Step 6: Rebuild the ChromaDB Database

After moving your files, rebuild the database:

```bash
# Activate your virtual environment
source venv/bin/activate

# Run the data preparation script
prepare-data
```

This will:
- Read files from your Google Drive location
- Create a new `chroma_db` folder in Google Drive
- Generate embeddings from your documents

### Step 7: Test the Setup

Generate a test cover letter to verify everything works:

```bash
cover-letter-cli
```

## Updating Your Documents

Whenever you update documents in Google Drive:

1. Save the new/updated file (PDF or DOCX) to your Google Drive `AI Data` folder
   - For Google Docs: File → Download → Microsoft Word (.docx)
2. Run `prepare-data` to rebuild the database
3. The new information will be available for cover letter generation

## Troubleshooting

### "ChromaDB not found" Error

Make sure you've run `prepare-data` after setting up DATA_DIR:
```bash
source venv/bin/activate
prepare-data
```

### Google Drive Path Not Found

Check if Google Drive is running and synced:
1. Look for the Google Drive icon in your menu bar (macOS) or system tray (Windows)
2. Make sure files are synced (not just available in the cloud)
3. Right-click files → "Available offline"

### Wrong Path in DATA_DIR

Verify your path:
```bash
# Check what's in your DATA_DIR
ls "$DATA_DIR"

# Or if that doesn't work, expand the path manually
ls ~/Library/CloudStorage/GoogleDrive-{youremail}@gmail.com/My\ Drive/AI\ Data
```

## Going Back to Local Storage

If you want to go back to local storage:

1. Remove or comment out the DATA_DIR line in `.env`:
   ```bash
   # DATA_DIR=~/Library/CloudStorage/GoogleDrive-{youremail}@gmail.com/My Drive/AI Data
   ```

2. Copy files back to local `data/` folder:
   ```bash
   cp ~/Library/CloudStorage/GoogleDrive-{youremail}@gmail.com/My\ Drive/AI\ Data/*.pdf data/
   ```

3. Rebuild the database:
   ```bash
   prepare-data
   ```

## Security Note

- The ChromaDB database (`chroma_db` folder) will be created inside your DATA_DIR
- This folder is automatically excluded from git via `.gitignore`
- Your personal documents will never be committed to the repository
- Keep your `.env` file secure and never commit it to git
