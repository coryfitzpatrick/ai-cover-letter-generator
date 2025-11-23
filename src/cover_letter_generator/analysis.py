"""Job analysis logic for extracting requirements and classifying job types."""

import re
from dataclasses import dataclass
from enum import Enum
from typing import List

from groq import Groq


class JobLevel(Enum):
    """Job level classification."""
    IC_SENIOR = "ic_senior"  # Senior IC roles
    MANAGER = "manager"  # Engineering Manager
    SENIOR_MANAGER = "senior_manager"  # Senior Manager / Director
    DIRECTOR_VP = "director_vp"  # Director / VP / Executive


class JobType(Enum):
    """Job type classification."""
    STARTUP = "startup"
    ENTERPRISE = "enterprise"
    PRODUCT = "product"
    INFRASTRUCTURE = "infrastructure"


@dataclass
class JobRequirement:
    """Represents a key requirement from job description."""
    category: str  # "leadership", "technical", "domain", "cultural"
    description: str
    priority: int  # 1 = highest priority


@dataclass
class JobAnalysis:
    """Analysis of job posting requirements."""
    level: JobLevel
    job_type: JobType
    requirements: List[JobRequirement]
    key_technologies: List[str]
    team_size_mentioned: bool


def analyze_job_posting(
    client: Groq,
    model: str,
    job_description: str,
    job_title: str = None
) -> JobAnalysis:
    """Analyze job posting to extract requirements and classify job type.

    Args:
        client: Groq client instance
        model: Model name to use
        job_description: The job description text
        job_title: Optional job title for context

    Returns:
        JobAnalysis object with requirements and classification
    """
    print("Analyzing job requirements...")

    # Prepare analysis prompt
    prompt = f"""Analyze this job posting and extract key information.

Job Title: {job_title or "Not specified"}

Job Description:
{job_description[:4000]}

Extract:
1. Job Level (IC_SENIOR, MANAGER, SENIOR_MANAGER, DIRECTOR_VP)
2. Job Type (STARTUP, ENTERPRISE, PRODUCT, INFRASTRUCTURE)
3. Top 5-7 key requirements categorized as:
   - leadership (team management, mentorship, cross-functional work)
   - technical (specific technologies, architectures, systems)
   - domain (industry knowledge, specific domains like healthcare, fintech)
   - cultural (values, work style, team culture)
4. Specific technologies mentioned (programming languages, tools, platforms)
5. Whether team size is mentioned

Respond in this EXACT format:

LEVEL: [one of: IC_SENIOR, MANAGER, SENIOR_MANAGER, DIRECTOR_VP]
TYPE: [one of: STARTUP, ENTERPRISE, PRODUCT, INFRASTRUCTURE]
REQUIREMENTS:
1. [category]: [description] (priority: [1-3])
2. [category]: [description] (priority: [1-3])
...
TECHNOLOGIES: [comma-separated list, or "none" if none mentioned]
TEAM_SIZE_MENTIONED: [yes/no]

Example:
LEVEL: MANAGER
TYPE: PRODUCT
REQUIREMENTS:
1. leadership: Lead team of 8-12 engineers (priority: 1)
2. technical: Experience with React and Java microservices (priority: 1)
3. leadership: Drive process improvements and best practices (priority: 2)
4. cultural: Build psychologically safe team environments (priority: 2)
5. domain: Experience in healthcare or regulated industries (priority: 3)
TECHNOLOGIES: React, Java, Docker, Kubernetes, AWS
TEAM_SIZE_MENTIONED: yes
"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a precise job posting analyzer. Extract requirements exactly as requested."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1000,
        )

        result = response.choices[0].message.content.strip()

        # Parse the response
        level_match = re.search(r'LEVEL:\s*(\w+)', result, re.IGNORECASE)
        type_match = re.search(r'TYPE:\s*(\w+)', result, re.IGNORECASE)
        requirements_match = re.search(r'REQUIREMENTS:\s*\n(.*?)(?=TECHNOLOGIES:|$)', result, re.IGNORECASE | re.DOTALL)
        tech_match = re.search(r'TECHNOLOGIES:\s*(.+?)(?:\n|$)', result, re.IGNORECASE)
        team_size_match = re.search(r'TEAM_SIZE_MENTIONED:\s*(\w+)', result, re.IGNORECASE)

        # Parse level
        level_str = level_match.group(1).upper() if level_match else "MANAGER"
        level = JobLevel[level_str] if level_str in JobLevel.__members__ else JobLevel.MANAGER

        # Parse type
        type_str = type_match.group(1).upper() if type_match else "ENTERPRISE"
        job_type = JobType[type_str] if type_str in JobType.__members__ else JobType.ENTERPRISE

        # Parse requirements
        requirements = []
        if requirements_match:
            req_text = requirements_match.group(1)
            req_lines = re.findall(r'\d+\.\s*(\w+):\s*(.+?)\s*\(priority:\s*(\d+)\)', req_text, re.IGNORECASE)
            for category, description, priority in req_lines:
                requirements.append(JobRequirement(
                    category=category.lower(),
                    description=description.strip(),
                    priority=int(priority)
                ))

        # Parse technologies
        key_technologies = []
        if tech_match:
            tech_str = tech_match.group(1).strip()
            if tech_str.lower() != "none":
                key_technologies = [t.strip() for t in tech_str.split(',')]

        # Parse team size mention
        team_size_mentioned = False
        if team_size_match:
            team_size_mentioned = team_size_match.group(1).lower() == "yes"

        analysis = JobAnalysis(
            level=level,
            job_type=job_type,
            requirements=requirements,
            key_technologies=key_technologies,
            team_size_mentioned=team_size_mentioned
        )

        print(f"  Level: {level.value}")
        print(f"  Type: {job_type.value}")
        print(f"  Requirements: {len(requirements)} key requirements identified")
        print(f"  Technologies: {', '.join(key_technologies) if key_technologies else 'None specific'}")

        return analysis

    except Exception as e:
        print(f"Warning: Could not analyze job posting: {e}")
        # Return default analysis
        return JobAnalysis(
            level=JobLevel.MANAGER,
            job_type=JobType.ENTERPRISE,
            requirements=[],
            key_technologies=[],
            team_size_mentioned=False
        )
