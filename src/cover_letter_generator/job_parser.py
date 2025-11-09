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

        # Limit text length to avoid token limits (keep first 8000 chars which is plenty for a job posting)
        text_sample = text[:8000]

        prompt = f"""Analyze this job posting and extract the following information:
1. Company Name
2. Job Title
3. Full Job Description (complete text of the job posting)

Job Posting Text:
{text_sample}

Respond in this EXACT format:
COMPANY: [company name]
TITLE: [job title]
DESCRIPTION:
[complete job description starting here and continuing for as many lines as needed]

Important:
- Extract the EXACT company name as it appears
- Extract the EXACT job title as it appears
- Include the COMPLETE job description with all details
- If you cannot find a field, use "Unknown" for that field
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
            print("Warning: Could not parse all fields from LLM response")
            print(f"LLM Response:\n{result}")
            return None

        company_name = company_match.group(1).strip()
        job_title = title_match.group(1).strip()
        job_description = description_match.group(1).strip()

        # Clean job title (remove parenthetical content)
        job_title = clean_job_title(job_title)

        # Validate we got real data
        if company_name.lower() == "unknown" or job_title.lower() == "unknown":
            print("Warning: Could not extract company name or job title from the posting")
            return None

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

    # Fetch webpage
    html = fetch_webpage(url)
    if not html:
        return None

    print("Extracting text from webpage...")

    # Extract text
    text = extract_text_from_html(html)
    if not text or len(text) < 100:
        print("Error: Could not extract sufficient text from webpage")
        return None

    print(f"Analyzing job posting with AI (extracted {len(text)} characters)...")

    # Parse with LLM
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
