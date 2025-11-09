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


class JobTracker:
    """Track job applications in Google Sheets."""

    def __init__(self, service_account_path: str = None):
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
        spreadsheet_id: str = None,
        sheet_name: str = None
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
            job_title_with_link = f'=HYPERLINK("{job_url}", "{job_title}")'

            # Prepare the row data
            values = [
                [company_name, job_title_with_link, date_created]
            ]

            # Prepare the request body
            body = {
                'values': values
            }

            # Append the row to the sheet
            result = self.service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!A:C",
                valueInputOption='USER_ENTERED',  # Important: processes formulas
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()

            print(f"\n✓ Added job application to tracking sheet")
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

    def get_spreadsheet_id_from_url(self, url: str) -> Optional[str]:
        """Extract spreadsheet ID from Google Sheets URL.

        Args:
            url: Google Sheets URL

        Returns:
            Spreadsheet ID or None if not found
        """
        import re
        # Match pattern: /spreadsheets/d/{SPREADSHEET_ID}/
        match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
        if match:
            return match.group(1)
        return None
