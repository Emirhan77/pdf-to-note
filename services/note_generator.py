from __future__ import annotations

import re
from collections import Counter
from itertools import chain

from services.sentence_scorer import ScoredSentence


SUMMARY_LIMITS = {
    "short": 4,
    "medium": 7,
    "long": 10,
}

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "can",
    "for",
    "from",
    "have",
    "in",
    "into",
    "is",
    "it",
    "line",
    "notes",
    "of",
    "on",
    "or",
    "section",
    "slide",
    "that",
    "the",
    "their",
    "these",
    "this",
    "to",
    "when",
    "will",
    "with",
    "you",
    "your",
    "futures",
    "future",
    "past",
    "icin",
    "için",
    "olan",
    "olarak",
    "ve",
    "veya",
    "ile",
    "bir",
    "bu",
    "su",
    "şu",
    "daha",
    "gibi",
    "ise",
    "cok",
    "çok",
    "bulunan",
    "konusunda",
    "şekilde",
    "sekilde",
    "altında",
    "altinda",
    "üzerinden",
    "uzerinden",
    "kapsamında",
    "kapsaminda",
    "farklı",
    "farkli",
    "büyük",
    "buyuk",
    "tarafından",
    "tarafindan",
    "üçüncü",
    "ucuncu",
    "parti",
    "com",
    "söz",
    "soz",
    "söz konusu",
    "soz konusu",
    "milyar",
    "avro",
    "not",
    "there",
    "get",
    "full",
    "credit",
    "problems",
    "problem set",
}

DOMAIN_PHRASES = (
    "bulut bilişim",
    "bulut bilisim",
    "veri merkezi",
    "veri merkezleri",
    "özel bulut",
    "ozel bulut",
    "hibrit bulut",
    "karma bulut",
    "genel bulut",
    "topluluk bulutu",
    "machine learning",
    "knowledge representation",
    "supervised learning",
    "unsupervised learning",
    "reinforcement learning",
    "artificial intelligence",
    "search",
    "inference",
)


def generate_notes(scored_sentences: list[ScoredSentence], summary_length: str = "medium") -> dict:
    limit = SUMMARY_LIMITS.get(summary_length, SUMMARY_LIMITS["medium"])
    candidates = [item for item in scored_sentences if item.score > -2 and item.noise_score < 3]
    selected = _dedupe_sentences(candidates, limit)
    if not selected:
        selected = _dedupe_sentences(scored_sentences, limit)

    all_sentences = [item.sentence for item in scored_sentences if item.noise_score < 3]
    definition = _pick_definition(scored_sentences)
    keywords = extract_keywords(all_sentences)
    bullets = [_shorten_sentence(item.sentence) for item in selected[:5]]

    markdown = "\n".join(
        [
            "## Konu Ozeti",
            "",
            "### Kisa Tanim",
            definition or "Guvenilir tanim cumlesi bulunamadi.",
            "",
            "### Onemli Noktalar",
            *[f"- {bullet}" for bullet in bullets],
            "",
            "### Anahtar Kavramlar",
            ", ".join(keywords) if keywords else "Anahtar kavram bulunamadi.",
            "",
            "### Kisa Ders Notu",
            " ".join(_shorten_sentence(item.sentence, max_words=35) for item in selected[:3]),
        ]
    )

    return {"markdown": markdown, "keywords": keywords}


def extract_keywords(sentences: list[str], limit: int = 8) -> list[str]:
    text = " ".join(sentences)
    normalized_text = text.casefold()
    phrase_scores: Counter[str] = Counter()

    for phrase in DOMAIN_PHRASES:
        count = normalized_text.count(phrase.casefold())
        if count:
            phrase_scores[phrase] += count * (4 if " " in phrase else 2)

    tokenized_sentences = [_tokens(sentence) for sentence in sentences]
    unigram_counts = Counter(chain.from_iterable(tokenized_sentences))
    phrase_scores.update(_ngram_scores(tokenized_sentences, 2))
    phrase_scores.update(_ngram_scores(tokenized_sentences, 3))

    for word, count in unigram_counts.items():
        phrase_scores[word] += count

    selected: list[str] = []
    for phrase, _score in phrase_scores.most_common(limit * 3):
        if _is_redundant_keyword(phrase, selected):
            continue
        selected.append(phrase)
        if len(selected) >= limit:
            break
    return selected


def _pick_definition(sentences: list[ScoredSentence]) -> str:
    for item in sentences:
        normalized = item.sentence.casefold()
        if item.noise_score >= 3:
            continue
        if any(
            marker in normalized
            for marker in (
                " olarak tanımlanır",
                " olarak tanimlanir",
                " ifade eder ",
                " denir",
                " sistemidir",
                " modelidir",
                " hizmetidir",
            )
        ):
            return _shorten_sentence(item.sentence)
    return ""


def _tokens(sentence: str) -> list[str]:
    return [
        word.casefold()
        for word in re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü]{3,}", sentence)
        if word.casefold() not in STOPWORDS
    ]


def _ngram_scores(tokenized_sentences: list[list[str]], size: int) -> Counter[str]:
    scores: Counter[str] = Counter()
    for tokens in tokenized_sentences:
        for index in range(0, max(len(tokens) - size + 1, 0)):
            ngram = tokens[index : index + size]
            if any(token in STOPWORDS for token in ngram):
                continue
            phrase = " ".join(ngram)
            if phrase in STOPWORDS or _looks_like_noise_phrase(phrase):
                continue
            scores[phrase] += size + 1
    return scores


def _dedupe_sentences(sentences: list[ScoredSentence], limit: int) -> list[ScoredSentence]:
    selected: list[ScoredSentence] = []
    seen_roots: set[str] = set()
    for item in sentences:
        root = " ".join(_tokens(item.sentence)[:5])
        if not root or root in seen_roots:
            continue
        seen_roots.add(root)
        selected.append(item)
        if len(selected) >= limit:
            break
    return selected


def _shorten_sentence(sentence: str, max_words: int = 45) -> str:
    words = sentence.split()
    if len(words) <= max_words:
        return sentence
    return " ".join(words[:max_words]).rstrip(",;:") + "."


def _is_redundant_keyword(candidate: str, selected: list[str]) -> bool:
    if _looks_like_noise_phrase(candidate):
        return True
    candidate_set = set(candidate.split())
    for keyword in selected:
        keyword_set = set(keyword.split())
        if candidate == keyword:
            return True
        if _normalized_keyword(candidate) == _normalized_keyword(keyword):
            return True
        if candidate_set and candidate_set.issubset(keyword_set):
            return True
        if keyword_set and keyword_set.issubset(candidate_set):
            return True
    return False


def _normalized_keyword(keyword: str) -> str:
    normalized = keyword.casefold()
    normalized = normalized.replace("bilişimin", "bilişim").replace("bilişime", "bilişim")
    normalized = normalized.replace("bilisimin", "bilisim").replace("bilisime", "bilisim")
    normalized = normalized.replace("merkezleri", "merkezi")
    return normalized.strip()


def _looks_like_noise_phrase(phrase: str) -> bool:
    tokens = phrase.casefold().split()
    if not tokens:
        return True
    if any(token in STOPWORDS for token in tokens):
        return True
    if len(tokens) >= 2 and all(len(token) <= 3 for token in tokens):
        return True
    return False
