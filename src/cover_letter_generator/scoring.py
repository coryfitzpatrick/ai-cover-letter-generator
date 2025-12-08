"""Scoring logic for ranking retrieved documents."""

import re
from datetime import datetime

from .analysis import JobAnalysis, JobLevel

# Scoring boost values
ACHIEVEMENT_SOURCE_BOOST = 15
RESUME_SOURCE_BOOST = 10
RECOMMENDATION_BOOST = 8
RECENT_COMPANY_BOOST = 12  # J&J (most recent)
PREVIOUS_COMPANY_BOOST = 8  # Fitbit+Google
PERCENTAGE_METRIC_BOOST = 10
TEAM_SIZE_METRIC_BOOST = 8
LEADERSHIP_TERM_BOOST = 8  # Increased from 5
TECHNICAL_TERM_BOOST = 5
TECHNOLOGY_MATCH_BOOST = 7
PROCESS_IMPROVEMENT_BOOST = 6

# Engineering Manager specific boosts
EM_TERM_BOOST = 12  # Increased from 8 to prioritize manager terms
EM_TERMS = [
    "hiring",
    "recruiting",
    "performance review",
    "roadmap",
    "stakeholder",
    "budget",
    "career growth",
    "1:1",
    "one-on-one",
    "promotion",
    "conflict resolution",
    "strategy",
    "okr",
    "kpi",
    "headcount",
    "direct report",
    "mentoring",
    "coaching",
]


def score_document(doc: str, metadata: dict, job_analysis: JobAnalysis, distance: float) -> float:
    """Score a document's relevance based on multiple factors.

    Args:
        doc: Document text
        metadata: Document metadata
        job_analysis: Analyzed job requirements
        distance: Embedding distance from query

    Returns:
        Relevance score (higher is better)
    """
    score = 0.0
    doc_lower = doc.lower()
    source = metadata.get("source", "").lower()

    # Base score from embedding similarity (invert distance, normalize)
    # Distance typically ranges 0-2, so we invert it
    similarity_score = max(0, 2.0 - distance) * 10  # Scale to 0-20 range
    score += similarity_score

    # Boost for achievements document (usually most relevant)
    if "achievement" in source:
        score += ACHIEVEMENT_SOURCE_BOOST

    # Boost for resume (comprehensive info)
    if "resume" in source or "cv" in source:
        score += RESUME_SOURCE_BOOST

    # Boost for recommendations (leadership philosophy, soft skills)
    if "recommendation" in source:
        score += RECOMMENDATION_BOOST

    # Recency boost based on year (more recent experience is more relevant)
    # Dynamically boost based on year metadata instead of hardcoded companies
    year_meta = metadata.get("year", "")
    if year_meta and year_meta != "unknown":
        try:
            year = int(year_meta)
            current_year = datetime.now().year
            years_ago = current_year - year

            if years_ago <= 2:  # Last 2 years (most recent)
                score += RECENT_COMPANY_BOOST
            elif years_ago <= 5:  # 3-5 years ago
                score += PREVIOUS_COMPANY_BOOST
            # Older than 5 years gets no boost
        except (ValueError, TypeError):
            pass  # Invalid year format, skip boost

    # Boost for metrics/numbers (concrete achievements)
    if re.search(r"\d+%", doc):  # Percentages
        score += PERCENTAGE_METRIC_BOOST
    if re.search(r"\d+\s+(?:person|people|engineer|member)", doc_lower):  # Team sizes
        score += TEAM_SIZE_METRIC_BOOST

    # Leadership indicators boost (especially for manager+ roles)
    if job_analysis.level in [JobLevel.MANAGER, JobLevel.SENIOR_MANAGER, JobLevel.DIRECTOR_VP]:
        leadership_terms = [
            "led team",
            "managed",
            "mentored",
            "coordinated",
            "cross-functional",
            "leadership",
            "guided",
            "coached",
        ]
        for term in leadership_terms:
            if term in doc_lower:
                score += LEADERSHIP_TERM_BOOST
                break  # Only boost once

        # Extra boost for Engineering Manager specific terms
        for term in EM_TERMS:
            if term in doc_lower:
                score += EM_TERM_BOOST
                # Don't break here, allow multiple EM terms to stack slightly?
                # Actually, let's cap it or just break to avoid over-boosting one doc
                break

    # Technical depth boost for IC roles
    if job_analysis.level == JobLevel.IC_SENIOR:
        tech_terms = [
            "architected",
            "designed",
            "implemented",
            "built",
            "migrated",
            "optimized",
            "developed",
        ]
        for term in tech_terms:
            if term in doc_lower:
                score += TECHNICAL_TERM_BOOST
                break

    # Technology match boost
    for tech in job_analysis.key_technologies:
        if tech.lower() in doc_lower:
            score += TECHNOLOGY_MATCH_BOOST

    # Process improvement boost (valuable across all roles)
    process_terms = ["reduced", "improved", "increased", "optimized", "streamlined"]
    for term in process_terms:
        if term in doc_lower:
            score += PROCESS_IMPROVEMENT_BOOST
            break

    return score
