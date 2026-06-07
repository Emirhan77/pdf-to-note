from __future__ import annotations

import re

from services.sentence_scorer import ScoredSentence


ENGLISH_HINTS = {"the", "and", "of", "to", "learning", "knowledge", "problem", "system"}
TURKISH_HINTS = {"ve", "bir", "bulut", "bilişim", "veri", "olarak", "için", "nedir"}


def generate_questions(
    scored_sentences: list[ScoredSentence],
    keywords: list[str] | None = None,
    limit: int = 20,
) -> list[dict]:
    questions: list[dict] = []
    keyword_list = keywords or []
    language = _detect_language([item.sentence for item in scored_sentences])
    for item in scored_sentences:
        if len(questions) >= limit:
            break
        generated = _question_from_sentence(item, keyword_list, language)
        if generated:
            questions.append(generated)

    questions.extend(_fallback_keyword_questions(scored_sentences, keyword_list, language, limit))
    return questions


def _question_from_sentence(
    item: ScoredSentence,
    keywords: list[str],
    language: str,
) -> dict | None:
    sentence = item.sentence.strip()
    if item.noise_score >= 3 or item.word_count > 45:
        return None

    topic = _topic_from_sentence(sentence, keywords)
    normalized = sentence.casefold()

    if not topic:
        return None

    question_type = _question_type(normalized)
    question = _render_question(topic, question_type, language)

    return {
        "question": question,
        "answer": sentence,
        "source_sentence": sentence,
        "type": question_type,
        "topic": topic,
        "quality_score": max(item.score, 0) + len(topic.split()),
        "quality_reason": f"candidate:{item.reason}; topic:{topic}; language:{language}",
    }


def _topic_from_sentence(sentence: str, keywords: list[str]) -> str:
    normalized = sentence.casefold()
    domain_keywords = [keyword for keyword in keywords if _is_domain_topic(keyword)]
    fallback_keywords = domain_keywords or keywords

    for keyword in sorted(domain_keywords, key=len, reverse=True):
        if len(keyword.split()) >= 2 and keyword.casefold() in normalized:
            return _title_topic(keyword)

    definition_match = re.match(
        r"^(.{3,80}?)(?:,\s*)?(?:bir|the|an)?\s*(?:[^.]{0,30})?"
        r"(?:olarak tanımlanır|olarak tanimlanir|ifade eder|denir|sistemidir|modelidir|hizmetidir|is|are)\b",
        sentence,
        flags=re.IGNORECASE,
    )
    if definition_match:
        topic = _clean_topic(definition_match.group(1))
        if topic:
            return topic

    for keyword in sorted(fallback_keywords, key=lambda item: (len(item.split()), len(item)), reverse=True):
        if keyword.casefold() in normalized and keyword.casefold() not in {"search", "inference"}:
            return _title_topic(keyword)

    return ""


def _question_type(normalized_sentence: str) -> str:
    if any(marker in normalized_sentence for marker in ("dezavantaj", "risk", "zorluk")):
        return "dezavantaj"
    if any(marker in normalized_sentence for marker in ("avantaj", "fayda", "yarar")):
        return "avantaj"
    if any(marker in normalized_sentence for marker in ("amac", "amaç", "hedef")):
        return "amac"
    if any(marker in normalized_sentence for marker in ("ayrilir", "ayrılır", "türleri", "turleri", "modelleri", "classes")):
        return "siniflandirma"
    if any(marker in normalized_sentence for marker in ("onem", "önem", "saglar", "sağlar", "important")):
        return "neden_sonuc"
    return "tanim"


def _render_question(topic: str, question_type: str, language: str) -> str:
    if language == "en":
        templates = {
            "dezavantaj": f"What are the disadvantages of {topic}?",
            "avantaj": f"What are the advantages of {topic}?",
            "amac": f"What is the purpose of {topic}?",
            "siniflandirma": f"What are the types of {topic}?",
            "neden_sonuc": f"Why is {topic} important?",
            "tanim": f"What is {topic}?",
        }
    else:
        templates = {
            "dezavantaj": f"{topic} dezavantajları nelerdir?",
            "avantaj": f"{topic} avantajları nelerdir?",
            "amac": f"{topic} amacı nedir?",
            "siniflandirma": f"{topic} türleri nelerdir?",
            "neden_sonuc": f"{topic} neden önemlidir?",
            "tanim": f"{topic} nedir?",
        }
    return templates[question_type]


def _detect_language(sentences: list[str]) -> str:
    tokens = set(
        word.casefold()
        for word in re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü]{2,}", " ".join(sentences[:40]))
    )
    english_score = len(tokens & ENGLISH_HINTS)
    turkish_score = len(tokens & TURKISH_HINTS)
    return "en" if english_score > turkish_score else "tr"


def _clean_topic(topic: str) -> str:
    topic = re.sub(r"^[\d.)\s-]+", "", topic)
    topic = re.sub(r"\s+", " ", topic).strip(" ,;:-")
    words = [word for word in topic.split() if len(word) > 1]
    if len(words) > 6:
        words = words[:6]
    if len(words) < 1:
        return ""
    if words[0].casefold() in {"we", "our", "these", "there", "someone", "some", "for", "but", "the", "this"}:
        return ""
    return " ".join(words)


def _title_topic(topic: str) -> str:
    return " ".join(word.capitalize() if word.islower() else word for word in topic.split())


def _is_domain_topic(keyword: str) -> bool:
    normalized = keyword.casefold()
    return any(
        marker in normalized
        for marker in (
            "bulut",
            "veri",
            "machine learning",
            "learning",
            "knowledge",
            "intelligence",
            "hypothesis",
            "model",
            "bilişim",
            "bilisim",
        )
    )


def _fallback_keyword_questions(
    scored_sentences: list[ScoredSentence],
    keywords: list[str],
    language: str,
    remaining: int,
) -> list[dict]:
    generated: list[dict] = []
    used_topics: set[str] = set()
    domain_keywords = [keyword for keyword in keywords if _is_domain_topic(keyword)]

    for keyword in domain_keywords:
        if remaining <= 0:
            break
        normalized_keyword = keyword.casefold()
        if normalized_keyword in used_topics:
            continue
        source = next(
            (
                item
                for item in scored_sentences
                if normalized_keyword in item.sentence.casefold()
                and item.noise_score < 3
                and item.word_count >= 6
            ),
            None,
        )
        if not source:
            continue
        topic = _title_topic(keyword)
        question_type = _question_type(source.sentence.casefold())
        answer = _shorten_answer(source.sentence)
        generated.append(
            {
                "question": _render_question(topic, question_type, language),
                "answer": answer,
                "source_sentence": source.sentence,
                "type": question_type,
                "topic": topic,
                "quality_score": max(source.score, 0) + len(topic.split()),
                "quality_reason": f"fallback_keyword; candidate:{source.reason}; topic:{topic}; language:{language}",
            }
        )
        used_topics.add(normalized_keyword)
        remaining -= 1

    return generated


def _shorten_answer(sentence: str, max_words: int = 45) -> str:
    words = sentence.split()
    if len(words) <= max_words:
        return sentence
    return " ".join(words[:max_words]).rstrip(",;:") + "."
