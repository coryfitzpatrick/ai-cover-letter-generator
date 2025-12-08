"""System improvement suggestions based on feedback patterns."""

import difflib
import os
from pathlib import Path
from typing import Optional, Tuple

from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()


class SystemImprover:
    """Suggest and apply improvements to system prompt based on feedback patterns."""

    def __init__(self, system_prompt_path: Optional[Path] = None):
        """Initialize system improver.

        Args:
            system_prompt_path: Path to system prompt file
        """
        if system_prompt_path is None:
            project_root = Path(__file__).parent.parent.parent
            system_prompt_path = project_root / "prompts" / "system_prompt.txt"

        self.system_prompt_path = system_prompt_path

        # Initialize Groq
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found")
        self.groq_client = Groq(api_key=api_key)

    def _read_system_prompt(self) -> str:
        """Read current system prompt."""
        if not self.system_prompt_path.exists():
            raise FileNotFoundError(f"System prompt not found at {self.system_prompt_path}")

        with open(self.system_prompt_path, "r") as f:
            return f.read()

    def _write_system_prompt(self, content: str):
        """Write updated system prompt."""
        with open(self.system_prompt_path, "w") as f:
            f.write(content)

    def suggest_improvement(
        self, category: str, example_feedbacks: list, count: int
    ) -> Optional[Tuple[str, str]]:
        """Suggest a system prompt improvement based on feedback pattern.

        Args:
            category: Feedback category
            example_feedbacks: List of example feedback strings
            count: Number of times this feedback has occurred

        Returns:
            Tuple of (original_prompt, improved_prompt) or None if no suggestion
        """
        try:
            current_prompt = self._read_system_prompt()

            # Create prompt for LLM to suggest improvements
            prompt = (
                "You are helping improve a cover letter generation system based on recurring "
                "user feedback patterns."
            )

            prompt += f"""
RECURRING ISSUE DETECTED:
Category: {category}
Occurrences: {count} times
Example user revision requests:
{chr(10).join(f'- "{fb}"' for fb in example_feedbacks)}

CURRENT SYSTEM PROMPT (excerpt):
{current_prompt[:2000]}...

The user keeps having to manually request these changes. Your task: Suggest a modification 
to the system prompt that would make the generator automatically address this issue 
in future cover letters, so the user never has to ask for this again.

You should analyze:
1. WHY does the user keep asking for this?
2. What's missing from the current system prompt?
3. What specific instruction would prevent this recurring feedback?
4. Could this also indicate missing data in the user's knowledge base?

Provide your suggestion in this format:
SUGGESTION: [Your suggested text to add/modify in the system prompt]
PLACEMENT: [Where to add it: "After introduction" / "In requirements section" / "At end"]
EXPLANATION: [Brief explanation: why this recurring feedback happens and how this change fixes it]
DATA_NOTE: [Optional: If this suggests missing data, note what data the user should add]

Requirements:
1. Be specific and actionable
2. Make the instruction clear enough that it prevents future occurrences
3. Keep tone consistent with existing prompt
4. Focus on ONE clear improvement
"""

            response = self.groq_client.chat.completions.create(
                model="meta-llama/llama-4-maverick-17b-128e-instruct",
                messages=[
                    {"role": "system", "content": "You are an AI system improvement assistant."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=500,
            )

            result = response.choices[0].message.content.strip()

            # Parse the response
            suggestion = None
            placement = None
            explanation = None
            data_note = None

            # Parse the response using regex for robustness
            import re

            # Extract fields using regex (case insensitive, multiline)
            suggestion_match = re.search(
                r"SUGGESTION:\s*(.*?)(?=\n(?:PLACEMENT|EXPLANATION|DATA_NOTE):|$)",
                result,
                re.IGNORECASE | re.DOTALL,
            )
            placement_match = re.search(
                r"PLACEMENT:\s*(.*?)(?=\n(?:SUGGESTION|EXPLANATION|DATA_NOTE):|$)",
                result,
                re.IGNORECASE,
            )
            explanation_match = re.search(
                r"EXPLANATION:\s*(.*?)(?=\n(?:SUGGESTION|PLACEMENT|DATA_NOTE):|$)",
                result,
                re.IGNORECASE | re.DOTALL,
            )
            data_note_match = re.search(
                r"DATA_NOTE:\s*(.*?)(?=\n(?:SUGGESTION|PLACEMENT|EXPLANATION):|$)",
                result,
                re.IGNORECASE | re.DOTALL,
            )

            suggestion = suggestion_match.group(1).strip() if suggestion_match else None
            placement = placement_match.group(1).strip() if placement_match else None
            explanation = explanation_match.group(1).strip() if explanation_match else None
            data_note = data_note_match.group(1).strip() if data_note_match else None

            if not suggestion:
                return None

            # Create improved prompt
            improved_prompt = self._apply_suggestion(current_prompt, suggestion, placement)

            return (current_prompt, improved_prompt, explanation, data_note)

        except Exception as e:
            print(f"Warning: Could not generate improvement suggestion: {e}")
            return None

    def _apply_suggestion(self, current_prompt: str, suggestion: str, placement: str) -> str:
        """Apply suggestion to system prompt.

        Args:
            current_prompt: Current prompt text
            suggestion: Suggested text to add
            placement: Where to place it

        Returns:
            Modified prompt
        """
        # Add the suggestion with clear markers
        suggestion_block = (
            f"\n\n# AUTO-GENERATED IMPROVEMENT (based on user feedback patterns)\n{suggestion}\n"
        )

        # Simple placement strategy - add at end for now
        # (Could be made more sophisticated based on placement hint)
        improved_prompt = current_prompt.rstrip() + suggestion_block

        return improved_prompt

    def show_diff(self, original: str, improved: str) -> str:
        """Generate a readable diff between original and improved prompts.

        Args:
            original: Original prompt
            improved: Improved prompt

        Returns:
            Formatted diff string
        """
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            improved.splitlines(keepends=True),
            fromfile="current_system_prompt.txt",
            tofile="improved_system_prompt.txt",
            lineterm="",
        )

        return "".join(diff)

    def apply_improvement(self, improved_prompt: str):
        """Apply the improved prompt to both system prompt files.

        Updates both system_prompt.txt and system_prompt.txt.example with the same
        improvements, keeping the example version with placeholder names.

        Args:
            improved_prompt: The improved prompt text
        """
        # 1. Update main system_prompt.txt
        backup_path = self.system_prompt_path.with_suffix(".txt.backup")
        current = self._read_system_prompt()
        with open(backup_path, "w") as f:
            f.write(current)

        self._write_system_prompt(improved_prompt)
        print("✓ System prompt updated")
        print(f"✓ Backup saved to: {backup_path}")

        # 2. Also update system_prompt.txt.example
        example_path = self.system_prompt_path.parent / "system_prompt.txt.example"
        if example_path.exists():
            try:
                # Backup example file
                example_backup_path = example_path.with_suffix(".txt.backup")
                with open(example_path, "r") as f:
                    current_example = f.read()
                with open(example_backup_path, "w") as f:
                    f.write(current_example)

                # Apply same improvement to example (improvements are name-agnostic)
                # We need to apply the same structural changes that were made to the main file
                # Get just the improvement section from improved_prompt
                improvement_marker = (
                    "# AUTO-GENERATED IMPROVEMENT (based on user feedback patterns)"
                )
                if improvement_marker in improved_prompt:
                    improvement_section = improved_prompt.split(improvement_marker)[1]
                    improved_example = (
                        current_example.rstrip() + f"\n\n{improvement_marker}{improvement_section}"
                    )

                    with open(example_path, "w") as f:
                        f.write(improved_example)

                    print("✓ Example system prompt updated")
                    print(f"✓ Example backup saved to: {example_backup_path}")
                else:
                    print(
                        "⚠ Warning: Could not parse improvement section, example file not updated"
                    )

            except Exception as e:
                print(f"⚠ Warning: Could not update example file: {e}")

    def suggest_and_show(
        self, category: str, example_feedbacks: list, count: int
    ) -> Optional[Tuple[str, str, str, str]]:
        """Suggest improvement and show diff.

        Args:
            category: Feedback category
            example_feedbacks: Example feedback strings
            count: Number of occurrences

        Returns:
            Tuple of (diff_text, improved_prompt, explanation, data_note) or None
        """
        result = self.suggest_improvement(category, example_feedbacks, count)
        if not result:
            return None

        original, improved, explanation, data_note = result

        # Generate diff
        diff_text = self.show_diff(original, improved)

        return (diff_text, improved, explanation, data_note)
