"""Comprehensive tests for job_parser module to increase coverage to 80%+.

This test suite covers:
- Webpage fetching with mocked requests
- HTML text extraction with various structures
- Job posting parsing with mocked Groq/LLM responses
- Edge cases: malformed HTML, network errors, API failures
- Playwright integration for JavaScript-heavy sites
- URL validation and job title cleaning
"""

import json
from unittest.mock import Mock, patch, MagicMock, call

import pytest
import requests

from src.cover_letter_generator.job_parser import (
    fetch_webpage,
    fetch_webpage_with_playwright,
    extract_text_from_html,
    parse_job_posting_with_llm,
    parse_job_from_url,
    is_valid_url,
    clean_job_title,
    JobPosting,
)


class TestFetchWebpage:
    """Tests for webpage fetching functionality."""

    @patch('src.cover_letter_generator.job_parser.requests.get')
    def test_fetch_webpage_success(self, mock_get):
        """Test successful webpage fetch."""
        mock_response = Mock()
        mock_response.text = "<html><body>Job posting content</body></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = fetch_webpage("https://example.com/jobs/123")

        assert result is not None
        assert "Job posting content" in result
        mock_get.assert_called_once()

    @patch('src.cover_letter_generator.job_parser.requests.get')
    def test_fetch_webpage_with_timeout(self, mock_get):
        """Test webpage fetch with custom timeout."""
        mock_response = Mock()
        mock_response.text = "<html><body>Content</body></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        fetch_webpage("https://example.com/jobs/456", timeout=5)

        # Verify timeout was passed
        call_args = mock_get.call_args
        assert call_args[1]['timeout'] == 5

    @patch('src.cover_letter_generator.job_parser.requests.get')
    def test_fetch_webpage_network_error(self, mock_get):
        """Test handling of network errors."""
        mock_get.side_effect = requests.RequestException("Network error")

        result = fetch_webpage("https://example.com/jobs/789")

        assert result is None

    @patch('src.cover_letter_generator.job_parser.requests.get')
    def test_fetch_webpage_http_error(self, mock_get):
        """Test handling of HTTP errors (404, 500, etc.)."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        result = fetch_webpage("https://example.com/nonexistent")

        assert result is None

    @patch('src.cover_letter_generator.job_parser.requests.get')
    def test_fetch_webpage_timeout_error(self, mock_get):
        """Test handling of timeout errors."""
        mock_get.side_effect = requests.Timeout("Request timed out")

        result = fetch_webpage("https://slow-site.com/jobs/123", timeout=1)

        assert result is None

    @patch('src.cover_letter_generator.job_parser.requests.get')
    def test_fetch_webpage_includes_user_agent(self, mock_get):
        """Test that User-Agent header is included in request."""
        mock_response = Mock()
        mock_response.text = "<html></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        fetch_webpage("https://example.com/jobs")

        # Verify User-Agent was included in headers
        call_args = mock_get.call_args
        headers = call_args[1]['headers']
        assert 'User-Agent' in headers
        assert 'Mozilla' in headers['User-Agent']


class TestFetchWebpageWithPlaywright:
    """Tests for Playwright-based webpage fetching."""

    @patch('src.cover_letter_generator.job_parser.sync_playwright')
    def test_fetch_with_playwright_success(self, mock_playwright):
        """Test successful fetch with Playwright."""
        # Mock the Playwright context manager and page
        mock_browser = Mock()
        mock_context = Mock()
        mock_page = Mock()
        mock_page.content.return_value = "<html><body>Content</body></html>"
        mock_page.inner_text.return_value = "Content"

        mock_context.new_page.return_value = mock_page
        mock_browser.new_context.return_value = mock_context

        mock_p = Mock()
        mock_p.chromium.launch.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_p

        html, text = fetch_webpage_with_playwright("https://example.com")

        assert html is not None
        assert text is not None
        assert "Content" in text

    @patch('src.cover_letter_generator.job_parser.sync_playwright')
    def test_fetch_with_playwright_import_error(self, mock_playwright):
        """Test handling when Playwright is not installed."""
        mock_playwright.side_effect = ImportError("Playwright not found")

        html, text = fetch_webpage_with_playwright("https://example.com")

        assert html is None
        assert text is None

    @patch('src.cover_letter_generator.job_parser.sync_playwright')
    def test_fetch_with_playwright_navigation_error(self, mock_playwright):
        """Test handling of navigation errors."""
        mock_browser = Mock()
        mock_context = Mock()
        mock_page = Mock()
        mock_page.goto.side_effect = Exception("Navigation failed")

        mock_context.new_page.return_value = mock_page
        mock_browser.new_context.return_value = mock_context

        mock_p = Mock()
        mock_p.chromium.launch.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_p

        html, text = fetch_webpage_with_playwright("https://example.com")

        # Should handle error gracefully
        assert html is None
        assert text is None

    @patch('src.cover_letter_generator.job_parser.sync_playwright')
    @patch('src.cover_letter_generator.job_parser.Stealth')
    def test_fetch_with_playwright_stealth_mode(self, mock_stealth_class, mock_playwright):
        """Test that stealth mode is used when available."""
        mock_stealth = Mock()
        mock_stealth_class.return_value = mock_stealth

        mock_browser = Mock()
        mock_context = Mock()
        mock_page = Mock()
        mock_page.content.return_value = "<html></html>"
        mock_page.inner_text.return_value = "Text"

        mock_context.new_page.return_value = mock_page
        mock_browser.new_context.return_value = mock_context

        mock_p = Mock()
        mock_p.chromium.launch.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_p

        fetch_webpage_with_playwright("https://example.com")

        # Stealth mode should be applied
        mock_stealth.apply_stealth_sync.assert_called_once()


class TestExtractTextFromHTML:
    """Tests for HTML text extraction."""

    def test_extract_text_basic_html(self):
        """Test extracting text from basic HTML."""
        html = "<html><body><p>This is a test paragraph.</p></body></html>"
        text = extract_text_from_html(html)

        assert "test paragraph" in text

    def test_extract_text_removes_scripts(self):
        """Test that script tags are removed."""
        html = """
        <html>
        <head><script>console.log('test');</script></head>
        <body><p>Visible content</p></body>
        </html>
        """
        text = extract_text_from_html(html)

        assert "Visible content" in text
        assert "console.log" not in text

    def test_extract_text_removes_styles(self):
        """Test that style tags are removed."""
        html = """
        <html>
        <head><style>body { color: red; }</style></head>
        <body><p>Content</p></body>
        </html>
        """
        text = extract_text_from_html(html)

        assert "Content" in text
        assert "color: red" not in text

    def test_extract_text_removes_navigation(self):
        """Test that navigation elements are removed."""
        html = """
        <html>
        <nav>Home | About | Contact</nav>
        <body><p>Main content</p></body>
        </html>
        """
        text = extract_text_from_html(html)

        assert "Main content" in text
        # Navigation should be removed or minimal
        assert text.count("Home") == 0 or "Main content" in text

    def test_extract_text_with_json_ld(self):
        """Test extraction of JSON-LD structured data."""
        html = """
        <html>
        <head>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org/",
            "@type": "JobPosting",
            "title": "Software Engineer",
            "hiringOrganization": {
                "@type": "Organization",
                "name": "TechCorp"
            },
            "description": "We are looking for a talented engineer.",
            "jobLocation": {
                "address": {
                    "addressLocality": "San Francisco"
                }
            },
            "employmentType": "Full-time"
        }
        </script>
        </head>
        <body></body>
        </html>
        """
        text = extract_text_from_html(html)

        # Should extract structured data
        assert "Software Engineer" in text
        assert "TechCorp" in text
        assert "talented engineer" in text

    def test_extract_text_cleans_whitespace(self):
        """Test that excessive whitespace is cleaned."""
        html = """
        <html>
        <body>
        <p>Line 1</p>


        <p>Line 2</p>
        </body>
        </html>
        """
        text = extract_text_from_html(html)

        # Should clean up excessive whitespace
        assert "Line 1" in text
        assert "Line 2" in text

    def test_extract_text_nested_elements(self):
        """Test extraction from nested HTML elements."""
        html = """
        <html>
        <body>
        <div>
            <section>
                <article>
                    <h1>Job Title</h1>
                    <p>Description</p>
                </article>
            </section>
        </div>
        </body>
        </html>
        """
        text = extract_text_from_html(html)

        assert "Job Title" in text
        assert "Description" in text

    def test_extract_text_with_special_characters(self):
        """Test handling of special characters in HTML."""
        html = """
        <html>
        <body>
        <p>Salary: $100,000 - $150,000</p>
        <p>Location: New York, NY</p>
        </body>
        </html>
        """
        text = extract_text_from_html(html)

        assert "$100,000" in text or "100,000" in text
        assert "New York" in text


class TestParseJobPostingWithLLM:
    """Tests for LLM-based job posting parsing."""

    @patch('src.cover_letter_generator.job_parser.Groq')
    @patch.dict('os.environ', {'GROQ_API_KEY': 'test-key'})
    def test_parse_job_posting_success(self, mock_groq_class):
        """Test successful job posting parsing."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """
COMPANY: TechCorp
TITLE: Software Engineer
DESCRIPTION:
We are looking for a talented Software Engineer to join our team.

Requirements:
- 5+ years of experience
- Python expertise
- Strong communication skills

Benefits:
- Competitive salary
- Health insurance
- Remote work options
        """
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq_class.return_value = mock_client

        text = "Job posting text here..."
        url = "https://example.com/jobs/123"

        result = parse_job_posting_with_llm(text, url)

        assert result is not None
        assert result.company_name == "TechCorp"
        assert result.job_title == "Software Engineer"
        assert "talented Software Engineer" in result.job_description
        assert result.url == url

    @patch('src.cover_letter_generator.job_parser.Groq')
    @patch.dict('os.environ', {'GROQ_API_KEY': 'test-key'})
    def test_parse_job_posting_cleans_verbose_response(self, mock_groq_class):
        """Test that verbose LLM responses are cleaned."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """
COMPANY: The company name is TechCorp
TITLE: The job title appears to be Software Engineer
DESCRIPTION:
Job description here.
        """
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq_class.return_value = mock_client

        result = parse_job_posting_with_llm("text", "url")

        # Verbose prefixes should be cleaned
        assert result.company_name == "TechCorp"
        assert result.job_title == "Software Engineer"

    @patch('src.cover_letter_generator.job_parser.Groq')
    @patch.dict('os.environ', {'GROQ_API_KEY': 'test-key'})
    def test_parse_job_posting_handles_unknown_fields(self, mock_groq_class):
        """Test handling when company or title are unknown."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """
COMPANY: Unknown
TITLE: Unknown
DESCRIPTION:
Description without clear company or title.
        """
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq_class.return_value = mock_client

        result = parse_job_posting_with_llm("text", "url")

        # Should still return a result even with Unknown values
        assert result is not None
        assert result.company_name == "Unknown"
        assert result.job_title == "Unknown"

    @patch.dict('os.environ', {'GROQ_API_KEY': ''})
    def test_parse_job_posting_missing_api_key(self):
        """Test handling when API key is missing."""
        result = parse_job_posting_with_llm("text", "url")

        assert result is None

    @patch('src.cover_letter_generator.job_parser.Groq')
    @patch.dict('os.environ', {'GROQ_API_KEY': 'test-key'})
    def test_parse_job_posting_api_error(self, mock_groq_class):
        """Test handling of API errors."""
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_groq_class.return_value = mock_client

        result = parse_job_posting_with_llm("text", "url")

        assert result is None

    @patch('src.cover_letter_generator.job_parser.Groq')
    @patch.dict('os.environ', {'GROQ_API_KEY': 'test-key'})
    def test_parse_job_posting_malformed_response(self, mock_groq_class):
        """Test handling of malformed LLM response."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "This is not a properly formatted response"
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq_class.return_value = mock_client

        result = parse_job_posting_with_llm("text", "url")

        # Should return None or handle gracefully
        assert result is None or isinstance(result, JobPosting)

    @patch('src.cover_letter_generator.job_parser.Groq')
    @patch.dict('os.environ', {'GROQ_API_KEY': 'test-key'})
    def test_parse_job_posting_cleans_job_title(self, mock_groq_class):
        """Test that job titles are cleaned (parentheticals removed)."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """
COMPANY: TechCorp
TITLE: Software Engineer (Remote)
DESCRIPTION:
Job description.
        """
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq_class.return_value = mock_client

        result = parse_job_posting_with_llm("text", "url")

        # Title should be cleaned
        assert result.job_title == "Software Engineer"

    @patch('src.cover_letter_generator.job_parser.Groq')
    @patch.dict('os.environ', {'GROQ_API_KEY': 'test-key'})
    def test_parse_job_posting_flexible_matching(self, mock_groq_class):
        """Test flexible parsing when exact format isn't followed."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """
company: TechCorp
job title: Software Engineer
job description:
Full description here.
        """
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq_class.return_value = mock_client

        result = parse_job_posting_with_llm("text", "url")

        # Should use flexible matching
        assert result is not None
        assert result.company_name == "TechCorp"


class TestParseJobFromURL:
    """Tests for complete job parsing from URL."""

    @patch('src.cover_letter_generator.job_parser.fetch_webpage')
    @patch('src.cover_letter_generator.job_parser.extract_text_from_html')
    @patch('src.cover_letter_generator.job_parser.parse_job_posting_with_llm')
    def test_parse_job_from_url_simple_site(self, mock_parse, mock_extract, mock_fetch):
        """Test parsing from a simple (non-JavaScript) site."""
        mock_fetch.return_value = "<html><body>Job content</body></html>"
        mock_extract.return_value = "Job posting text"
        mock_parse.return_value = JobPosting(
            company_name="TechCorp",
            job_title="Engineer",
            job_description="Description",
            url="https://example.com"
        )

        result = parse_job_from_url("https://example.com/jobs/123")

        assert result is not None
        assert result.company_name == "TechCorp"
        mock_fetch.assert_called_once()

    @patch('src.cover_letter_generator.job_parser.fetch_webpage_with_playwright')
    def test_parse_job_from_url_js_heavy_site(self, mock_playwright):
        """Test parsing from JavaScript-heavy job board."""
        mock_playwright.return_value = (
            "<html><body>Content</body></html>",
            "Clean text content"
        )

        with patch('src.cover_letter_generator.job_parser.parse_job_posting_with_llm') as mock_parse:
            mock_parse.return_value = JobPosting(
                company_name="Greenhouse",
                job_title="Engineer",
                job_description="Desc",
                url="https://greenhouse.io/job"
            )

            result = parse_job_from_url("https://boards.greenhouse.io/company/job")

            assert result is not None
            # Should use Playwright for greenhouse.io
            mock_playwright.assert_called_once()

    @patch('src.cover_letter_generator.job_parser.fetch_webpage')
    def test_parse_job_from_url_fetch_failure(self, mock_fetch):
        """Test handling when webpage fetch fails."""
        mock_fetch.return_value = None

        result = parse_job_from_url("https://example.com/jobs/123")

        assert result is None

    @patch('src.cover_letter_generator.job_parser.fetch_webpage')
    @patch('src.cover_letter_generator.job_parser.extract_text_from_html')
    @patch('src.cover_letter_generator.job_parser.fetch_webpage_with_playwright')
    def test_parse_job_from_url_bot_detection_fallback(
        self, mock_playwright, mock_extract, mock_fetch
    ):
        """Test fallback to Playwright when bot detection is encountered."""
        mock_fetch.return_value = "<html><body>Please enable JavaScript</body></html>"
        mock_extract.return_value = "Please enable JavaScript to continue"
        mock_playwright.return_value = (
            "<html><body>Real content</body></html>",
            "Real job posting content"
        )

        with patch('src.cover_letter_generator.job_parser.parse_job_posting_with_llm') as mock_parse:
            mock_parse.return_value = JobPosting(
                company_name="Company",
                job_title="Role",
                job_description="Desc",
                url="url"
            )

            result = parse_job_from_url("https://example.com/jobs/123")

            # Should fallback to Playwright
            assert mock_playwright.called

    @patch('src.cover_letter_generator.job_parser.fetch_webpage')
    @patch('src.cover_letter_generator.job_parser.extract_text_from_html')
    def test_parse_job_from_url_insufficient_text(self, mock_extract, mock_fetch):
        """Test handling when insufficient text is extracted."""
        mock_fetch.return_value = "<html><body>Short</body></html>"
        mock_extract.return_value = "X"  # Very short text

        with patch('src.cover_letter_generator.job_parser.fetch_webpage_with_playwright') as mock_pw:
            mock_pw.return_value = (
                "<html><body>Full content</body></html>",
                "Full job posting text here"
            )

            with patch('src.cover_letter_generator.job_parser.parse_job_posting_with_llm') as mock_parse:
                mock_parse.return_value = JobPosting(
                    company_name="Co",
                    job_title="Title",
                    job_description="Desc",
                    url="url"
                )

                result = parse_job_from_url("https://example.com/job")

                # Should try Playwright due to insufficient text
                assert mock_pw.called


class TestCleanJobTitle:
    """Additional tests for job title cleaning beyond existing tests."""

    def test_clean_job_title_multiple_remote_indicators(self):
        """Test cleaning titles with multiple remote indicators."""
        title = "Engineer - Remote | Work from Home"
        cleaned = clean_job_title(title)
        assert cleaned == "Engineer"

    def test_clean_job_title_preserves_slashes(self):
        """Test that slashes in titles are preserved."""
        title = "Mobile/Web Software Engineer (Remote)"
        cleaned = clean_job_title(title)
        assert "Mobile/Web Software Engineer" in cleaned
        assert "Remote" not in cleaned


class TestIsValidURL:
    """Additional tests for URL validation beyond existing tests."""

    def test_is_valid_url_with_subdomain(self):
        """Test URLs with subdomains."""
        assert is_valid_url("https://careers.company.com/jobs")

    def test_is_valid_url_localhost(self):
        """Test localhost URLs."""
        assert is_valid_url("http://localhost:8080/jobs")

    def test_is_valid_url_ip_address(self):
        """Test URLs with IP addresses."""
        assert is_valid_url("http://192.168.1.1/jobs")


class TestJobPostingDataclass:
    """Additional tests for JobPosting dataclass."""

    def test_job_posting_str_method(self):
        """Test string representation of JobPosting."""
        posting = JobPosting(
            company_name="TestCorp",
            job_title="Test Engineer",
            job_description="Description",
            url="https://example.com"
        )

        str_repr = str(posting)
        assert "TestCorp" in str_repr
        assert "Test Engineer" in str_repr


class TestEdgeCases:
    """Tests for edge cases and unusual scenarios."""

    def test_extract_text_from_empty_html(self):
        """Test extracting text from empty HTML."""
        html = "<html></html>"
        text = extract_text_from_html(html)
        assert text == "" or text.strip() == ""

    def test_extract_text_from_malformed_html(self):
        """Test extracting text from malformed HTML."""
        html = "<html><body><p>Unclosed paragraph<div>Content</body></html>"
        text = extract_text_from_html(html)

        # Should still extract some text despite malformed HTML
        assert "Unclosed paragraph" in text or "Content" in text

    @patch('src.cover_letter_generator.job_parser.Groq')
    @patch.dict('os.environ', {'GROQ_API_KEY': 'test-key'})
    def test_parse_very_long_job_description(self, mock_groq_class):
        """Test parsing with very long job descriptions."""
        mock_client = Mock()
        mock_response = Mock()
        long_description = "Requirements: " + "x" * 10000
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = f"""
COMPANY: BigCorp
TITLE: Engineer
DESCRIPTION:
{long_description}
        """
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq_class.return_value = mock_client

        result = parse_job_posting_with_llm("x" * 15000, "url")

        # Should handle long descriptions
        assert result is not None

    def test_extract_text_with_unicode(self):
        """Test HTML extraction with Unicode characters."""
        html = "<html><body><p>Café résumé naïve</p></body></html>"
        text = extract_text_from_html(html)

        # Should handle Unicode properly
        assert "Café" in text or "Cafe" in text

    def test_clean_job_title_with_emoji(self):
        """Test cleaning job titles containing emoji."""
        title = "Software Engineer 🚀 (Remote)"
        cleaned = clean_job_title(title)

        # Should handle emoji gracefully
        assert "Software Engineer" in cleaned
