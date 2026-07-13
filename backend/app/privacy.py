import re
import spacy
nlp = spacy.load("en_core_web_sm")
ATTRIBUTE_LABELS = {
    "name": "Name",
    "dob": "Date of Birth",
    "gender": "Gender",
    "address": "Address",
    "phone": "Phone Number",
    "email": "Email Address",
    "aadhaar": "Aadhaar Number",
    "pan": "PAN Number",
    "photo": "Photo",
}

ATTRIBUTE_WEIGHTS = {
    "aadhaar": 10,
    "pan": 8,
    "photo": 7,
    "address": 6,
    "dob": 5,
    "phone": 5,
    "email": 4,
    "name": 2,
    "gender": 2,
}

PATTERNS = {
    "aadhaar": re.compile(r"(?<!\d)(?:\d{4}[\s-]?){2}\d{4}(?!\d)"),
    "pan": re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.IGNORECASE),
    "email": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    "phone": re.compile(r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{9}(?!\d)"),
    "dob": re.compile(
        r"\b(?:\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})\b"
    ),
    "gender": re.compile(r"\b(?:male|female|other|transgender)\b", re.IGNORECASE),
}

LINE_PATTERNS = {
    "name": re.compile(r"\b(?:name|candidate name|full name)\s*[:\-]\s*([A-Z][A-Za-z .]{2,60})", re.IGNORECASE),
    "dob": re.compile(
        r"\b(?:dob|d\.o\.b|date of birth|birth date)\s*[:\-]\s*([0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{4})",
        re.IGNORECASE,
    ),
    "address": re.compile(r"(?im)^(?:address|residence)\s*[:\-]\s*(.{5,120})$"),
    "gender": re.compile(r"\b(?:gender|sex)\s*[:\-]\s*(male|female|other|transgender)", re.IGNORECASE),
}


def clean_value(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" .,:;-")


def first_match(pattern: re.Pattern, text: str) -> tuple[str, int, int] | None:
    match = pattern.search(text)
    if not match:
        return None
    return clean_value(match.group(0)), match.start(), match.end()


def all_matches(pattern: re.Pattern, text: str) -> list[tuple[str, int, int]]:
    return [
        (clean_value(match.group(0)), match.start(), match.end())
        for match in pattern.finditer(text)
    ]


def labeled_match(key: str, text: str) -> tuple[str, int, int] | None:
    pattern = LINE_PATTERNS[key]
    match = pattern.search(text)
    if not match:
        return None
    value = clean_value(match.group(1))
    return value, match.start(1), match.end(1)


def labeled_matches(key: str, text: str) -> list[tuple[str, int, int]]:
    pattern = LINE_PATTERNS[key]
    return [
        (clean_value(match.group(1)), match.start(1), match.end(1))
        for match in pattern.finditer(text)
    ]


def extract_name_fallback(text: str) -> tuple[str, int, int] | None:
    ignored = {
        "government of india",
        "income tax department",
        "permanent account number",
        "unique identification authority",
    }
    for line in text.splitlines()[:12]:
        value = clean_value(line)
        if not value or value.lower() in ignored:
            continue
        if re.fullmatch(r"[A-Z][A-Za-z]+(?: [A-Z][A-Za-z]+){1,3}", value):
            start = text.find(line)
            return value, start, start + len(line)
    return None


def extract_address_fallback(text: str) -> tuple[str, int, int] | None:
    city_words = r"Bangalore|Bengaluru|Mumbai|Delhi|Chennai|Hyderabad|Pune|Kolkata|Karnataka|Maharashtra|Tamil Nadu|Kerala|India"
    match = re.search(rf"\b(?:{city_words})(?:[, ]+[A-Za-z ]+){{0,4}}", text, re.IGNORECASE)
    if not match:
        return None
    return clean_value(match.group(0)), match.start(), match.end()

def extract_ml_attributes(text: str) -> list[dict]:
    """
    Extract PERSON, GPE/LOC and ORG entities using spaCy.
    """
    doc = nlp(text)

    attributes = []
    seen = set()

    for ent in doc.ents:
        label = ent.label_

        if label == "PERSON":
            key = "name"

        elif label in {"GPE", "LOC"}:
            key = "address"

        elif label == "ORG":
            # Optional future attribute
            continue

        else:
            continue

        value = clean_value(ent.text)

        marker = (key, value.lower())

        if marker in seen:
            continue

        seen.add(marker)

        attributes.append(
            attribute_item(
                key,
                value,
                ent.start_char,
                ent.end_char,
            )
        )

    return attributes
def extract_attributes(text: str, photo_detected: bool = False) -> list[dict]:
    attributes: list[dict] = []
    ml_attributes = extract_ml_attributes(text)

    attributes.extend(ml_attributes)

    seen = {
         (item["key"], item["value"].lower(), item["start"])
         for item in attributes
    }
    

    for key in ["aadhaar", "pan", "email", "phone"]:
        for value, start, end in all_matches(PATTERNS[key], text):
            marker = (key, value.lower(), start)
            if marker in seen:
                continue
            attributes.append(attribute_item(key, value, start, end))
            seen.add(marker)

    for key in ["name", "dob", "gender", "address"]:
        matches = labeled_matches(key, text)
        if not matches and key == "name":
            fallback = extract_name_fallback(text)
            matches = [fallback] if fallback else []
        if not matches and key == "address":
            fallback = extract_address_fallback(text)
            matches = [fallback] if fallback else []
        for value, start, end in matches:
            marker = (key, value.lower(), start)
            if marker in seen:
                continue
            attributes.append(attribute_item(key, value, start, end))
            seen.add(marker)

    if not any(item["key"] == "dob" for item in attributes):
        for value, start, end in all_matches(PATTERNS["dob"], text):
            marker = ("dob", value.lower(), start)
            if marker in seen:
                continue
            attributes.append(attribute_item("dob", value, start, end))
            seen.add(marker)

    if not any(item["key"] == "gender" for item in attributes):
        for value, start, end in all_matches(PATTERNS["gender"], text):
            marker = ("gender", value.lower(), start)
            if marker in seen:
                continue
            attributes.append(attribute_item("gender", value, start, end))
            seen.add(marker)

    if photo_detected:
        attributes.append(attribute_item("photo", "Detected", -1, -1))

    return sorted(attributes, key=lambda item: (item["start"] < 0, item["start"]))


def attribute_item(key: str, value: str, start: int, end: int) -> dict:
    return {
        "key": key,
        "label": ATTRIBUTE_LABELS[key],
        "value": value,
        "start": start,
        "end": end,
        "weight": ATTRIBUTE_WEIGHTS[key],
    }


def mask_value(key: str, value: str) -> str:
    digits = re.sub(r"\D", "", value)

    if key == "aadhaar":
        return f"XXXX XXXX {digits[-4:]}" if len(digits) >= 4 else "XXXX XXXX XXXX"

    if key == "pan":
        normalized = value.upper()
        return f"XXXXX{normalized[-5:]}" if len(normalized) >= 5 else "XXXXXXXXXX"

    if key == "phone":
        return f"XXXXXXX{digits[-3:]}" if len(digits) >= 3 else "XXXXXXXXXX"

    if key == "email" and "@" in value:
        name, domain = value.split("@", 1)
        first = name[0] if name else "*"
        return f"{first}****@{domain}"

    if key == "dob":
        match = re.search(r"(\d{4})$", value)
        year = match.group(1) if match else "YYYY"
        return f"XX-XX-{year}"

    if key == "name":
        return " ".join(mask_word(part) for part in value.split())

    if key == "address":
        return "*" * len(value)

    if key == "gender":
        return "******"

    return value


def mask_word(word: str) -> str:
    if not word:
        return ""
    return word[0] + ("*" * max(len(word) - 1, 1))


def redact_text(text: str, attributes: list[dict], selected_fields: list[str]) -> str:
    selected = set(selected_fields)
    replacements = [
        item for item in attributes if item["key"] in selected and item["start"] >= 0 and item["end"] > item["start"]
    ]
    replacements.sort(key=lambda item: item["start"])

    chunks = []
    cursor = 0
    for item in replacements:
        if item["start"] < cursor:
            continue
        chunks.append(text[cursor : item["start"]])
        chunks.append(mask_value(item["key"], item["value"]))
        cursor = item["end"]
    chunks.append(text[cursor:])
    return "".join(chunks)


def score_risk(attributes: list[dict], selected_fields: list[str]) -> dict:
    available = {item["key"]: item["weight"] for item in attributes}
    total = sum(available.values())
    selected = sum(weight for key, weight in available.items() if key in selected_fields)
    score = round((selected / total) * 100) if total else 0

    if score <= 30:
        level = "Low"
    elif score <= 70:
        level = "Medium"
    else:
        level = "High"

    return {"risk_score": score, "risk_level": level}


def build_attribute_rows(attributes: list[dict], selected_fields: list[str]) -> list[dict]:
    selected = set(selected_fields)
    return [
        {
            **item,
            "sensitive": item["key"] in selected,
            "masked_value": mask_value(item["key"], item["value"]) if item["key"] in selected else item["value"],
        }
        for item in attributes
    ]


def personalize_redaction(text: str, attributes: list[dict], selected_fields: list[str]) -> dict:
    clean_selected = [field for field in selected_fields if field in ATTRIBUTE_WEIGHTS]
    risk = score_risk(attributes, clean_selected)
    return {
        "selected_fields": clean_selected,
        "attribute_rows": build_attribute_rows(attributes, clean_selected),
        "redacted_text": redact_text(text, attributes, clean_selected),
        **risk,
    }
