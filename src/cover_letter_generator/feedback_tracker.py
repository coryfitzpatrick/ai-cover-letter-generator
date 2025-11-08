"""Feedback tracking and pattern detection for meta-learning."""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class FeedbackEntry:
    """Single feedback entry."""
    timestamp: str
    feedback: str
    category: str  # e.g., "leadership", "technical_depth", "tone", "length"
    company: str
    job_title: str

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(data: dict):
        return FeedbackEntry(**data)


class FeedbackTracker:
    """Track and analyze user feedback patterns."""

    def __init__(self, feedback_file: Path = None):
        """Initialize feedback tracker.

        Args:
            feedback_file: Path to feedback history JSON file
        """
        if feedback_file is None:
            project_root = Path(__file__).parent.parent.parent
            feedback_file = project_root / ".feedback_history.json"

        self.feedback_file = feedback_file
        self.feedback_history = self._load_feedback_history()

        # Initialize Groq for categorization
        api_key = os.getenv("GROQ_API_KEY")
        self.groq_client = Groq(api_key=api_key) if api_key else None

    def _load_feedback_history(self) -> List[FeedbackEntry]:
        """Load feedback history from file."""
        if not self.feedback_file.exists():
            return []

        try:
            with open(self.feedback_file, 'r') as f:
                data = json.load(f)
                return [FeedbackEntry.from_dict(entry) for entry in data]
        except Exception as e:
            print(f"Warning: Could not load feedback history: {e}")
            return []

    def _save_feedback_history(self):
        """Save feedback history to file."""
        try:
            with open(self.feedback_file, 'w') as f:
                data = [entry.to_dict() for entry in self.feedback_history]
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save feedback history: {e}")

    def categorize_feedback(self, feedback: str) -> str:
        """Categorize feedback into a theme using LLM.

        Args:
            feedback: User feedback text

        Returns:
            Category string (e.g., "leadership", "technical_depth", "tone")
        """
        if not self.groq_client:
            return "general"

        try:
            prompt = f"""Categorize this cover letter feedback into ONE of these categories:
- leadership (mentions leadership, management, team, mentoring)
- technical_depth (mentions technical skills, technologies, coding, architecture)
- tone (mentions formality, casual, professional tone)
- length (mentions too long, too short, conciseness)
- specificity (mentions adding examples, metrics, details, specifics)
- general (doesn't fit other categories)

Feedback: "{feedback}"

Respond with ONLY the category name, nothing else."""

            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are a categorization assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=20,
            )

            category = response.choices[0].message.content.strip().lower()
            # Validate category
            valid_categories = ["leadership", "technical_depth", "tone", "length", "specificity", "general"]
            if category not in valid_categories:
                category = "general"

            return category

        except Exception as e:
            print(f"Warning: Could not categorize feedback: {e}")
            return "general"

    def add_feedback(
        self,
        feedback: str,
        company: str = "",
        job_title: str = ""
    ):
        """Add new feedback to history.

        Args:
            feedback: User feedback text
            company: Company name
            job_title: Job title
        """
        category = self.categorize_feedback(feedback)

        entry = FeedbackEntry(
            timestamp=datetime.now().isoformat(),
            feedback=feedback,
            category=category,
            company=company,
            job_title=job_title
        )

        self.feedback_history.append(entry)
        self._save_feedback_history()

    def get_pattern_analysis(self) -> Dict[str, int]:
        """Analyze feedback patterns.

        Returns:
            Dictionary of category counts
        """
        category_counts = defaultdict(int)
        for entry in self.feedback_history:
            category_counts[entry.category] += 1

        return dict(category_counts)

    def detect_recurring_pattern(self, threshold: int = 3) -> Optional[Tuple[str, int, List[str]]]:
        """Detect if a feedback pattern is recurring.

        Args:
            threshold: Number of occurrences to consider a pattern

        Returns:
            Tuple of (category, count, example_feedbacks) if pattern detected, None otherwise
        """
        category_counts = self.get_pattern_analysis()

        # Find categories that meet threshold
        for category, count in category_counts.items():
            if count >= threshold and category != "general":
                # Get example feedbacks from this category
                examples = [
                    entry.feedback
                    for entry in self.feedback_history
                    if entry.category == category
                ][-3:]  # Last 3 examples

                return (category, count, examples)

        return None

    def get_recent_feedback_by_category(self, category: str, limit: int = 5) -> List[FeedbackEntry]:
        """Get recent feedback entries for a category.

        Args:
            category: Category to filter by
            limit: Maximum number of entries to return

        Returns:
            List of feedback entries
        """
        entries = [
            entry
            for entry in self.feedback_history
            if entry.category == category
        ]
        return entries[-limit:]

    def clear_category(self, category: str):
        """Clear feedback history for a specific category.

        This is called after a system improvement is applied for that category.

        Args:
            category: Category to clear
        """
        self.feedback_history = [
            entry
            for entry in self.feedback_history
            if entry.category != category
        ]
        self._save_feedback_history()
