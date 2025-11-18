"""Cover Letter Generator - AI-powered cover letter generation using RAG."""

__version__ = "0.1.0"

# Expose main classes and functions for external use
from .generator import CoverLetterGenerator
from .pdf_generator_template import generate_cover_letter_pdf
from .docx_generator import generate_cover_letter_docx
from .job_parser import parse_job_from_url, is_valid_url
from .signature_validator import validate_pdf_signature

__all__ = [
    "CoverLetterGenerator",
    "generate_cover_letter_pdf",
    "generate_cover_letter_docx",
    "parse_job_from_url",
    "is_valid_url",
    "validate_pdf_signature",
]
