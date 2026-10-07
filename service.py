"""Bulk resume processing orchestration."""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from werkzeug.utils import secure_filename

from parser import ResumeParseError, SUPPORTED_EXTENSIONS, parse_resume


def process_uploads(files, database, upload_folder: str) -> list[dict]:
    Path(upload_folder).mkdir(parents=True, exist_ok=True)
    results = []
    for upload in files:
        filename = secure_filename(upload.filename or "")
        extension = Path(filename).suffix.lower()
        if not filename:
            results.append({"filename": "(unnamed)", "status": "error", "error": "No file was selected."})
            continue
        if extension not in SUPPORTED_EXTENSIONS:
            results.append({"filename": filename, "status": "error", "error": "Only PDF and DOCX resumes are supported."})
            continue

        file_bytes = upload.read()
        resume_hash = hashlib.sha256(file_bytes).hexdigest()
        try:
            parsed = parse_resume(file_bytes, filename)
            candidate_id, duplicate = database.save_candidate(parsed, resume_hash, filename)
            if not duplicate:
                stored_name = f"{uuid.uuid4().hex}{extension}"
                Path(upload_folder, stored_name).write_bytes(file_bytes)
            results.append({
                "filename": filename,
                "status": "duplicate" if duplicate else "processed",
                "candidate_id": candidate_id,
                "candidate": database.get_candidate(candidate_id),
            })
        except ResumeParseError as exc:
            results.append({"filename": filename, "status": "error", "error": str(exc)})
    return results
