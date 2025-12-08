"""Command-line interface for cover letter generation."""

import os

import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from dotenv import load_dotenv

from .docx_generator import generate_cover_letter_docx
from .feedback_tracker import FeedbackTracker
from .generator import CoverLetterGenerator
from .job_tracker import JobTracker
from .pdf_generator_template import generate_cover_letter_pdf
from .signature_validator import validate_pdf_signature
from .system_improver import SystemImprover
from .ui_components import (
    DASH_LINE,
    SEPARATOR_LINE,
    get_job_details_interactive,
    get_user_choice,
    print_divider,
    print_header,
    read_multiline_input,
)
from .utils import create_folder_name_from_details

# Load environment variables
load_dotenv()

# Get user configuration from environment
USER_NAME = os.getenv("USER_NAME")

# Contact information for PDF headers - read from environment variables
DEFAULT_CONTACT_INFO = {
    "name": USER_NAME,
    "email": os.getenv("USER_EMAIL", ""),
    "phone": os.getenv("USER_PHONE", ""),
    "location": os.getenv("USER_LOCATION", ""),
    "linkedin": os.getenv("USER_LINKEDIN", ""),
    "portfolio": os.getenv("USER_PORTFOLIO", ""),
}

# Default output directory for cover letters
# Can be customized via OUTPUT_DIR env variable
_output_dir = os.getenv("OUTPUT_DIR")
if _output_dir:
    DEFAULT_OUTPUT_DIR = Path(_output_dir)
else:
    # Default to iCloud Documents/Cover Letters
    icloud_path = (
        Path.home()
        / "Library"
        / "Mobile Documents"
        / "com~apple~CloudDocs"
        / "Documents"
        / "Cover Letters"
    )
    if icloud_path.exists():
        DEFAULT_OUTPUT_DIR = icloud_path
    else:
        # Fallback to ~/Documents/Cover Letters if iCloud not available
        DEFAULT_OUTPUT_DIR = Path.home() / "Documents" / "Cover Letters"


def print_welcome():
    """Print welcome message."""
    print_header("Cover Letter Generator")
    print("\nThis tool generates personalized cover letters based on job descriptions.")
    print("\nInstructions:")
    print("  1. Paste a job posting URL OR enter details manually")
    print("  2. The cover letter will be generated and displayed")
    print("  3. Provide feedback or save the final version")
    print("\nType 'quit' or 'exit' to exit the program.")
    print(SEPARATOR_LINE + "\n")


def save_cover_letter(
    cover_letter: str,
    company_name: Optional[str] = None,
    job_title: Optional[str] = None,
    output_dir: Optional[Path] = None,
):
    """Save the cover letter to a PDF file and validate signature.

    Args:
        cover_letter: The cover letter text
        company_name: The company name
        job_title: The job title
        output_dir: Directory to save the cover letter (default: iCloud Documents/Cover Letters)

    Returns:
        SignatureValidationResult: Result of signature validation
    """
    if output_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR

    # Create directory if it doesn't exist
    if not output_dir.exists():
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            print(f"Created directory: {output_dir}")
        except Exception as e:
            print(f"Warning: Could not create directory {output_dir}: {e}")
            print("Falling back to current directory")
            output_dir = Path.cwd()
    elif not output_dir.is_dir():
        print(f"Warning: {output_dir} exists but is not a directory")
        print("Falling back to current directory")
        output_dir = Path.cwd()

    # Create a timestamp for fallback
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create folder name from provided company and job title
    folder_name = create_folder_name_from_details(company_name, job_title, timestamp)

    # Create application subfolder
    application_dir = output_dir / folder_name
    try:
        application_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Warning: Could not create subfolder {application_dir}: {e}")
        application_dir = output_dir

    # Use standard filename from environment variable
    user_name = os.getenv("USER_NAME")
    base_filename = f"{user_name} Cover Letter"

    # Save as both PDF and DOCX
    pdf_filepath = application_dir / f"{base_filename}.pdf"
    docx_filepath = application_dir / f"{base_filename}.docx"

    generate_cover_letter_pdf(
        cover_letter, application_dir, f"{base_filename}.pdf", DEFAULT_CONTACT_INFO
    )

    generate_cover_letter_docx(
        cover_letter, application_dir, f"{base_filename}.docx", DEFAULT_CONTACT_INFO
    )

    # Print saved file locations
    print()
    print("✓ Cover letter saved:")
    print(f"  PDF:  {pdf_filepath}")
    print(f"  DOCX: {docx_filepath}")

    # Validate signature (pass cover letter text for precise cut-off calculation)
    validation_result = validate_pdf_signature(
        pdf_filepath, user_name, cover_letter_text=cover_letter, verbose=True
    )

    return validation_result


def ensure_signature(cover_letter: str, user_name: str, print_preview: bool = True) -> str:
    """Ensure cover letter ends with signature and optionally print it in preview.

    Args:
        cover_letter: The cover letter text
        user_name: User's full name for signature
        print_preview: Whether to print the signature to console if added

    Returns:
        Cover letter with signature guaranteed at the end
    """
    signature_added = False
    if not cover_letter.strip().endswith(user_name):
        cover_letter = cover_letter.rstrip() + f"\\n\\nSincerely,\\n{user_name}"
        signature_added = True

    # Show signature in preview if we added it
    if signature_added and print_preview:
        print(f"\\n\\nSincerely,\\n{user_name}")

    return cover_letter


def initialize_components() -> Tuple[
    CoverLetterGenerator,
    Optional[FeedbackTracker],
    Optional[SystemImprover],
    Optional[JobTracker],
]:
    """Initialize all system components."""
    # Validate required environment variables
    if not USER_NAME:
        print("\nError: USER_NAME not set in .env file")
        print('Please add USER_NAME="Your Full Name" to your .env file')
        sys.exit(1)

    # Validate required contact information
    missing_fields = []
    if not DEFAULT_CONTACT_INFO.get("email"):
        missing_fields.append("USER_EMAIL")
    if not DEFAULT_CONTACT_INFO.get("location"):
        missing_fields.append("USER_LOCATION")

    if missing_fields:
        print(f"\nWarning: Missing contact information: {', '.join(missing_fields)}")
        print("Cover letters may be generated without complete contact details.")
        print("Add these to your .env file for complete headers.")

    # Print welcome message
    print_welcome()

    # Ask user which model to use
    print_header("Which AI model would you like to use?")
    print("\nAvailable models:")
    print("  (1) GPT-4o [Default]")
    print("      - Best quality, cost-effective")
    print("      - Cost: ~$0.01-0.02 per cover letter")
    print("  (2) Claude Opus 4")
    print("      - Maximum reasoning power")
    print("      - Cost: ~$0.10-0.15 per cover letter (expensive)")
    print()

    model_choice = get_user_choice(["1", "2"], default="1")
    model_name = "gpt-4o" if model_choice == "1" else "opus"

    # Initialize generator
    try:
        generator = CoverLetterGenerator(model_name=model_name)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("\nPlease run 'prepare-data' first to set up the knowledge base.")
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}")
        print(
            "\nPlease ensure OPENAI_API_KEY, ANTHROPIC_API_KEY and "
            "GROQ_API_KEY are set in your .env file."
        )
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error during initialization: {e}")
        sys.exit(1)

    # Initialize feedback tracker and system improver
    try:
        feedback_tracker = FeedbackTracker()
        system_improver = SystemImprover()
    except Exception as e:
        print(f"Warning: Could not initialize meta-learning features: {e}")
        feedback_tracker = None
        system_improver = None

    # Initialize job tracker (optional feature)
    try:
        job_tracker = JobTracker()
    except Exception:
        # Silently disable if not configured
        job_tracker = None

    return generator, feedback_tracker, system_improver, job_tracker


def handle_feedback_loop(
    generator: CoverLetterGenerator,
    cover_letter: str,
    job_description: str,
    company_name: str,
    job_title: str,
    custom_context: Optional[str],
    feedback_tracker: Optional[FeedbackTracker],
) -> str:
    """Handle the feedback and revision loop."""
    current_version = cover_letter

    while True:
        print("\nOptions:")
        print("  (1) Save this version")
        print("  (2) Provide feedback for revision")
        print("  (3) Start over with new job description")

        print("  (4) Exit")
        print("  (5) Copy to clipboard")

        choice = get_user_choice(["1", "2", "3", "4", "5"], default="1")

        if choice == "1":
            return current_version

        elif choice == "2":
            print("\nWhat would you like to change?")
            print("(e.g. 'Make it more professional', 'Focus on leadership', 'Shorten it')")
            user_feedback = read_multiline_input("Feedback:")

            if user_feedback:
                print(f"\nRegenerating with feedback: {user_feedback}")
                revised_letter, cost_info = generator.revise_cover_letter(
                    current_version,
                    user_feedback,
                    job_description,
                    company_name,
                    job_title,
                    custom_context=custom_context,
                )

                # Show preview
                print("\n" + SEPARATOR_LINE)
                print("REVISED VERSION (PREVIEW)")
                print(SEPARATOR_LINE)
                print(revised_letter)
                print(SEPARATOR_LINE)

                print(f"\n💰 Revision cost: ${cost_info['revision_cost']:.4f}")

                # Ensure signature
                revised_letter = ensure_signature(revised_letter, USER_NAME)

                # Ask to accept or discard
                print("\nDo you want to keep this revision?")
                print("  (1) Yes, keep it")
                print("  (2) No, discard and go back")
                keep_choice = get_user_choice(["1", "2"], default="1")

                if keep_choice == "1":
                    current_version = revised_letter
                    print("✓ Revision accepted")

                    # Track feedback
                    if feedback_tracker:
                        try:
                            feedback_tracker.add_feedback(user_feedback, company_name, job_title)
                        except Exception:
                            pass
                else:
                    print("✓ Revision discarded")

        elif choice == "3":
            return None  # Signal to start over

        elif choice == "4":
            print("\nExiting...")

            sys.exit(0)

        elif choice == "5":
            try:
                # Try pyperclip first (cross-platform)
                try:
                    import pyperclip

                    pyperclip.copy(current_version)
                    print("\n✓ Copied to clipboard!")
                except ImportError:
                    # Fallback to platform-specific methods
                    import platform

                    system = platform.system()

                    if system == "Darwin":  # macOS
                        process = subprocess.Popen(
                            "pbcopy", env={"LANG": "en_US.UTF-8"}, stdin=subprocess.PIPE
                        )
                        process.communicate(current_version.encode("utf-8"))
                        print("\n✓ Copied to clipboard!")
                    elif system == "Windows":
                        process = subprocess.Popen(["clip"], stdin=subprocess.PIPE, shell=True)
                        process.communicate(current_version.encode("utf-8"))
                        print("\n✓ Copied to clipboard!")
                    elif system == "Linux":
                        # Try xclip first, then xsel
                        try:
                            process = subprocess.Popen(
                                ["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE
                            )
                            process.communicate(current_version.encode("utf-8"))
                            print("\n✓ Copied to clipboard!")
                        except FileNotFoundError:
                            process = subprocess.Popen(
                                ["xsel", "--clipboard", "--input"], stdin=subprocess.PIPE
                            )
                            process.communicate(current_version.encode("utf-8"))
                            print("\n✓ Copied to clipboard!")
                    else:
                        print(
                            f"\n⚠ Clipboard not supported on {system}. Please install pyperclip: pip install pyperclip"
                        )
            except Exception as e:
                print(f"\nError copying to clipboard: {e}")
                print("Tip: Install pyperclip for better clipboard support: pip install pyperclip")

    return current_version


def handle_save_and_validate(
    generator: CoverLetterGenerator,
    cover_letter: str,
    company_name: str,
    job_title: str,
    job_description: str,
    job_tracker: Optional[JobTracker],
    job_url: Optional[str],
    feedback_tracker: Optional[FeedbackTracker],
):
    """Handle saving and signature validation."""
    while True:
        # Save and validate
        validation_result = save_cover_letter(cover_letter, company_name, job_title)

        # If valid or skipped, we're done with validation
        if validation_result.is_valid or validation_result.confidence == "low":
            break

        # Handle invalid signature
        print("\n" + SEPARATOR_LINE)
        print("⚠ SIGNATURE ISSUE DETECTED")
        print(SEPARATOR_LINE)
        print(f"Details: {validation_result.message}")
        if validation_result.details:
            print(f"Additional info: {validation_result.details}")

        print("\nWhat would you like to do?")
        print("  (1) Regenerate a shorter version (Automatic)")
        print("  (2) Keep the current version")

        choice = get_user_choice(["1", "2"], default="1")

        if choice == "2":
            break

        # Automatic shortening
        print("\nRegenerating with targeted shortening...")
        shortening_feedback = (
            "Revise the cover letter to be shorter to ensure the signature fits on one page. "
            "Remove 2-3 sentences."
        )

        cover_letter_parts = []
        for chunk in generator.revise_cover_letter_stream(
            cover_letter, shortening_feedback, job_description, company_name, job_title
        ):
            print(chunk, end="", flush=True)
            cover_letter_parts.append(chunk)

        cover_letter = "".join(cover_letter_parts)
        cover_letter = ensure_signature(cover_letter, USER_NAME)
        print("\n✓ Shortened version generated.")

        # Loop back to save and validate again

    # Job Tracking
    if job_tracker and job_url:
        print("\n" + SEPARATOR_LINE)
        print("Would you like to add this to your job tracking sheet? (y/n) [y]")
        choice = input().strip().lower()
        if choice != "n":
            try:
                duplicate = job_tracker.check_duplicate(job_url)
                if duplicate:
                    print(f"⚠ Already in sheet: {duplicate}")
                    print("Add anyway? (y/n) [n]")
                    if input().strip().lower() != "y":
                        return

                job_tracker.add_job_application(company_name, job_title, job_url)
                print("✓ Added to job tracker")
            except Exception as e:
                print(f"Error adding to tracker: {e}")


def main():
    """Main CLI function."""
    try:
        generator, feedback_tracker, system_improver, job_tracker = initialize_components()

        while True:
            # Get job details
            details = get_job_details_interactive()
            if details is None:
                print("\nExiting...")
                break

            company_name, job_title, job_description, job_url, custom_context = details

            # Ask for any final custom instructions
            print_divider()
            print("Do you have any specific instructions for this cover letter?")
            print("(e.g., 'Focus on my startup experience', 'Keep it under 300 words')")
            print("Press Enter to skip.")
            print(DASH_LINE)

            additional_instructions = input("Instructions: ").strip()
            if additional_instructions:
                if custom_context:
                    custom_context += f"\n\nADDITIONAL INSTRUCTIONS:\n{additional_instructions}"
                else:
                    custom_context = f"ADDITIONAL INSTRUCTIONS:\n{additional_instructions}"
                print("✓ Instructions added")

            # Generate cover letter
            print(f"\nGenerating cover letter with {generator.model_name}...")

            try:
                cover_letter, cost_info = generator.generate_cover_letter(
                    job_description, company_name, job_title, custom_context=custom_context
                )

                # Display
                print_header("GENERATED COVER LETTER")
                print(cover_letter)
                print(SEPARATOR_LINE)

                print(f"\n💰 Cost: ${cost_info['total_cost']:.4f}")

                # Ensure signature
                cover_letter = ensure_signature(cover_letter, USER_NAME)

                # Feedback Loop
                final_version = handle_feedback_loop(
                    generator,
                    cover_letter,
                    job_description,
                    company_name,
                    job_title,
                    custom_context,
                    feedback_tracker,
                )

                if final_version is None:
                    continue  # Start over

                # Save and Validate
                handle_save_and_validate(
                    generator,
                    final_version,
                    company_name,
                    job_title,
                    job_description,
                    job_tracker,
                    job_url,
                    feedback_tracker,
                )

            except Exception as e:
                print(f"\nError generating cover letter: {e}")
                print("Please try again.")
                continue

    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)


if __name__ == "__main__":
    main()
