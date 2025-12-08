"""Comprehensive tests for company extraction from section headers."""
import pytest
from src.cover_letter_generator.prepare_data import (
    extract_company_from_section_headers,
    parse_sections_by_company,
    extract_text_from_docx,
    chunk_text
)


class TestExtractCompanyFromSectionHeaders:
    """Test company name extraction from various header formats."""

    def test_extract_company_from_h2_achievements_at_format(self):
        """Test extracting company from '[H2]Achievements at Company:' format."""
        text = "[H2]Achievements at J&J:\n\nSome achievement here"
        company = extract_company_from_section_headers(text)
        assert company == "j&j"

    def test_extract_company_from_h2_work_at_format(self):
        """Test extracting company from '[H2]Work at Company:' format."""
        text = "[H2]Work at Google:\n\nSome work description"
        company = extract_company_from_section_headers(text)
        assert company == "google"

    def test_extract_company_from_h2_experience_at_format(self):
        """Test extracting company from '[H2]Experience at Company:' format."""
        text = "[H2]Experience at Amazon:\n\nSome experience"
        company = extract_company_from_section_headers(text)
        assert company == "amazon"

    def test_extract_company_from_h2_projects_at_format(self):
        """Test extracting company from '[H2]Projects at Company:' format."""
        text = "[H2]Projects at Microsoft:\n\nSome project"
        company = extract_company_from_section_headers(text)
        assert company == "microsoft"

    def test_extract_company_from_plain_text_format(self):
        """Test extracting company from plain text 'Achievements at Company:' format."""
        text = "Achievements at Apple:\n\nSome achievement"
        company = extract_company_from_section_headers(text)
        assert company == "apple"

    def test_extract_company_from_company_dash_format(self):
        """Test extracting company from 'Company - Achievements' format."""
        text = "[H2]Tesla - Achievements\n\nSome achievement"
        company = extract_company_from_section_headers(text)
        assert company == "tesla"

    def test_extract_company_with_multiword_name(self):
        """Test extracting multi-word company names."""
        text = "[H2]Achievements at Johnson Johnson:\n\nSome achievement"
        company = extract_company_from_section_headers(text)
        # Should extract the full company name
        assert "johnson" in company.lower()

    def test_extract_company_with_ampersand(self):
        """Test extracting company names with ampersands."""
        text = "[H2]Achievements at Procter & Gamble:\n\nSome achievement"
        company = extract_company_from_section_headers(text)
        assert "procter" in company.lower() or "gamble" in company.lower()

    def test_extract_company_no_match_returns_unknown(self):
        """Test that 'unknown' is returned when no company is found."""
        text = "Some random text without any company header"
        company = extract_company_from_section_headers(text)
        assert company == "unknown"

    def test_extract_company_ignores_generic_phrases(self):
        """Test that generic phrases like 'the company' are ignored."""
        text = "[H2]Achievements at the company:\n\nSome achievement"
        company = extract_company_from_section_headers(text)
        assert company == "unknown"

    def test_extract_company_multiple_headers_finds_first(self):
        """Test that when multiple headers exist, the first valid one is found."""
        text = """[H2]Achievements at Google:

Some Google achievement

[H2]Achievements at Amazon:

Some Amazon achievement"""
        company = extract_company_from_section_headers(text)
        assert company == "google"

    def test_extract_company_with_whitespace_variations(self):
        """Test company extraction handles various whitespace patterns."""
        test_cases = [
            "[H2]Achievements at  Google  :\n\nText",  # Extra spaces
            "[H2]  Achievements at Google:\n\nText",    # Leading spaces after H2
            "[H2]Achievements at Google:  \n\nText",    # Trailing spaces
        ]
        for text in test_cases:
            company = extract_company_from_section_headers(text)
            assert company == "google", f"Failed for: {repr(text)}"

    def test_extract_company_case_insensitive_result(self):
        """Test that company names are returned in lowercase."""
        text = "[H2]Achievements at GOOGLE:\n\nSome achievement"
        company = extract_company_from_section_headers(text)
        assert company == "google"
        assert company.islower()

    def test_extract_company_with_plus_sign(self):
        """Test extracting company names with plus signs."""
        text = "[H2]Achievements at Fitbit + Google:\n\nSome achievement"
        company = extract_company_from_section_headers(text)
        assert company == "fitbit + google"

    def test_extract_company_from_company_name_format(self):
        """Test extracting from 'Company Name: XYZ' format."""
        text = "[H2]Company Name: J&J\n\nSome achievement"
        company = extract_company_from_section_headers(text)
        assert company == "j&j"

    def test_extract_company_from_company_name_with_plus(self):
        """Test extracting from 'Company Name: XYZ' format with plus sign."""
        text = "[H2]Company Name: Fitbit + Google\n\nSome achievement"
        company = extract_company_from_section_headers(text)
        assert company == "fitbit + google"


class TestParseSectionsByCompany:
    """Test parsing documents into sections by company."""

    def test_parse_single_company_section(self):
        """Test parsing a document with a single company section."""
        text = """[H2]Achievements at Google:

Achievement 1: Did something great
Achievement 2: Did something else"""

        sections = parse_sections_by_company(text)

        assert len(sections) == 1
        section_text, company = sections[0]
        assert company == "google"
        assert "Achievement 1" in section_text
        assert "Achievement 2" in section_text

    def test_parse_multiple_company_sections(self):
        """Test parsing a document with multiple company sections."""
        text = """[H2]Achievements at Google:

Achievement 1: Did something at Google
Achievement 2: More Google work

[H2]Achievements at Amazon:

Achievement 1: Did something at Amazon
Achievement 2: More Amazon work"""

        sections = parse_sections_by_company(text)

        assert len(sections) == 2

        # First section should be Google
        google_text, google_company = sections[0]
        assert google_company == "google"
        assert "Google" in google_text
        assert "Amazon" not in google_text

        # Second section should be Amazon
        amazon_text, amazon_company = sections[1]
        assert amazon_company == "amazon"
        assert "Amazon" in amazon_text

    def test_parse_sections_preserves_h2_headers(self):
        """Test that H2 headers are included in the section text."""
        text = """[H2]Achievements at Google:

Some achievement here"""

        sections = parse_sections_by_company(text)

        assert len(sections) == 1
        section_text, _ = sections[0]
        assert "[H2]Achievements at Google:" in section_text

    def test_parse_sections_handles_unknown_company(self):
        """Test parsing when company cannot be extracted."""
        text = """[H2]Some Random Header:

Some content here"""

        sections = parse_sections_by_company(text)

        assert len(sections) == 1
        section_text, company = sections[0]
        assert company == "unknown"
        assert "Some Random Header" in section_text

    def test_parse_sections_no_h2_headers(self):
        """Test parsing a document without H2 headers."""
        text = """Just some plain text
without any headers
at all"""

        sections = parse_sections_by_company(text)

        # Should return the entire text as one section with unknown company
        assert len(sections) == 1
        section_text, company = sections[0]
        assert company == "unknown"
        assert "plain text" in section_text

    def test_parse_sections_mixed_h2_headers(self):
        """Test parsing with both company and non-company H2 headers."""
        text = """[H2]Introduction

Some intro text

[H2]Achievements at Google:

Google achievement 1

[H2]Summary

Some summary"""

        sections = parse_sections_by_company(text)

        # Should create sections based on company headers
        # The intro would be in first section (unknown)
        # Google section would be separate
        # Summary might be part of Google or separate unknown
        assert len(sections) >= 2

        # Find the Google section
        google_sections = [s for s in sections if s[1] == "google"]
        assert len(google_sections) == 1
        assert "Google achievement" in google_sections[0][0]

    def test_parse_sections_empty_sections(self):
        """Test that empty sections are handled properly."""
        text = """[H2]Achievements at Google:



[H2]Achievements at Amazon:

Some Amazon content"""

        sections = parse_sections_by_company(text)

        # Empty Google section might or might not be included depending on implementation
        # But Amazon section should definitely be there
        amazon_sections = [s for s in sections if s[1] == "amazon"]
        assert len(amazon_sections) == 1
        assert "Amazon content" in amazon_sections[0][0]

    def test_parse_sections_with_plus_signs(self):
        """Test parsing companies with plus signs in the name."""
        text = """[H2]Achievements at J&J:

J&J achievement 1
J&J achievement 2

[H2]Achievements at Fitbit + Google:

Fitbit + Google achievement 1
Fitbit + Google achievement 2"""

        sections = parse_sections_by_company(text)

        assert len(sections) == 2

        # First section should be J&J
        jj_text, jj_company = sections[0]
        assert jj_company == "j&j"
        assert "J&J achievement" in jj_text
        assert "Fitbit" not in jj_text

        # Second section should be Fitbit + Google
        fitbit_text, fitbit_company = sections[1]
        assert fitbit_company == "fitbit + google"
        assert "Fitbit + Google achievement" in fitbit_text
        assert "J&J" not in fitbit_text

    def test_parse_sections_company_name_format(self):
        """Test parsing with 'Company Name:' format."""
        text = """[H2]Company Name: J&J

J&J achievement 1
J&J achievement 2

[H2]Company Name: Fitbit + Google

Fitbit + Google achievement 1
Fitbit + Google achievement 2"""

        sections = parse_sections_by_company(text)

        assert len(sections) == 2

        # First section should be J&J
        jj_text, jj_company = sections[0]
        assert jj_company == "j&j"
        assert "J&J achievement" in jj_text
        assert "Fitbit" not in jj_text

        # Second section should be Fitbit + Google
        fitbit_text, fitbit_company = sections[1]
        assert fitbit_company == "fitbit + google"
        assert "Fitbit + Google achievement" in fitbit_text
        assert "J&J" not in fitbit_text


class TestCompanyAssociationEndToEnd:
    """End-to-end tests for company-achievement association."""

    def test_chunking_preserves_company_metadata(self):
        """Test that chunking maintains company association in metadata."""
        # Create a section with company header
        section_text = """[H2]Achievements at Google:

Achievement 1: Reduced verification time by 50% through algorithm optimization.
This was a critical improvement that saved the team 20 hours per week.

Achievement 2: Implemented Docker containerization for development environment.
New hires could now get running in 10 minutes instead of 3 days."""

        # Parse sections
        sections = parse_sections_by_company(section_text)
        assert len(sections) == 1
        text, company = sections[0]
        assert company == "google"

        # Chunk the section with metadata header
        meta_header = f"SOURCE DOCUMENT: achievements.docx\nCOMPANY: {company.upper()}"
        chunks = chunk_text(text, metadata_header=meta_header)

        # Each chunk should contain the company metadata
        for chunk in chunks:
            assert "COMPANY: GOOGLE" in chunk

    def test_multiple_companies_get_separate_chunks(self):
        """Test that achievements from different companies are in separate chunks."""
        text = """[H2]Achievements at Google:

Google Achievement 1: Did something amazing at Google.
Google Achievement 2: Another great thing at Google.

[H2]Achievements at Amazon:

Amazon Achievement 1: Did something amazing at Amazon.
Amazon Achievement 2: Another great thing at Amazon."""

        sections = parse_sections_by_company(text)

        # Should have 2 sections
        assert len(sections) == 2

        # Chunk each section separately
        all_chunks = []
        for section_text, company in sections:
            meta_header = f"COMPANY: {company.upper()}"
            section_chunks = chunk_text(section_text, metadata_header=meta_header)
            all_chunks.extend([(chunk, company) for chunk in section_chunks])

        # Verify Google chunks don't mention Amazon and vice versa
        google_chunks = [c for c, co in all_chunks if co == "google"]
        amazon_chunks = [c for c, co in all_chunks if co == "amazon"]

        assert len(google_chunks) > 0
        assert len(amazon_chunks) > 0

        # Google chunks should not contain Amazon content
        for chunk in google_chunks:
            assert "Amazon" not in chunk or "COMPANY: GOOGLE" in chunk

        # Amazon chunks should not contain Google content (except in metadata)
        for chunk in amazon_chunks:
            assert "Google" not in chunk or "COMPANY: AMAZON" in chunk

    def test_chunking_splits_large_sections_preserving_company(self):
        """Test that large company sections are split into chunks while preserving company association."""
        # Create a large achievement section
        achievement = """Achievement {}: This is a significant achievement that demonstrates
impact and value. It involved complex technical work and delivered measurable results
that benefited the entire organization."""

        achievements = "\n\n".join([achievement.format(i) for i in range(1, 11)])  # 10 achievements

        text = f"[H2]Achievements at Google:\n\n{achievements}"

        sections = parse_sections_by_company(text)
        assert len(sections) == 1
        section_text, company = sections[0]
        assert company == "google"

        # Chunk with small chunk size to force multiple chunks
        meta_header = f"COMPANY: {company.upper()}"
        chunks = chunk_text(section_text, chunk_size=600, metadata_header=meta_header)

        # Should create multiple chunks
        assert len(chunks) > 1

        # All chunks should have the Google company metadata
        for chunk in chunks:
            assert "COMPANY: GOOGLE" in chunk


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
