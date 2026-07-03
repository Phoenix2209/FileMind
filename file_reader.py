# file_reader.py
# Reads every supported file type and returns
# (text_content, base64_image_or_None, metadata_dict)

from __future__ import annotations

import base64
import csv
import json
import os
from pathlib import Path
from typing import Optional

import fitz  # pymupdf

from config import MAX_CHARS_PER_FILE, SUPPORTED_EXTENSIONS


# ── Public API ─────────────────────────────────────────────────────────────

class FileReadResult:
    """Container returned by read_file()."""

    def __init__(
        self,
        filename:     str,
        filepath:     str,
        file_type:    str,
        file_size_kb: float,
        text:         str = "",
        image_b64:    Optional[str] = None,   # set for JPEG/PNG
        is_image:     bool = False,
        error:        Optional[str] = None,
    ):
        self.filename     = filename
        self.filepath     = filepath
        self.file_type    = file_type
        self.file_size_kb = file_size_kb
        self.text         = text
        self.image_b64    = image_b64
        self.is_image     = is_image
        self.error        = error
        self.success      = error is None


def read_file(path: Path) -> FileReadResult:
    """
    Entry point. Dispatches to the right reader based on extension.
    Returns a FileReadResult regardless of success/failure.
    """
    ext  = path.suffix.lower()
    size = round(path.stat().st_size / 1024, 2)
    meta = dict(
        filename=path.name,
        filepath=str(path.resolve()),
        file_type=ext,
        file_size_kb=size,
    )

    if ext not in SUPPORTED_EXTENSIONS:
        return FileReadResult(**meta, error=f"Unsupported extension: {ext}")

    try:
        if ext in {".jpeg", ".jpg", ".png"}:
            return _read_image(path, **meta)
        elif ext in {".csv", ".tsv"}:
            return _read_csv(path, **meta)
        elif ext in {".json", ".jsonl"}:
            return _read_json(path, **meta)
        elif ext == ".pdf":
            return _read_pdf(path, **meta)
        else:                               # .txt .md .log
            return _read_text(path, **meta)
    except Exception as exc:
        return FileReadResult(**meta, error=str(exc))


def discover_files(folder: Path, recursive: bool = False) -> list[Path]:
    """
    Walk a directory and return all supported files.
    If recursive=True, descends into sub-folders.
    """
    pattern = "**/*" if recursive else "*"
    found = []
    for p in sorted(folder.glob(pattern)):
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
            found.append(p)
    return found


# ── Readers ────────────────────────────────────────────────────────────────

def _read_text(path: Path, **meta) -> FileReadResult:
    text = path.read_text(encoding="utf-8", errors="replace")
    return FileReadResult(text=_truncate(text), **meta)


def _read_csv(path: Path, **meta) -> FileReadResult:
    delimiter = "\t" if meta["file_type"] == ".tsv" else ","
    lines = []
    with open(path, newline="", encoding="utf-8", errors="replace") as fh:
        reader = csv.reader(fh, delimiter=delimiter)
        for i, row in enumerate(reader):
            lines.append(" | ".join(row))
            if i >= 500:          # cap rows fed to LLM
                lines.append("... (truncated at 500 rows)")
                break
    return FileReadResult(text=_truncate("\n".join(lines)), **meta)


def _read_json(path: Path, **meta) -> FileReadResult:
    raw = path.read_text(encoding="utf-8", errors="replace")
    if meta["file_type"] == ".jsonl":
        # each line is a JSON object
        objects = []
        for line in raw.splitlines()[:200]:
            line = line.strip()
            if line:
                try:
                    objects.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        text = json.dumps(objects, indent=2)
    else:
        try:
            parsed = json.loads(raw)
            text = json.dumps(parsed, indent=2)
        except json.JSONDecodeError:
            text = raw          # pass raw if malformed
    return FileReadResult(text=_truncate(text), **meta)


def _read_pdf(path: Path, **meta) -> FileReadResult:
    """
    Extracts text from every page of a PDF using PyMuPDF.
    Handles scanned PDFs gracefully — returns whatever text is embedded.
    """
    doc = fitz.open(str(path))
    pages_text = []

    for page_num, page in enumerate(doc, start=1):
        page_text = page.get_text()
        if page_text.strip():
            pages_text.append(f"--- Page {page_num} ---\n{page_text.strip()}")

    doc.close()

    if not pages_text:
        # PDF exists but has no extractable text (e.g. scanned image-only PDF)
        return FileReadResult(
            **meta,
            error="PDF has no extractable text. It may be a scanned image-only PDF."
        )

    full_text = "\n\n".join(pages_text)
    return FileReadResult(text=_truncate(full_text), **meta)


def _read_image(path: Path, **meta) -> FileReadResult:
    with open(path, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode("utf-8")
    return FileReadResult(image_b64=b64, is_image=True, **meta)


# ── Helpers ────────────────────────────────────────────────────────────────

def _truncate(text: str) -> str:
    if len(text) > MAX_CHARS_PER_FILE:
        return text[:MAX_CHARS_PER_FILE] + f"\n\n[... truncated at {MAX_CHARS_PER_FILE} chars]"
    return text