"""Unit tests for utility functions."""

import unittest

from src.cover_letter_generator.utils import (
    create_folder_name_from_details,
)


class TestUtils(unittest.TestCase):
    """Test utility functions."""

    def test_create_folder_name_from_details(self):
        """Test folder name creation."""
        timestamp = "20231025_120000"
        
        # Test with all details
        name = create_folder_name_from_details("Google", "Software Engineer", timestamp)
        self.assertEqual(name, "Google - Software Engineer - 2023-10-25")

        # Test with special characters
        name = create_folder_name_from_details("ACME/Inc.", "Dev/Ops", timestamp)
        self.assertEqual(name, "ACMEInc. - DevOps - 2023-10-25")

        # Test with only company
        name = create_folder_name_from_details("Google", None, timestamp)
        self.assertEqual(name, "Google - 2023-10-25")

        # Test fallback
        name = create_folder_name_from_details(None, None, timestamp)
        self.assertEqual(name, "Application_20231025_120000")

        # Test truncation
        long_company = "A" * 100
        long_title = "B" * 100
        name = create_folder_name_from_details(long_company, long_title, timestamp)
        self.assertTrue(len(name) <= 120)
        self.assertTrue(name.endswith("- 2023-10-25"))


if __name__ == "__main__":
    unittest.main()
