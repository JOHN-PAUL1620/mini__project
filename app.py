"""Resume Analyser web application."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from database import CandidateDatabase
from service import process_uploads
from roles import ROLES, analyze_match, infer_candidate_role

load_dotenv("jj.env")


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,
        UPLOAD_FOLDER=str(Path(__file__).resolve().parent / "uploads"),
        DATABASE_URL=os.getenv("DATABASE_URL"),
    )
    if test_config:
        app.config.update(test_config)

    database = CandidateDatabase(app.config.get("DATABASE_URL"))
    app.extensions["candidate_database"] = database

    @app.get("/")
    def home():
        return render_template("index.html", candidates=database.list_candidates(), roles=ROLES)

    @app.post("/analyze")
    def analyze():
        files = request.files.getlist("resumes") or request.files.getlist("resume")
        if not files:
            return render_template("index.html", candidates=database.list_candidates(), roles=ROLES, error="Select at least one PDF or DOCX resume."), 400
        role = request.form.get("role", "")
        if role not in ROLES:
            return render_template("index.html", candidates=database.list_candidates(), roles=ROLES, error="Choose a role from the list."), 400
        results = process_uploads(files, database, app.config["UPLOAD_FOLDER"])
        total_candidates = sum(bool(result.get("candidate")) for result in results)
        results = _rank_results(results, role)
        return render_template("result.html", results=results, role=role, filtered_count=total_candidates - sum(bool(result.get("candidate")) for result in results))

    @app.post("/api/resumes/analyze")
    def analyze_api():
        files = request.files.getlist("resumes") or request.files.getlist("resume")
        if not files:
            return jsonify({"error": "Upload at least one resume using the 'resumes' field."}), 400
        role = request.form.get("role", "")
        if role and role not in ROLES:
            return jsonify({"error": "Choose a valid role.", "available_roles": list(ROLES)}), 400
        results = process_uploads(files, database, app.config["UPLOAD_FOLDER"])
        if role:
            total_candidates = sum(bool(result.get("candidate")) for result in results)
            results = _rank_results(results, role)
            filtered_count = total_candidates - sum(bool(result.get("candidate")) for result in results)
        else:
            filtered_count = 0
        return jsonify({"role": role or None, "filtered_count": filtered_count, "results": results})

    @app.get("/api/candidates")
    def candidates_api():
        return jsonify({"candidates": database.list_candidates()})

    @app.get("/api/candidates/analyze")
    def analyze_stored_candidates_api():
        role = request.args.get("role", "")
        if role not in ROLES:
            return jsonify({"error": "Choose a valid role.", "available_roles": list(ROLES)}), 400
        candidates = [
            candidate
            for summary in database.list_candidates()
            if (candidate := database.get_candidate(summary["candidate_id"]))
        ]
        results = _analyze_candidates(candidates, role)
        return jsonify({
            "role": role,
            "filtered_count": len(candidates) - len(results),
            "results": results,
        })

    @app.get("/api/candidates/<int:candidate_id>")
    def candidate_api(candidate_id: int):
        candidate = database.get_candidate(candidate_id)
        return (jsonify(candidate), 200) if candidate else (jsonify({"error": "Candidate not found."}), 404)

    @app.patch("/api/candidates/<int:candidate_id>")
    def update_candidate_api(candidate_id: int):
        changes = request.get_json(silent=True)
        if not isinstance(changes, dict):
            return jsonify({"error": "Send the edited candidate fields as JSON."}), 400
        try:
            candidate = database.update_candidate(candidate_id, changes)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return (jsonify(candidate), 200) if candidate else (jsonify({"error": "Candidate not found."}), 404)

    @app.delete("/api/candidates/<int:candidate_id>")
    def delete_candidate_api(candidate_id: int):
        deleted = database.delete_candidate(candidate_id)
        return (jsonify({"deleted": True}), 200) if deleted else (jsonify({"error": "Candidate not found."}), 404)

    return app


def _rank_results(results: list[dict], role: str) -> list[dict]:
    matching_results = []
    for result in results:
        if result.get("candidate"):
            analysis = analyze_match(result["candidate"], role)
            if not analysis["matched_skills"]:
                continue
            analysis["candidate_role"] = infer_candidate_role(result["candidate"])
            result["analysis"] = analysis
        matching_results.append(result)
    return sorted(matching_results, key=lambda result: result.get("analysis", {}).get("score", -1), reverse=True)


def _analyze_candidates(candidates: list[dict], role: str) -> list[dict]:
    results = []
    for candidate in candidates:
        analysis = analyze_match(candidate, role)
        if not analysis["matched_skills"]:
            continue
        analysis["candidate_role"] = infer_candidate_role(candidate)
        results.append({"candidate": candidate, "analysis": analysis})
    return sorted(results, key=lambda result: result["analysis"]["score"], reverse=True)


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=8080)