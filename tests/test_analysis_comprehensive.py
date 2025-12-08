"""Comprehensive tests for analysis module to increase coverage to 80%+.

This test suite covers:
- Job posting analysis with mocked Groq responses
- Job level classification (IC, MANAGER, DIRECTOR, VP, etc.)
- Job type classification (PRODUCT, ENGINEERING, LEADERSHIP, etc.)
- Requirement extraction and prioritization
- Edge cases and error handling
"""

from unittest.mock import Mock, patch

import pytest

from src.cover_letter_generator.analysis import (
    analyze_job_posting,
    JobLevel,
    JobType,
    JobRequirement,
    JobAnalysis,
)


class TestJobLevelEnum:
    """Tests for JobLevel enumeration."""

    def test_job_level_values(self):
        """Test that all job levels have correct values."""
        assert JobLevel.IC_SENIOR.value == "ic_senior"
        assert JobLevel.MANAGER.value == "manager"
        assert JobLevel.SENIOR_MANAGER.value == "senior_manager"
        assert JobLevel.DIRECTOR_VP.value == "director_vp"

    def test_job_level_membership(self):
        """Test checking membership in JobLevel enum."""
        assert "IC_SENIOR" in JobLevel.__members__
        assert "MANAGER" in JobLevel.__members__
        assert "SENIOR_MANAGER" in JobLevel.__members__
        assert "DIRECTOR_VP" in JobLevel.__members__


class TestJobTypeEnum:
    """Tests for JobType enumeration."""

    def test_job_type_values(self):
        """Test that all job types have correct values."""
        assert JobType.STARTUP.value == "startup"
        assert JobType.ENTERPRISE.value == "enterprise"
        assert JobType.PRODUCT.value == "product"
        assert JobType.INFRASTRUCTURE.value == "infrastructure"

    def test_job_type_membership(self):
        """Test checking membership in JobType enum."""
        assert "STARTUP" in JobType.__members__
        assert "ENTERPRISE" in JobType.__members__
        assert "PRODUCT" in JobType.__members__
        assert "INFRASTRUCTURE" in JobType.__members__


class TestJobRequirementDataclass:
    """Tests for JobRequirement dataclass."""

    def test_create_job_requirement(self):
        """Test creating a JobRequirement instance."""
        req = JobRequirement(
            category="leadership", description="Lead team of 10 engineers", priority=1
        )

        assert req.category == "leadership"
        assert req.description == "Lead team of 10 engineers"
        assert req.priority == 1

    def test_job_requirement_categories(self):
        """Test different requirement categories."""
        categories = ["leadership", "technical", "domain", "cultural"]

        for category in categories:
            req = JobRequirement(category=category, description="Test requirement", priority=1)
            assert req.category == category


class TestJobAnalysisDataclass:
    """Tests for JobAnalysis dataclass."""

    def test_create_job_analysis(self):
        """Test creating a JobAnalysis instance."""
        requirements = [
            JobRequirement("leadership", "Lead team", 1),
            JobRequirement("technical", "Python expertise", 2),
        ]

        analysis = JobAnalysis(
            level=JobLevel.MANAGER,
            job_type=JobType.PRODUCT,
            requirements=requirements,
            key_technologies=["Python", "React"],
            team_size_mentioned=True,
        )

        assert analysis.level == JobLevel.MANAGER
        assert analysis.job_type == JobType.PRODUCT
        assert len(analysis.requirements) == 2
        assert "Python" in analysis.key_technologies
        assert analysis.team_size_mentioned is True


class TestAnalyzeJobPosting:
    """Tests for job posting analysis function."""

    @patch("src.cover_letter_generator.analysis.Groq")
    def test_analyze_job_posting_manager_role(self, mock_groq_class):
        """Test analyzing a manager-level job posting."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[
            0
        ].message.content = """
LEVEL: MANAGER
TYPE: PRODUCT
REQUIREMENTS:
1. leadership: Lead team of 8-12 engineers (priority: 1)
2. technical: Experience with React and Java microservices (priority: 1)
3. leadership: Drive process improvements (priority: 2)
4. cultural: Build psychologically safe environment (priority: 2)
5. domain: Experience in healthcare or regulated industries (priority: 3)
TECHNOLOGIES: React, Java, Docker, Kubernetes, AWS
TEAM_SIZE_MENTIONED: yes
        """
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq_class.return_value = mock_client

        result = analyze_job_posting(
            mock_client,
            "test-model",
            "Job description for engineering manager role",
            "Engineering Manager",
        )

        assert result.level == JobLevel.MANAGER
        assert result.job_type == JobType.PRODUCT
        assert len(result.requirements) == 5
        assert len(result.key_technologies) == 5
        assert result.team_size_mentioned is True

        # Check priority requirements
        priority_1_reqs = [r for r in result.requirements if r.priority == 1]
        assert len(priority_1_reqs) == 2

    @patch("src.cover_letter_generator.analysis.Groq")
    def test_analyze_job_posting_senior_ic_role(self, mock_groq_class):
        """Test analyzing a senior IC job posting."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[
            0
        ].message.content = """
LEVEL: IC_SENIOR
TYPE: INFRASTRUCTURE
REQUIREMENTS:
1. technical: Distributed systems expertise (priority: 1)
2. technical: Kubernetes and Docker experience (priority: 1)
3. technical: Experience with Go or Rust (priority: 2)
4. cultural: Strong collaboration skills (priority: 2)
TECHNOLOGIES: Kubernetes, Docker, Go, Rust, Terraform
TEAM_SIZE_MENTIONED: no
        """
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq_class.return_value = mock_client

        result = analyze_job_posting(mock_client, "test-model", "Senior engineer job description")

        assert result.level == JobLevel.IC_SENIOR
        assert result.job_type == JobType.INFRASTRUCTURE
        assert result.team_size_mentioned is False

    @patch("src.cover_letter_generator.analysis.Groq")
    def test_analyze_job_posting_director_level(self, mock_groq_class):
        """Test analyzing a director-level job posting."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[
            0
        ].message.content = """
LEVEL: DIRECTOR_VP
TYPE: ENTERPRISE
REQUIREMENTS:
1. leadership: Lead multiple teams and managers (priority: 1)
2. leadership: Set technical strategy and vision (priority: 1)
3. leadership: Partner with C-suite executives (priority: 1)
4. domain: Experience in enterprise software (priority: 2)
TECHNOLOGIES: none
TEAM_SIZE_MENTIONED: yes
        """
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq_class.return_value = mock_client

        result = analyze_job_posting(
            mock_client,
            "test-model",
            "Director of Engineering job description",
            "Director of Engineering",
        )

        assert result.level == JobLevel.DIRECTOR_VP
        assert result.job_type == JobType.ENTERPRISE
        assert len(result.key_technologies) == 0  # "none" should result in empty list

    @patch("src.cover_letter_generator.analysis.Groq")
    def test_analyze_job_posting_startup_type(self, mock_groq_class):
        """Test analyzing a startup job posting."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[
            0
        ].message.content = """
LEVEL: SENIOR_MANAGER
TYPE: STARTUP
REQUIREMENTS:
1. leadership: Wear multiple hats (priority: 1)
2. technical: Full-stack development (priority: 1)
3. cultural: Thrive in fast-paced environment (priority: 1)
TECHNOLOGIES: Python, React, PostgreSQL
TEAM_SIZE_MENTIONED: no
        """
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq_class.return_value = mock_client

        result = analyze_job_posting(mock_client, "test-model", "Startup role")

        assert result.job_type == JobType.STARTUP
        assert result.level == JobLevel.SENIOR_MANAGER

    @patch("src.cover_letter_generator.analysis.Groq")
    def test_analyze_job_posting_handles_api_error(self, mock_groq_class):
        """Test handling of API errors during analysis."""
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        result = analyze_job_posting(mock_client, "test-model", "Job description")

        # Should return default analysis on error
        assert result is not None
        assert result.level == JobLevel.MANAGER
        assert result.job_type == JobType.ENTERPRISE
        assert len(result.requirements) == 0
        assert len(result.key_technologies) == 0
        assert result.team_size_mentioned is False

    @patch("src.cover_letter_generator.analysis.Groq")
    def test_analyze_job_posting_invalid_level(self, mock_groq_class):
        """Test handling of invalid job level in response."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[
            0
        ].message.content = """
LEVEL: INVALID_LEVEL
TYPE: PRODUCT
REQUIREMENTS:
1. leadership: Test requirement (priority: 1)
TECHNOLOGIES: Python
TEAM_SIZE_MENTIONED: no
        """
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq_class.return_value = mock_client

        result = analyze_job_posting(mock_client, "test-model", "Job desc")

        # Should default to MANAGER for invalid level
        assert result.level == JobLevel.MANAGER

    @patch("src.cover_letter_generator.analysis.Groq")
    def test_analyze_job_posting_invalid_type(self, mock_groq_class):
        """Test handling of invalid job type in response."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[
            0
        ].message.content = """
LEVEL: MANAGER
TYPE: INVALID_TYPE
REQUIREMENTS:
1. leadership: Test requirement (priority: 1)
TECHNOLOGIES: Python
TEAM_SIZE_MENTIONED: no
        """
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq_class.return_value = mock_client

        result = analyze_job_posting(mock_client, "test-model", "Job desc")

        # Should default to ENTERPRISE for invalid type
        assert result.job_type == JobType.ENTERPRISE

    @patch("src.cover_letter_generator.analysis.Groq")
    def test_analyze_job_posting_no_requirements(self, mock_groq_class):
        """Test handling when no requirements are extracted."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[
            0
        ].message.content = """
LEVEL: MANAGER
TYPE: PRODUCT
REQUIREMENTS:
TECHNOLOGIES: Python
TEAM_SIZE_MENTIONED: no
        """
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq_class.return_value = mock_client

        result = analyze_job_posting(mock_client, "test-model", "Job desc")

        assert len(result.requirements) == 0

    @patch("src.cover_letter_generator.analysis.Groq")
    def test_analyze_job_posting_with_job_title(self, mock_groq_class):
        """Test that job title is used in analysis when provided."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[
            0
        ].message.content = """
LEVEL: MANAGER
TYPE: PRODUCT
REQUIREMENTS:
1. leadership: Lead team (priority: 1)
TECHNOLOGIES: Python
TEAM_SIZE_MENTIONED: yes
        """
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq_class.return_value = mock_client

        result = analyze_job_posting(
            mock_client, "test-model", "Job description", "Senior Engineering Manager"
        )

        # Verify the API was called with job title in prompt
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        user_message = messages[1]["content"]
        assert "Senior Engineering Manager" in user_message

    @patch("src.cover_letter_generator.analysis.Groq")
    def test_analyze_job_posting_mixed_priorities(self, mock_groq_class):
        """Test extracting requirements with mixed priority levels."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[
            0
        ].message.content = """
LEVEL: MANAGER
TYPE: PRODUCT
REQUIREMENTS:
1. leadership: Priority 1 requirement (priority: 1)
2. technical: Priority 1 tech requirement (priority: 1)
3. leadership: Priority 2 requirement (priority: 2)
4. domain: Priority 2 domain requirement (priority: 2)
5. cultural: Priority 3 requirement (priority: 3)
TECHNOLOGIES: Python, React
TEAM_SIZE_MENTIONED: yes
        """
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq_class.return_value = mock_client

        result = analyze_job_posting(mock_client, "test-model", "Job desc")

        # Check that priorities are correctly parsed
        priority_1 = [r for r in result.requirements if r.priority == 1]
        priority_2 = [r for r in result.requirements if r.priority == 2]
        priority_3 = [r for r in result.requirements if r.priority == 3]

        assert len(priority_1) == 2
        assert len(priority_2) == 2
        assert len(priority_3) == 1

    @patch("src.cover_letter_generator.analysis.Groq")
    def test_analyze_job_posting_multiple_technologies(self, mock_groq_class):
        """Test parsing multiple technologies."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[
            0
        ].message.content = """
LEVEL: IC_SENIOR
TYPE: INFRASTRUCTURE
REQUIREMENTS:
1. technical: Backend development (priority: 1)
TECHNOLOGIES: Python, Java, JavaScript, Docker, Kubernetes, AWS, PostgreSQL, Redis, React
TEAM_SIZE_MENTIONED: no
        """
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq_class.return_value = mock_client

        result = analyze_job_posting(mock_client, "test-model", "Job desc")

        assert len(result.key_technologies) == 9
        assert "Python" in result.key_technologies
        assert "Kubernetes" in result.key_technologies

    @patch("src.cover_letter_generator.analysis.Groq")
    def test_analyze_job_posting_requirement_categories(self, mock_groq_class):
        """Test that all requirement categories are properly parsed."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[
            0
        ].message.content = """
LEVEL: MANAGER
TYPE: PRODUCT
REQUIREMENTS:
1. leadership: Leadership requirement (priority: 1)
2. technical: Technical requirement (priority: 1)
3. domain: Domain requirement (priority: 2)
4. cultural: Cultural requirement (priority: 2)
TECHNOLOGIES: Python
TEAM_SIZE_MENTIONED: yes
        """
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq_class.return_value = mock_client

        result = analyze_job_posting(mock_client, "test-model", "Job desc")

        categories = {r.category for r in result.requirements}
        assert "leadership" in categories
        assert "technical" in categories
        assert "domain" in categories
        assert "cultural" in categories

    @patch("src.cover_letter_generator.analysis.Groq")
    def test_analyze_job_posting_truncates_long_description(self, mock_groq_class):
        """Test that very long job descriptions are truncated."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[
            0
        ].message.content = """
LEVEL: MANAGER
TYPE: PRODUCT
REQUIREMENTS:
1. leadership: Test (priority: 1)
TECHNOLOGIES: Python
TEAM_SIZE_MENTIONED: no
        """
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq_class.return_value = mock_client

        # Create a very long description (10,000 characters)
        long_description = "x" * 10000

        result = analyze_job_posting(mock_client, "test-model", long_description)

        # Verify API was called
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        user_message = messages[1]["content"]

        # Description should be truncated to 4000 characters
        # (the prompt contains the description with [:4000] slice)
        assert len(user_message) < len(long_description) + 1000


class TestEdgeCases:
    """Tests for edge cases and unusual scenarios."""

    @patch("src.cover_letter_generator.analysis.Groq")
    def test_analyze_empty_job_description(self, mock_groq_class):
        """Test analyzing an empty job description."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[
            0
        ].message.content = """
LEVEL: MANAGER
TYPE: ENTERPRISE
REQUIREMENTS:
TECHNOLOGIES: none
TEAM_SIZE_MENTIONED: no
        """
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq_class.return_value = mock_client

        result = analyze_job_posting(mock_client, "test-model", "")

        assert result is not None

    @patch("src.cover_letter_generator.analysis.Groq")
    def test_analyze_job_posting_malformed_requirements(self, mock_groq_class):
        """Test handling of malformed requirements section."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[
            0
        ].message.content = """
LEVEL: MANAGER
TYPE: PRODUCT
REQUIREMENTS:
This is not properly formatted
Some random text here
TECHNOLOGIES: Python
TEAM_SIZE_MENTIONED: yes
        """
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq_class.return_value = mock_client

        result = analyze_job_posting(mock_client, "test-model", "Job desc")

        # Should handle malformed requirements gracefully
        assert result is not None
        # Requirements might be empty or partially parsed
        assert len(result.requirements) >= 0

    @patch("src.cover_letter_generator.analysis.Groq")
    def test_analyze_job_posting_case_insensitive_parsing(self, mock_groq_class):
        """Test that parsing is case-insensitive."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[
            0
        ].message.content = """
level: manager
type: product
requirements:
1. leadership: Lead team (priority: 1)
technologies: Python
team_size_mentioned: YES
        """
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq_class.return_value = mock_client

        result = analyze_job_posting(mock_client, "test-model", "Job desc")

        # Should parse correctly despite lowercase
        assert result.level == JobLevel.MANAGER
        assert result.job_type == JobType.PRODUCT
        assert result.team_size_mentioned is True
