"""PDF generation for cover letters."""

import os
from pathlib import Path
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_LEFT, TA_RIGHT

# Load environment variables
load_dotenv()


def create_cover_letter_pdf(
    cover_letter_text: str,
    output_path: Path,
    contact_info: Optional[dict] = None
) -> Path:
    """Create a professional PDF cover letter.

    Args:
        cover_letter_text: The cover letter text content
        output_path: Path where PDF will be saved
        contact_info: Optional dict with keys: name, email, phone, location, linkedin, portfolio

    Returns:
        Path to the created PDF file
    """
    # Create the PDF document
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    # Container for the 'Flowable' objects
    story = []

    # Define styles
    styles = getSampleStyleSheet()

    # Custom style for contact header
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Normal'],
        fontSize=10,
        textColor='#333333',
        spaceAfter=6,
        alignment=TA_LEFT,
    )

    # Custom style for date
    date_style = ParagraphStyle(
        'DateStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor='#666666',
        spaceAfter=12,
        alignment=TA_RIGHT,
    )

    # Custom style for body text
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=11,
        leading=16,
        textColor='#333333',
        alignment=TA_LEFT,
        spaceAfter=12,
    )

    # Add contact information header if provided
    if contact_info:
        name = contact_info.get('name', os.getenv('USER_NAME'))
        email = contact_info.get('email', '')
        phone = contact_info.get('phone', '')
        location = contact_info.get('location', '')
        linkedin = contact_info.get('linkedin', '')
        portfolio = contact_info.get('portfolio', '')

        # Name (larger and bold)
        name_style = ParagraphStyle(
            'NameStyle',
            parent=styles['Normal'],
            fontSize=14,
            textColor='#000000',
            spaceAfter=4,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold',
        )
        story.append(Paragraph(name, name_style))

        # Contact details
        contact_parts = []
        if location:
            contact_parts.append(location)
        if phone:
            contact_parts.append(phone)
        if email:
            contact_parts.append(f'<a href="mailto:{email}" color="#0066cc">{email}</a>')

        if contact_parts:
            story.append(Paragraph(' | '.join(contact_parts), header_style))

        # Links
        link_parts = []
        if linkedin:
            link_parts.append(f'<a href="{linkedin}" color="#0066cc">LinkedIn</a>')
        if portfolio:
            link_parts.append(f'<a href="{portfolio}" color="#0066cc">Portfolio</a>')

        if link_parts:
            story.append(Paragraph(' | '.join(link_parts), header_style))

        story.append(Spacer(1, 0.3 * inch))

    # Add date
    current_date = datetime.now().strftime("%B %d, %Y")
    story.append(Paragraph(current_date, date_style))
    story.append(Spacer(1, 0.2 * inch))

    # Process the cover letter text
    paragraphs = cover_letter_text.strip().split('\n\n')

    for para in paragraphs:
        if para.strip():
            # Clean up the text
            clean_para = para.strip().replace('\n', ' ')

            # Handle the salutation specially
            if clean_para.startswith('Dear '):
                story.append(Paragraph(clean_para, body_style))
                story.append(Spacer(1, 0.15 * inch))
            # Handle the closing specially
            elif clean_para.startswith('Sincerely'):
                story.append(Spacer(1, 0.15 * inch))
                story.append(Paragraph(clean_para, body_style))
            else:
                story.append(Paragraph(clean_para, body_style))

    # Build the PDF
    doc.build(story)

    return output_path


def generate_cover_letter_pdf(
    cover_letter_text: str,
    output_dir: Path = None,
    filename: str = None,
    contact_info: Optional[dict] = None
) -> Path:
    """Generate a cover letter PDF with automatic filename.

    Args:
        cover_letter_text: The cover letter content
        output_dir: Directory to save the PDF (default: current directory)
        filename: Custom filename (default: cover_letter_TIMESTAMP.pdf)
        contact_info: Optional contact information dict

    Returns:
        Path to the generated PDF
    """
    if output_dir is None:
        output_dir = Path.cwd()

    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"cover_letter_{timestamp}.pdf"

    output_path = output_dir / filename

    return create_cover_letter_pdf(cover_letter_text, output_path, contact_info)
