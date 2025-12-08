"""Integration tests for the document scoring system."""

import pytest
from datetime import datetime

from src.cover_letter_generator.analysis import JobAnalysis, JobLevel, JobType, JobRequirement
from src.cover_letter_generator.scoring import score_document


class TestScoringIntegration:
    """Integration tests for document scoring with real data."""

    def test_recent_work_gets_higher_boost(self):
        """Test that more recent work experience receives higher scoring boost."""
        current_year = datetime.now().year

        # Create a job analysis for a manager role
        job_analysis = JobAnalysis(
            level=JobLevel.MANAGER,
            job_type=JobType.PRODUCT,
            requirements=[
                JobRequirement(category="leadership", description="Team leadership", priority=1),
                JobRequirement(category="leadership", description="Project management", priority=1),
            ],
            key_technologies=["Python", "AWS"],
            team_size_mentioned=True
        )

        # Document from recent work (last 2 years)
        recent_doc = "Led a team of 5 engineers at Company A, improving deployment speed by 40%."
        recent_metadata = {
            "source": "resume.pdf",
            "company": "companyA",
            "year": str(current_year - 1)  # Last year
        }

        # Document from older work (5+ years ago)
        old_doc = "Led a team of 5 engineers at Company B, improving deployment speed by 40%."
        old_metadata = {
            "source": "resume.pdf",
            "company": "companyB",
            "year": str(current_year - 6)  # 6 years ago
        }

        # Score both documents with same distance
        distance = 0.5
        recent_score = score_document(recent_doc, recent_metadata, job_analysis, distance)
        old_score = score_document(old_doc, old_metadata, job_analysis, distance)

        # Recent work should score higher due to recency boost
        assert recent_score > old_score, "Recent work should score higher than old work"

        # The difference should be the recency boost (12 points)
        assert (recent_score - old_score) >= 12, "Recent boost should be at least 12 points"

    def test_achievement_source_boost(self):
        """Test that achievements document gets proper boost."""
        job_analysis = JobAnalysis(
            level=JobLevel.IC_SENIOR,
            job_type=JobType.PRODUCT,
            requirements=[],
            key_technologies=[],
            team_size_mentioned=False
        )

        doc = "Implemented a new caching system that reduced latency by 50%."

        # Achievement source
        achievement_metadata = {"source": "achievements.pdf", "company": "unknown", "year": "unknown"}

        # Resume source
        resume_metadata = {"source": "resume.pdf", "company": "unknown", "year": "unknown"}

        distance = 0.5
        achievement_score = score_document(doc, achievement_metadata, job_analysis, distance)
        resume_score = score_document(doc, resume_metadata, job_analysis, distance)

        # Achievement should score higher (15 point boost vs 10 point boost)
        assert achievement_score > resume_score
        assert (achievement_score - resume_score) == 5  # Difference of 5 points

    def test_leadership_terms_boost_for_manager_roles(self):
        """Test that leadership terms provide boost for manager-level roles."""
        manager_job = JobAnalysis(
            level=JobLevel.MANAGER,
            job_type=JobType.PRODUCT,
            requirements=[],
            key_technologies=[],
            team_size_mentioned=False
        )

        ic_job = JobAnalysis(
            level=JobLevel.IC_SENIOR,
            job_type=JobType.PRODUCT,
            requirements=[],
            key_technologies=[],
            team_size_mentioned=False
        )

        # Document with leadership terms
        leadership_doc = "Led team of engineers and mentored junior developers."
        metadata = {"source": "resume.pdf", "company": "unknown", "year": "unknown"}
        distance = 0.5

        manager_score = score_document(leadership_doc, metadata, manager_job, distance)
        ic_score = score_document(leadership_doc, metadata, ic_job, distance)

        # Should get leadership boost for manager role but not IC role
        assert manager_score > ic_score

    def test_em_specific_terms_boost(self):
        """Test that EM-specific terms (hiring, 1:1s, etc.) provide additional boost."""
        manager_job = JobAnalysis(
            level=JobLevel.MANAGER,
            job_type=JobType.PRODUCT,
            requirements=[],
            key_technologies=[],
            team_size_mentioned=False
        )

        # Document with EM-specific terms
        em_doc = "Responsible for hiring, conducting performance reviews, and 1:1 meetings."

        # Document with general leadership terms
        general_doc = "Led team and coordinated cross-functional initiatives."

        metadata = {"source": "resume.pdf", "company": "unknown", "year": "unknown"}
        distance = 0.5

        em_score = score_document(em_doc, metadata, manager_job, distance)
        general_score = score_document(general_doc, metadata, manager_job, distance)

        # EM-specific terms should provide additional boost (12 points vs 8 points)
        assert em_score > general_score

    def test_technology_match_boost(self):
        """Test that matching technologies in job requirements provides boost."""
        job_with_python = JobAnalysis(
            level=JobLevel.IC_SENIOR,
            job_type=JobType.PRODUCT,
            requirements=[],
            key_technologies=["Python", "AWS"],
            team_size_mentioned=False
        )

        job_with_java = JobAnalysis(
            level=JobLevel.IC_SENIOR,
            job_type=JobType.PRODUCT,
            requirements=[],
            key_technologies=["Java", "GCP"],
            team_size_mentioned=False
        )

        doc = "Built a Python application deployed on AWS infrastructure."
        metadata = {"source": "resume.pdf", "company": "unknown", "year": "unknown"}
        distance = 0.5

        python_score = score_document(doc, metadata, job_with_python, distance)
        java_score = score_document(doc, metadata, job_with_java, distance)

        # Should score higher when technologies match
        assert python_score > java_score

    def test_metrics_boost(self):
        """Test that documents with metrics (percentages, team sizes) get boost."""
        job_analysis = JobAnalysis(
            level=JobLevel.IC_SENIOR,
            job_type=JobType.PRODUCT,
            requirements=[],
            key_technologies=[],
            team_size_mentioned=False
        )

        # Document with metrics
        metrics_doc = "Improved performance by 50% and led team of 10 engineers."

        # Document without metrics
        no_metrics_doc = "Improved performance and led team of engineers."

        metadata = {"source": "resume.pdf", "company": "unknown", "year": "unknown"}
        distance = 0.5

        metrics_score = score_document(metrics_doc, metadata, job_analysis, distance)
        no_metrics_score = score_document(no_metrics_doc, metadata, job_analysis, distance)

        # Metrics should provide boost (10 for percentage + 8 for team size)
        assert metrics_score > no_metrics_score
        assert (metrics_score - no_metrics_score) >= 18

    def test_embedding_distance_affects_score(self):
        """Test that embedding distance properly affects the base score."""
        job_analysis = JobAnalysis(
            level=JobLevel.IC_SENIOR,
            job_type=JobType.PRODUCT,
            requirements=[],
            key_technologies=[],
            team_size_mentioned=False
        )

        doc = "Software engineer with Python experience."
        metadata = {"source": "resume.pdf", "company": "unknown", "year": "unknown"}

        # Better match (lower distance)
        close_score = score_document(doc, metadata, job_analysis, distance=0.3)

        # Worse match (higher distance)
        far_score = score_document(doc, metadata, job_analysis, distance=1.5)

        # Closer embedding distance should result in higher score
        assert close_score > far_score

    def test_combined_scoring_factors(self):
        """Test realistic scenario with multiple scoring factors combined."""
        current_year = datetime.now().year

        job_analysis = JobAnalysis(
            level=JobLevel.MANAGER,
            job_type=JobType.PRODUCT,
            requirements=[
                JobRequirement(category="leadership", description="Team leadership", priority=1),
                JobRequirement(category="technical", description="Technical excellence", priority=1),
            ],
            key_technologies=["Python", "Kubernetes"],
            team_size_mentioned=True
        )

        # Ideal document: recent, from achievements, has metrics, leadership terms, tech match
        ideal_doc = (
            "Led hiring for a team of 8 engineers, improving deployment frequency by 60% "
            "through Python and Kubernetes migration. Conducted weekly 1:1s and performance reviews."
        )
        ideal_metadata = {
            "source": "achievements.pdf",
            "company": "techcorp",
            "year": str(current_year - 1)
        }

        # Poor document: old, generic source, no metrics, no leadership
        poor_doc = "Worked on software projects."
        poor_metadata = {
            "source": "other.pdf",
            "company": "oldcorp",
            "year": str(current_year - 7)
        }

        distance = 0.5
        ideal_score = score_document(ideal_doc, ideal_metadata, job_analysis, distance)
        poor_score = score_document(poor_doc, poor_metadata, job_analysis, distance)

        # Ideal document should score significantly higher
        assert ideal_score > poor_score

        # Score difference should be substantial (multiple boost factors)
        assert (ideal_score - poor_score) > 40, "Combined boosts should create significant difference"
