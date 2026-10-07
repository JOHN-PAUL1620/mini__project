"""Explainable role matching for parsed resume profiles."""

ROLES = {
    "Software Engineer": {"skills": {"python", "java", "javascript", "typescript", "git", "sql", "docker", "linux"}, "experience": 2},
    "Backend Developer": {"skills": {"python", "java", "node.js", "flask", "django", "fastapi", "spring", "sql", "mysql", "postgresql", "redis", "docker"}, "experience": 2},
    "Frontend Developer": {"skills": {"javascript", "typescript", "react", "angular", "vue", "html", "css"}, "experience": 1},
    "Data Analyst": {"skills": {"sql", "python", "excel", "power bi", "tableau", "pandas", "numpy"}, "experience": 1},
    "Data Scientist": {"skills": {"python", "sql", "machine learning", "deep learning", "tensorflow", "pytorch", "pandas", "numpy"}, "experience": 2},
    "DevOps Engineer": {"skills": {"linux", "docker", "kubernetes", "aws", "azure", "gcp", "git", "python"}, "experience": 2},
    "Full Stack Developer": {"skills": {"javascript", "typescript", "react", "node.js", "html", "css", "python", "sql", "docker"}, "experience": 2},
    "QA Engineer": {"skills": {"python", "java", "javascript", "sql", "git", "linux"}, "experience": 1},
}


def analyze_match(candidate: dict, role: str) -> dict:
    """Score a candidate by role skill coverage and stated experience."""
    requirements = ROLES[role]
    candidate_skills = {str(skill).lower() for skill in candidate.get("skills", [])}
    matched = sorted(candidate_skills & requirements["skills"])
    missing = sorted(requirements["skills"] - candidate_skills)
    skill_score = round(80 * len(matched) / len(requirements["skills"]))
    years = float(candidate.get("total_years_experience") or 0)
    experience_score = round(20 * min(years / requirements["experience"], 1))
    return {
        "role": role,
        "score": skill_score + experience_score,
        "matched_skills": matched,
        "missing_skills": missing,
        "experience_years": years,
        "experience_target_years": requirements["experience"],
    }


def infer_candidate_role(candidate: dict) -> str:
    """Choose the strongest supported role from the configured role profiles."""
    ranked = [
        (analysis["score"], role)
        for role in ROLES
        if (analysis := analyze_match(candidate, role))["matched_skills"]
    ]
    best_score, best_role = max(ranked, default=(0, "Unclassified"))
    return best_role if best_score > 0 else "Unclassified"
