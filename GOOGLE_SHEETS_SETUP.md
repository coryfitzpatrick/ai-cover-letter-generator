# Google Sheets Job Tracker Setup

This guide explains how to set up automatic job tracking in Google Sheets. After generating a cover letter, you'll be prompted to add the job to your tracking spreadsheet.

## What Gets Tracked

After you generate and save a cover letter, the system will ask if you want to add an entry to your Google Sheets tracking list with:

- **Column A**: Company name
- **Column B**: Job title (hyperlinked to the job posting URL)
- **Column C**: Date created (in mm-dd-yyyy format)

## Prerequisites

You'll need a Google service account with access to Google Sheets API. Follow these steps to set it up:

### Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" dropdown at the top
3. Click "NEW PROJECT"
4. Enter a project name (e.g., "Cover Letter Generator")
5. Click "CREATE"

### Step 2: Enable Google Sheets API

1. In your project, go to **APIs & Services > Library**
2. Search for "Google Sheets API"
3. Click on "Google Sheets API"
4. Click "ENABLE"

### Step 3: Create a Service Account

1. Go to **APIs & Services > Credentials**
2. Click "CREATE CREDENTIALS" → "Service account"
3. Fill in the details:
   - **Service account name**: `cover-letter-sheets` (or any name you prefer)
   - **Service account ID**: will auto-populate
   - **Description**: "Access Google Sheets for job tracking"
4. Click "CREATE AND CONTINUE"
5. **Grant access**: Skip this step, click "CONTINUE"
6. **Grant users access**: Skip this step, click "DONE"

### Step 4: Create and Download the Service Account Key

1. On the **Credentials** page, find your service account in the list
2. Click on the service account email
3. Go to the **KEYS** tab
4. Click "ADD KEY" → "Create new key"
5. Select **JSON** format
6. Click "CREATE"
7. The key file will download automatically (e.g., `cover-letter-generator-abc123.json`)

**IMPORTANT:** Keep this file secure! It provides access to your Google Sheets.

### Step 5: Save the Service Account Key

1. Move the downloaded JSON key to a secure location:
   ```bash
   # Create a secure credentials folder
   mkdir -p ~/.config/cover-letter-generator

   # Move the key (replace the filename with yours)
   mv ~/Downloads/cover-letter-generator-*.json ~/.config/cover-letter-generator/service-account-key.json

   # Set secure permissions
   chmod 600 ~/.config/cover-letter-generator/service-account-key.json
   ```

### Step 6: Locate Your Jobs List Spreadsheet

1. In Google Drive, locate your `Jobs List.gsheet` file
   - This file is in the root of your Google Drive (or wherever you keep it)
   - The `.gsheet` extension means it's a Google Sheets spreadsheet

2. Open `Jobs List.gsheet` by double-clicking it

3. Set up the column headers if they don't exist (optional but recommended):
   - **A1**: Company
   - **B1**: Job Title
   - **C1**: Date Applied

4. Get the spreadsheet ID from the URL:
   ```
   https://docs.google.com/spreadsheets/d/[THIS_IS_THE_SPREADSHEET_ID]/edit
   ```
   Copy the ID between `/d/` and `/edit`

   Example: If the URL is:
   ```
   https://docs.google.com/spreadsheets/d/1a2b3c4d5e6f7g8h9i0j/edit
   ```
   The spreadsheet ID is: `1a2b3c4d5e6f7g8h9i0j`

### Step 7: Share the Spreadsheet with the Service Account

1. Open the `.json` key file you downloaded and find the `client_email` field. It looks like:
   ```
   cover-letter-sheets@cover-letter-generator.iam.gserviceaccount.com
   ```

2. Open your `Jobs List.gsheet` file in Google Drive (double-click to open it)
3. Click **Share** button
4. Paste the service account email
5. Set permission to **Editor** (needed to add rows)
6. Uncheck "Notify people"
7. Click "Share"

### Step 8: Configure Your .env File

1. Open your `.env` file in the project root:
   ```bash
   nano .env
   ```

2. Add these lines (update with your values):
   ```bash
   # Google Sheets Job Tracker Configuration
   GOOGLE_SERVICE_ACCOUNT_KEY=~/.config/cover-letter-generator/service-account-key.json
   GOOGLE_SHEETS_JOB_TRACKER_ID=your_spreadsheet_id_here
   ```

3. Replace `your_spreadsheet_id_here` with the ID from Step 6

4. Save and close (Ctrl+X, then Y, then Enter)

### Step 9: Test the Setup

1. Generate a cover letter:
   ```bash
   source venv/bin/activate
   cover-letter-cli
   ```

2. When using a URL to provide the job posting, after saving the cover letter you'll see:
   ```
   Would you like to add this to your job tracking sheet?
     Company: [Company Name]
     Job: [Job Title]
     URL: [Job URL]

   Add to tracking sheet? (y/n) [n]:
   ```

3. Type `y` and press Enter

4. Check your Google Sheets - you should see a new row with:
   - Company name in column A
   - Job title (clickable link) in column B
   - Today's date in mm-dd-yyyy format in column C

## Troubleshooting

### "GOOGLE_SERVICE_ACCOUNT_KEY not set in .env"

- Make sure you added both `GOOGLE_SERVICE_ACCOUNT_KEY` and `GOOGLE_SHEETS_JOB_TRACKER_ID` to your `.env` file
- Check that the path is correct and uses `~` for your home directory

### "Service account key not found"

- Verify the file exists at the path specified in `.env`:
  ```bash
  ls -la ~/.config/cover-letter-generator/service-account-key.json
  ```

### "Error adding job to tracking sheet"

- Make sure you shared the spreadsheet with the service account email
- Check the service account email in the JSON key file (`client_email` field)
- Verify the Google Sheets API is enabled in your Google Cloud project
- Ensure `GOOGLE_SHEETS_JOB_TRACKER_ID` is correct (from the spreadsheet URL)

### Sheet name doesn't match

The system defaults to `Sheet1`. If your sheet tab has a different name:
- Either rename your sheet tab to "Sheet1" (right-click tab → Rename)
- Or the system will still work, as it appends to range `A:C` which works across all sheets

### Job tracker doesn't prompt

The job tracker only prompts when:
1. You provided a job URL (not manual entry)
2. The service account is properly configured
3. The cover letter was successfully saved

If you entered the job details manually (option 2), there's no URL to link, so the tracker won't prompt.

## Disabling the Job Tracker

To disable the job tracker feature:

1. Remove or comment out the Google Sheets config in `.env`:
   ```bash
   # GOOGLE_SERVICE_ACCOUNT_KEY=~/.config/cover-letter-generator/service-account-key.json
   # GOOGLE_SHEETS_JOB_TRACKER_ID=your_spreadsheet_id_here
   ```

2. The feature will silently disable and won't prompt you

## Security Best Practices

1. **Never commit the service account key** to git
   - It's already in `.gitignore` at `~/.config/`

2. **Set secure file permissions**:
   ```bash
   chmod 600 ~/.config/cover-letter-generator/service-account-key.json
   ```

3. **Use least privilege**: The service account only needs "Editor" permission on the specific spreadsheet

4. **Rotate keys periodically**:
   - Delete old keys in Google Cloud Console
   - Create new keys if compromised

## Using Multiple Spreadsheets

To track different types of jobs in different sheets:

1. Create multiple spreadsheets in Google Drive
2. Get each spreadsheet ID
3. When running the CLI, you can temporarily change the `GOOGLE_SHEETS_JOB_TRACKER_ID` in your `.env` file
4. Or modify the code to prompt which sheet to use (advanced)
