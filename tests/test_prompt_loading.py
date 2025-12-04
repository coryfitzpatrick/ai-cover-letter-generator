import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.cover_letter_generator.generator import CoverLetterGenerator

try:
    generator = CoverLetterGenerator()
    print(f"Success! Loaded prompt length: {len(generator.system_prompt_template)}")
except Exception as e:
    print(f"Failed: {e}")
