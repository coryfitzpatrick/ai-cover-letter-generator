from unittest.mock import MagicMock, patch

import pytest

from cover_letter_generator.system_improver import SystemImprover


@pytest.fixture
def mock_groq_client():
    with patch('cover_letter_generator.system_improver.Groq') as mock_groq:
        yield mock_groq

@pytest.fixture
def system_improver(mock_groq_client, tmp_path):
    # Create a dummy system prompt file
    prompt_file = tmp_path / "system_prompt.txt"
    prompt_file.write_text("Original system prompt content.")
    
    # Initialize SystemImprover with the dummy file
    with patch.dict('os.environ', {'GROQ_API_KEY': 'test_key'}):
        improver = SystemImprover(system_prompt_path=prompt_file)
        return improver

def test_suggest_improvement_parsing_success(system_improver):
    # Mock the LLM response
    mock_response = MagicMock()
    mock_response.choices[0].message.content = """
SUGGESTION: Add a rule to never use the word "synergy".
PLACEMENT: At the end
EXPLANATION: The user hates corporate jargon.
DATA_NOTE: None
"""
    system_improver.groq_client.chat.completions.create.return_value = mock_response

    # Call the method
    result = system_improver.suggest_improvement("Style", ["Don't use synergy"], 3)

    # Verify results
    assert result is not None
    original, improved, explanation, data_note = result
    
    assert "Original system prompt content." in original
    assert "Add a rule to never use the word \"synergy\"" in improved
    assert "The user hates corporate jargon" in explanation
    assert "None" in data_note
    
    # Verify the improved prompt structure
    assert "# AUTO-GENERATED IMPROVEMENT" in improved

def test_suggest_improvement_parsing_robustness(system_improver):
    # Test with slightly messy output (no clear newlines, different casing)
    mock_response = MagicMock()
    mock_response.choices[0].message.content = """
Suggestion:   Do not mention "DevOps".  
Placement: Requirements section
Explanation: User is not a DevOps engineer.
Data_Note: Check resume for actual role.
"""
    system_improver.groq_client.chat.completions.create.return_value = mock_response

    result = system_improver.suggest_improvement("Specificity", ["Remove DevOps"], 5)

    assert result is not None
    _, improved, explanation, _ = result
    assert "Do not mention \"DevOps\"" in improved
    assert "User is not a DevOps engineer" in explanation

def test_suggest_improvement_parsing_failure(system_improver):
    # Test with completely malformed output
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "I can't help with that."
    system_improver.groq_client.chat.completions.create.return_value = mock_response

    result = system_improver.suggest_improvement("Unknown", [], 1)

    assert result is None

def test_apply_improvement(system_improver):
    # Test applying the improvement to the file
    improved_prompt = "Original system prompt content.\n\n# AUTO-GENERATED IMPROVEMENT\nNew Rule."
    
    system_improver.apply_improvement(improved_prompt)
    
    # Verify the file was updated
    with open(system_improver.system_prompt_path, 'r') as f:
        content = f.read()
        assert content == improved_prompt
    
    # Verify backup was created
    backup_path = system_improver.system_prompt_path.with_suffix('.txt.backup')
    assert backup_path.exists()
    with open(backup_path, 'r') as f:
        backup_content = f.read()
        assert backup_content == "Original system prompt content."
