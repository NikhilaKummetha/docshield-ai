# DocShield AI

DocShield AI is a Personalized Privacy Protection System. It uploads a PDF, image, CSV, or XLSX file, extracts readable text, identifies personal attributes using rule-based extraction, lets the user choose which attributes are sensitive, masks only those fields, calculates a personalized privacy risk score, and stores scan history in SQLite.

## Tech Stack

- Backend: FastAPI, Python, SQLite
- Frontend: React, Vite, Tailwind CSS
- OCR/Documents: Tesseract OCR, pdf2image, Pillow
- Spreadsheets: Python CSV reader, built-in XLSX parser

No Docker, PostgreSQL, Redis, Celery, Kubernetes, authentication, cloud deployment, or external AI APIs are used.

## Features

- Upload PDF, PNG, JPG, JPEG, CSV, or XLSX files
- OCR text extraction
- Spreadsheet text extraction
- Rule-based personal attribute extraction
- User-controlled sensitive field selection
- Dynamic masking based on selected fields
- Personalized risk score and risk level
- Photo detection placeholder for future image masking
- Redacted TXT export for documents
- Redacted CSV export for spreadsheets
- Row-wise spreadsheet redaction for all matching records, not only the first row
- SQLite scan history

## Supported Attributes

- Name
- Date of Birth
- Gender
- Address
- Phone Number
- Email Address
- Aadhaar Number
- PAN Number
- Photo detected: Yes/No

## Folder Structure

```text
docshield-ai/
  backend/
    app/
      __init__.py
      database.py
      detector.py
      main.py
      ocr.py
      privacy.py
      spreadsheet.py
    uploads/
      .gitkeep
    .env.example
    requirements.txt
  frontend/
    src/
      main.jsx
      styles.css
    index.html
    package.json
    postcss.config.js
    tailwind.config.js
    vite.config.js
  .gitignore
  README.md
```

`detector.py` is kept for compatibility with the first MVP. The upgraded personalized system uses `privacy.py`.

## Workflow

```text
Upload
-> OCR or Spreadsheet Reader
-> Extract Attributes
-> User Selects Sensitive Fields
-> Dynamic Masking
-> Personalized Risk Score
-> Safe Output
-> Save Scan History
```

## Dynamic Masking Examples

| Attribute | Input | Output |
| --- | --- | --- |
| Name | `Rahul Sharma` | `R**** S*****` |
| Phone | `9876543210` | `XXXXXXX210` |
| Email | `rahul@gmail.com` | `r****@gmail.com` |
| Aadhaar | `1234 5678 9123` | `XXXX XXXX 9123` |
| PAN | `ABCDE1234F` | `XXXXX1234F` |
| Address | `Bangalore, Karnataka` | `********************` |
| DOB | `12-06-2002` | `XX-XX-2002` |

## Risk Scoring

Weights:

| Attribute | Weight |
| --- | ---: |
| Aadhaar | 10 |
| PAN | 8 |
| Photo | 7 |
| Address | 6 |
| DOB | 5 |
| Phone | 5 |
| Email | 4 |
| Name | 2 |

Formula:

```text
Risk Score = selected sensitive attribute weights / all available attribute weights * 100
```

Risk levels:

- 0-30: Low
- 31-70: Medium
- 71-100: High

## Backend API

```text
POST /extract
```

Uploads a document or spreadsheet, extracts readable text, extracts attributes, and returns photo detection status for image/PDF files.

```text
POST /redact
```

Accepts extracted attributes plus selected sensitive fields, returns masked output and risk score, and saves scan history.

```text
GET /history
```

Returns recent scans.

```text
POST /analyze
```

Compatibility endpoint that extracts and redacts all detected fields.

## Prerequisites

Install:

1. Python 3.10+
2. Node.js 18+
3. Tesseract OCR
4. Poppler, required for PDF OCR through `pdf2image`

For Windows, set these in the backend terminal if needed:

```powershell
$env:TESSERACT_CMD="C:\Program Files\Tesseract-OCR\tesseract.exe"
$env:POPPLER_PATH="C:\poppler\Library\bin"
```

If Poppler is already added to your system PATH, `POPPLER_PATH` is optional.

## Run Backend

```powershell
cd C:\Users\kcrre\Documents\Codex\2026-06-16\build-a-working-mvp-called-docshield\outputs\docshield-ai\backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

If `.venv` does not exist:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Backend URL:

```text
http://localhost:8000
```

API docs:

```text
http://localhost:8000/docs
```

## Run Frontend

Open a second terminal:

```powershell
cd C:\Users\kcrre\Documents\Codex\2026-06-16\build-a-working-mvp-called-docshield\outputs\docshield-ai\frontend
npm install
npm run dev
```

Frontend URL:

```text
http://localhost:5173
```

## Migration From Previous MVP

The backend automatically adds these SQLite columns when it starts:

- `extracted_attributes`
- `selected_fields`
- `photo_detected`

No manual migration is required. To start fresh, stop the backend and delete:

```text
backend/docshield.db
```

Then restart the backend.

## Notes

- Attribute extraction is intentionally regex and rule based, with no LLM API.
- The system does not assume a specific document type. It can work with Aadhaar cards, PAN cards, resumes, forms, identity documents, and mixed PDFs.
- Spreadsheet support covers `.csv` and basic `.xlsx` files. Legacy `.xls` is not included to keep the project simple.
- Spreadsheet masking uses column headers such as Name, Phone, Email, Aadhaar, PAN, DOB, Gender, and Address, then applies the selected privacy choices to every data row.
- Photo detection is a Phase 2 placeholder. It only reports whether a likely photo/image region exists; it does not mask images yet.
- The redacted output is text-based. Visual PDF/image redaction can be added later.
