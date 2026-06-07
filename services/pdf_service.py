from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PdfTextBlock:
    page: int
    text: str
    word_count: int
    noise_hint: str


@dataclass(frozen=True)
class PdfExtraction:
    text: str
    page_count: int
    blocks: list[PdfTextBlock]


def validate_pdf_upload(uploaded_file: Any) -> str | None:
    if uploaded_file is None or not uploaded_file.filename:
        return "Lutfen bir PDF dosyasi secin."

    filename = uploaded_file.filename.lower()
    if not filename.endswith(".pdf"):
        return "Yalnizca PDF dosyalari yuklenebilir."

    uploaded_file.stream.seek(0, 2)
    size = uploaded_file.stream.tell()
    uploaded_file.stream.seek(0)
    if size == 0:
        return "Yuklenen PDF bos gorunuyor."

    return None


def extract_pdf_text(pdf_path: Path) -> PdfExtraction:
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("PyMuPDF kurulu degil. `pip install -r requirements.txt` calistirin.") from exc

    document = fitz.open(pdf_path)
    try:
        extracted_blocks: list[PdfTextBlock] = []
        for page_index, page in enumerate(document, start=1):
            for block in page.get_text("blocks", sort=True):
                if len(block) < 5:
                    continue
                block_text = " ".join(str(block[4]).split())
                if not block_text:
                    continue
                extracted_blocks.append(
                    PdfTextBlock(
                        page=page_index,
                        text=block_text,
                        word_count=len(block_text.split()),
                        noise_hint=_noise_hint(block_text),
                    )
                )

        text = "\n".join(block.text for block in extracted_blocks).strip()
        if not text:
            raise ValueError("PDF metni cikarilamadi. Bu dosya taranmis olabilir; OCR gerekli.")
        return PdfExtraction(text=text, page_count=document.page_count, blocks=extracted_blocks)
    finally:
        document.close()


def _noise_hint(text: str) -> str:
    normalized = text.casefold()
    if any(marker in normalized for marker in ("slide", "section", "notes", "sayfa")):
        return "layout"
    if any(marker in normalized for marker in ("http://", "https://", "www.")):
        return "url"
    if len(text.split()) <= 3:
        return "short"
    return "content"
