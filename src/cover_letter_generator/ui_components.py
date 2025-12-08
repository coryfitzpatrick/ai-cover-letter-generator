"""User interface components for the CLI."""

from typing import List, Optional, Tuple

try:
    from prompt_toolkit import prompt
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.styles import Style
    from prompt_toolkit.history import InMemoryHistory
    from prompt_toolkit import print_formatted_text

    HAS_PROMPT_TOOLKIT = True
except ImportError:
    HAS_PROMPT_TOOLKIT = False

from .job_parser import is_valid_url, parse_job_from_url

# UI formatting constants
SEPARATOR_LINE = "=" * 80
DASH_LINE = "-" * 80


def print_header(title: str):
    """Print a formatted header."""
    print("\n" + SEPARATOR_LINE)
    print(title)
    print(SEPARATOR_LINE)


def print_divider():
    """Print a divider line."""
    print("\n" + DASH_LINE)


def read_multiline_input(prompt_text: str) -> Optional[str]:
    """Read multiline input from the user.

    Args:
        prompt_text: Prompt to display to the user

    Returns:
        The input text as a string, or None if cancelled
    """
    if prompt_text:
        print(prompt_text)

    if HAS_PROMPT_TOOLKIT:
        print_formatted_text(
            HTML(
                "<b><style color='ansigray'>Press [Esc] followed by [Enter] to submit. Press [Ctrl-c] to cancel.</style></b>"
            )
        )
        try:
            text = prompt(
                "",
                multiline=True,
                mouse_support=False,  # Disable mouse support to allow native terminal copy/paste
                history=InMemoryHistory(),  # Disable history to prevent Up arrow from showing previous entries
            )
            return text.strip()
        except KeyboardInterrupt:
            print("\nCancelled.")
            return None
        except EOFError:
            return None
    else:
        # Fallback for when prompt_toolkit is not installed
        lines = []
        try:
            while True:
                line = input()
                # Check for quit commands
                if line.strip().lower() in ["quit", "exit", "q"]:
                    return None
                lines.append(line)
        except EOFError:
            pass
        except KeyboardInterrupt:
            print("\n\nExiting...")
            return None

        return "\n".join(lines).strip()


def get_user_choice(options: List[str], default: str = "1", prompt_text: str = "Choice") -> str:
    """Get a validated user choice from a list of options.

    Args:
        options: List of valid option strings (e.g. ['1', '2', '3'])
        default: Default option if user presses Enter
        prompt_text: Prompt text

    Returns:
        The selected option
    """
    while True:
        try:
            if HAS_PROMPT_TOOLKIT:
                # Disable mouse support here so user can select/copy text from the terminal
                choice = prompt(f"\n{prompt_text} [{default}]: ", mouse_support=False).strip()
            else:
                print(f"\n{prompt_text} [{default}]: ", end="")
                choice = input().strip()

            choice = choice or default

            if choice in options:
                return choice
            # Check for exit
            if choice.lower() in ["quit", "exit", "q"]:
                return "q"
            print(f"Invalid choice. Please select from: {', '.join(options)}")
        except (KeyboardInterrupt, EOFError):
            return "q"


def edit_job_field(field_name: str, current_value: str, multiline: bool = False) -> str:
    """Allow user to edit a job field.

    Args:
        field_name: Name of the field being edited
        current_value: Current value
        multiline: Whether this is a multiline field

    Returns:
        Updated value or current value if unchanged
    """
    print(
        f"\nCurrent {field_name}: "
        f"{current_value if not multiline else f'({len(current_value)} characters)'}"
    )

    if multiline:
        print(f"\nEnter new {field_name}:")
        new_value = read_multiline_input("")
        if new_value is None or not new_value.strip():
            print(f"Keeping current {field_name}.")
            return current_value
        return new_value
    else:
        try:
            if HAS_PROMPT_TOOLKIT:
                print(f"Enter new {field_name} (or press Enter to keep current):")
                new_value = prompt("> ", default=current_value, mouse_support=False).strip()
                # If user just hit enter with default, it returns default.
                # But we want to allow them to clear it? No, usually keep current.
                # Actually prompt_toolkit default puts the text there to edit.
                # If they clear it, it returns empty string.
            else:
                print(f"Enter new {field_name} (or press Enter to keep current): ", end="")
                new_value = input().strip()

            if not new_value:
                # If they cleared it or just hit enter (without default in input), keep current
                # With prompt_toolkit default, new_value will be the current_value if they just hit enter
                # If they explicitly cleared it, we might want to allow that?
                # But the logic says "keep current".
                # Let's stick to the original logic: empty input = keep current.
                # For prompt_toolkit with default, if they accept default, new_value == current_value.
                return new_value if new_value else current_value

            return new_value
        except (KeyboardInterrupt, EOFError):
            return current_value


def show_job_details(company_name: str, job_title: str, job_description: str):
    """Display job details for review."""
    print_header("EXTRACTED JOB DETAILS")
    print(f"\nCompany Name: {company_name}")
    print(f"Job Title: {job_title}")
    print(f"\nJob Description ({len(job_description)} characters):")
    print(DASH_LINE)

    # Show first 2000 characters of description
    if len(job_description) > 2000:
        print(job_description[:2000])
        print(f"\n... [truncated, showing first 2000 of {len(job_description)} characters]")
    else:
        print(job_description)

    print(DASH_LINE)


def get_job_details_interactive() -> Optional[Tuple[str, str, str, str, Optional[str]]]:
    """Get job details from user via URL or manual input.

    Returns:
        Tuple of (company_name, job_title, job_description, job_url, custom_context)
        Returns None if user chooses to exit.
    """
    while True:
        company_name = None
        job_title = None
        job_description = None
        job_url = None
        custom_context = None

        # Ask for input method
        print_divider()
        print("How would you like to provide the job posting?")
        print("  (1) Paste a URL to the job posting")
        print("  (2) Enter details manually")

        input_choice = get_user_choice(["1", "2"], default="1")
        if input_choice == "q":
            return None

        # Handle URL input
        if input_choice == "1":
            print("\nJob Posting URL: ", end="")
            try:
                url = input().strip()
                if url.lower() in ["quit", "exit", "q"]:
                    return None
                if not url:
                    print("No URL provided. Please try again.")
                    continue

                # Validate URL format
                if not is_valid_url(url):
                    print(
                        "Invalid URL format. Please provide a valid URL starting with http:// or https://"
                    )
                    continue

                # Parse the job posting
                job_posting = parse_job_from_url(url)

                if not job_posting:
                    print("\nCould not parse job posting from URL.")
                    print("Would you like to enter the details manually? (y/n): ", end="")
                    retry = input().strip().lower()
                    if retry == "y":
                        input_choice = "2"  # Fall through to manual entry
                    else:
                        continue

                if job_posting:
                    # Show extracted details with full description
                    show_job_details(
                        job_posting.company_name, job_posting.job_title, job_posting.job_description
                    )

                    # Set initial values
                    company_name = job_posting.company_name
                    job_title = job_posting.job_title
                    job_description = job_posting.job_description
                    job_url = url

                    # Review and edit loop
                    while True:
                        print("\nWhat would you like to do?")
                        print("  (1) Use these details as-is")
                        print("  (2) Edit company name")
                        print("  (3) Edit job title")
                        print("  (4) Edit description")
                        print("  (5) View full description")
                        print("  (6) Start over - enter all details manually")
                        print(
                            "  (7) Add custom context for this job"
                            + (" ✓" if custom_context else "")
                        )

                        review_choice = get_user_choice(
                            ["1", "2", "3", "4", "5", "6", "7"], default="1"
                        )

                        if review_choice == "q":
                            print("\n\nCancelled. Using extracted details as-is.")
                            break
                        elif review_choice == "1":
                            print("\n✓ Using extracted details")
                            break
                        elif review_choice == "2":
                            company_name = edit_job_field(
                                "Company Name", company_name, multiline=False
                            )
                        elif review_choice == "3":
                            job_title = edit_job_field("Job Title", job_title, multiline=False)
                        elif review_choice == "4":
                            job_description = edit_job_field(
                                "Job Description", job_description, multiline=True
                            )
                        elif review_choice == "5":
                            print("\n" + SEPARATOR_LINE)
                            print("FULL JOB DESCRIPTION")
                            print(SEPARATOR_LINE)
                            print(job_description)
                            print(SEPARATOR_LINE)
                        elif review_choice == "6":
                            print("\nSwitching to manual entry mode.")
                            input_choice = "2"
                            company_name = None
                            job_title = None
                            job_description = None
                            break
                        elif review_choice == "7":
                            print("\n" + SEPARATOR_LINE)
                            print("ADD CUSTOM CONTEXT FOR THIS JOB")
                            print(SEPARATOR_LINE)
                            print("\nThis context will be used ONLY for this cover letter.")
                            print("Use this to add relevant experience not in your resume/data.")
                            print("\nEnter custom context (or press Ctrl+D when done):")
                            print(DASH_LINE)
                            custom_context = read_multiline_input("")
                            if custom_context:
                                print(f"\n✓ Custom context added ({len(custom_context)} chars)")
                            else:
                                print("\n  No context entered")

            except KeyboardInterrupt:
                return None

        # Handle manual input
        if input_choice == "2":
            custom_context = None
            print("\nCompany Name: ", end="")
            try:
                company_name = input().strip()
                if company_name.lower() in ["quit", "exit", "q"]:
                    return None
                if not company_name:
                    print("No company name provided. Please try again.")
                    continue
            except KeyboardInterrupt:
                return None

            print("Job Title: ", end="")
            try:
                job_title = input().strip()
                if job_title.lower() in ["quit", "exit", "q"]:
                    return None
                if not job_title:
                    print("No job title provided. Please try again.")
                    continue
            except KeyboardInterrupt:
                return None

            job_description = read_multiline_input(
                "\nPaste the job description below (press Ctrl+D when done):"
            )

            if job_description is None:
                return None

            if not job_description:
                print("No job description provided. Please try again.")
                continue

        # Verify we have all required fields
        if not company_name or not job_title or not job_description:
            print("Missing required information. Please try again.")
            continue

        return company_name, job_title, job_description, job_url, custom_context
