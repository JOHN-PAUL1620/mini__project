"""SQLAlchemy persistence for SQLite development and MySQL deployment."""

from __future__ import annotations

import json
import os
from pathlib import Path

from sqlalchemy import Column, DateTime, ForeignKey, Integer, MetaData, String, Table, Text, create_engine, delete, func, select
from sqlalchemy.exc import IntegrityError


metadata = MetaData()
candidates = Table(
    "candidates", metadata,
    Column("candidate_id", Integer, primary_key=True),
    Column("resume_hash", String(64), nullable=False, unique=True),
    Column("source_filename", String(255), nullable=False),
    Column("full_name", String(255)), Column("email", String(255)), Column("phone", String(40)),
    Column("linkedin", Text), Column("github", Text), Column("portfolio", Text), Column("address", Text),
    Column("raw_resume_data", Text, nullable=False), Column("parsed_data", Text, nullable=False),
    Column("created_at", DateTime, server_default=func.now()),
)
education = Table(
    "education", metadata,
    Column("education_id", Integer, primary_key=True), Column("candidate_id", ForeignKey("candidates.candidate_id"), nullable=False),
    Column("details", Text, nullable=False),
)
certifications = Table(
    "certifications", metadata,
    Column("certification_id", Integer, primary_key=True), Column("candidate_id", ForeignKey("candidates.candidate_id"), nullable=False),
    Column("details", Text, nullable=False),
)
experience = Table(
    "experience", metadata,
    Column("experience_id", Integer, primary_key=True), Column("candidate_id", ForeignKey("candidates.candidate_id"), nullable=False),
    Column("experience_type", String(30), nullable=False), Column("details", Text, nullable=False),
)
internships = Table(
    "internships", metadata,
    Column("internship_id", Integer, primary_key=True), Column("candidate_id", ForeignKey("candidates.candidate_id"), nullable=False),
    Column("details", Text, nullable=False),
)
skills = Table(
    "skills", metadata,
    Column("skill_id", Integer, primary_key=True), Column("candidate_id", ForeignKey("candidates.candidate_id"), nullable=False),
    Column("skill_name", String(100), nullable=False), Column("skill_type", String(30), nullable=False),
)
class CandidateDatabase:
    def __init__(self, database_url: str | None = None):
        default_path = Path(__file__).resolve().parent / "resume_analyzer.db"
        configured_url = database_url or os.getenv("DATABASE_URL")
        if os.getenv("VERCEL") and not configured_url:
            raise RuntimeError(
                "DATABASE_URL is required on Vercel. Configure a reachable managed database; "
                "the function filesystem cannot persist SQLite data."
            )
        self.database_url = configured_url or f"sqlite:///{default_path.as_posix()}"
        self.engine = create_engine(self.database_url, pool_pre_ping=True)
        metadata.create_all(self.engine)

    def save_candidate(self, parsed: dict, resume_hash: str, filename: str) -> tuple[int, bool]:
        try:
            with self.engine.begin() as connection:
                cursor = connection.execute(candidates.insert().values(
                    resume_hash=resume_hash, source_filename=filename, full_name=parsed["full_name"],
                    email=parsed["email"], phone=parsed["phone"], linkedin=parsed["linkedin"], github=parsed["github"],
                    portfolio=parsed["portfolio"], address=parsed["address"], raw_resume_data=parsed["raw_text"],
                    parsed_data=json.dumps(parsed),
                ))
                candidate_id = cursor.inserted_primary_key[0]
                education_rows = [{"candidate_id": candidate_id, "details": item} for item in parsed["education"]]
                experience_rows = [
                    *[{"candidate_id": candidate_id, "experience_type": "work", "details": item} for item in parsed["work_experience"]],
                ]
                certification_rows = [{"candidate_id": candidate_id, "details": item} for item in parsed["certifications"]]
                internship_rows = [{"candidate_id": candidate_id, "details": item} for item in parsed["internship_experience"]]
                skill_rows = [
                    {"candidate_id": candidate_id, "skill_name": skill, "skill_type": "soft" if skill in parsed["soft_skills"] else "technical"}
                    for skill in parsed["skills"]
                ]
                if education_rows:
                    connection.execute(education.insert(), education_rows)
                if certification_rows:
                    connection.execute(certifications.insert(), certification_rows)
                if experience_rows:
                    connection.execute(experience.insert(), experience_rows)
                if internship_rows:
                    connection.execute(internships.insert(), internship_rows)
                if skill_rows:
                    connection.execute(skills.insert(), skill_rows)
                return candidate_id, False
        except IntegrityError:
            with self.engine.connect() as connection:
                duplicate = connection.execute(select(candidates.c.candidate_id).where(candidates.c.resume_hash == resume_hash)).scalar_one()
            return duplicate, True

    def get_candidate(self, candidate_id: int) -> dict | None:
        query = select(candidates).where(candidates.c.candidate_id == candidate_id)
        with self.engine.connect() as connection:
            row = connection.execute(query).mappings().first()
        if not row:
            return None
        result = json.loads(row["parsed_data"])
        result.update(candidate_id=row["candidate_id"], source_filename=row["source_filename"])
        return result

    def update_candidate(self, candidate_id: int, changes: dict) -> dict | None:
        """Update editable profile fields and keep the normalized tables in sync."""
        candidate = self.get_candidate(candidate_id)
        if not candidate:
            return None

        text_fields = ("full_name", "email", "phone", "linkedin", "github", "portfolio", "address")
        list_fields = ("skills", "education", "certifications", "work_experience", "internship_experience")
        for field in text_fields:
            if field in changes:
                candidate[field] = str(changes[field] or "").strip()
        for field in list_fields:
            if field in changes:
                value = changes[field]
                if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                    raise ValueError(f"{field} must be a list of text values.")
                candidate[field] = [item.strip() for item in value if item.strip()]

        candidate["technical_skills"] = [skill for skill in candidate["skills"] if skill not in candidate.get("soft_skills", [])]
        candidate["missing_fields"] = [
            field for field in ("full_name", "email", "phone", "skills", "education") if not candidate.get(field)
        ]
        with self.engine.begin() as connection:
            connection.execute(candidates.update().where(candidates.c.candidate_id == candidate_id).values(
                **{field: candidate[field] for field in text_fields}, parsed_data=json.dumps(candidate)
            ))
            for table in (education, certifications, experience, internships, skills):
                connection.execute(delete(table).where(table.c.candidate_id == candidate_id))
            if candidate["education"]:
                connection.execute(education.insert(), [{"candidate_id": candidate_id, "details": item} for item in candidate["education"]])
            if candidate["certifications"]:
                connection.execute(certifications.insert(), [{"candidate_id": candidate_id, "details": item} for item in candidate["certifications"]])
            experience_rows = [
                *[{"candidate_id": candidate_id, "experience_type": "work", "details": item} for item in candidate["work_experience"]],
            ]
            if experience_rows:
                connection.execute(experience.insert(), experience_rows)
            if candidate["internship_experience"]:
                connection.execute(internships.insert(), [{"candidate_id": candidate_id, "details": item} for item in candidate["internship_experience"]])
            if candidate["skills"]:
                connection.execute(skills.insert(), [
                    {"candidate_id": candidate_id, "skill_name": skill, "skill_type": "soft" if skill in candidate.get("soft_skills", []) else "technical"}
                    for skill in candidate["skills"]
                ])
        return self.get_candidate(candidate_id)

    def delete_candidate(self, candidate_id: int) -> bool:
        with self.engine.begin() as connection:
            exists = connection.execute(select(candidates.c.candidate_id).where(candidates.c.candidate_id == candidate_id)).first()
            if not exists:
                return False
            for table in (education, certifications, experience, internships, skills):
                connection.execute(delete(table).where(table.c.candidate_id == candidate_id))
            connection.execute(delete(candidates).where(candidates.c.candidate_id == candidate_id))
            return True

    def list_candidates(self) -> list[dict]:
        query = select(
            candidates.c.candidate_id, candidates.c.full_name, candidates.c.email, candidates.c.phone,
            candidates.c.source_filename, candidates.c.created_at,
        ).order_by(candidates.c.candidate_id.desc())
        with self.engine.connect() as connection:
            return [dict(row) for row in connection.execute(query).mappings()]
