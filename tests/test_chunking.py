import unittest

from src.cover_letter_generator.prepare_data import chunk_text


class TestChunking(unittest.TestCase):
    def test_chunking_achievements(self):
        """Test that distinct achievements separated by double newlines are chunked separately."""
        achievements = [
            """Achievement 1: Verification Reduction
Context: The verification process was slow and cumbersome, taking up to 4 hours per build.
Action: I implemented a new reduction algorithm using Python and optimized the database queries.
Result: Verification time reduced by 50%, saving the team 20 hours per week.""",
            """Achievement 2: Git Workflow
Context: The team had frequent merge conflicts and lost code due to poor version control practices.
Action: I introduced a rebase workflow and conducted training sessions for the entire engineering team.
Result: Conflicts reduced by 90% and deployment frequency doubled.""",
            """Achievement 3: Docker Onboarding
Context: New hires struggled with environment setup, often taking 3 days to get running.
Action: I dockerized the application and created a one-command setup script.
Result: Onboarding time dropped to 10 minutes, improving developer experience.""",
        ]

        full_text = "\n\n".join(achievements)

        # Use default chunk size (600) and overlap (100)
        # The logic should force splits because each achievement > 200 chars and separated by blank lines
        chunks = chunk_text(full_text)

        self.assertEqual(len(chunks), 3, "Should have created 3 chunks")

        self.assertIn("Verification Reduction", chunks[0])
        self.assertNotIn("Git Workflow", chunks[0])

        self.assertIn("Git Workflow", chunks[1])
        self.assertNotIn("Docker Onboarding", chunks[1])

        self.assertIn("Docker Onboarding", chunks[2])

    def test_small_paragraphs_grouped(self):
        """Test that small paragraphs are still grouped together."""
        text = "Para 1.\n\nPara 2.\n\nPara 3."
        chunks = chunk_text(text, chunk_size=100)

        # Total length is small, should be 1 chunk
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], text)

    def test_long_text_split(self):
        """Test that a single long block is still split if it exceeds chunk size."""
        # Create a block larger than chunk_size (600) without newlines
        long_text = "A" * 700
        chunks = chunk_text(long_text, chunk_size=600, overlap=0)

        self.assertEqual(len(chunks), 2)
        self.assertEqual(len(chunks[0]), 600)
        self.assertEqual(len(chunks[1]), 100)


if __name__ == "__main__":
    unittest.main()
