import re
from dataclasses import dataclass


@dataclass
class Entity:
    type: str
    value: str
    masked: str
    start: int
    end: int
    points: int


PATTERNS = [
    ("Aadhaar", re.compile(r"(?<!\d)(?:\d{4}[\s-]?){2}\d{4}(?!\d)"), 40),
    ("PAN", re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.IGNORECASE), 30),
    ("Email", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE), 10),
    ("Phone", re.compile(r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{9}(?!\d)"), 10),
]


def mask_entity(entity_type: str, value: str) -> str:
    digits = re.sub(r"\D", "", value)

    if entity_type == "Aadhaar":
        return f"XXXX XXXX {digits[-4:]}"

    if entity_type == "PAN":
        normalized = value.upper()
        return f"XXXXX{normalized[-5:]}"

    if entity_type == "Phone":
        return f"XXXXXXX{digits[-3:]}"

    if entity_type == "Email":
        name, domain = value.split("@", 1)
        first = name[0] if name else "*"
        return f"{first}****@{domain}"

    return "REDACTED"


def risk_level(score: int) -> str:
    if score >= 70:
        return "High"
    if score >= 30:
        return "Medium"
    return "Low"


def detect_entities(text: str) -> list[Entity]:
    matches: list[Entity] = []

    for entity_type, pattern, points in PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(0)
            matches.append(
                Entity(
                    type=entity_type,
                    value=value,
                    masked=mask_entity(entity_type, value),
                    start=match.start(),
                    end=match.end(),
                    points=points,
                )
            )

    matches.sort(key=lambda item: (item.start, -(item.end - item.start)))
    selected: list[Entity] = []
    last_end = -1

    for entity in matches:
        if entity.start >= last_end:
            selected.append(entity)
            last_end = entity.end

    return selected


def redact_text(text: str, entities: list[Entity]) -> str:
    redacted = []
    cursor = 0

    for entity in sorted(entities, key=lambda item: item.start):
        redacted.append(text[cursor : entity.start])
        redacted.append(entity.masked)
        cursor = entity.end

    redacted.append(text[cursor:])
    return "".join(redacted)


def analyze_text(text: str) -> dict:
    entities = detect_entities(text)
    score = min(sum(entity.points for entity in entities), 100)

    return {
        "entities": [entity.__dict__ for entity in entities],
        "redacted_text": redact_text(text, entities),
        "risk_score": score,
        "risk_level": risk_level(score),
    }
