#!/usr/bin/env python3
"""Rename files in Google Drive AI Data folder to snake_case.

This script renames all files in the Google Drive AI Data folder to follow
snake_case naming conventions.

Usage:
    python scripts/rename_google_drive_files.py [--dry-run]
"""

import os
import re
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def to_snake_case(name: str) -> str:
    """Convert a string to snake_case.

    Args:
        name: String to convert

    Returns:
        snake_case version of the string

    Examples:
        >>> to_snake_case("Leadership Philosophy.docx")
        'leadership_philosophy.docx'
        >>> to_snake_case("Cover Letter_ AI Template.pdf")
        'cover_letter_ai_template.pdf'
        >>> to_snake_case("My Resume 2024.pdf")
        'my_resume_2024.pdf'
    """
    # Preserve file extension
    parts = name.rsplit('.', 1)
    basename = parts[0]
    extension = f".{parts[1]}" if len(parts) > 1 else ""

    # Replace special characters (including colons) and spaces with underscores
    # Handle underscores at word boundaries: "Cover Letter_ AI" -> "Cover_Letter_AI"
    basename = re.sub(r'[:_\s-]+', '_', basename)

    # Convert to lowercase
    basename = basename.lower()

    # Remove multiple consecutive underscores
    basename = re.sub(r'_+', '_', basename)

    # Remove leading/trailing underscores
    basename = basename.strip('_')

    return basename + extension


def get_data_directory() -> Path:
    """Get the DATA_DIR from environment or default location."""
    data_dir_env = os.getenv("DATA_DIR")
    if data_dir_env:
        data_dir_clean = data_dir_env.strip('"').strip("'")
        return Path(data_dir_clean).expanduser().resolve()

    # Default to project data directory
    return Path(__file__).parent.parent / "data"


def rename_files_in_directory(directory: Path, dry_run: bool = True) -> None:
    """Rename all files in directory to snake_case.

    Args:
        directory: Directory to process
        dry_run: If True, only print what would be renamed without actually renaming
    """
    if not directory.exists():
        print(f"❌ Error: Directory does not exist: {directory}")
        print(f"\nPlease ensure Google Drive is mounted and DATA_DIR is set correctly.")
        print(f"Current DATA_DIR: {os.getenv('DATA_DIR', 'Not set')}")
        sys.exit(1)

    print(f"{'🔍 DRY RUN - ' if dry_run else ''}Processing directory: {directory}\n")

    renamed_count = 0
    skipped_count = 0

    # Process all files recursively
    for root, dirs, files in os.walk(directory):
        root_path = Path(root)

        for filename in files:
            # Skip hidden files
            if filename.startswith('.'):
                continue

            new_filename = to_snake_case(filename)

            if filename == new_filename:
                skipped_count += 1
                continue

            old_path = root_path / filename
            new_path = root_path / new_filename

            # Check if target file already exists
            if new_path.exists():
                print(f"⚠️  WARNING: Target file already exists, skipping:")
                print(f"   {old_path}")
                print(f"   -> {new_path}")
                print()
                continue

            print(f"{'[DRY RUN] ' if dry_run else ''}Renaming:")
            print(f"  {old_path.relative_to(directory)}")
            print(f"  -> {new_filename}")
            print()

            if not dry_run:
                try:
                    old_path.rename(new_path)
                    renamed_count += 1
                except Exception as e:
                    print(f"❌ Error renaming {filename}: {e}")
                    print()
            else:
                renamed_count += 1

    print("\n" + "="*60)
    print(f"{'DRY RUN ' if dry_run else ''}Summary:")
    print(f"  Files to rename: {renamed_count}")
    print(f"  Files already in snake_case: {skipped_count}")
    print("="*60)

    if dry_run:
        print("\n💡 To actually rename files, run:")
        print("   python scripts/rename_google_drive_files.py --apply")


def main():
    """Main entry point."""
    dry_run = "--apply" not in sys.argv

    if dry_run:
        print("🔍 DRY RUN MODE - No files will be renamed\n")

    data_dir = get_data_directory()
    rename_files_in_directory(data_dir, dry_run=dry_run)


if __name__ == "__main__":
    main()
