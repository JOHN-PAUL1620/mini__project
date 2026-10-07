# Resume Analyser

Flask application that accepts bulk PDF and DOCX uploads, extracts structured candidate data, stores relational records, and detects duplicate resumes.

## Setup

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open `http://localhost:8080`.

## Configuration

The app stores relational data in `resume_analyzer.db` by default. For the SRS deployment target, create a MySQL database and set `DATABASE_URL`, for example:

```powershell
$env:DATABASE_URL = "mysql+pymysql://talentiq_user:password@localhost/talentiq"
```

## API

- `POST /api/resumes/analyze`: upload one or more files in the `resumes` multipart field.
- `GET /api/candidates`: list stored candidates.
- `GET /api/candidates/<id>`: retrieve a structured candidate profile.

## Notes

- Uploaded resume data is sensitive. Run behind HTTPS, restrict access, and provide a suitable retention policy before production deployment.
- Image-only PDFs need OCR, which is outside Phase 1.
