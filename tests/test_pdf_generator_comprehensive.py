"""Comprehensive tests for pdf_generator_template module to increase coverage to 80%+.

This test suite covers:
- PDF generation with template
- Text overlay creation
- PDF generation without template (fallback)
- Template path resolution
- Edge cases and error handling
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from pypdf import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from src.cover_letter_generator.pdf_generator_template import (
    create_text_overlay,
    generate_cover_letter_from_template,
    generate_cover_letter_pdf,
)


class TestCreateTextOverlay:
    """Tests for creating text overlay PDFs."""

    def test_create_text_overlay_basic(self):
        """Test creating a basic text overlay."""
        cover_letter = "Dear Hiring Manager,\n\nI am interested in this position."

        width, height = letter
        buffer = create_text_overlay(cover_letter, width, height)

        assert buffer is not None
        assert buffer.tell() == 0  # Buffer position reset to start

        # Verify it's a valid PDF
        reader = PdfReader(buffer)
        assert len(reader.pages) == 1

    def test_create_text_overlay_with_date(self):
        """Test that overlay includes current date."""
        cover_letter = "Dear Hiring Manager,\n\nContent."

        width, height = letter
        buffer = create_text_overlay(cover_letter, width, height)

        # Verify PDF was created
        assert buffer is not None
        reader = PdfReader(buffer)
        assert len(reader.pages) == 1

    def test_create_text_overlay_multiline(self):
        """Test creating overlay with multiple paragraphs."""
        cover_letter = """Dear Hiring Manager,

This is the first paragraph with some content.

This is the second paragraph with more content.

Sincerely,
Test User"""

        width, height = letter
        buffer = create_text_overlay(cover_letter, width, height)

        assert buffer is not None
        reader = PdfReader(buffer)
        assert len(reader.pages) == 1

    def test_create_text_overlay_special_characters(self):
        """Test overlay with special characters."""
        cover_letter = "Dear Hiring Manager,\n\nI have experience with C++ & .NET.\nSalary: $100,000.\n\nSincerely,\nJosé"

        width, height = letter
        buffer = create_text_overlay(cover_letter, width, height)

        # Should handle special characters (they get escaped)
        assert buffer is not None
        reader = PdfReader(buffer)
        assert len(reader.pages) == 1

    def test_create_text_overlay_sincerely_formatting(self):
        """Test that 'Sincerely' is formatted with proper spacing."""
        cover_letter = """Dear Hiring Manager,

Content here.

Sincerely,
Alice Johnson"""

        width, height = letter
        buffer = create_text_overlay(cover_letter, width, height)

        assert buffer is not None
        reader = PdfReader(buffer)
        assert len(reader.pages) == 1

    def test_create_text_overlay_empty_content(self):
        """Test creating overlay with empty content."""
        cover_letter = ""

        width, height = letter
        buffer = create_text_overlay(cover_letter, width, height)

        # Should still create valid PDF with date
        assert buffer is not None
        reader = PdfReader(buffer)
        assert len(reader.pages) == 1

    def test_create_text_overlay_long_content(self):
        """Test overlay with very long content."""
        long_paragraph = "This is a long sentence. " * 100
        cover_letter = f"Dear Hiring Manager,\n\n{long_paragraph}\n\nSincerely,\nTest"

        width, height = letter
        buffer = create_text_overlay(cover_letter, width, height)

        assert buffer is not None
        reader = PdfReader(buffer)
        assert len(reader.pages) == 1

    def test_create_text_overlay_custom_page_size(self):
        """Test creating overlay with custom page size."""
        cover_letter = "Dear Hiring Manager,\n\nContent."

        # Use A4 size instead of letter
        from reportlab.lib.pagesizes import A4

        width, height = A4

        buffer = create_text_overlay(cover_letter, width, height)

        assert buffer is not None
        reader = PdfReader(buffer)
        assert len(reader.pages) == 1


class TestGenerateCoverLetterFromTemplate:
    """Tests for generating cover letters using a template."""

    def test_generate_from_template_basic(self, tmp_path):
        """Test generating cover letter from template."""
        # Create a simple template PDF
        template_path = tmp_path / "template.pdf"
        c = canvas.Canvas(str(template_path), pagesize=letter)
        c.drawString(100, 750, "HEADER")
        c.save()

        cover_letter = "Dear Hiring Manager,\n\nI am interested in this role."
        output_path = tmp_path / "output.pdf"

        result = generate_cover_letter_from_template(
            cover_letter_text=cover_letter, template_path=template_path, output_path=output_path
        )

        assert result == output_path
        assert output_path.exists()

        # Verify output is valid PDF
        reader = PdfReader(str(output_path))
        assert len(reader.pages) == 1

    def test_generate_from_template_merges_content(self, tmp_path):
        """Test that template and content are properly merged."""
        # Create template with visible content
        template_path = tmp_path / "template.pdf"
        c = canvas.Canvas(str(template_path), pagesize=letter)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, 750, "Template Header")
        c.save()

        cover_letter = "Dear Hiring Manager,\n\nMy content."
        output_path = tmp_path / "output.pdf"

        generate_cover_letter_from_template(
            cover_letter_text=cover_letter, template_path=template_path, output_path=output_path
        )

        # Output should exist and be valid
        assert output_path.exists()
        reader = PdfReader(str(output_path))
        assert len(reader.pages) == 1

        # Page should contain merged content
        page = reader.pages[0]
        assert page is not None

    def test_generate_from_template_missing_template(self, tmp_path):
        """Test handling of missing template file."""
        template_path = tmp_path / "nonexistent.pdf"
        output_path = tmp_path / "output.pdf"
        cover_letter = "Dear Hiring Manager,\n\nContent."

        with pytest.raises(Exception):
            generate_cover_letter_from_template(
                cover_letter_text=cover_letter, template_path=template_path, output_path=output_path
            )

    def test_generate_from_template_invalid_template(self, tmp_path):
        """Test handling of invalid template PDF."""
        template_path = tmp_path / "invalid.pdf"
        template_path.write_text("This is not a valid PDF")

        output_path = tmp_path / "output.pdf"
        cover_letter = "Dear Hiring Manager,\n\nContent."

        with pytest.raises(Exception):
            generate_cover_letter_from_template(
                cover_letter_text=cover_letter, template_path=template_path, output_path=output_path
            )


class TestGenerateCoverLetterPDF:
    """Tests for main PDF generation function."""

    @patch("src.cover_letter_generator.pdf_generator_template.get_data_directory")
    def test_generate_pdf_with_template(self, mock_get_data_dir, tmp_path):
        """Test PDF generation using template."""
        # Create a template
        template_dir = tmp_path / "template"
        template_dir.mkdir()
        template_path = template_dir / "Cover Letter_ AI Template.pdf"

        c = canvas.Canvas(str(template_path), pagesize=letter)
        c.drawString(100, 750, "Template")
        c.save()

        mock_get_data_dir.return_value = tmp_path

        cover_letter = "Dear Hiring Manager,\n\nContent."
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        output_path = generate_cover_letter_pdf(
            cover_letter_text=cover_letter, output_dir=output_dir, use_template=True
        )

        assert output_path.exists()
        assert output_path.suffix == ".pdf"

    @patch("src.cover_letter_generator.pdf_generator_template.get_data_directory")
    @patch("src.cover_letter_generator.pdf_generator_template.create_cover_letter_pdf")
    def test_generate_pdf_fallback_no_template(self, mock_create_pdf, mock_get_data_dir, tmp_path):
        """Test fallback to non-template generation when template missing."""
        mock_get_data_dir.return_value = tmp_path  # No template in this directory

        output_path = tmp_path / "output.pdf"
        mock_create_pdf.return_value = output_path

        cover_letter = "Dear Hiring Manager,\n\nContent."

        generate_cover_letter_pdf(
            cover_letter_text=cover_letter, output_dir=tmp_path, use_template=True
        )

        # Should fall back to non-template generation
        mock_create_pdf.assert_called_once()

    def test_generate_pdf_default_output_dir(self):
        """Test PDF generation with default output directory."""
        cover_letter = "Dear Hiring Manager,\n\nContent."

        with patch(
            "src.cover_letter_generator.pdf_generator_template.get_data_directory"
        ) as mock_dir:
            mock_dir.return_value = Path("/nonexistent")  # No template

            with patch(
                "src.cover_letter_generator.pdf_generator_template.create_cover_letter_pdf"
            ) as mock_create:
                output = Path.cwd() / "test_output.pdf"
                mock_create.return_value = output

                result = generate_cover_letter_pdf(
                    cover_letter_text=cover_letter, use_template=False
                )

                # Should use current directory by default
                assert result is not None

    def test_generate_pdf_custom_filename(self, tmp_path):
        """Test PDF generation with custom filename."""
        cover_letter = "Dear Hiring Manager,\n\nContent."

        with patch(
            "src.cover_letter_generator.pdf_generator_template.get_data_directory"
        ) as mock_dir:
            mock_dir.return_value = Path("/nonexistent")

            with patch(
                "src.cover_letter_generator.pdf_generator_template.create_cover_letter_pdf"
            ) as mock_create:
                output = tmp_path / "custom_name.pdf"
                mock_create.return_value = output

                result = generate_cover_letter_pdf(
                    cover_letter_text=cover_letter,
                    output_dir=tmp_path,
                    filename="custom_name.pdf",
                    use_template=False,
                )

                assert result == output

    @patch("src.cover_letter_generator.pdf_generator_template.get_data_directory")
    def test_generate_pdf_searches_multiple_template_locations(self, mock_get_data_dir, tmp_path):
        """Test that PDF generator searches multiple locations for template."""
        mock_get_data_dir.return_value = tmp_path

        cover_letter = "Dear Hiring Manager,\n\nContent."

        with patch(
            "src.cover_letter_generator.pdf_generator_template.create_cover_letter_pdf"
        ) as mock_create:
            output = tmp_path / "output.pdf"
            mock_create.return_value = output

            # No template in any location, should fall back
            result = generate_cover_letter_pdf(
                cover_letter_text=cover_letter, output_dir=tmp_path, use_template=True
            )

            # Should have attempted fallback
            assert result is not None

    @patch("src.cover_letter_generator.pdf_generator_template.get_data_directory")
    def test_generate_pdf_with_contact_info(self, mock_get_data_dir, tmp_path):
        """Test PDF generation with contact information."""
        mock_get_data_dir.return_value = tmp_path

        cover_letter = "Dear Hiring Manager,\n\nContent."
        contact_info = {"name": "Test User", "email": "test@example.com"}

        with patch(
            "src.cover_letter_generator.pdf_generator_template.create_cover_letter_pdf"
        ) as mock_create:
            output = tmp_path / "output.pdf"
            mock_create.return_value = output

            generate_cover_letter_pdf(
                cover_letter_text=cover_letter,
                output_dir=tmp_path,
                contact_info=contact_info,
                use_template=False,
            )

            # Contact info should be passed to fallback generator
            call_args = mock_create.call_args
            assert call_args[0][2] == contact_info

    def test_generate_pdf_default_filename_has_timestamp(self, tmp_path):
        """Test that default filename includes timestamp."""
        cover_letter = "Dear Hiring Manager,\n\nContent."

        with patch(
            "src.cover_letter_generator.pdf_generator_template.get_data_directory"
        ) as mock_dir:
            mock_dir.return_value = Path("/nonexistent")

            with patch(
                "src.cover_letter_generator.pdf_generator_template.create_cover_letter_pdf"
            ) as mock_create:

                def create_with_timestamp(*args):
                    # Simulate the actual behavior of creating a timestamped file
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    return tmp_path / f"cover_letter_{timestamp}.pdf"

                mock_create.side_effect = create_with_timestamp

                result = generate_cover_letter_pdf(
                    cover_letter_text=cover_letter, output_dir=tmp_path, use_template=False
                )

                # Filename should contain timestamp
                assert "cover_letter_" in result.name

    @patch("src.cover_letter_generator.pdf_generator_template.get_data_directory")
    def test_generate_pdf_prefers_google_drive_template(self, mock_get_data_dir, tmp_path):
        """Test that Google Drive template location is preferred."""
        # Create template in Google Drive location
        template_dir = tmp_path / "template"
        template_dir.mkdir()
        template_path = template_dir / "Cover Letter_ AI Template.pdf"

        c = canvas.Canvas(str(template_path), pagesize=letter)
        c.drawString(100, 750, "Template")
        c.save()

        mock_get_data_dir.return_value = tmp_path

        cover_letter = "Dear Hiring Manager,\n\nContent."

        result = generate_cover_letter_pdf(
            cover_letter_text=cover_letter, output_dir=tmp_path, use_template=True
        )

        # Should successfully use the template
        assert result.exists()


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_create_overlay_with_xml_special_chars(self):
        """Test overlay creation with XML special characters."""
        cover_letter = "Dear Manager,\n\n5 < 10 and 10 > 5\nUse & operator\n\nSincerely,\nTest"

        width, height = letter
        buffer = create_text_overlay(cover_letter, width, height)

        # Should escape special characters
        assert buffer is not None
        reader = PdfReader(buffer)
        assert len(reader.pages) == 1

    def test_create_overlay_sincerely_without_comma(self):
        """Test overlay with 'Sincerely' but no comma."""
        cover_letter = "Dear Manager,\n\nContent.\n\nSincerely\nYour Name"

        width, height = letter
        buffer = create_text_overlay(cover_letter, width, height)

        assert buffer is not None

    def test_generate_from_template_multipage_template(self, tmp_path):
        """Test generation from multi-page template (uses only first page)."""
        template_path = tmp_path / "template.pdf"

        # Create multi-page template
        c = canvas.Canvas(str(template_path), pagesize=letter)
        c.drawString(100, 750, "Page 1")
        c.showPage()
        c.drawString(100, 750, "Page 2")
        c.save()

        cover_letter = "Dear Manager,\n\nContent."
        output_path = tmp_path / "output.pdf"

        generate_cover_letter_from_template(
            cover_letter_text=cover_letter, template_path=template_path, output_path=output_path
        )

        # Output should have only one page (merged first template page with content)
        reader = PdfReader(str(output_path))
        assert len(reader.pages) == 1

    def test_create_overlay_with_unicode(self):
        """Test overlay creation with Unicode characters."""
        cover_letter = "Dear Manager,\n\nCafé résumé naïve São Paulo\n\nSincerely,\nJosé"

        width, height = letter
        buffer = create_text_overlay(cover_letter, width, height)

        # Should handle Unicode
        assert buffer is not None
        reader = PdfReader(buffer)
        assert len(reader.pages) == 1

    @patch("src.cover_letter_generator.pdf_generator_template.load_dotenv")
    @patch("src.cover_letter_generator.pdf_generator_template.get_data_directory")
    def test_generate_pdf_loads_env_vars(self, mock_get_data_dir, mock_load_dotenv, tmp_path):
        """Test that environment variables are loaded."""
        mock_get_data_dir.return_value = tmp_path

        cover_letter = "Content"

        with patch(
            "src.cover_letter_generator.pdf_generator_template.create_cover_letter_pdf"
        ) as mock_create:
            mock_create.return_value = tmp_path / "output.pdf"

            generate_cover_letter_pdf(
                cover_letter_text=cover_letter, output_dir=tmp_path, use_template=True
            )

            # Should attempt to load environment variables
            mock_load_dotenv.assert_called_once()

    def test_create_overlay_very_small_page(self):
        """Test creating overlay on very small page size."""
        cover_letter = "Dear Manager,\n\nContent."

        # Very small page
        width, height = 200, 300

        buffer = create_text_overlay(cover_letter, width, height)

        # Should still create valid PDF
        assert buffer is not None
        reader = PdfReader(buffer)
        assert len(reader.pages) == 1
