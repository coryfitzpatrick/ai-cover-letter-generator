"""Job posting parser for extracting details from URLs."""

import os
import re
from typing import Optional, Tuple
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class JobPosting:
    """Structured job posting information."""
    company_name: str
    job_title: str
    job_description: str
    url: str

    def __str__(self):
        return f"{self.company_name} - {self.job_title}"


def fetch_webpage(url: str, timeout: int = 10) -> Optional[str]:
    """Fetch webpage content from URL.

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds

    Returns:
        HTML content as string or None if failed
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching URL: {e}")
        return None


def fetch_webpage_with_playwright(url: str, timeout: int = 30000) -> Optional[Tuple[str, str]]:
    """Fetch webpage content using Playwright (handles JavaScript-rendered pages).

    Args:
        url: URL to fetch
        timeout: Page load timeout in milliseconds (default: 30 seconds)

    Returns:
        Tuple of (HTML content, plain text) or (None, None) if failed
    """
    try:
        from playwright.sync_api import sync_playwright

        # Try to import stealth plugin for better bot detection bypass
        try:
            from playwright_stealth.stealth import Stealth
            stealth = Stealth()
            has_stealth = True
            print("  Using headless browser with stealth mode enabled...")
        except ImportError:
            has_stealth = False
            stealth = None
            print("  Using headless browser (stealth mode not available)...")

        with sync_playwright() as p:
            # Launch browser with more realistic settings to avoid bot detection
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process'
                ]
            )

            # Create context with realistic browser settings
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='en-US',
                timezone_id='America/New_York',
                # Add permissions to avoid detection
                permissions=['geolocation']
            )

            page = context.new_page()

            # Apply stealth mode if available
            if has_stealth:
                stealth.apply_stealth_sync(page)

            # Set extra headers
            page.set_extra_http_headers({
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Upgrade-Insecure-Requests': '1'
            })

            # Navigate to URL with timeout
            page.goto(url, timeout=timeout, wait_until='networkidle')

            # Wait for content to load (longer wait for ADP and similar sites)
            page.wait_for_timeout(8000)  # 8 seconds for dynamic content

            # Get both HTML and clean text
            html = page.content()
            text = page.inner_text('body')  # Get clean rendered text without HTML tags

            # Close browser
            context.close()
            browser.close()

            return html, text

    except ImportError:
        print("  Error: Playwright not installed. Install with: pip install playwright")
        print("  Then run: playwright install chromium")
        return None, None
    except Exception as e:
        print(f"  Error fetching with Playwright: {e}")
        return None, None


def clean_job_title(title: str) -> str:
    """Clean job title by removing parenthetical content.

    Args:
        title: Job title string

    Returns:
        Cleaned job title without parentheses

    Examples:
        "Mobile/Web Software Engineering Manager (Remote - USA)" -> "Mobile/Web Software Engineering Manager"
        "Senior Engineer (Full-time)" -> "Senior Engineer"
    """
    # Remove anything in parentheses and trim whitespace
    cleaned = re.sub(r'\s*\([^)]*\)', '', title).strip()
    return cleaned


def extract_text_from_html(html: str) -> str:
    """Extract clean text from HTML content.

    Args:
        html: HTML content

    Returns:
        Cleaned text content
    """
    soup = BeautifulSoup(html, 'html.parser')

    # First, try to extract JSON-LD structured data (common on job boards like Ashby, Greenhouse, etc.)
    json_ld_scripts = soup.find_all('script', type='application/ld+json')
    for script in json_ld_scripts:
        try:
            import json
            data = json.loads(script.string)
            # Check if it's a JobPosting
            if isinstance(data, dict) and data.get('@type') == 'JobPosting':
                # Extract the description and clean HTML tags from it
                description = data.get('description', '')
                if description:
                    # Parse the description HTML to get clean text
                    desc_soup = BeautifulSoup(description, 'html.parser')
                    description_text = desc_soup.get_text()

                    # Build a structured text with key fields
                    structured_text = f"""
Job Title: {data.get('title', 'Unknown')}
Company: {data.get('hiringOrganization', {}).get('name', 'Unknown')}
Location: {data.get('jobLocation', {}).get('address', {}).get('addressLocality', 'Unknown')}
Employment Type: {data.get('employmentType', 'Unknown')}

Job Description:
{description_text}
"""
                    return structured_text.strip()
        except Exception:
            # If JSON-LD parsing fails, fall back to regular HTML extraction
            pass

    # Fallback: Remove script and style elements
    for script in soup(["script", "style", "header", "footer", "nav"]):
        script.decompose()

    # Get text
    text = soup.get_text()

    # Clean up whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)

    return text


def parse_job_posting_with_llm(text: str, url: str) -> Optional[JobPosting]:
    """Parse job posting text using LLM to extract structured information.

    Args:
        text: Job posting text
        url: Original URL

    Returns:
        JobPosting object or None if parsing failed
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY not found in environment variables")
        return None

    try:
        client = Groq(api_key=api_key)

        # Show what text we're working with for debugging
        print(f"\n  First 500 characters of text being analyzed:")
        print("  " + "=" * 76)
        print("  " + text[:500].replace('\n', '\n  '))
        print("  " + "=" * 76)
        print()

        # Limit text length to avoid token limits (keep first 8000 chars which is plenty for a job posting)
        text_sample = text[:8000]

        prompt = f"""Extract the company name and job title from this job posting.

CRITICAL INSTRUCTIONS:
- Look at the BEGINNING of the text - the job title is usually in the first few lines
- Respond with ONLY the company name and job title - NO explanations, NO extra text
- If you cannot find something, write exactly "Unknown" and nothing else
- Do NOT write "The company is..." or "The job title is..." - just write the actual values

Job Posting Text:
{text_sample}

Respond in this EXACT format (no extra words):
COMPANY: [just the company name]
TITLE: [just the job title]
DESCRIPTION:
[complete job description]

Example good response:
COMPANY: Google
TITLE: Software Engineer
DESCRIPTION:
[full description here]

Example BAD response (DO NOT DO THIS):
COMPANY: The company name is Google
TITLE: The job title appears to be Software Engineer
"""

        response = client.chat.completions.create(
            model="meta-llama/llama-4-maverick-17b-128e-instruct",
            messages=[
                {"role": "system", "content": "You are a precise job posting parser. Extract information exactly as requested."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Low temperature for consistency
            max_tokens=4000,
        )

        result = response.choices[0].message.content.strip()

        # Parse the response
        company_match = re.search(r'COMPANY:\s*(.+?)(?:\n|$)', result, re.IGNORECASE)
        title_match = re.search(r'TITLE:\s*(.+?)(?:\n|$)', result, re.IGNORECASE)
        description_match = re.search(r'DESCRIPTION:\s*\n(.+)', result, re.IGNORECASE | re.DOTALL)

        if not company_match or not title_match or not description_match:
            print("\n⚠ Warning: Could not parse all fields from LLM response")
            print("=" * 80)
            print("LLM Response (first 1000 chars):")
            print(result[:1000])
            print("=" * 80)
            print(f"Company match: {bool(company_match)}")
            print(f"Title match: {bool(title_match)}")
            print(f"Description match: {bool(description_match)}")
            print()

            # Try more flexible parsing
            if not company_match:
                company_match = re.search(r'company[:\s]+(.+?)(?:\n|$)', result, re.IGNORECASE)
            if not title_match:
                title_match = re.search(r'(?:job\s+)?title[:\s]+(.+?)(?:\n|$)', result, re.IGNORECASE)
            if not description_match:
                description_match = re.search(r'(?:job\s+)?description[:\s]*\n(.+)', result, re.IGNORECASE | re.DOTALL)

            if not company_match or not title_match or not description_match:
                print("Could not parse even with flexible matching")
                return None
            else:
                print("✓ Parsed with flexible matching")

        company_name = company_match.group(1).strip()
        job_title = title_match.group(1).strip()
        job_description = description_match.group(1).strip()

        # Clean up verbose LLM responses
        # Remove explanatory prefixes like "The company name is..." or "The job title is..."
        company_name = re.sub(r'^(?:The\s+)?company(?:\s+name)?\s+(?:is|appears to be)\s+', '', company_name, flags=re.IGNORECASE).strip()
        job_title = re.sub(r'^(?:The\s+)?job\s+title\s+(?:is|appears to be)\s+', '', job_title, flags=re.IGNORECASE).strip()

        # Remove trailing explanations like ". Therefore, it is Unknown"
        company_name = re.sub(r'\.\s+Therefore.*$', '', company_name, flags=re.IGNORECASE).strip()
        job_title = re.sub(r'\.\s+Therefore.*$', '', job_title, flags=re.IGNORECASE).strip()

        # Clean job title (remove parenthetical content)
        job_title = clean_job_title(job_title)

        # Check if we got real data - but continue even if Unknown
        if company_name.lower() == "unknown" or job_title.lower() == "unknown":
            print(f"\n⚠ Note: Could not extract company name or job title from the posting")
            print(f"  Company: '{company_name}'")
            print(f"  Title: '{job_title}'")
            print(f"  You'll be able to edit these in the next step.")

        return JobPosting(
            company_name=company_name,
            job_title=job_title,
            job_description=job_description,
            url=url
        )

    except Exception as e:
        print(f"Error parsing job posting with LLM: {e}")
        return None


def parse_job_from_url(url: str) -> Optional[JobPosting]:
    """Main function to parse a job posting from a URL.

    Args:
        url: URL of the job posting

    Returns:
        JobPosting object or None if parsing failed
    """
    print(f"\nFetching job posting from URL...")

    # Try normal fetch first
    html = fetch_webpage(url)
    if not html:
        return None

    print("Extracting text from webpage...")

    # Extract text
    text = extract_text_from_html(html)

    # Check if we got meaningful content
    needs_playwright = False
    text_lower = text.lower()[:1000] if text else ""

    # Detect bot blocking or JavaScript requirement messages
    bot_detection_phrases = [
        "please switch to a supported browser",
        "you need to enable javascript",
        "javascript is required",
        "enable javascript",
        "browser is not supported",
        "please enable javascript",
        "this site requires javascript",
    ]

    has_bot_detection = any(phrase in text_lower for phrase in bot_detection_phrases)

    if not text or len(text) < 100:
        print("⚠ Insufficient text extracted from static HTML")
        needs_playwright = True
    elif has_bot_detection:
        print("⚠ Bot detection or JavaScript requirement detected")
        needs_playwright = True
    elif "javascript" in text_lower and len(text) < 500:
        print("⚠ Page appears to require JavaScript")
        needs_playwright = True

    # Try Playwright fallback if needed
    if needs_playwright:
        print("\nRetrying with JavaScript rendering...")
        html, playwright_text = fetch_webpage_with_playwright(url)
        if not html or not playwright_text:
            print("Error: Could not fetch page with JavaScript rendering")
            return None

        # Use the clean text from Playwright instead of parsing HTML
        text = playwright_text

        if not text or len(text) < 100:
            print("Error: Could not extract sufficient text even with JavaScript rendering")
            return None

    print(f"Analyzing job posting with AI (extracted {len(text)} characters)...")

    # Parse with LLM
    job_posting = parse_job_posting_with_llm(text, url)

    # If parsing failed (returned None), try Playwright if we haven't already
    if not job_posting and not needs_playwright:
        print("\n⚠ Initial parsing failed. Retrying with JavaScript rendering...")

        html, playwright_text = fetch_webpage_with_playwright(url)
        if html and playwright_text:
            # Use the clean text from Playwright
            text = playwright_text
            if text and len(text) >= 100:
                print(f"Analyzing job posting with AI (extracted {len(text)} characters)...")
                job_posting = parse_job_posting_with_llm(text, url)

    if job_posting:
        print(f"✓ Successfully parsed job posting:")
        print(f"  Company: {job_posting.company_name}")
        print(f"  Title: {job_posting.job_title}")
        print(f"  Description length: {len(job_posting.job_description)} characters")

    return job_posting


def is_valid_url(url: str) -> bool:
    """Check if a string is a valid URL.

    Args:
        url: String to check

    Returns:
        True if valid URL, False otherwise
    """
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(url) is not None
