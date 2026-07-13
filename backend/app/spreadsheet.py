import csv
import re
import zipfile
from io import StringIO
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from .privacy import PATTERNS, mask_value


SPREADSHEET_EXTENSIONS = {".csv", ".xlsx"}


def extract_spreadsheet(file_path: Path) -> tuple[str, list[list[str]]]:
    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        rows = read_csv(file_path)
    elif suffix == ".xlsx":
        rows = read_xlsx(file_path)
    else:
        raise ValueError("Only CSV and XLSX spreadsheet files are supported.")

    return rows_to_attribute_text(rows), rows


def read_csv(file_path: Path) -> list[list[str]]:
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            with file_path.open("r", encoding=encoding, newline="") as handle:
                return normalize_rows(csv.reader(handle))
        except UnicodeDecodeError:
            continue
    raise ValueError("Unable to read CSV file. Please save it as UTF-8 CSV and try again.")


def read_xlsx(file_path: Path) -> list[list[str]]:
    try:
        with zipfile.ZipFile(file_path) as workbook:
            shared_strings = read_shared_strings(workbook)
            sheet_name = first_sheet_name(workbook)
            xml = workbook.read(sheet_name)
    except KeyError as exc:
        raise ValueError("Unable to read XLSX worksheet data.") from exc
    except zipfile.BadZipFile as exc:
        raise ValueError("Invalid XLSX file.") from exc

    return normalize_rows(parse_sheet(xml, shared_strings))


def read_shared_strings(workbook: zipfile.ZipFile) -> list[str]:
    try:
        xml = workbook.read("xl/sharedStrings.xml")
    except KeyError:
        return []

    root = ET.fromstring(xml)
    values = []
    for item in root.findall(".//{*}si"):
        text_parts = [node.text or "" for node in item.findall(".//{*}t")]
        values.append("".join(text_parts))
    return values


def first_sheet_name(workbook: zipfile.ZipFile) -> str:
    worksheet_names = sorted(
        name for name in workbook.namelist() if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")
    )
    if not worksheet_names:
        raise KeyError("No worksheet found")
    return worksheet_names[0]


def parse_sheet(xml: bytes, shared_strings: list[str]) -> list[list[str]]:
    root = ET.fromstring(xml)
    rows: list[list[str]] = []
    for row_node in root.findall(".//{*}sheetData/{*}row"):
        row: list[str] = []
        for cell in row_node.findall("{*}c"):
            index = column_index(cell.attrib.get("r", ""))
            while len(row) < index:
                row.append("")
            row.append(cell_value(cell, shared_strings))
        rows.append(row)
    return rows


def column_index(reference: str) -> int:
    match = re.match(r"([A-Z]+)", reference.upper())
    if not match:
        return 0
    index = 0
    for char in match.group(1):
        index = index * 26 + (ord(char) - ord("A") + 1)
    return max(index - 1, 0)


def cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//{*}t"))

    value_node = cell.find("{*}v")
    if value_node is None or value_node.text is None:
        return ""

    value = value_node.text
    if cell_type == "s":
        try:
            return shared_strings[int(value)]
        except (ValueError, IndexError):
            return value
    return value


def normalize_rows(raw_rows: Any) -> list[list[str]]:
    rows: list[list[str]] = []
    for raw_row in raw_rows:
        row = [cell_to_text(cell) for cell in raw_row]
        while row and row[-1] == "":
            row.pop()
        if any(row):
            rows.append(row)
    return rows


def cell_to_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def rows_to_attribute_text(rows: list[list[str]]) -> str:
    if not rows:
        return ""

    headers = [header.strip() for header in rows[0]]
    has_headers = any(headers) and len(rows) > 1
    lines: list[str] = []

    if has_headers:
        for row_number, row in enumerate(rows[1:], start=1):
            lines.append(f"Record {row_number}")
            for index, value in enumerate(row):
                if not value:
                    continue
                label = headers[index] if index < len(headers) and headers[index] else f"Column {index + 1}"
                lines.append(f"{label}: {value}")
            lines.append("")
    else:
        lines = [", ".join(cell for cell in row if cell) for row in rows]

    return "\n".join(lines).strip()


def attribute_text_to_rows(text: str) -> list[list[str]]:
    records: list[dict[str, str]] = []
    current: dict[str, str] = {}

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if re.fullmatch(r"Record\s+\d+", line, re.IGNORECASE):
            if current:
                records.append(current)
            current = {}
            continue
        if ":" not in line:
            continue
        label, value = line.split(":", 1)
        current[label.strip()] = value.strip()

    if current:
        records.append(current)

    if not records:
        return []

    headers: list[str] = []
    for record in records:
        for key in record:
            if key not in headers:
                headers.append(key)

    return [headers] + [[record.get(header, "") for header in headers] for record in records]


def redact_spreadsheet_rows(
    rows: list[list[str]],
    attributes: list[dict],
    selected_fields: list[str],
) -> list[list[str]]:
    selected = set(selected_fields)
    headers = rows[0] if len(rows) > 1 else []
    header_keys = [header_to_key(header) for header in headers]
    known_values = [
        (item["key"], item["value"], mask_value(item["key"], item["value"]))
        for item in attributes
        if item["key"] in selected and item.get("value")
    ]

    redacted_rows: list[list[str]] = []
    for row_index, row in enumerate(rows):
        redacted_row = []
        for column_index, cell in enumerate(row):
            if row_index == 0 and headers:
                redacted_row.append(cell)
                continue

            header_key = header_keys[column_index] if column_index < len(header_keys) else None
            redacted_row.append(redact_cell(cell, header_key, selected, known_values))
        redacted_rows.append(redacted_row)
    return redacted_rows


def header_to_key(header: str) -> str | None:
    normalized = re.sub(r"[^a-z0-9]", "", header.lower())
    if not normalized:
        return None
    if "aadhaar" in normalized or "aadhar" in normalized:
        return "aadhaar"
    if normalized in {"pan", "panno", "pannumber"} or "pancard" in normalized:
        return "pan"
    if "email" in normalized or "mail" in normalized:
        return "email"
    if "phone" in normalized or "mobile" in normalized or "contact" in normalized:
        return "phone"
    if normalized in {"dob", "dateofbirth", "birthdate"}:
        return "dob"
    if "address" in normalized or "residence" in normalized:
        return "address"
    if "gender" in normalized or normalized == "sex":
        return "gender"
    if normalized in {"name", "fullname", "candidatename", "studentname", "employeename", "customername"}:
        return "name"
    return None


def redact_cell(
    cell: str,
    header_key: str | None,
    selected: set[str],
    known_values: list[tuple[str, str, str]],
) -> str:
    if not cell:
        return cell

    if header_key in selected:
        return mask_value(header_key, cell)

    redacted = cell
    for key, original, masked in known_values:
        redacted = redacted.replace(original, masked)

    for key in ["aadhaar", "pan", "email", "phone", "dob", "gender"]:
        if key not in selected:
            continue
        redacted = PATTERNS[key].sub(lambda match: mask_value(key, match.group(0)), redacted)

    return redacted


def rows_to_csv_text(rows: list[list[str]]) -> str:
    output = StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerows(rows)
    return output.getvalue().strip()
