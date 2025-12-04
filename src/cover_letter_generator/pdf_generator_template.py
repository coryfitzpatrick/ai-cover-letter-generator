"""Template-based PDF generation for cover letters."""

from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Optional

from pypdf import PdfReader, PdfWriter
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import Frame, Paragraph, Spacer


def create_text_overlay(cover_letter_text: str, width: float, height: float) -> BytesIO:
    """Create a transparent PDF overlay with the cover letter text.

    Args:
        cover_letter_text: The cover letter content
        width: Page width
        height: Page height

    Returns:
        BytesIO buffer containing the overlay PDF
    """
    # Create a buffer for the overlay
    buffer = BytesIO()

    # Create the PDF canvas
    c = canvas.Canvas(buffer, pagesize=letter)

    # Define the text area - starting right below header with more space
    text_x = 0.75 * inch  # Left margin
    text_width = width - (1.5 * inch)  # Width minus margins
    text_height = height - 2.5 * inch  # More height for content area (less reserved for header)

    # Create a frame for the text
    frame = Frame(
        text_x,
        0.5 * inch,  # Bottom margin (reduced from 0.75)
        text_width,
        text_height,
        leftPadding=0,
        bottomPadding=0,
        rightPadding=0,
        topPadding=0,
        showBoundary=0  # Set to 1 for debugging
    )

    # Define styles
    styles = getSampleStyleSheet()

    # Date style
    date_style = ParagraphStyle(
        'DateStyle',
        parent=styles['Normal'],
        fontName='Helvetica',  # Arial equivalent in ReportLab
        fontSize=11,
        leading=14,
        textColor='#333333',
        alignment=TA_LEFT,
        spaceAfter=0,  # No extra space after date (tight spacing to Dear line)
    )

    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontName='Helvetica',  # Arial equivalent in ReportLab
        fontSize=11,
        leading=14,  # Tighter line spacing for more content
        textColor='#333333',
        alignment=TA_LEFT,
        spaceAfter=10,  # Less space between paragraphs
    )

    # Closing style for "Sincerely," line
    closing_style = ParagraphStyle(
        'ClosingStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=14,
        textColor='#333333',
        alignment=TA_LEFT,
        spaceAfter=0,  # Tight spacing after "Sincerely," (no extra space before name)
    )

    # Process the cover letter text into paragraphs
    story = []

    # Add current date at the top
    current_date = datetime.now().strftime("%B %d, %Y")
    story.append(Paragraph(current_date, date_style))

    paragraphs = cover_letter_text.strip().split('\n\n')

    for para in paragraphs:
        if para.strip():
            clean_para = para.strip().replace('\n', ' ')

            # Escape special XML/HTML characters for ReportLab
            clean_para = clean_para.replace('&', '&amp;')
            clean_para = clean_para.replace('<', '&lt;')
            clean_para = clean_para.replace('>', '&gt;')

            # Add spacing for salutation and closing
            if clean_para.startswith('Dear '):
                story.append(Paragraph(clean_para, body_style))
                story.append(Spacer(1, 0.1 * inch))  # Reduced from 0.15
            elif clean_para.startswith('Sincerely'):
                story.append(Spacer(1, 0.1 * inch))  # Space before closing
                # Split "Sincerely," and name for soft return
                if ',' in clean_para:
                    lines = clean_para.split('\n')
                    if len(lines) > 1:
                        # Already split by newline
                        story.append(Paragraph(lines[0], closing_style))  # "Sincerely,"
                        story.append(Paragraph(lines[1], body_style))  # "Cory Fitzpatrick"
                    else:
                        # Handle "Sincerely, Cory Fitzpatrick" on one line
                        parts = clean_para.split(',', 1)
                        story.append(Paragraph(parts[0] + ',', closing_style))  # "Sincerely,"
                        if len(parts) > 1:
                            story.append(Paragraph(parts[1].strip(), body_style))
                else:
                    story.append(Paragraph(clean_para, body_style))
            else:
                story.append(Paragraph(clean_para, body_style))

    # Add the story to the frame
    frame.addFromList(story, c)

    # Save the canvas
    c.save()
    buffer.seek(0)

    return buffer


def generate_cover_letter_from_template(
    cover_letter_text: str,
    template_path: Path,
    output_path: Path
) -> Path:
    """Generate a cover letter PDF using a template.

    Args:
        cover_letter_text: The cover letter content
        template_path: Path to the template PDF
        output_path: Path where the final PDF will be saved

    Returns:
        Path to the generated PDF
    """
    # Read the template (no cleaning needed, {data} already removed)
    template_reader = PdfReader(str(template_path))
    template_page = template_reader.pages[0]

    # Get page dimensions
    page_width = float(template_page.mediabox.width)
    page_height = float(template_page.mediabox.height)

    # Create the text overlay
    overlay_buffer = create_text_overlay(cover_letter_text, page_width, page_height)
    overlay_reader = PdfReader(overlay_buffer)
    overlay_page = overlay_reader.pages[0]

    # Merge the overlay with the template
    template_page.merge_page(overlay_page)

    # Write the output
    writer = PdfWriter()
    writer.add_page(template_page)

    with open(output_path, 'wb') as output_file:
        writer.write(output_file)

    return output_path


def generate_cover_letter_pdf(
    cover_letter_text: str,
    output_dir: Path = None,
    filename: str = None,
    contact_info: Optional[dict] = None,
    use_template: bool = True
) -> Path:
    """Generate a cover letter PDF.

    Args:
        cover_letter_text: The cover letter content
        output_dir: Directory to save the PDF (default: current directory)
        filename: Custom filename (default: cover_letter_TIMESTAMP.pdf)
        contact_info: Optional contact information dict (not used with template)
        use_template: Whether to use template PDF (default: True)

    Returns:
        Path to the generated PDF
    """
    from datetime import datetime

    if output_dir is None:
        output_dir = Path.cwd()

    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"cover_letter_{timestamp}.pdf"

    output_path = output_dir / filename

    if use_template:
        # Look for template in multiple locations
        import os

        from dotenv import load_dotenv

        # Load environment variables
        env_path = Path(__file__).parent.parent.parent / ".env"
        load_dotenv(dotenv_path=env_path)

        template_locations = []

        # 1. Check DATA_DIR/template folder (Google Drive)
        data_dir = os.getenv("DATA_DIR")
        if data_dir:
            data_dir_clean = data_dir.strip('"').strip("'")
            google_drive_template = (
                Path(data_dir_clean).expanduser() / "template" / "Cover Letter_ AI Template.pdf"
            )
            template_locations.append(google_drive_template)

        # 2. Check project root (fallback)
        project_template = Path(__file__).parent.parent.parent / "Cover Letter_ AI Template.pdf"
        template_locations.append(project_template)

        # Find first existing template
        template_path = None
        for loc in template_locations:
            if loc.exists():
                template_path = loc
                break

        if template_path:
            return generate_cover_letter_from_template(
                cover_letter_text,
                template_path,
                output_path
            )
        else:
            print("Warning: Template not found in any location, using default generation")
            print(f"  Checked: {[str(loc) for loc in template_locations]}")
            use_template = False

    # Fall back to original generation if template not available
    if not use_template:
        from .pdf_generator import create_cover_letter_pdf
        return create_cover_letter_pdf(cover_letter_text, output_path, contact_info)

    return output_path
