from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class TextUnit:
    text: str
    source_page: int | None = None
    source_type: str = "content"


NOISE_PATTERNS = [
    r"^sayfa\s+\d+\s*$",
    r"^\d+\s*$",
    r"^şekil\s+\d+.*$",
    r"^sekil\s+\d+.*$",
    r"^tablo\s+\d+.*$",
    r"^kaynakça.*$",
    r"^kaynakca.*$",
    r"^references.*$",
    r"https?://\S+",
    r"www\.\S+",
    r"^slide\s+\d+(\.\d+)*.*$",
    r"^section\s+\d+(\.\d+)*.*$",
    r"^\d+(\.\d+)+\s*$",
    r"^6\.034\s+notes.*$",
]

BULLET_CHARS = "•►▪▫●○■□–"
LAYOUT_PREFIXES = ("slide", "section", "notes", "copyright", "page")

TURKISH_CHAR_REPAIRS = str.maketrans(
    {
        "ţ": "ş",
        "Ţ": "Ş",
        "þ": "ş",
        "Þ": "Ş",
        "ý": "ı",
        "Ý": "İ",
        "ð": "ğ",
        "Ð": "Ğ",
        "đ": "ğ",
        "Đ": "Ğ",
    }
)


def clean_text(raw_text: str) -> str:
    seen_lines: set[str] = set()
    cleaned_lines: list[str] = []

    for raw_line in raw_text.splitlines():
        line = _normalize_line(raw_line)
        if not line:
            continue
        if _is_noise_line(line):
            continue
        normalized = line.casefold()
        if normalized in seen_lines:
            continue
        seen_lines.add(normalized)
        cleaned_lines.append(line)

    joined = "\n".join(cleaned_lines)
    return re.sub(r"\s+", " ", joined).strip()


def clean_blocks(blocks: list) -> list[TextUnit]:
    seen_lines: set[str] = set()
    units: list[TextUnit] = []

    for block in blocks:
        page = getattr(block, "page", None)
        raw_text = getattr(block, "text", str(block))
        for raw_piece in _split_bullets(raw_text):
            line = _normalize_line(raw_piece)
            if not line or _is_noise_line(line):
                continue
            normalized = line.casefold()
            if normalized in seen_lines:
                continue
            seen_lines.add(normalized)
            units.append(TextUnit(text=line, source_page=page, source_type=_source_type(line)))

    return units


def units_to_text(units: list[TextUnit]) -> str:
    return " ".join(unit.text for unit in units)


def split_sentences(text_or_units: str | list[TextUnit]) -> list[TextUnit]:
    if isinstance(text_or_units, str):
        units = [TextUnit(text=text_or_units)]
    else:
        units = text_or_units

    sentences: list[TextUnit] = []
    for unit in units:
        for piece in _split_bullets(unit.text):
            piece = re.sub(r"\s+", " ", piece).strip()
            if not piece:
                continue
            candidates = re.split(r"(?<=[.!?])\s+|(?<=;)\s+", piece)
            for candidate in candidates:
                candidate = _trim_sentence(candidate)
                if _is_valid_sentence(candidate):
                    sentences.append(
                        TextUnit(
                            text=candidate,
                            source_page=unit.source_page,
                            source_type=unit.source_type,
                        )
                    )
    return sentences


def _normalize_line(raw_line: str) -> str:
    raw_line = _repair_turkish_mojibake(raw_line)
    line = raw_line.replace("\uf0b7", " ").replace("\u2022", " ")
    line = re.sub(rf"[{re.escape(BULLET_CHARS)}]+", " ", line)
    line = re.sub(r"\s+", " ", line).strip()
    line = re.sub(r"^(?:[-*]+|\d+[.)])\s+", "", line)
    return line.strip()


def _repair_turkish_mojibake(text: str) -> str:
    return text.translate(TURKISH_CHAR_REPAIRS)


def _split_bullets(text: str) -> list[str]:
    marked = text
    marked = re.sub(rf"\s*[{re.escape(BULLET_CHARS)}]\s*", "\n", marked)
    marked = re.sub(r"\s+(?=\d+[.)]\s+)", "\n", marked)
    marked = re.sub(r"\s+(?=[A-ZÇĞİÖŞÜ][A-Za-zÇĞİÖŞÜçğıöşü ]{2,30}:\s)", "\n", marked)
    return [part.strip() for part in marked.splitlines() if part.strip()]


def _is_noise_line(line: str) -> bool:
    normalized = line.casefold().strip()
    if len(normalized) < 3:
        return True
    if any(re.search(pattern, line, flags=re.IGNORECASE) for pattern in NOISE_PATTERNS):
        return True
    if normalized.startswith(LAYOUT_PREFIXES):
        return True
    if re.fullmatch(r"[\d\s./:-]+", normalized):
        return True
    if len(normalized.split()) <= 2 and not normalized.endswith(":"):
        return True
    return False


def _source_type(line: str) -> str:
    normalized = line.casefold()
    if line.endswith(":") or re.match(r"^\d+(\.\d+)*\s+[A-ZÇĞİÖŞÜ]", line):
        return "heading"
    if any(marker in normalized for marker in ("slide", "section", "notes")):
        return "layout"
    return "content"


def _trim_sentence(sentence: str) -> str:
    sentence = sentence.strip(" -–:;")
    sentence = re.sub(r"\s+", " ", sentence)
    words = sentence.split()
    if len(words) > 45:
        sentence = " ".join(words[:45]).rstrip(",;:")
    return sentence


def _is_valid_sentence(sentence: str) -> bool:
    words = sentence.split()
    if len(words) < 6:
        return False
    if len(sentence) < 25:
        return False
    if _is_noise_line(sentence):
        return False
    return True
