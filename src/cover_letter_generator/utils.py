"""Utility functions for cover letter generation."""

import os
import re
import sys
import warnings
from typing import Optional, Tuple


class TelemetryFilter:
    """Filter to suppress ChromaDB telemetry errors from stderr."""

    def __init__(self, stream: object) -> None:
        self.stream = stream

    def write(self, message: str) -> None:
        """Write message to stream, filtering out telemetry messages."""
        # Only suppress telemetry-related messages
        if ('telemetry' not in message.lower() and 
            'CollectionQueryEvent' not in message and 
            'ClientStartEvent' not in message):
            self.stream.write(message)

    def flush(self) -> None:
        """Flush the underlying stream."""
        self.stream.flush()


def suppress_telemetry_errors() -> None:
    """Suppress ChromaDB telemetry error messages."""
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    sys.stderr = TelemetryFilter(sys.stderr)


def extract_company_name(cover_letter_text: str) -> Optional[str]:
    """Extract company name from cover letter salutation.

    Args:
        cover_letter_text: The cover letter content

    Returns:
        Company name or None if not found
    """
    # Look for "Dear [Company Name] Hiring Team" pattern
    match = re.search(r'Dear\s+(.+?)\s+Hiring\s+Team', cover_letter_text, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Try alternative patterns
    match = re.search(r'Dear\s+(.+?)\s+Recruitment', cover_letter_text, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    match = re.search(r'Dear\s+(.+?)\s+Team', cover_letter_text, re.IGNORECASE)
    if match:
        company = match.group(1).strip()
        # Filter out generic terms
        if company.lower() not in ['hiring', 'recruitment', 'talent']:
            return company

    return None


def extract_job_title(job_description: str) -> Optional[str]:
    """Extract job title from job description.

    Args:
        job_description: The job description text

    Returns:
        Job title or None if not found
    """
    # Common patterns for job titles at the start of job descriptions
    patterns = [
        r'(?:apply|application)\s+for\s+(?:the\s+)?(.+?)(?:\s+position|\s+role|\n|$)',
        r'(?:hiring|seeking|looking\s+for)\s+(?:a|an)\s+(.+?)(?:\s+to|\n|$)',
        r'(?:position|role|job\s+title|title):\s*(.+?)(?:\n|$)',
        r'^(.+?)\s+(?:position|role|opportunity)',
    ]

    for pattern in patterns:
        match = re.search(pattern, job_description, re.IGNORECASE | re.MULTILINE)
        if match:
            title = match.group(1).strip()
            # Clean up the title
            title = re.sub(r'\s+', ' ', title)  # Normalize whitespace
            title = title.strip('.,;:-')  # Remove trailing punctuation
            if len(title) > 5 and len(title) < 100:  # Reasonable length
                return title

    return None


def create_folder_name_from_details(
    company_name: Optional[str],
    job_title: Optional[str],
    timestamp: str
) -> str:
    """Create a folder name from company name and job title with date applied.

    Args:
        company_name: Company name
        job_title: Job title
        timestamp: Timestamp string in format YYYYMMDD_HHMMSS

    Returns:
        Formatted folder name like "Company Name - Job Title - YYYY-MM-DD" or fallback
    """
    # Extract date from timestamp (format: YYYYMMDD_HHMMSS -> YYYY-MM-DD)
    date_applied = f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}"

    if company_name and job_title:
        # Clean for folder name (keep spaces, remove problematic chars)
        clean_company = re.sub(r'[<>:"/\\|?*]', '', company_name).strip()
        clean_title = re.sub(r'[<>:"/\\|?*]', '', job_title).strip()

        folder_name = f"{clean_company} - {clean_title} - {date_applied}"

        # Limit length (leave room for date suffix)
        if len(folder_name) > 120:
            # Truncate company and title parts while keeping date
            max_name_length = 120 - len(date_applied) - 3  # 3 for " - "
            base_name = f"{clean_company} - {clean_title}"
            if len(base_name) > max_name_length:
                base_name = base_name[:max_name_length]
            folder_name = f"{base_name} - {date_applied}"

        return folder_name
    elif company_name:
        # Just company name with date if no job title
        clean_company = re.sub(r'[<>:"/\\|?*]', '', company_name).strip()
        return f"{clean_company} - {date_applied}"
    else:
        # Fallback to timestamp-based name
        return f"Application_{timestamp}"


def create_filename_from_details(
    company_name: Optional[str],
    job_title: Optional[str],
    timestamp: str
) -> str:
    """Create a filename from company name and job title.

    Args:
        company_name: Company name
        job_title: Job title
        timestamp: Timestamp string

    Returns:
        Formatted filename
    """
    # Get user name from environment variable (required)
    user_name = os.getenv("USER_NAME")
    return f"{user_name} Cover Letter"


def extract_cover_letter_details(
    cover_letter_text: str,
    job_description: str
) -> Tuple[Optional[str], Optional[str]]:
    """Extract company name and job title from texts.

    Args:
        cover_letter_text: The generated cover letter
        job_description: The original job description

    Returns:
        Tuple of (company_name, job_title)
    """
    company = extract_company_name(cover_letter_text)
    job_title = extract_job_title(job_description)

    return company, job_title
