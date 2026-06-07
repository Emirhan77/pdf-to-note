from __future__ import annotations

import os
import re
from dataclasses import asdict

from services.sentence_scorer import ScoredSentence


DEFAULT_MAX_SOURCE_CHARS = 9000
TOPIC_WINDOW_CHARS = 650

CLOUD_TOPIC_QUERIES = [
    ("Bulut bilisim tanimi", ["bulut bilisimin tanimi", "nist", "bulut bilisim,"]),
    ("Bulut bilisimin gelisimi", ["bulut bilisimin gelisimi", "mainframe", "grid computing"]),
    ("Bulut bilisime duyulan ihtiyac", ["duyulan ihtiyac", "ihtiyac duyul", "maliyet"]),
    ("Temel paydaslar", ["tuketici:", "saglayici:", "gelistirici:"]),
    ("Hizmet modelleri", ["iaas", "paas", "saas", "servis olarak yazilim"]),
    ("Kullanim senaryolari", ["kullanim senaryolari", "bulut bilisim kullanim"]),
    ("Avantajlar ve dezavantajlar", ["avantaj ve dezavantaj", "avantajlari", "dezavantajlari"]),
    ("AB'de bulut bilisim", ["ab'de bulut", "ab'de bulut bilisim", "avrupa birligi"]),
    ("AB stratejisi", ["ab'nin bulut bilisim stratejisi", "avrupa komisyonu"]),
    ("Turkiye'de bulut bilisim", ["turkiye'de bulut", "turkiye kamu entegre", "yetkilendirilmis isletmeci"]),
    ("Sonuc ve oneriler", ["sonuc ve oneriler", "farkindalik", "politika ve strateji"]),
]

GENERIC_TOPIC_QUERIES = [
    ("Temel kavramlar", ["introduction", "overview", "basic concepts", "temel kavram", "genel bakis"]),
    ("Tanimlar", ["definition", "defined as", "is a", "tanimi", "olarak tanimlanir"]),
    ("Tarihce ve arka plan", ["history", "background", "historical", "tarihce", "arka plan"]),
    ("Yontemler ve yaklasimlar", ["method", "approach", "technique", "algorithm", "yontem", "yaklasim"]),
    ("Onemli problemler", ["problem", "challenge", "issue", "limitation", "problem", "sinirlilik"]),
    ("Ornekler", ["example", "for example", "such as", "ornek"]),
    ("Avantajlar ve sinirliliklar", ["advantage", "benefit", "limitation", "constraint", "avantaj", "sinirlilik"]),
    ("Sonuc ve genel degerlendirme", ["summary", "conclusion", "therefore", "sonuc", "degerlendirme"]),
]


def build_source_pack(
    *,
    file_name: str,
    page_count: int,
    clean_text: str,
    keywords: list[str],
    scored_sentences: list[ScoredSentence],
    question_count: int,
    output_language: str = "tr",
) -> dict:
    max_chars = int(os.getenv("LLM_MAX_SOURCE_CHARS", str(DEFAULT_MAX_SOURCE_CHARS)))
    prepared_text = _prepare_source_text(clean_text)
    topic_profile = _detect_topic_profile(file_name, prepared_text, keywords)
    topic_sections = _build_topic_sections(prepared_text, topic_profile)
    selected_sentences = _dedupe_selected_sentences(
        [
            asdict(item)
            for item in scored_sentences
            if item.noise_score < 3 and item.word_count >= 6
        ],
        limit=50,
    )
    source_text = _compose_balanced_source(topic_sections, selected_sentences, prepared_text, max_chars)

    return {
        "file_name": file_name,
        "page_count": page_count,
        "output_language": output_language,
        "question_count": question_count,
        "keywords": keywords,
        "source_text": source_text,
        "source_text_truncated": len(prepared_text) > len(source_text),
        "clean_text_word_count": len(prepared_text.split()),
        "topic_sections": topic_sections,
        "topic_profile": topic_profile,
        "selected_sentences": selected_sentences,
        "method_note": (
            "Bu not, yuklenen PDF metninin temizlenmis ve konu bazli dengelenmis "
            "kaynak paketinden LLM yardimiyla uretilmistir."
        ),
    }


def _prepare_source_text(text: str) -> str:
    text = re.sub(r"\.{5,}\s*(?:[ivxlcdm]+|\d+)?", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:YONETICI OZETI|ICINDEKILER|TABLOLAR LISTESI|SEKILLER LISTESI)\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _detect_topic_profile(file_name: str, text: str, keywords: list[str]) -> str:
    folded = _fold_tr(" ".join([file_name, text[:12000], " ".join(keywords)]))
    cloud_terms = ("bulut", "cloud", "saas", "paas", "iaas")
    cloud_score = sum(folded.count(term) for term in cloud_terms)
    cloud_context = any(term in folded for term in ("veri merkezi", "data center", "nist", "servis olarak"))
    if cloud_score >= 5 or (cloud_score >= 2 and cloud_context):
        return "cloud"
    return "generic_academic"


def _build_topic_sections(text: str, topic_profile: str) -> list[dict]:
    normalized = _fold_tr(text)
    sections: list[dict] = []
    used_ranges: list[tuple[int, int]] = []
    topic_queries = CLOUD_TOPIC_QUERIES if topic_profile == "cloud" else GENERIC_TOPIC_QUERIES

    for label, queries in topic_queries:
        match_index = _find_first(normalized, [_fold_tr(query) for query in queries])
        if match_index < 0:
            continue
        start = max(0, match_index - 450)
        end = min(len(text), match_index + TOPIC_WINDOW_CHARS)
        start, end = _avoid_large_overlap(start, end, used_ranges, len(text))
        if end <= start:
            continue
        excerpt = _trim_to_sentence_boundary(text[start:end])
        if len(excerpt.split()) < 25:
            continue
        used_ranges.append((start, end))
        sections.append({"heading": label, "text": excerpt})

    return sections


def _compose_balanced_source(
    topic_sections: list[dict],
    selected_sentences: list[dict],
    fallback_text: str,
    max_chars: int,
) -> str:
    parts: list[str] = []

    if topic_sections:
        for section in topic_sections:
            parts.append(f"## {section['heading']}\n{section['text']}")
    else:
        parts.append(_truncate_preserving_words(fallback_text, max_chars))

    if selected_sentences:
        sentence_lines = []
        for item in selected_sentences[:4]:
            sentence = str(item.get("sentence", "")).strip()
            if sentence:
                sentence_lines.append(f"- {sentence}")
        if sentence_lines:
            parts.append("## Skorlanmis onemli cumleler\n" + "\n".join(sentence_lines))

    return _truncate_preserving_words("\n\n".join(parts), max_chars)


def _dedupe_selected_sentences(sentences: list[dict], limit: int) -> list[dict]:
    selected = []
    seen: set[str] = set()
    for item in sentences:
        sentence = str(item.get("sentence", "")).strip()
        key = _sentence_key(sentence)
        if not key or key in seen:
            continue
        seen.add(key)
        selected.append(item)
        if len(selected) >= limit:
            break
    return selected


def _sentence_key(sentence: str) -> str:
    folded = _fold_tr(sentence)
    words = re.findall(r"[a-z0-9]+", folded)
    words = [word for word in words if len(word) > 3]
    return " ".join(words[:18])


def _find_first(text: str, queries: list[str]) -> int:
    positions = [text.find(query) for query in queries if text.find(query) >= 0]
    return min(positions) if positions else -1


def _avoid_large_overlap(start: int, end: int, used_ranges: list[tuple[int, int]], text_length: int) -> tuple[int, int]:
    for used_start, used_end in used_ranges:
        overlap = max(0, min(end, used_end) - max(start, used_start))
        if overlap > (end - start) * 0.65:
            start = min(text_length, used_end + 1)
            end = min(text_length, start + TOPIC_WINDOW_CHARS)
    return start, end


def _trim_to_sentence_boundary(text: str) -> str:
    text = text.strip(" ,.;:-")
    first_period = text.find(". ")
    if 0 <= first_period < 160:
        text = text[first_period + 2 :]
    last_period = max(text.rfind(". "), text.rfind("? "), text.rfind("! "))
    if last_period > 600:
        text = text[: last_period + 1]
    return text.strip()


def _truncate_preserving_words(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    if " " in truncated:
        truncated = truncated.rsplit(" ", 1)[0]
    return truncated.strip()


def _fold_tr(text: str) -> str:
    table = str.maketrans(
        {
            "ç": "c",
            "ğ": "g",
            "ı": "i",
            "i": "i",
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
    return text.translate(table).casefold()
