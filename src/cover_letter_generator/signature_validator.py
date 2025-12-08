"""Signature validation for cover letter PDFs using AI vision."""

import base64
import os
from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple

from dotenv import load_dotenv

try:
    from groq import Groq
    from pdf2image import convert_from_path
    from PIL import Image

    DEPENDENCIES_AVAILABLE = True
    HAS_PDF2IMAGE = True  # Alias for backward compatibility
except ImportError:
    DEPENDENCIES_AVAILABLE = False
    HAS_PDF2IMAGE = False


# Load environment variables
load_dotenv()


class SignatureValidationResult:
    """Result of signature validation."""

    def __init__(
        self, is_valid: bool, confidence: str, message: str, details: Optional[str] = None
    ):
        self.is_valid = is_valid
        self.confidence = confidence  # "high", "medium", "low"
        self.message = message
        self.details = details

    def __str__(self):
        return f"Valid: {self.is_valid} | Confidence: {self.confidence} | {self.message}"


def convert_pdf_to_image(pdf_path: Path) -> Optional[Image.Image]:
    """Convert PDF to PIL Image.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        PIL Image or None if conversion fails
    """
    if not DEPENDENCIES_AVAILABLE:
        return None

    try:
        # Convert PDF to images (we only need the first page)
        images = convert_from_path(
            pdf_path,
            dpi=150,  # Good balance between quality and file size
            first_page=1,
            last_page=1,
        )
        return images[0] if images else None
    except Exception as e:
        print(f"Warning: Could not convert PDF to image: {e}")
        return None


def image_to_base64(image: Image.Image, max_size: Tuple[int, int] = (1568, 1568)) -> str:
    """Convert PIL Image to base64 string.

    Args:
        image: PIL Image
        max_size: Maximum dimensions to resize to (Claude has limits)

    Returns:
        Base64 encoded image string
    """
    # Resize if needed (Claude has image size limits)
    if image.width > max_size[0] or image.height > max_size[1]:
        image.thumbnail(max_size, Image.Resampling.LANCZOS)

    # Convert to PNG bytes
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)

    # Encode to base64
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def validate_signature_with_vision(
    pdf_path: Path, user_name: str, cover_letter_text: Optional[str] = None
) -> SignatureValidationResult:
    """Validate that the signature is visible and not cut off using Claude vision.

    Args:
        pdf_path: Path to the PDF file to validate
        user_name: Expected signature name
        cover_letter_text: The full cover letter text for comparison (optional)

    Returns:
        SignatureValidationResult with validation details
    """
    # Check if dependencies are available
    if not DEPENDENCIES_AVAILABLE:
        return SignatureValidationResult(
            is_valid=True,
            confidence="low",
            message="Signature validation skipped (dependencies not available)",
            details="Install pdf2image and anthropic to enable validation",
        )

    # Check if API key is available
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return SignatureValidationResult(
            is_valid=True,
            confidence="low",
            message="Signature validation skipped (GROQ_API_KEY not set)",
            details="Set GROQ_API_KEY in .env to enable validation",
        )

    try:
        # Convert PDF to image
        image = convert_pdf_to_image(pdf_path)
        if not image:
            return SignatureValidationResult(
                is_valid=True,
                confidence="low",
                message="Could not convert PDF to image for validation",
                details="Proceeding without validation",
            )

        # Convert image to base64
        image_b64 = image_to_base64(image)

        # Create Groq client
        client = Groq(api_key=api_key)

        # Build prompt - include full text if provided for precise comparison
        if cover_letter_text:
            word_count = len(cover_letter_text.split())
            prompt_text = f"""Analyze this cover letter PDF image and determine if the signature 
at the bottom is fully visible and not cut off.

FULL COVER LETTER TEXT (for comparison):
{cover_letter_text}

Word count of full text: {word_count} words

Your task:
1. Read what text IS visible in the PDF image
2. Compare it to the full text provided above
3. Determine if signature "{user_name}" is fully visible
4. If text is cut off, estimate approximately how many words are missing/cut off

Respond in this exact format:
VALID: [YES/NO]
CONFIDENCE: [HIGH/MEDIUM/LOW]
MESSAGE: [Brief explanation]
DETAILS: [If invalid, estimate: "Approximately X words are cut off" or 
"Only signature cut off, body text fits"]"""
        else:
            # Fallback if no text provided
            prompt_text = f"""Analyze this cover letter PDF image and determine if the signature 
at the bottom is fully visible and not cut off.

Look for:
1. The closing "Sincerely," or similar
2. The signature name "{user_name}"
3. Whether these elements appear complete and not truncated by the page boundary

Respond in this exact format:
VALID: [YES/NO]
CONFIDENCE: [HIGH/MEDIUM/LOW]
MESSAGE: [Brief explanation in one sentence]
DETAILS: [Be specific about what is cut off]"""

        # Call Groq Llama 3.2 Vision
        completion = client.chat.completions.create(
            model="llama-3.2-11b-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                        },
                    ],
                }
            ],
            temperature=0.1,
            max_tokens=500,
        )

        # Parse the response
        response_text = completion.choices[0].message.content
        lines = response_text.strip().split("\n")

        # Extract values
        is_valid = False
        confidence = "medium"
        message_text = "Validation completed"
        details = None

        for line in lines:
            if line.startswith("VALID:"):
                is_valid = "YES" in line.upper()
            elif line.startswith("CONFIDENCE:"):
                confidence = line.split(":", 1)[1].strip().lower()
            elif line.startswith("MESSAGE:"):
                message_text = line.split(":", 1)[1].strip()
            elif line.startswith("DETAILS:"):
                details = line.split(":", 1)[1].strip()

        return SignatureValidationResult(
            is_valid=is_valid, confidence=confidence, message=message_text, details=details
        )

    except Exception as e:
        # Check if it's a model access error (404)
        error_str = str(e)
        if "404" in error_str or "not_found_error" in error_str or "model" in error_str:
            return SignatureValidationResult(
                is_valid=True,
                confidence="low",
                message="Signature validation skipped (Vision model not available)",
                details="The model 'llama-3.2-11b-vision-preview' is not available on your Groq account.",
            )

        # On any other error, fail gracefully and allow the save
        return SignatureValidationResult(
            is_valid=True,
            confidence="low",
            message=f"Validation error: {str(e)[:100]}",
            details="Proceeding without validation",
        )


def validate_pdf_signature(
    pdf_path: Path, user_name: str, cover_letter_text: Optional[str] = None, verbose: bool = True
) -> SignatureValidationResult:
    """Main entry point for signature validation.

    Args:
        pdf_path: Path to the PDF file
        user_name: Expected signature name
        cover_letter_text: Full cover letter text for precise comparison (optional)
        verbose: Whether to print status messages

    Returns:
        SignatureValidationResult
    """
    if verbose:
        print("\nValidating signature visibility...")

    result = validate_signature_with_vision(pdf_path, user_name, cover_letter_text)

    if verbose:
        if result.is_valid:
            print(f"✓ Signature validation passed: {result.message}")
        else:
            print(f"⚠ Warning: {result.message}")
            if result.details:
                print(f"  Details: {result.details}")

    return result
