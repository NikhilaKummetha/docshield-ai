import os
import shutil
from pathlib import Path

import pytesseract
from pdf2image import convert_from_path
from PIL import Image, ImageStat


def find_tesseract_cmd() -> str | None:
    configured = os.getenv("TESSERACT_CMD")
    path_command = shutil.which("tesseract")
    candidates = [
        Path(configured) if configured else None,
        Path(path_command) if path_command else None,
        Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
        Path.home() / "AppData/Local/Programs/Tesseract-OCR/tesseract.exe",
    ]

    for candidate in candidates:
        try:
            if candidate and candidate.is_file():
                return str(candidate)
        except OSError:
            continue
    return None


def configure_tesseract() -> bool:
    command = find_tesseract_cmd()
    if not command:
        return False
    pytesseract.pytesseract.tesseract_cmd = command
    return True


configure_tesseract()


def find_poppler_path() -> str | None:
    configured = os.getenv("POPPLER_PATH")
    candidates = [
        Path(configured) if configured else None,
        Path(r"C:\poppler\Library\bin"),
        Path(r"C:\poppler\bin"),
    ]

    downloads = Path.home() / "Downloads"
    try:
        if downloads.exists():
            candidates.extend(downloads.glob("Release*/poppler*/Library/bin"))
            candidates.extend(downloads.glob("poppler*/Library/bin"))
            candidates.extend(downloads.glob("poppler*/bin"))
    except OSError:
        pass

    for candidate in candidates:
        try:
            if candidate and (candidate / "pdfinfo.exe").exists() and (candidate / "pdftoppm.exe").exists():
                return str(candidate)
        except OSError:
            continue

    if shutil.which("pdfinfo") and shutil.which("pdftoppm"):
        return None

    return ""


def extract_document(file_path: Path) -> tuple[str, bool]:
    suffix = file_path.suffix.lower()

    if not configure_tesseract():
        raise RuntimeError(
            "Tesseract OCR is required. Install Tesseract or set TESSERACT_CMD "
            "to the full path of tesseract.exe, then restart the backend."
        )

    if suffix == ".pdf":
        poppler_path = find_poppler_path()
        if poppler_path == "":
            raise RuntimeError(
                "Poppler is required for PDF files. Extract Poppler and set "
                "POPPLER_PATH to its Library\\bin folder, then restart the backend."
            )

        kwargs = {"dpi": 220}
        if poppler_path:
            kwargs["poppler_path"] = poppler_path
        pages = convert_from_path(str(file_path), **kwargs)
        text = [pytesseract.image_to_string(page) for page in pages]
        photo_detected = any(detect_photo_region(page) for page in pages)
        return "\n\n".join(text).strip(), photo_detected

    if suffix in {".png", ".jpg", ".jpeg"}:
        with Image.open(file_path) as image:
            return pytesseract.image_to_string(image).strip(), detect_photo_region(image)

    raise ValueError("Only PDF, PNG, JPG, and JPEG files are supported.")


def extract_text(file_path: Path) -> str:
    text, _ = extract_document(file_path)
    return text


def detect_photo_region(image: Image.Image) -> bool:
    rgb = image.convert("RGB")
    width, height = rgb.size
    block_w = max(width // 4, 80)
    block_h = max(height // 4, 80)

    for top in range(0, height - block_h + 1, max(block_h // 2, 40)):
        for left in range(0, width - block_w + 1, max(block_w // 2, 40)):
            block = rgb.crop((left, top, left + block_w, top + block_h))
            stat = ImageStat.Stat(block)
            brightness = sum(stat.mean) / 3
            color_spread = max(stat.mean) - min(stat.mean)
            texture = sum(stat.stddev) / 3
            if 35 < brightness < 235 and texture > 22 and color_spread > 8:
                return True

    return False
