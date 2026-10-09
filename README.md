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

### Vercel

Vercel functions have a read-only, ephemeral application filesystem. Before
deploying, configure `DATABASE_URL` in the Vercel project settings with a
network-reachable managed database URL (not `localhost`). Do not rely on the
local `jj.env` file in production. The app stores parsed data in the database
and does not retain uploaded resume files on the function filesystem.

## API

- `POST /api/resumes/analyze`: upload one or more files in the `resumes` multipart field.
- `GET /api/candidates`: list stored candidates.
- `GET /api/candidates/<id>`: retrieve a structured candidate profile.

## Notes

- Uploaded resume data is sensitive. Run behind HTTPS, restrict access, and provide a suitable retention policy before production deployment.
- Image-only PDFs need OCR, which is outside Phase 1.
