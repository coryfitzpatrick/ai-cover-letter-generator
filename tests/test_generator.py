"""Tests for cover letter generator core logic."""

from unittest.mock import Mock

import pytest

from cover_letter_generator.analysis import (
    JobAnalysis,
    JobLevel,
    JobType,
    analyze_job_posting,
)
from cover_letter_generator.scoring import score_document


@pytest.fixture
def mock_groq_client():
    client = Mock()
    client.chat.completions.create.return_value.choices = [
        Mock(message=Mock(content="""
LEVEL: MANAGER
TYPE: PRODUCT
REQUIREMENTS:
1. leadership: Lead team of 8-12 engineers (priority: 1)
2. technical: Experience with React (priority: 1)
TECHNOLOGIES: React, Python
TEAM_SIZE_MENTIONED: yes
"""))
    ]
    return client


def test_analyze_job_posting(mock_groq_client):
    analysis = analyze_job_posting(
        mock_groq_client,
        "fake-model",
        "We need a manager for our product team."
    )
    
    assert analysis.level == JobLevel.MANAGER
    assert analysis.job_type == JobType.PRODUCT
    assert len(analysis.requirements) == 2
    assert analysis.requirements[0].category == "leadership"
    assert "React" in analysis.key_technologies
    assert analysis.team_size_mentioned is True


def test_score_document_basic():
    job_analysis = JobAnalysis(
        level=JobLevel.MANAGER,
        job_type=JobType.PRODUCT,
        requirements=[],
        key_technologies=["Python"],
        team_size_mentioned=False
    )
    
    # Test basic document
    doc = "I have experience with Python."
    metadata = {"source": "resume.pdf"}
    score = score_document(doc, metadata, job_analysis, distance=1.0)
    
    # Base score (1.0 distance -> 1.0 similarity * 10 = 10) + Resume boost (10) + Tech match (7)
    # Total should be around 27
    assert score > 20


def test_score_document_engineering_manager_boost():
    job_analysis = JobAnalysis(
        level=JobLevel.MANAGER,
        job_type=JobType.PRODUCT,
        requirements=[],
        key_technologies=[],
        team_size_mentioned=False
    )
    
    # Document with EM terms
    doc = "I conducted performance reviews and managed hiring."
    metadata = {"source": "achievements.pdf"}
    score = score_document(doc, metadata, job_analysis, distance=1.0)
    
    # Should get EM_TERM_BOOST (12)
    # Base (10) + Achievement (15) + Leadership term (8) + EM term (12) = 45
    assert score > 40


def test_score_document_recency_boost():
    job_analysis = JobAnalysis(
        level=JobLevel.IC_SENIOR,
        job_type=JobType.PRODUCT,
        requirements=[],
        key_technologies=[],
        team_size_mentioned=False
    )
    
    # J&J doc
    doc = "Worked at Johnson & Johnson."
    metadata = {"source": "resume.pdf"}
    score = score_document(doc, metadata, job_analysis, distance=1.0)
    
    # Base (10) + Resume (10) + Recent Company (12) = 32
    assert score >= 32
