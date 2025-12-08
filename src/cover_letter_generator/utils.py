"""Utility functions for cover letter generation."""

import os
import re
import sys
import warnings
from pathlib import Path
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


def get_data_directory() -> Path:
    """Get the data directory from environment or default location.

    Returns:
        Path: Resolved data directory path

    Examples:
        >>> # With DATA_DIR set to ~/Google Drive/Data
        >>> get_data_directory()
        PosixPath('/Users/username/Google Drive/Data')

        >>> # Without DATA_DIR (uses project default)
        >>> get_data_directory()
        PosixPath('/path/to/project/data')
    """
    data_dir_env = os.getenv("DATA_DIR")
    if data_dir_env:
        # Remove quotes if present and expand ~ to home directory
        data_dir_clean = data_dir_env.strip('"').strip("'")
        return Path(data_dir_clean).expanduser().resolve()

    # Default to project data directory
    return Path(__file__).parent.parent.parent / "data"


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


