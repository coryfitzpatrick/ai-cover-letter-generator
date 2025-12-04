"""Unit tests for utility functions."""

import unittest

from src.cover_letter_generator.utils import (
    create_folder_name_from_details,
    extract_company_name,
    extract_job_title,
)


class TestUtils(unittest.TestCase):
    """Test utility functions."""

    def test_extract_company_name(self):
        """Test company name extraction."""
        # Test standard format
        text = "Dear Google Hiring Team,"
        self.assertEqual(extract_company_name(text), "Google")

        # Test alternative format
        text = "Dear Microsoft Recruitment,"
        self.assertEqual(extract_company_name(text), "Microsoft")

        # Test another alternative
        text = "Dear Apple Team,"
        self.assertEqual(extract_company_name(text), "Apple")

        # Test generic terms (should be ignored)
        text = "Dear Hiring Team,"
        self.assertIsNone(extract_company_name(text))

        # Test no match
        text = "Hello there,"
        self.assertIsNone(extract_company_name(text))

    def test_extract_job_title(self):
        """Test job title extraction."""
        # Test standard pattern
        text = "We are looking for a Senior Software Engineer to join our team."
        self.assertEqual(extract_job_title(text), "Senior Software Engineer")

        # Test position pattern
        text = "Position: Product Manager\nLocation: Remote"
        self.assertEqual(extract_job_title(text), "Product Manager")

        # Test role pattern
        text = "Role: Data Scientist"
        self.assertEqual(extract_job_title(text), "Data Scientist")

        # Test application for pattern
        text = "Application for the UX Designer position"
        self.assertEqual(extract_job_title(text), "UX Designer")

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
