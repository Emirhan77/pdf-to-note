from __future__ import annotations


BLOCKED_PREFIXES = ("bu ", "su ", "şu ", "o ")
BLOCKED_TERMS = ("sekil", "şekil", "tablo", "kaynakca", "kaynakça", "slide", "section", "notes")
BLOCKED_STARTS = ("slide", "section", "notes", "034", "6.034", "for short problems")
BLOCKED_TOPIC_STARTS = ("we ", "our ", "these ", "there ", "someone ", "some ", "for ", "but ", "this ")


def filter_questions(
    questions: list[dict],
    limit: int = 10,
    keywords: list[str] | None = None,
) -> list[dict]:
    accepted: list[dict] = []
    seen_questions: set[str] = set()
    keyword_set = {keyword.casefold() for keyword in keywords or []}

    for question in questions:
        text = question["question"].strip()
        normalized = text.casefold()
        answer = question["answer"].strip()
        topic = question.get("topic", "").casefold()

        if normalized in seen_questions:
            continue
        word_count = len(text.split())
        if word_count < 3:
            continue
        if word_count < 4 and not normalized.endswith(" nedir?"):
            continue
        if word_count > 12:
            continue
        if normalized.startswith(BLOCKED_PREFIXES):
            continue
        if normalized.startswith(BLOCKED_STARTS):
            continue
        if topic.startswith(BLOCKED_TOPIC_STARTS):
            continue
        if any(term in normalized for term in BLOCKED_TERMS):
            continue
        if not answer or len(answer.split()) < 6:
            continue
        if len(answer.split()) > 45:
            continue
        if keyword_set and topic and not any(keyword in topic or topic in keyword for keyword in keyword_set):
            continue

        seen_questions.add(normalized)
        question["quality_reason"] = question.get("quality_reason", "") + "; accepted"
        accepted.append(question)
        if len(accepted) >= limit:
            break

    return accepted
