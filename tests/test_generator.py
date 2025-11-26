"""Unit tests for CoverLetterGenerator."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Mock external dependencies before importing generator
with patch.dict('sys.modules', {
    'chromadb': MagicMock(),
    'chromadb.config': MagicMock(),
    'anthropic': MagicMock(),
    'groq': MagicMock(),
    'openai': MagicMock(),
    'sentence_transformers': MagicMock(),
    'docx': MagicMock(),
    'docx.shared': MagicMock(),
}):
    from src.cover_letter_generator.generator import CoverLetterGenerator


class TestCoverLetterGenerator(unittest.TestCase):
    """Test CoverLetterGenerator class."""

    def setUp(self):
        """Set up test environment."""
        self.mock_chroma_client = MagicMock()
        self.mock_collection = MagicMock()
        self.mock_chroma_client.get_collection.return_value = self.mock_collection
        
        # Mock environment variables
        self.env_patcher = patch.dict('os.environ', {
            'OPENAI_API_KEY': 'test-openai-key',
            'ANTHROPIC_API_KEY': 'test-anthropic-key',
            'GROQ_API_KEY': 'test-groq-key',
            'USER_NAME': 'Test User',
            'DATA_DIR': '/tmp/test_data'
        })
        self.env_patcher.start()

        # Mock file system for system prompt
        self.fs_patcher = patch('pathlib.Path.exists')
        self.mock_exists = self.fs_patcher.start()
        self.mock_exists.return_value = True

        self.open_patcher = patch('builtins.open', new_callable=unittest.mock.mock_open, read_data="System Prompt")
        self.mock_open = self.open_patcher.start()

    def tearDown(self):
        """Clean up."""
        self.env_patcher.stop()
        self.fs_patcher.stop()
        self.open_patcher.stop()

    @patch('src.cover_letter_generator.generator.chromadb.PersistentClient')
    @patch('src.cover_letter_generator.generator.SentenceTransformer')
    @patch('src.cover_letter_generator.generator.Groq')
    @patch('src.cover_letter_generator.generator.openai.Client')
    def test_initialization_gpt4o(self, mock_openai, mock_groq, mock_st, mock_chroma):
        """Test initialization with GPT-4o."""
        mock_chroma.return_value = self.mock_chroma_client
        
        generator = CoverLetterGenerator(model_name="gpt-4o")
        
        self.assertEqual(generator.model_name, "gpt-4o")
        mock_openai.assert_called_once()
        mock_groq.assert_called_once()
        mock_st.assert_called_once()
        mock_chroma.assert_called_once()

    @patch('src.cover_letter_generator.generator.chromadb.PersistentClient')
    @patch('src.cover_letter_generator.generator.SentenceTransformer')
    @patch('src.cover_letter_generator.generator.Groq')
    @patch('src.cover_letter_generator.generator.Anthropic')
    def test_initialization_opus(self, mock_anthropic, mock_groq, mock_st, mock_chroma):
        """Test initialization with Claude Opus."""
        mock_chroma.return_value = self.mock_chroma_client
        
        generator = CoverLetterGenerator(model_name="opus")
        
        self.assertIn("opus", generator.model_name)
        mock_anthropic.assert_called_once()
        mock_groq.assert_called_once()

    @patch('src.cover_letter_generator.generator.chromadb.PersistentClient')
    @patch('src.cover_letter_generator.generator.SentenceTransformer')
    @patch('src.cover_letter_generator.generator.Groq')
    @patch('src.cover_letter_generator.generator.openai.Client')
    def test_generate_cover_letter_flow(self, mock_openai, mock_groq, mock_st, mock_chroma):
        """Test the generation flow (mocked)."""
        mock_chroma.return_value = self.mock_chroma_client
        
        # Setup mocks
        generator = CoverLetterGenerator(model_name="gpt-4o")
        
        # Mock analyze_job_posting
        mock_analysis = MagicMock()
        mock_analysis.job_type = MagicMock()
        mock_analysis.job_type.value = "standard"
        mock_analysis.formatted_analysis = "Job Analysis"
        generator.analyze_job_posting = MagicMock(return_value=mock_analysis)
        
        # Mock get_relevant_context
        generator.get_relevant_context = MagicMock(return_value="Context")
        
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Generated Cover Letter"
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        generator.openai_client.chat.completions.create.return_value = mock_response
        
        # Call generate
        cover_letter, cost_info = generator.generate_cover_letter(
            "Job Description", "Company", "Title"
        )
        
        self.assertEqual(cover_letter, "Generated Cover Letter")
        self.assertIn("total_cost", cost_info)
        
        # Verify calls
        generator.analyze_job_posting.assert_called_once()
        generator.get_relevant_context.assert_called_once()
        generator.openai_client.chat.completions.create.assert_called()


if __name__ == "__main__":
    unittest.main()
