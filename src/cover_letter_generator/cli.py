"""Command-line interface for cover letter generation."""

import os
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from .generator import CoverLetterGenerator
from .pdf_generator_template import generate_cover_letter_pdf
from .utils import create_folder_name_from_details
from .signature_validator import validate_pdf_signature
from .job_parser import parse_job_from_url, is_valid_url
from .feedback_tracker import FeedbackTracker
from .system_improver import SystemImprover
from .job_tracker import JobTracker

# Load environment variables
load_dotenv()

# Get user name from environment
USER_NAME = os.getenv("USER_NAME")

# Default contact information for PDF headers
# Edit these values to customize your cover letter headers
DEFAULT_CONTACT_INFO = {
    "name": USER_NAME,
    "email": "cory@coryfitzpatrick.com",
    "phone": "",  # Optional: add phone number
    "location": "Greater Boston",
    "linkedin": "https://www.linkedin.com/in/coryfitzpatrick",
    "portfolio": "http://www.coryfitzpatrick.com",
}

# Default output directory for cover letters
DEFAULT_OUTPUT_DIR = (
    Path.home()
    / "Library/Mobile Documents/com~apple~CloudDocs/Documents/Cover Letters"
)




def print_welcome():
    """Print welcome message."""
    print("\n" + "=" * 80)
    print("Cover Letter Generator")
    print("=" * 80)
    print("\nThis tool generates personalized cover letters based on job descriptions.")
    print("\nInstructions:")
    print("  1. Paste a job posting URL OR enter details manually")
    print("  2. The cover letter will be generated and displayed")
    print("  3. Provide feedback or save the final version")
    print("\nType 'quit' or 'exit' to exit the program.")
    print("=" * 80 + "\n")


def read_multiline_input(prompt: str) -> str:
    """Read multiline input from the user.

    Args:
        prompt: Prompt to display to the user

    Returns:
        The input text as a string
    """
    print(prompt)
    lines = []

    try:
        while True:
            line = input()
            # Check for quit commands
            if line.strip().lower() in ['quit', 'exit', 'q']:
                return None
            lines.append(line)
    except EOFError:
        # User pressed Ctrl+D (Unix) or Ctrl+Z (Windows)
        pass
    except KeyboardInterrupt:
        print("\n\nExiting...")
        return None

    return '\n'.join(lines).strip()


def show_job_details(company_name: str, job_title: str, job_description: str):
    """Display job details for review.

    Args:
        company_name: Company name
        job_title: Job title
        job_description: Full job description
    """
    print("\n" + "=" * 80)
    print("EXTRACTED JOB DETAILS")
    print("=" * 80)
    print(f"\nCompany Name: {company_name}")
    print(f"Job Title: {job_title}")
    print(f"\nJob Description ({len(job_description)} characters):")
    print("-" * 80)

    # Show first 2000 characters of description
    if len(job_description) > 2000:
        print(job_description[:2000])
        print(f"\n... [truncated, showing first 2000 of {len(job_description)} characters]")
    else:
        print(job_description)

    print("-" * 80)


def edit_job_field(field_name: str, current_value: str, multiline: bool = False) -> str:
    """Allow user to edit a job field.

    Args:
        field_name: Name of the field being edited
        current_value: Current value
        multiline: Whether this is a multiline field

    Returns:
        Updated value or current value if unchanged
    """
    print(f"\nCurrent {field_name}: {current_value if not multiline else f'({len(current_value)} characters)'}")

    if multiline:
        print(f"\nEnter new {field_name} (press Ctrl+D when done):")
        print("Or press Ctrl+D immediately to keep current value.")
        new_value = read_multiline_input("")
        if new_value is None or not new_value.strip():
            print(f"Keeping current {field_name}.")
            return current_value
        return new_value
    else:
        print(f"Enter new {field_name} (or press Enter to keep current): ", end='')
        new_value = input().strip()
        if not new_value:
            print(f"Keeping current {field_name}.")
            return current_value
        return new_value


def save_cover_letter(
    cover_letter: str,
    company_name: str = None,
    job_title: str = None,
    output_dir: Path = None
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

    # Save as PDF only
    pdf_filepath = application_dir / f"{base_filename}.pdf"
    generate_cover_letter_pdf(
        cover_letter, application_dir, f"{base_filename}.pdf", DEFAULT_CONTACT_INFO
    )

    # Print saved file location
    print()
    print(f"✓ Cover letter saved to: {pdf_filepath}")

    # Validate signature (pass cover letter text for precise cut-off calculation)
    validation_result = validate_pdf_signature(
        pdf_filepath,
        user_name,
        cover_letter_text=cover_letter,
        verbose=True
    )

    return validation_result


def main():
    """Main CLI function."""
    try:
        # Print welcome message
        print_welcome()

        # Initialize generator
        try:
            generator = CoverLetterGenerator()
        except FileNotFoundError as e:
            print(f"Error: {e}")
            print("\nPlease run 'prepare-data' first to set up the knowledge base.")
            sys.exit(1)
        except ValueError as e:
            print(f"Error: {e}")
            print("\nPlease set GROQ_API_KEY in your .env file.")
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
        except Exception as e:
            # Silently disable if not configured
            job_tracker = None

        # Main loop
        while True:
            company_name = None
            job_title = None
            job_description = None
            job_url = None  # Track the job URL for adding to tracker

            # Ask for input method
            print("\n" + "-" * 80)
            print("How would you like to provide the job posting?")
            print("  (1) Paste a URL to the job posting")
            print("  (2) Enter details manually")
            print("\nChoice [1]: ", end='')

            try:
                input_choice = input().strip() or '1'
                if input_choice.lower() in ['quit', 'exit', 'q']:
                    print("\nExiting...")
                    break
            except KeyboardInterrupt:
                print("\n\nExiting...")
                break

            # Handle URL input
            if input_choice == '1':
                print("\nJob Posting URL: ", end='')
                try:
                    url = input().strip()
                    if url.lower() in ['quit', 'exit', 'q']:
                        print("\nExiting...")
                        break
                    if not url:
                        print("No URL provided. Please try again.")
                        continue

                    # Validate URL format
                    if not is_valid_url(url):
                        print("Invalid URL format. Please provide a valid URL starting with http:// or https://")
                        continue

                    # Parse the job posting
                    job_posting = parse_job_from_url(url)

                    if not job_posting:
                        print("\nCould not parse job posting from URL.")
                        print("Would you like to enter the details manually? (y/n): ", end='')
                        retry = input().strip().lower()
                        if retry == 'y':
                            input_choice = '2'  # Fall through to manual entry
                        else:
                            continue

                    if job_posting:
                        # Show extracted details with full description
                        show_job_details(
                            job_posting.company_name,
                            job_posting.job_title,
                            job_posting.job_description
                        )

                        # Set initial values
                        company_name = job_posting.company_name
                        job_title = job_posting.job_title
                        job_description = job_posting.job_description
                        job_url = url  # Save the URL for job tracker

                        # Review and edit loop
                        while True:
                            print("\nWhat would you like to do?")
                            print("  (1) Use these details as-is")
                            print("  (2) Edit company name")
                            print("  (3) Edit job title")
                            print("  (4) Edit description")
                            print("  (5) View full description")
                            print("  (6) Start over - enter all details manually")
                            print("\nChoice [1]: ", end='')

                            try:
                                review_choice = input().strip() or '1'

                                if review_choice == '1':
                                    # Accept as-is
                                    print("\n✓ Using extracted details")
                                    break

                                elif review_choice == '2':
                                    # Edit company name
                                    company_name = edit_job_field("Company Name", company_name, multiline=False)

                                elif review_choice == '3':
                                    # Edit job title
                                    job_title = edit_job_field("Job Title", job_title, multiline=False)

                                elif review_choice == '4':
                                    # Edit description
                                    job_description = edit_job_field("Job Description", job_description, multiline=True)

                                elif review_choice == '5':
                                    # Show full description
                                    print("\n" + "=" * 80)
                                    print("FULL JOB DESCRIPTION")
                                    print("=" * 80)
                                    print(job_description)
                                    print("=" * 80)

                                elif review_choice == '6':
                                    # Start over with manual entry
                                    print("\nSwitching to manual entry mode.")
                                    input_choice = '2'
                                    company_name = None
                                    job_title = None
                                    job_description = None
                                    break

                                else:
                                    print("Invalid choice. Please select 1-6.")

                            except (EOFError, KeyboardInterrupt):
                                print("\n\nCancelled. Using extracted details as-is.")
                                break

                except KeyboardInterrupt:
                    print("\n\nExiting...")
                    break

            # Handle manual input (either chosen initially or as fallback)
            if input_choice == '2':
                print("\nCompany Name: ", end='')
                try:
                    company_name = input().strip()
                    if company_name.lower() in ['quit', 'exit', 'q']:
                        print("\nExiting...")
                        break
                    if not company_name:
                        print("No company name provided. Please try again.")
                        continue
                except KeyboardInterrupt:
                    print("\n\nExiting...")
                    break

                print("Job Title: ", end='')
                try:
                    job_title = input().strip()
                    if job_title.lower() in ['quit', 'exit', 'q']:
                        print("\nExiting...")
                        break
                    if not job_title:
                        print("No job title provided. Please try again.")
                        continue
                except KeyboardInterrupt:
                    print("\n\nExiting...")
                    break

                # Get job description from user
                job_description = read_multiline_input(
                    "\nPaste the job description below (press Ctrl+D when done):"
                )

                if job_description is None:
                    print("\nExiting...")
                    break

                if not job_description:
                    print("No job description provided. Please try again.")
                    continue

            # Verify we have all required fields before continuing
            if not company_name or not job_title or not job_description:
                print("Missing required information. Please try again.")
                continue

            try:
                # Prepare date and greeting
                from datetime import datetime
                current_date = datetime.now().strftime("%B %d, %Y")
                greeting = f"Dear {company_name} Hiring Team,"

                # Generate cover letter with streaming
                cover_letter_parts = []
                for chunk in generator.generate_cover_letter_stream(job_description, company_name, job_title):
                    print(chunk, end='', flush=True)
                    cover_letter_parts.append(chunk)

                # Combine the body
                cover_letter_body = ''.join(cover_letter_parts)

                # Only add date if LLM didn't already include it
                if current_date in cover_letter_body[:50]:
                    # LLM already included the date, use as-is
                    cover_letter = cover_letter_body
                else:
                    # Add date at the top
                    cover_letter = f"{current_date}\n{cover_letter_body}"

                # Ensure it ends with signature
                if not cover_letter.strip().endswith(USER_NAME):
                    cover_letter = cover_letter.rstrip() + f'\n\nSincerely,\n{USER_NAME}'

                # Always show signature in preview if not already visible in streamed output
                if not cover_letter_body.strip().endswith(USER_NAME):
                    print(f"\n\nSincerely,\n{USER_NAME}")

                print("\n" + "-" * 80)

                # Feedback loop
                while True:
                    # Ask if user wants to save or provide feedback
                    print("\nOptions:")
                    print("  (1) Save this version")
                    print("  (2) Provide feedback for revision")
                    print("  (3) Start over with new job description")
                    print("  (4) Exit")
                    print("\nWhat would you like to do? [1]: ", end='')

                    try:
                        choice = input().strip() or '1'

                        if choice == '2':
                            # Get feedback
                            print("\nDescribe the changes you'd like to see in the cover letter.")
                            print("(Be specific: e.g., 'Add more about my leadership experience',")
                            print(" 'Make the tone more formal', 'Emphasize technical skills')")
                            print("\nYour feedback (press Ctrl+D when done):")

                            user_feedback = read_multiline_input("")
                            if user_feedback is None or not user_feedback.strip():
                                print("No feedback provided, skipping revision.")
                                continue

                            # Use feedback directly (no enhancement)
                            # Regenerate with user's feedback AS-IS
                            cover_letter_parts = []
                            for chunk in generator.revise_cover_letter_stream(
                                cover_letter,
                                user_feedback,
                                job_description,
                                company_name,
                                job_title
                            ):
                                print(chunk, end='', flush=True)
                                cover_letter_parts.append(chunk)

                            # Combine the body
                            cover_letter_body = ''.join(cover_letter_parts)

                            # Only add date if LLM didn't already include it
                            if current_date in cover_letter_body[:50]:
                                # LLM already included the date, use as-is
                                cover_letter = cover_letter_body
                            else:
                                # Add date at the top
                                cover_letter = f"{current_date}\n{cover_letter_body}"

                            # Ensure it ends with signature
                            if not cover_letter.strip().endswith(USER_NAME):
                                cover_letter = cover_letter.rstrip() + f'\n\nSincerely,\n{USER_NAME}'

                            # Always show signature in preview if not already visible in streamed output
                            if not cover_letter_body.strip().endswith(USER_NAME):
                                print(f"\n\nSincerely,\n{USER_NAME}")

                            print("\n" + "-" * 80)

                            # META-LEARNING: Track feedback and check for patterns
                            if feedback_tracker and system_improver:
                                try:
                                    # Track the feedback
                                    feedback_tracker.add_feedback(user_feedback, company_name, job_title)

                                    # Check for recurring patterns
                                    pattern = feedback_tracker.detect_recurring_pattern(threshold=3)

                                    if pattern:
                                        category, count, examples = pattern

                                        print("\n" + "=" * 80)
                                        print("💡 SYSTEM IMPROVEMENT SUGGESTION")
                                        print("=" * 80)
                                        print(f"\nI've noticed you've given similar feedback {count} times:")
                                        print(f"Category: {category.replace('_', ' ').title()}")
                                        print("\nExamples:")
                                        for ex in examples[-3:]:
                                            print(f'  - "{ex}"')
                                        print()

                                        # Generate improvement suggestion
                                        print("Analyzing patterns to suggest permanent improvements to the generator...")
                                        result = system_improver.suggest_and_show(category, examples, count)

                                        if result:
                                            diff_text, improved_prompt, explanation, data_note = result

                                            print("\n" + "=" * 80)
                                            print("💡 GENERATOR IMPROVEMENT SUGGESTION")
                                            print("=" * 80)
                                            print(f"\nWhy you keep giving this feedback: {explanation}")
                                            print("\nProposed fix: Update system_prompt.txt to automatically address this")
                                            print("in all future cover letters, so you never have to ask again.")

                                            if data_note and data_note.lower() != "none":
                                                print(f"\n📊 Data suggestion: {data_note}")
                                            print()

                                            # Show abbreviated diff (just the additions)
                                            print("Changes that would be made:")
                                            print("-" * 80)
                                            diff_lines = diff_text.split('\n')
                                            for line in diff_lines:
                                                if line.startswith('+') and not line.startswith('+++'):
                                                    print(line)
                                            print("-" * 80)
                                            print()

                                            print("Would you like to apply this permanent improvement?")
                                            print("  (y) Yes, update the system prompt")
                                            print("  (n) No, keep asking me each time")
                                            print("  (v) View full diff")
                                            print("\nChoice [n]: ", end='')

                                            try:
                                                improve_choice = input().strip().lower() or 'n'

                                                if improve_choice == 'v':
                                                    print("\nFull diff:")
                                                    print(diff_text)
                                                    print("\nApply this improvement? (y/n) [n]: ", end='')
                                                    improve_choice = input().strip().lower() or 'n'

                                                if improve_choice == 'y':
                                                    system_improver.apply_improvement(improved_prompt)
                                                    feedback_tracker.clear_category(category)
                                                    print("\n✓ System prompt updated successfully!")
                                                    print("✓ Future cover letters will automatically incorporate this improvement.")
                                                    print(f"✓ Cleared {count} feedback entries for '{category}' category.")
                                                else:
                                                    print("\nImprovement not applied. I'll keep tracking this feedback.")

                                            except (EOFError, KeyboardInterrupt):
                                                print("\n\nImprovement not applied.")

                                except Exception as e:
                                    print(f"\nNote: Meta-learning feature encountered an issue: {e}")

                            # Continue the loop to ask again

                        elif choice == '1':
                            # Save the cover letter
                            break  # Exit feedback loop to save

                        elif choice == '3':
                            # Start over
                            cover_letter = None
                            break

                        elif choice == '4':
                            # Exit program
                            print("\nExiting...")
                            sys.exit(0)

                        else:
                            print("Invalid choice, please try again.")

                    except EOFError:
                        # Treat EOF as save
                        break
                    except KeyboardInterrupt:
                        print("\n\nOperation cancelled.")
                        break

                # If user chose to start over, skip saving
                if cover_letter is None:
                    continue

                # Save/validate loop - allows regenerating if signature is cut off
                save_and_validate_complete = False
                while not save_and_validate_complete:
                    # Save the cover letter as PDF and validate signature
                    validation_result = save_cover_letter(cover_letter, company_name, job_title)

                    # Check if signature validation failed
                    if not validation_result.is_valid and validation_result.confidence in ["high", "medium"]:
                        print("\n" + "=" * 80)
                        print("⚠ SIGNATURE ISSUE DETECTED")
                        print("=" * 80)
                        print(f"\nThe signature appears to be cut off or not fully visible.")
                        print(f"Details: {validation_result.message}")
                        if validation_result.details:
                            print(f"Additional info: {validation_result.details}")

                        print("\nWhat would you like to do?")
                        print("  (1) Regenerate a shorter version")
                        print("  (2) Manually revise to shorten")
                        print("  (3) Keep the current version")
                        print("\nChoice [1]: ", end='')

                        try:
                            shorten_choice = input().strip() or '1'

                            if shorten_choice == '1':
                                # Determine shortening approach based on validation details
                                details_lower = (validation_result.details or "").lower()
                                message_lower = validation_result.message.lower()

                                # Try to extract word count from details
                                import re
                                word_match = re.search(r'approximately\s+(\d+)\s+words?\s+(?:are\s+)?cut\s+off', details_lower)

                                if word_match:
                                    # Precise shortening based on actual word count
                                    words_cut_off = int(word_match.group(1))
                                    # Suggest removing slightly more to ensure it fits (add 10-20%)
                                    words_to_remove = int(words_cut_off * 1.15)
                                    shortening_feedback = f"Revise the cover letter to be approximately {words_to_remove} words shorter to ensure the signature fits on one page. Keep all key achievements but make the content more concise."
                                    print(f"\nRegenerating with targeted shortening (approximately {words_cut_off} words cut off, removing ~{words_to_remove} words)...")
                                elif "only signature" in details_lower and "body text fits" in details_lower:
                                    # Just signature cut off, minimal shortening needed
                                    shortening_feedback = "Revise to be slightly shorter (about 15-25 words) to make room for the signature. Keep all key achievements and important details - just trim minimally."
                                    print("\nRegenerating with minimal shortening (just signature needs space)...")
                                else:
                                    # Default: moderate shortening
                                    shortening_feedback = "Make the cover letter more concise to ensure the signature fits. Remove 2-3 sentences or combine points where possible, keeping the most impactful achievements."
                                    print("\nRegenerating with moderate shortening...")

                                print(f"Feedback: {shortening_feedback}")
                                print()

                                # Regenerate with automatic feedback to shorten
                                cover_letter_parts = []
                                for chunk in generator.revise_cover_letter_stream(
                                    cover_letter,
                                    shortening_feedback,
                                    job_description,
                                    company_name,
                                    job_title
                                ):
                                    print(chunk, end='', flush=True)
                                    cover_letter_parts.append(chunk)

                                # Combine the body
                                cover_letter_body = ''.join(cover_letter_parts)

                                # Only add date if LLM didn't already include it
                                if current_date in cover_letter_body[:50]:
                                    # LLM already included the date, use as-is
                                    cover_letter = cover_letter_body
                                else:
                                    # Add date at the top
                                    cover_letter = f"{current_date}\n{cover_letter_body}"

                                # Ensure it ends with signature
                                if not cover_letter.strip().endswith(USER_NAME):
                                    cover_letter = cover_letter.rstrip() + f'\n\nSincerely,\n{USER_NAME}'

                                # Always show signature in preview if not already visible in streamed output
                                if not cover_letter_body.strip().endswith(USER_NAME):
                                    print(f"\n\nSincerely,\n{USER_NAME}")

                                print("\n" + "-" * 80)

                                # Track this automatic feedback for meta-learning
                                if feedback_tracker:
                                    feedback_tracker.add_feedback(shortening_feedback, company_name, job_title)

                                # Now give user chance to review shortened version before saving
                                print("\n✓ Shortened version generated.")
                                print("\nReturning to options so you can review and choose to save or revise further...")
                                save_and_validate_complete = 'manual_revision'
                                break  # Break out to return to feedback loop

                            elif shorten_choice == '2':
                                # User wants to manually revise - go back to feedback loop
                                print("\nReturning to feedback options. You can now provide manual revisions.")
                                # Break out of save/validate loop and set flag to return to feedback loop
                                save_and_validate_complete = 'manual_revision'
                                break

                            else:  # choice == '3' or other
                                print("\nKeeping current version. The PDF has been saved.")
                                save_and_validate_complete = True

                        except (EOFError, KeyboardInterrupt):
                            print("\n\nKeeping current version.")
                            save_and_validate_complete = True
                    else:
                        # Validation passed or was skipped
                        save_and_validate_complete = True

                # If user chose manual revision, go back to feedback loop
                if save_and_validate_complete == 'manual_revision':
                    continue  # Go back to "while True" feedback loop at line 426

                # Ask if user wants to add to job tracking sheet
                if job_tracker and job_url:
                    print("\n" + "=" * 80)
                    print("Would you like to add this to your job tracking sheet?")
                    print(f"  Company: {company_name}")
                    print(f"  Job: {job_title}")
                    print(f"  URL: {job_url}")
                    print("\nAdd to tracking sheet? (y/n) [n]: ", end='')

                    try:
                        track_choice = input().strip().lower() or 'n'
                        if track_choice == 'y':
                            success = job_tracker.add_job_application(
                                company_name=company_name,
                                job_title=job_title,
                                job_url=job_url
                            )
                            if not success:
                                print("Could not add to tracking sheet. See error messages above.")
                    except (EOFError, KeyboardInterrupt):
                        print("\n\nSkipping job tracker.")
                    except Exception as e:
                        print(f"\nError adding to tracking sheet: {e}")
                    print()

                # Loop continues to prompt for another job description

            except KeyboardInterrupt:
                print("\n\nOperation cancelled.")
                continue
            except Exception as e:
                print(f"\nError generating cover letter: {e}")
                print("Please try again.")
                continue

    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)


if __name__ == "__main__":
    main()
