from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re

from services.text_cleaner import TextUnit


@dataclass(frozen=True)
class DocumentChunk:
    chunk_id: str
    title_hint: str
    page_start: int | None
    page_end: int | None
    text: str
    word_count: int
    key_terms: list[str]


STOPWORDS = {
    "a",
    "an",
    "about",
    "all",
    "am",
    "and",
    "any",
    "are",
    "as",
    "after",
    "again",
    "also",
    "another",
    "at",
    "be",
    "been",
    "being",
    "both",
    "because",
    "before",
    "between",
    "but",
    "by",
    "can",
    "could",
    "did",
    "does",
    "do",
    "during",
    "each",
    "for",
    "from",
    "had",
    "has",
    "have",
    "he",
    "her",
    "hers",
    "him",
    "his",
    "how",
    "if",
    "in",
    "is",
    "it",
    "its",
    "into",
    "like",
    "may",
    "many",
    "more",
    "most",
    "much",
    "must",
    "no",
    "nor",
    "not",
    "of",
    "on",
    "or",
    "only",
    "other",
    "over",
    "same",
    "should",
    "such",
    "that",
    "the",
    "them",
    "then",
    "these",
    "they",
    "this",
    "those",
    "to",
    "too",
    "than",
    "there",
    "their",
    "through",
    "under",
    "until",
    "up",
    "very",
    "was",
    "we",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "who",
    "whom",
    "why",
    "will",
    "with",
    "would",
    "you",
    "your",
    "yours",
    "i",
    "me",
    "my",
    "mine",
    "through",
    "used",
    "using",
    "could",
    "should",
    "would",
    "can",
    "may",
    "how",
    "what",
    "about",
    "when",
    "where",
    "which",
    "from",
    "have",
    "this",
    "that",
    "they",
    "them",
    "into",
    "acaba",
    "ancak",
    "ama",
    "bazi",
    "baska",
    "bile",
    "bircok",
    "birden",
    "biri",
    "birisi",
    "birlikte",
    "boyle",
    "bu",
    "bunun",
    "bir",
    "biraz",
    "biz",
    "daha",
    "da",
    "de",
    "degil",
    "diye",
    "edilen",
    "eder",
    "en",
    "fakat",
    "gibi",
    "hem",
    "her",
    "icin",
    "ile",
    "ise",
    "mi",
    "mı",
    "mu",
    "mü",
    "ne",
    "olan",
    "olarak",
    "oldugu",
    "olur",
    "o",
    "şu",
    "sonra",
    "sure",
    "tarafindan",
    "ve",
    "veya",
    "ya",
    "yada",
    "uzere",
    "yani",
    "çok",
}

NOISE_TERMS = {
    "able",
    "button",
    "check",
    "else",
    "html",
    "javascript",
    "line",
    "make",
    "notes",
    "page",
    "section",
    "slide",
    "someone",
    "sure",
    "the",
    "you",
    "your",
    "and",
    "for",
    "with",
    "this",
    "that",
    "have",
    "from",
    "they",
    "them",
    "can",
    "may",
    "should",
    "would",
    "could",
    "into",
    "about",
    "when",
    "where",
    "which",
    "what",
    "how",
}

WEAK_TITLE_PHRASES = {
    "yer almaktadir",
    "yer almaktadır",
    "hususlar asagida ozetlenmistir",
    "hususlar aşağıda özetlenmiştir",
    "kaynaklar",
    "references",
    "kaynakca",
    "kaynakça",
}

PRIORITY_PHRASES = {
    "knowledge representation",
    "problem set",
    "artificial intelligence",
    "machine learning",
    "bulut bilisim",
    "bulut bilişim",
    "servis saglayici",
    "servis sağlayıcı",
    "veri merkezi",
}


def build_document_chunks(
    text_or_units: str | list[TextUnit],
    target_words: int = 700,
    min_words: int = 180,
    max_words: int = 900,
) -> list[DocumentChunk]:
    target_words = max(250, target_words)
    min_words = max(60, min(min_words, target_words))
    max_words = max(target_words, max_words)

    units = _coerce_units(text_or_units)
    chunks: list[DocumentChunk] = []
    current_units: list[TextUnit] = []
    current_title = ""
    current_words = 0

    for unit in units:
        for piece in _split_long_unit(unit, max_words):
            text = _normalize_text(piece.text)
            if not text:
                continue
            piece = TextUnit(text=text, source_page=piece.source_page, source_type=piece.source_type)
            piece_words = _word_count(text)
            is_heading = _looks_like_heading(piece)

            if is_heading:
                if current_words >= min_words:
                    chunks.append(_finalize_chunk(len(chunks) + 1, current_title, current_units))
                    current_units = []
                    current_words = 0
                current_title = text

            if current_units and current_words + piece_words > max_words:
                chunks.append(_finalize_chunk(len(chunks) + 1, current_title, current_units))
                current_units = []
                current_words = 0
                current_title = text if is_heading else ""

            current_units.append(piece)
            current_words += piece_words

            if current_words >= target_words:
                chunks.append(_finalize_chunk(len(chunks) + 1, current_title, current_units))
                current_units = []
                current_words = 0
                current_title = ""

    if current_units:
        chunks.append(_finalize_chunk(len(chunks) + 1, current_title, current_units))

    return _merge_short_chunks(chunks, min_words, max_words)


def _coerce_units(text_or_units: str | list[TextUnit]) -> list[TextUnit]:
    if isinstance(text_or_units, str):
        parts = _split_plain_text(text_or_units)
        return [
            TextUnit(text=part, source_page=None, source_type="heading" if _looks_like_heading(part) else "content")
            for part in parts
        ]
    return [unit for unit in text_or_units if _normalize_text(getattr(unit, "text", ""))]


def _split_plain_text(text: str) -> list[str]:
    text = text.replace("\r\n", "\n")
    lines = [_normalize_text(line) for line in text.splitlines() if _normalize_text(line)]
    if len(lines) > 1:
        return lines

    normalized = _normalize_text(text)
    if not normalized:
        return []
    return [
        part.strip()
        for part in re.split(r"(?<=[.!?])\s+", normalized)
        if len(part.strip().split()) >= 4
    ] or [normalized]


def _looks_like_heading(unit_or_text: TextUnit | str) -> bool:
    if isinstance(unit_or_text, TextUnit):
        text = unit_or_text.text.strip()
        if unit_or_text.source_type == "heading":
            return True
    else:
        text = unit_or_text.strip()

    words = text.split()
    if not 3 <= len(words) <= 12:
        return False
    if re.match(r"^\d+(?:\.\d+)*[.)]?\s+\S+", text):
        return True
    if text.endswith(":"):
        return True
    letters = [char for char in text if char.isalpha()]
    if letters:
        uppercase_ratio = sum(1 for char in letters if char.isupper()) / len(letters)
        if uppercase_ratio >= 0.65 and len(words) >= 3:
            return True
    title_like_words = sum(1 for word in words if word[:1].isupper())
    return title_like_words >= max(2, len(words) - 1)


def _split_long_unit(unit: TextUnit, max_words: int) -> list[TextUnit]:
    text = _normalize_text(unit.text)
    if _word_count(text) <= max_words:
        return [unit]

    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    if len(sentences) <= 1:
        return [
            TextUnit(text=" ".join(words), source_page=unit.source_page, source_type=unit.source_type)
            for words in _batch_words(text.split(), max_words)
        ]

    pieces: list[TextUnit] = []
    current: list[str] = []
    current_words = 0
    for sentence in sentences:
        sentence_words = _word_count(sentence)
        if current and current_words + sentence_words > max_words:
            pieces.append(TextUnit(text=" ".join(current), source_page=unit.source_page, source_type=unit.source_type))
            current = []
            current_words = 0
        current.append(sentence)
        current_words += sentence_words
    if current:
        pieces.append(TextUnit(text=" ".join(current), source_page=unit.source_page, source_type=unit.source_type))
    return pieces


def _finalize_chunk(index: int, title_hint: str, units: list[TextUnit]) -> DocumentChunk:
    text = "\n".join(unit.text for unit in units).strip()
    pages = [unit.source_page for unit in units if unit.source_page is not None]
    word_count = _word_count(text)
    normalized_title = _select_title_hint(title_hint, units)
    return DocumentChunk(
        chunk_id=f"chunk_{index:03d}",
        title_hint=normalized_title,
        page_start=min(pages) if pages else None,
        page_end=max(pages) if pages else None,
        text=text,
        word_count=word_count,
        key_terms=_extract_key_terms(text),
    )


def _extract_key_terms(text: str, limit: int = 8) -> list[str]:
    tokens = _tokenize_terms(text)
    single_counts = Counter(token for token in tokens if _is_term_token(token) and len(token) >= 5)
    bi_counts = Counter(
        f"{left} {right}"
        for left, right in zip(tokens, tokens[1:])
        if _is_term_token(left) and _is_term_token(right)
    )
    tri_counts = Counter(
        f"{a} {b} {c}"
        for a, b, c in zip(tokens, tokens[1:], tokens[2:])
        if _is_term_token(a) and _is_term_token(b) and _is_term_token(c)
    )

    scored: list[tuple[float, str]] = []
    for term, count in single_counts.items():
        scored.append((count * 0.7 + min(len(term), 14) / 28, term))
    for term, count in bi_counts.items():
        term_score = count * 2.8 + len(term) / 22
        if _is_priority_phrase(term):
            term_score += 4.0
        if count > 1 or _contains_strong_term(term):
            scored.append((term_score, term))
    for term, count in tri_counts.items():
        term_score = count * 4.2 + len(term) / 18
        if _is_priority_phrase(term):
            term_score += 6.0
        if count > 0 and _contains_strong_term(term):
            scored.append((term_score, term))

    terms: list[str] = []
    seen: set[str] = set()
    for _score, term in sorted(scored, key=lambda item: (-item[0], item[1])):
        folded = _fold_text(term)
        if _is_too_generic_term(term):
            continue
        if folded in seen or any(_overlaps_term(folded, _fold_text(existing)) for existing in terms):
            continue
        seen.add(folded)
        terms.append(term)
        if len(terms) >= limit:
            break
    return terms


def _fold_text(text: str) -> str:
    table = str.maketrans(
        {
            "ç": "c",
            "ğ": "g",
            "ı": "i",
            "ö": "o",
            "ş": "s",
            "ü": "u",
            "Ç": "c",
            "Ğ": "g",
            "İ": "i",
            "I": "i",
            "Ö": "o",
            "Ş": "s",
            "Ü": "u",
        }
    )
    return re.sub(r"[^a-z0-9]+", " ", text.translate(table).casefold()).strip()


def _merge_short_chunks(chunks: list[DocumentChunk], min_words: int, max_words: int) -> list[DocumentChunk]:
    merged: list[DocumentChunk] = []
    for chunk in chunks:
        if merged and chunk.word_count < min_words and merged[-1].word_count + chunk.word_count <= int(max_words * 1.15):
            previous = merged.pop()
            merged.append(_merge_pair(previous, chunk, len(merged) + 1))
        else:
            merged.append(chunk)
    return [_renumber_chunk(chunk, index + 1) for index, chunk in enumerate(merged)]


def _merge_pair(left: DocumentChunk, right: DocumentChunk, index: int) -> DocumentChunk:
    text = "\n".join(part for part in (left.text, right.text) if part).strip()
    pages = [page for page in (left.page_start, left.page_end, right.page_start, right.page_end) if page is not None]
    return DocumentChunk(
        chunk_id=f"chunk_{index:03d}",
        title_hint=left.title_hint or right.title_hint,
        page_start=min(pages) if pages else None,
        page_end=max(pages) if pages else None,
        text=text,
        word_count=_word_count(text),
        key_terms=_extract_key_terms(text),
    )


def _renumber_chunk(chunk: DocumentChunk, index: int) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=f"chunk_{index:03d}",
        title_hint=chunk.title_hint,
        page_start=chunk.page_start,
        page_end=chunk.page_end,
        text=chunk.text,
        word_count=chunk.word_count,
        key_terms=chunk.key_terms,
    )


def _fallback_title(units: list[TextUnit]) -> str:
    for unit in units[:3]:
        candidate = unit.text.strip(" #:")
        if _looks_like_heading(unit) and not _is_weak_title(candidate):
            return candidate
    for unit in units[:5]:
        candidate = unit.text.strip(" #:")
        if _is_title_like_sentence(candidate):
            return candidate
    return "Genel Bolum"


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text)).strip()


def _word_count(text: str) -> int:
    return len(text.split())


def _tokenize_terms(text: str) -> list[str]:
    return re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü0-9]{3,}", text.casefold())


def _is_term_token(token: str) -> bool:
    folded = _fold_text(token)
    return len(folded) >= 3 and folded not in STOPWORDS and folded not in NOISE_TERMS and not folded.isdigit()


def _select_title_hint(title_hint: str, units: list[TextUnit]) -> str:
    candidate = title_hint.strip(" #:")
    if candidate and not _is_weak_title(candidate):
        return candidate
    return _fallback_title(units)


def _is_weak_title(title: str) -> bool:
    folded = _fold_text(title)
    if not folded:
        return True
    if folded in WEAK_TITLE_PHRASES:
        return True
    if folded.startswith("kaynaklar") or folded.startswith("references"):
        return True
    if re.fullmatch(r"[0-9 ]+", folded):
        return True
    if re.search(r"\b(tez|ankara|copyright)\b", folded) and len(folded.split()) <= 4:
        return True
    return False


def _is_title_like_sentence(text: str) -> bool:
    words = text.split()
    if len(words) < 3 or len(words) > 14:
        return False
    if len(text) > 100:
        return False
    if text.endswith((".", "?", "!")):
        return False
    if _is_weak_title(text):
        return False
    strong_ratio = sum(1 for word in words if len(_fold_text(word)) >= 5) / max(1, len(words))
    return strong_ratio >= 0.45


def _is_priority_phrase(term: str) -> bool:
    folded = _fold_text(term)
    return folded in {_fold_text(item) for item in PRIORITY_PHRASES}


def _contains_strong_term(term: str) -> bool:
    folded = _fold_text(term)
    parts = folded.split()
    return any(len(part) >= 6 and part not in STOPWORDS and part not in NOISE_TERMS for part in parts)


def _is_too_generic_term(term: str) -> bool:
    folded = _fold_text(term)
    parts = folded.split()
    if not parts:
        return True
    if len(parts) == 1 and (len(parts[0]) < 5 or parts[0] in STOPWORDS or parts[0] in NOISE_TERMS):
        return True
    if all(part in STOPWORDS or part in NOISE_TERMS for part in parts):
        return True
    if parts[0] in {"the", "you", "your", "and", "for"} and len(parts) <= 2:
        return True
    return False


def _overlaps_term(left: str, right: str) -> bool:
    return left == right or left in right or right in left


def _batch_words(words: list[str], max_words: int) -> list[list[str]]:
    return [words[index : index + max_words] for index in range(0, len(words), max_words)]
