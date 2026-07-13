# DocShield AI

DocShield AI is a Personalized Privacy Protection System that detects sensitive information in documents and allows users to selectively redact confidential data before sharing.

## Features

- Upload PDF, Image, CSV, and XLSX files
- OCR-based text extraction
- Sensitive information detection
- Personalized field selection
- Selective redaction
- Privacy risk score
- Scan history
- Download redacted document

## Tech Stack

- React
- FastAPI
- Python
- SQLite
- Tesseract OCR
- spaCy (NLP)
- Regular Expressions (Rule-Based AI)

## Machine Learning

The project uses **spaCy's pre-trained Named Entity Recognition (NER)** model to identify contextual entities such as person names and locations. Structured data like Aadhaar, PAN, phone numbers, and email addresses are detected using rule-based pattern matching.

## Run Locally

### Backend

```bash
cd backend
python -m uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Author

**Nikhila Kummetha**
