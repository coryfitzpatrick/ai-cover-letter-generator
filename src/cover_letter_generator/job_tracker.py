"""Job tracking integration with Google Sheets."""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Load environment variables
load_dotenv()


def escape_formula_string(text: str) -> str:
    """Escape quotes for safe use in Google Sheets formulas.

    Args:
        text: String to escape

    Returns:
        Escaped string safe for use in formulas
    """
    # Google Sheets uses "" to escape a single " character
    return text.replace('"', '""')


class JobTracker:
    """Track job applications in Google Sheets."""

    def __init__(self, service_account_path: Optional[str] = None):
        """Initialize job tracker.

        Args:
            service_account_path: Path to service account JSON key file
        """
        # Get service account path from env or parameter
        if service_account_path is None:
            service_account_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY")

        if not service_account_path:
            raise ValueError(
                "GOOGLE_SERVICE_ACCOUNT_KEY not set in .env. "
                "Please set up Google Sheets API access (see GOOGLE_SHEETS_SETUP.md)"
            )

        # Expand path if it contains ~
        service_account_path = Path(service_account_path).expanduser()

        if not service_account_path.exists():
            raise FileNotFoundError(
                f"Service account key not found at {service_account_path}"
            )

        # Authenticate with service account
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        credentials = service_account.Credentials.from_service_account_file(
            str(service_account_path), scopes=SCOPES
        )

        # Build the Sheets API service
        self.service = build('sheets', 'v4', credentials=credentials)

    def add_job_application(
        self,
        company_name: str,
        job_title: str,
        job_url: str,
        spreadsheet_id: Optional[str] = None,
        sheet_name: Optional[str] = None
    ) -> bool:
        """Add a job application entry to Google Sheets.

        Args:
            company_name: Company name for column A
            job_title: Job title for column B (will be hyperlinked)
            job_url: URL to link the job title to
            spreadsheet_id: Google Sheets ID (from URL or env)
            sheet_name: Name of the sheet tab (default from env or "Sheet1")

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get spreadsheet ID from env if not provided
            if spreadsheet_id is None:
                spreadsheet_id = os.getenv("GOOGLE_SHEETS_JOB_TRACKER_ID")

            if not spreadsheet_id:
                print("Error: GOOGLE_SHEETS_JOB_TRACKER_ID not set in .env")
                return False

            # Get sheet name from env if not provided
            if sheet_name is None:
                sheet_name = os.getenv("GOOGLE_SHEETS_SHEET_NAME", "Sheet1")

            # Format date as mm-dd-yyyy
            date_created = datetime.now().strftime("%m-%d-%Y")

            # Create hyperlink formula for job title
            # Google Sheets formula: =HYPERLINK("url", "display text")
            # Escape quotes to prevent formula injection
            job_url_escaped = escape_formula_string(job_url)
            job_title_escaped = escape_formula_string(job_title)
            job_title_with_link = f'=HYPERLINK("{job_url_escaped}", "{job_title_escaped}")'

            # Prepare the row data
            values = [
                [company_name, job_title_with_link, date_created]
            ]

            # Prepare the request body
            body = {
                'values': values
            }

            # Append the row to the sheet
            self.service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!A:C",
                valueInputOption='USER_ENTERED',  # Important: processes formulas
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()

            print("\n✓ Added job application to tracking sheet")
            print(f"  Company: {company_name}")
            print(f"  Job: {job_title}")
            print(f"  Date: {date_created}")

            return True

        except Exception as e:
            print(f"\nError adding job to tracking sheet: {e}")
            print("Make sure:")
            print("1. The spreadsheet is shared with your service account email")
            print("2. GOOGLE_SHEETS_JOB_TRACKER_ID is set correctly in .env")
            print("3. The sheet name matches (default: 'Sheet1')")
            return False

    def check_duplicate(self, job_url: str, spreadsheet_id: Optional[str] = None) -> Optional[str]:
        """Check if a job URL already exists in any sheet.

        Args:
            job_url: The job posting URL to check
            spreadsheet_id: Google Sheets ID (optional, uses env if None)

        Returns:
            Name of the sheet where duplicate was found, or None if not found
        """
        try:
            # Get spreadsheet ID from env if not provided
            if spreadsheet_id is None:
                spreadsheet_id = os.getenv("GOOGLE_SHEETS_JOB_TRACKER_ID")

            if not spreadsheet_id:
                return None

            # Get metadata to find all sheet names
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            
            sheets = spreadsheet.get('sheets', [])
            
            # Check each sheet
            for sheet in sheets:
                sheet_title = sheet['properties']['title']
                
                # Get data from Column B (Job Title/Link)
                # We fetch the formula to see the URL in HYPERLINK("url", ...)
                result = self.service.spreadsheets().values().get(
                    spreadsheetId=spreadsheet_id,
                    range=f"'{sheet_title}'!B:B",
                    valueRenderOption='FORMULA' 
                ).execute()
                
                rows = result.get('values', [])
                
                # Check each row for the URL
                for row in rows:
                    if not row:
                        continue
                        
                    cell_value = row[0]
                    # Check if URL is in the cell (either as raw text or in formula)
                    if job_url in cell_value:
                        return sheet_title
                        
            return None

        except Exception as e:
            print(f"Warning: Could not check for duplicates: {e}")
            return None
