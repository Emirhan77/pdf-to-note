from __future__ import annotations

from collections import Counter
import re

from services.document_chunker import DocumentChunk


DEFAULT_SOURCE_NOTE = "Bu ders notu PDF kaynagindan cikarilan metin ve outline_v2 extractive birlestirme adimlariyla uretilmistir."

NOISE_KEYWORDS = {
    "slide",
    "section",
    "notes",
    "page",
    "line",
    "html",
    "javascript",
    "button",
    "make",
    "sure",
    "someone",
    "else",
    "browser",
    "virtual",
    "machine",
    "submitted",
    "contents",
    "credit",
    "problems",
}

STOPWORDS = {
    "the",
    "and",
    "you",
    "your",
    "are",
    "for",
    "not",
    "will",
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
    "ve",
    "veya",
    "ile",
    "icin",
    "gibi",
    "olan",
    "olarak",
    "daha",
    "cok",
    "bir",
    "bu",
    "su",
    "o",
    "da",
    "de",
    "mi",
    "ise",
    "ancak",
    "fakat",
}


def compose_study_pack_from_outline(chunks: list[DocumentChunk], outline: dict) -> dict:
    chunk_map = {chunk.chunk_id: chunk for chunk in chunks}
    document_title = str(outline.get("document_title") or "PDF Notu").strip() or "PDF Notu"
    outline_sections = outline.get("sections") or []

    sections: list[dict] = []
    keywords_counter: Counter[str] = Counter()

    for section in outline_sections:
        heading = _clean_heading(section.get("heading"))
        source_chunk_ids = section.get("source_chunk_ids") or []
        selected_chunks = [chunk_map[chunk_id] for chunk_id in source_chunk_ids if chunk_id in chunk_map]
        if not selected_chunks:
            continue

        content = _compose_content_from_chunks(selected_chunks, section)
        if not content:
            continue

        key_points = _build_key_points(section, selected_chunks, content)
        key_points = [point for point in key_points if _is_meaningful_point(point)]

        section_entry = {
            "heading": heading or "Bolum",
            "content": content,
            "key_points": key_points[:5],
        }
        sections.append(section_entry)

        for concept in (section.get("key_concepts") or []):
            token = _clean_keyword(concept)
            if token:
                keywords_counter[token] += 3
        for chunk in selected_chunks:
            for term in chunk.key_terms[:8]:
                token = _clean_keyword(term)
                if token:
                    keywords_counter[token] += 1

    keywords = _select_keywords(keywords_counter, limit=18)

    return {
        "title": document_title,
        "sections": sections,
        "keywords": keywords,
        "source_note": DEFAULT_SOURCE_NOTE,
        "provider": "extractive_outline_v2",
    }


def _compose_content_from_chunks(chunks: list[DocumentChunk], section: dict) -> str:
    joined_text = "\n".join(chunk.text for chunk in chunks if chunk.text).strip()
    sentences = _split_sentences(joined_text)
    topic_terms = _section_terms(section)
    ranked = sorted(sentences, key=lambda sentence: _sentence_score(sentence, topic_terms), reverse=True)

    picked: list[str] = []
    for sentence in ranked:
        cleaned = _clean_sentence(sentence)
        if not cleaned:
            continue
        if any(_is_near_duplicate(cleaned, existing) for existing in picked):
            continue
        picked.append(cleaned)
        if len(picked) >= 4:
            break

    if len(picked) < 2:
        for sentence in sentences:
            cleaned = _clean_sentence(sentence)
            if not cleaned:
                continue
            if any(_is_near_duplicate(cleaned, existing) for existing in picked):
                continue
            picked.append(cleaned)
            if len(picked) >= 2:
                break

    return " ".join(picked[:4]).strip()


def _build_key_points(section: dict, chunks: list[DocumentChunk], content: str) -> list[str]:
    points: list[str] = []

    for concept in section.get("key_concepts") or []:
        cleaned = _clean_point(concept)
        if cleaned and cleaned not in points:
            points.append(cleaned)
        if len(points) >= 3:
            break

    if len(points) < 3:
        for chunk in chunks:
            for term in chunk.key_terms[:6]:
                cleaned = _clean_point(term)
                if cleaned and cleaned not in points:
                    points.append(cleaned)
                if len(points) >= 5:
                    break
            if len(points) >= 5:
                break

    if len(points) < 3:
        for sentence in _split_sentences(content):
            cleaned = _clean_point(_summarize_sentence_to_point(sentence))
            if cleaned and cleaned not in points:
                points.append(cleaned)
            if len(points) >= 5:
                break

    return points[:5]


def _select_keywords(counter: Counter[str], limit: int = 18) -> list[str]:
    selected: list[str] = []
    seen: set[str] = set()
    for item, _score in counter.most_common(64):
        folded = _fold(item)
        if not folded or folded in seen:
            continue
        if _is_noise_keyword(item):
            continue
        if any(folded in old or old in folded for old in seen):
            continue
        selected.append(item)
        seen.add(folded)
        if len(selected) >= limit:
            break
    return selected


def _split_sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", str(text)).strip()
    if not normalized:
        return []
    return [
        segment.strip()
        for segment in re.split(r"(?<=[.!?])\s+", normalized)
        if segment.strip()
    ]


def _sentence_score(sentence: str, topic_terms: set[str] | None = None) -> float:
    words = sentence.split()
    wc = len(words)
    if wc < 8:
        return -5.0
    if wc > 55:
        return -2.0
    score = 0.0
    score += min(wc, 32) / 8.0
    if re.search(r"\b(is|are|means|defined|denir|tanim|ifade eder|olarak)\b", sentence, re.IGNORECASE):
        score += 2.0
    if re.search(r"\b(avantaj|dezavantaj|risk|benefit|limitation|problem|yontem|yaklasim|model)\b", sentence, re.IGNORECASE):
        score += 1.2
    if re.search(r"\b(slide|section|notes|copyright)\b", sentence, re.IGNORECASE):
        score -= 3.0
    if re.search(r"\b(browser|java virtual machine|gold star|contents page|submitted|full credit)\b", sentence, re.IGNORECASE):
        score -= 2.5
    folded_sentence = _fold(sentence)
    for term in topic_terms or set():
        if term and term in folded_sentence:
            score += 1.8 if " " in term else 0.8
    return score


def _clean_sentence(sentence: str) -> str:
    s = re.sub(r"\s+", " ", sentence).strip(" \n\t-")
    if len(s.split()) < 8:
        return ""
    if len(s) > 360:
        return ""
    if not re.search(r"[.!?]$", s):
        s = f"{s}."
    return s


def _is_near_duplicate(left: str, right: str) -> bool:
    left_set = set(_fold(left).split())
    right_set = set(_fold(right).split())
    if not left_set or not right_set:
        return False
    overlap = len(left_set & right_set) / max(1, min(len(left_set), len(right_set)))
    return overlap >= 0.8


def _summarize_sentence_to_point(sentence: str) -> str:
    words = sentence.split()
    if len(words) <= 12:
        return sentence.strip()
    return " ".join(words[:12]).strip(" ,.;:") + "..."


def _is_meaningful_point(text: str) -> bool:
    words = text.split()
    if len(words) < 2:
        return False
    if len(words) == 2 and len("".join(words)) < 10:
        return False
    if len(words) > 16:
        return False
    folded = _fold(text)
    if folded in {"calisma sorulari", "study questions", "questions"}:
        return False
    return True


def _clean_keyword(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(text)).strip(" \n\t,.;:-")
    if not cleaned:
        return ""
    if _is_noise_keyword(cleaned):
        return ""
    return cleaned


def _clean_point(text: str) -> str:
    cleaned = _clean_keyword(text)
    if not cleaned:
        return ""
    if len(cleaned.split()) < 2 and len(cleaned) < 8:
        return ""
    return cleaned


def _section_terms(section: dict) -> set[str]:
    raw_terms = [str(section.get("heading", ""))]
    raw_terms.extend(str(item) for item in section.get("key_concepts") or [])
    terms: set[str] = set()
    for item in raw_terms:
        folded = _fold(item)
        if not folded:
            continue
        terms.add(folded)
        for word in folded.split():
            if len(word) >= 5 and word not in STOPWORDS and word not in NOISE_KEYWORDS:
                terms.add(word)
    return terms


def _clean_heading(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip(" \n\t#-")
    return cleaned


def _is_noise_keyword(text: str) -> bool:
    folded = _fold(text)
    if not folded:
        return True
    words = folded.split()
    if all(word in STOPWORDS for word in words):
        return True
    if any(word in NOISE_KEYWORDS for word in words):
        return True
    if len(words) == 1 and (len(words[0]) < 4 or words[0].isdigit()):
        return True
    return False


def _fold(text: str) -> str:
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
