from src.cover_letter_generator.ui_components import HAS_PROMPT_TOOLKIT
import sys

if HAS_PROMPT_TOOLKIT:
    print("SUCCESS: prompt_toolkit detected.")
    sys.exit(0)
else:
    print("FAILURE: prompt_toolkit NOT detected.")
    sys.exit(1)
