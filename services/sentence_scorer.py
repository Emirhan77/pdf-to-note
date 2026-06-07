from __future__ import annotations

from dataclasses import dataclass

from services.text_cleaner import TextUnit


POSITIVE_MARKERS = {
    "amac": 2,
    "amaç": 2,
    "avantaj": 2,
    "dezavantaj": 2,
    "onem": 2,
    "önem": 2,
    "kullanilir": 2,
    "kullanılır": 2,
    "saglar": 2,
    "sağlar": 2,
    "ayrilir": 2,
    "ayrılır": 2,
    "türleri": 2,
    "turleri": 2,
    "modelleri": 2,
    "hedef": 2,
}

DEFINITION_MARKERS = (
    " olarak tanimlanir",
    " olarak tanımlanır",
    " ifade eder ",
    " denir",
    " sistemidir",
    " modelidir",
    " hizmetidir",
    " kavramıdır",
    " kavramidir",
)
NEGATIVE_MARKERS = (
    "kaynakca",
    "kaynakça",
    "sekil",
    "şekil",
    "tablo",
    "sayfa",
    "slide",
    "section",
    "notes",
    "debug",
    "copyright",
)


@dataclass(frozen=True)
class ScoredSentence:
    sentence: str
    score: int
    reason: str
    word_count: int
    noise_score: int
    content_type: str
    source_page: int | None = None


def score_sentences(sentences: list[str] | list[TextUnit]) -> list[ScoredSentence]:
    scored = [_score_sentence(sentence) for sentence in sentences]
    return sorted(scored, key=lambda item: item.score, reverse=True)


def _score_sentence(sentence_or_unit: str | TextUnit) -> ScoredSentence:
    if isinstance(sentence_or_unit, TextUnit):
        sentence = sentence_or_unit.text
        source_page = sentence_or_unit.source_page
        content_type = sentence_or_unit.source_type
    else:
        sentence = sentence_or_unit
        source_page = None
        content_type = "content"

    normalized = sentence.casefold()
    score = 0
    noise_score = 0
    reasons: list[str] = []

    if any(marker in normalized for marker in DEFINITION_MARKERS) or _looks_like_definition(normalized):
        score += 3
        reasons.append("tanim")

    for marker, value in POSITIVE_MARKERS.items():
        if marker in normalized:
            score += value
            reasons.append(marker)

    if any(separator in sentence for separator in (";", ":", "1)", "2)", "- ")):
        score += 2
        reasons.append("liste")

    word_count = len(sentence.split())
    if word_count < 8:
        score -= 2
        noise_score += 1
        reasons.append("cok_kisa")
    if word_count > 45:
        score -= 3
        noise_score += 2
        reasons.append("cok_uzun")

    if any(marker in normalized for marker in NEGATIVE_MARKERS):
        score -= 4
        noise_score += 3
        reasons.append("gurultu")

    if content_type in {"heading", "layout"}:
        score -= 2
        noise_score += 1
        reasons.append(content_type)

    if _starts_like_layout(sentence):
        score -= 4
        noise_score += 2
        reasons.append("layout_baslangic")

    return ScoredSentence(
        sentence=sentence,
        score=score,
        reason=", ".join(reasons) or "genel",
        word_count=word_count,
        noise_score=noise_score,
        content_type=content_type,
        source_page=source_page,
    )


def _looks_like_definition(normalized: str) -> bool:
    return bool(
        re_search_definition_suffix(normalized)
        and any(marker in normalized for marker in ("internet", "sistem", "model", "hizmet", "kaynak", "veri", "bulut"))
    )


def _starts_like_layout(sentence: str) -> bool:
    normalized = sentence.casefold().strip()
    return bool(
        normalized.startswith(("slide", "section", "notes", "6.034", "for short problems"))
        or normalized[:4].isdigit()
    )


def re_search_definition_suffix(normalized: str) -> bool:
    import re

    return bool(re.search(r"\b(?:dir|dır|dur|dür|sistemidir|modelidir|hizmetidir)\b", normalized))
