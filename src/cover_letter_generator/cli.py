"""Command-line interface for cover letter generation."""

import os
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from .generator import CoverLetterGenerator
from .pdf_generator_template import generate_cover_letter_pdf
from .utils import create_folder_name_from_details

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
    print("  1. Enter the company name and job title")
    print("  2. Paste the job description (press Ctrl+D when done)")
    print("  3. The cover letter will be generated and displayed")
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


def save_cover_letter(
    cover_letter: str,
    company_name: str = None,
    job_title: str = None,
    output_dir: Path = None
):
    """Save the cover letter to a PDF file.

    Args:
        cover_letter: The cover letter text
        company_name: The company name
        job_title: The job title
        output_dir: Directory to save the cover letter (default: iCloud Documents/Cover Letters)
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

        # Main loop
        while True:
            # Get company name and job title
            print("\n" + "-" * 80)
            print("Company Name: ", end='')
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

            try:
                # Generate cover letter with streaming
                cover_letter_parts = []
                for chunk in generator.generate_cover_letter_stream(job_description, company_name, job_title):
                    print(chunk, end='', flush=True)
                    cover_letter_parts.append(chunk)

                print("\n" + "-" * 80)

                # Combine all parts
                cover_letter = ''.join(cover_letter_parts)

                # Ensure it ends with signature
                if not cover_letter.strip().endswith(USER_NAME):
                    cover_letter = cover_letter.rstrip() + f'\n\nSincerely,\n{USER_NAME}'

                # Feedback loop
                while True:
                    # Ask if user wants to provide feedback or save
                    print("\nOptions:")
                    print("  (1) Provide feedback for revision")
                    print("  (2) Save this version")
                    print("  (3) Start over with new job description")
                    print("  (4) Exit")
                    print("\nWhat would you like to do? [2]: ", end='')

                    try:
                        choice = input().strip() or '2'

                        if choice == '1':
                            # Get feedback
                            print("\nDescribe the changes you'd like to see in the cover letter.")
                            print("(Be specific: e.g., 'Add more about my leadership experience',")
                            print(" 'Make the tone more formal', 'Emphasize technical skills')")
                            print("\nYour feedback (press Ctrl+D when done):")

                            feedback = read_multiline_input("")
                            if feedback is None or not feedback.strip():
                                print("No feedback provided, skipping revision.")
                                continue

                            # Regenerate with feedback
                            cover_letter_parts = []
                            for chunk in generator.revise_cover_letter_stream(
                                cover_letter,
                                feedback,
                                job_description,
                                company_name,
                                job_title
                            ):
                                print(chunk, end='', flush=True)
                                cover_letter_parts.append(chunk)

                            print("\n" + "-" * 80)
                            cover_letter = ''.join(cover_letter_parts)

                            # Ensure it ends with signature
                            if not cover_letter.strip().endswith(USER_NAME):
                                cover_letter = cover_letter.rstrip() + f'\n\nSincerely,\n{USER_NAME}'
                            # Continue the loop to ask again

                        elif choice == '2':
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

                # Save the cover letter as PDF
                save_cover_letter(cover_letter, company_name, job_title)

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
