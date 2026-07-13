from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .database import get_history, init_db, save_scan
from .ocr import extract_document
from .privacy import ATTRIBUTE_LABELS, extract_attributes, personalize_redaction

from .spreadsheet import (
    SPREADSHEET_EXTENSIONS,
    attribute_text_to_rows,
    extract_spreadsheet,
    redact_spreadsheet_rows,
    rows_to_csv_text,
)

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
DOCUMENT_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
ALLOWED_EXTENSIONS = DOCUMENT_EXTENSIONS | SPREADSHEET_EXTENSIONS

app = FastAPI(
    title="DocShield AI",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RedactRequest(BaseModel):
    filename: str
    original_text: str
    attributes: list[dict]
    selected_fields: list[str]
    photo_detected: bool = False
    source_type: str = "document"
    table_rows: list[list[str]] | None = None


@app.on_event("startup")
def startup() -> None:
    UPLOAD_DIR.mkdir(exist_ok=True)
    init_db()


@app.get("/")
def health_check():
    return {
        "message": "DocShield AI API is running",
        "spreadsheet_redaction": "row-wise-v2",
    }


@app.post("/extract")
async def extract_document_attributes(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()

    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Upload a PDF, PNG, JPG, JPEG, CSV, or XLSX file.")

    safe_name = f"{uuid4().hex}{suffix}"
    file_path = UPLOAD_DIR / safe_name

    file_path.write_bytes(await file.read())

    try:
        table_rows = None
        source_type = "spreadsheet" if suffix in SPREADSHEET_EXTENSIONS else "document"

        if source_type == "spreadsheet":
            extracted_text, table_rows = extract_spreadsheet(file_path)
            photo_detected = False
        else:
            extracted_text, photo_detected = extract_document(file_path)

        
        attributes = extract_attributes(extracted_text, photo_detected)
        return {
            "filename": file.filename,
            "original_text": extracted_text,
            "attributes": attributes,
            "attribute_labels": ATTRIBUTE_LABELS,
            "photo_detected": photo_detected,
            "source_type": source_type,
            "table_rows": table_rows,
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    finally:
        file_path.unlink(missing_ok=True)


@app.post("/redact")
def redact_document(request: RedactRequest):
    result = personalize_redaction(
        request.original_text,
        request.attributes,
        request.selected_fields,
    )
    table_rows = request.table_rows or []
    if not table_rows and Path(request.filename or "").suffix.lower() in SPREADSHEET_EXTENSIONS:
        table_rows = attribute_text_to_rows(request.original_text)

    if table_rows:
        redacted_rows = redact_spreadsheet_rows(
            table_rows,
            request.attributes,
            result["selected_fields"],
        )
        result["redacted_table"] = redacted_rows
        result["export_text"] = rows_to_csv_text(redacted_rows)
        result["redacted_text"] = result["export_text"]
        result["export_extension"] = "csv"
    else:
        result["export_text"] = result["redacted_text"]
        result["export_extension"] = "txt"

    scan_id = save_scan(
        request.filename,
        request.original_text,
        request.attributes,
        result["selected_fields"],
        result,
        request.photo_detected,
    )
    return {"scan_id": scan_id, **result}


@app.post("/analyze")
async def analyze_document(file: UploadFile = File(...)):
    extracted = await extract_document_attributes(file)
    selected_fields = [item["key"] for item in extracted["attributes"]]
    result = personalize_redaction(
        extracted["original_text"],
        extracted["attributes"],
        selected_fields,
    )
    table_rows = extracted.get("table_rows") or []
    if not table_rows and Path(extracted.get("filename") or "").suffix.lower() in SPREADSHEET_EXTENSIONS:
        table_rows = attribute_text_to_rows(extracted["original_text"])

    if table_rows:
        redacted_rows = redact_spreadsheet_rows(
            table_rows,
            extracted["attributes"],
            result["selected_fields"],
        )
        result["redacted_table"] = redacted_rows
        result["export_text"] = rows_to_csv_text(redacted_rows)
        result["redacted_text"] = result["export_text"]
        result["export_extension"] = "csv"
    else:
        result["export_text"] = result["redacted_text"]
        result["export_extension"] = "txt"

    scan_id = save_scan(
        extracted["filename"] or "document",
        extracted["original_text"],
        extracted["attributes"],
        result["selected_fields"],
        result,
        extracted["photo_detected"],
    )
    return {"scan_id": scan_id, **extracted, **result}


@app.get("/history")
def scan_history():
    return {"history": get_history()}
