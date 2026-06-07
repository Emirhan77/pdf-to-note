from __future__ import annotations

from collections import Counter, defaultdict
import re

from services.document_chunker import DocumentChunk


TARGET_MIN_SECTIONS = 6
TARGET_MAX_SECTIONS = 10

GENERIC_NOISE_CONCEPTS = {
    "there",
    "subject",
    "topics",
    "problem",
    "problems",
    "bilisimin",
    "milyar",
    "yapilan",
    "genel",
    "konu",
    "bolum",
}


CLOUD_TOPICS = [
    {
        "id": "definition_intro",
        "heading": "Tanim ve Giris",
        "purpose": "Kavramin temel tanimini ve genel cerceveyi verir.",
        "patterns": ("tanim", "nedir", "giris", "overview", "bulut bilisim", "cloud computing"),
    },
    {
        "id": "history_need",
        "heading": "Gelisim ve Ihtiyac",
        "purpose": "Tarihsel gelisim ve bu yaklasima neden ihtiyac duyuldugunu aciklar.",
        "patterns": ("gelisim", "tarih", "history", "ihtiyac", "need", "mainframe", "grid computing"),
    },
    {
        "id": "stakeholders",
        "heading": "Temel Paydaslar",
        "purpose": "Sistemde rol alan aktorleri ve sorumluluklarini ozetler.",
        "patterns": ("paydas", "tuketici", "saglayici", "gelistirici", "stakeholder"),
    },
    {
        "id": "service_models",
        "heading": "Hizmet Modelleri",
        "purpose": "SaaS, PaaS, IaaS gibi hizmet katmanlarini aciklar.",
        "patterns": ("saas", "paas", "iaas", "hizmet modeli", "service model", "servis olarak"),
    },
    {
        "id": "use_cases",
        "heading": "Kullanim Senaryolari",
        "purpose": "Kurumsal ve teknik kullanim orneklerini bir araya getirir.",
        "patterns": ("kullanim", "senaryo", "use case", "uygulama"),
    },
    {
        "id": "pros_cons",
        "heading": "Avantajlar ve Dezavantajlar",
        "purpose": "Yararlarin ve sinirliliklarin dengeli degerlendirmesini sunar.",
        "patterns": ("avantaj", "dezavantaj", "benefit", "limitation", "risk"),
    },
    {
        "id": "eu",
        "heading": "AB Perspektifi",
        "purpose": "Avrupa duzeyindeki pazar, duzenleme ve strateji boyutunu aciklar.",
        "patterns": ("ab", "avrupa", "european", "eu", "komisyon", "komisyonu"),
    },
    {
        "id": "turkiye",
        "heading": "Turkiye Perspektifi",
        "purpose": "Turkiye tarafindaki uygulama, kamu-ozel sektor ve kapasite durumunu toplar.",
        "patterns": ("turkiye", "kamu", "veri merkezi", "btk", "isletmeci"),
    },
    {
        "id": "conclusion",
        "heading": "Sonuc ve Oneriler",
        "purpose": "Belgenin genel degerlendirme ve onerilerini toparlar.",
        "patterns": ("sonuc", "oner", "degerlendirme", "conclusion", "summary"),
    },
]


GENERIC_TOPICS = [
    {
        "id": "ai_intro",
        "heading": "Artificial Intelligence / Yapay Zeka",
        "purpose": "Belgenin genel alan tanimini ve giris baglamini ozetler.",
        "patterns": ("artificial intelligence", "yapay zeka", "ai", "introduction", "overview"),
    },
    {
        "id": "search",
        "heading": "Search / Arama",
        "purpose": "Arama problemleri ve yaklasimlarini aciklar.",
        "patterns": ("search", "arama", "state space", "path"),
    },
    {
        "id": "knowledge_representation",
        "heading": "Knowledge Representation / Bilgi Temsili",
        "purpose": "Bilginin nasil temsil edildigi ve modellenebilecegi uzerine odaklanir.",
        "patterns": ("knowledge representation", "bilgi temsili", "representation"),
    },
    {
        "id": "inference",
        "heading": "Inference / Cikarim",
        "purpose": "Cikarim mekanizmalarini ve akil yurutmeyi ele alir.",
        "patterns": ("inference", "cikarim", "reasoning", "logic"),
    },
    {
        "id": "scheme",
        "heading": "MIT Scheme",
        "purpose": "MIT Scheme baglamini ve programlama altyapisini ozetler.",
        "patterns": ("scheme", "mit scheme", "lisp"),
    },
    {
        "id": "problem_sets",
        "heading": "Problem Sets / Problem Setleri",
        "purpose": "Ders calismasi icin problem set beklentilerini ve odaklarini toplar.",
        "patterns": ("problem set", "problem sets", "assignment", "pset"),
    },
    {
        "id": "methods",
        "heading": "Yontemler ve Yaklasimlar",
        "purpose": "Teknik yaklasimlari ve uygulama bicimlerini siniflandirir.",
        "patterns": ("method", "yaklasim", "algorithm", "teknik"),
    },
    {
        "id": "challenges",
        "heading": "Sinirlar ve Zorluklar",
        "purpose": "Sinirlar, riskler ve pratik zorluklar uzerine odaklanir.",
        "patterns": ("challenge", "sinir", "limitation", "constraint", "problem"),
    },
    {
        "id": "conclusion",
        "heading": "Genel Degerlendirme",
        "purpose": "Belgenin cikarimlarini ve genel sonucunu bir araya getirir.",
        "patterns": ("conclusion", "summary", "degerlendirme", "sonuc"),
    },
]


def build_document_outline(chunks: list[DocumentChunk]) -> dict:
    if not chunks:
        return {"document_title": "Belge Ozeti", "sections": []}

    profile = _detect_profile(chunks)
    topics = CLOUD_TOPICS if profile == "cloud" else GENERIC_TOPICS
    assignments = _assign_chunks_to_topics(chunks, topics)
    sections = _build_sections(topics, assignments)
    sections = _normalize_section_count(chunks, sections, topics, assignments)
    title = _select_document_title(chunks, sections, profile)

    return {"document_title": title, "sections": sections}


def _detect_profile(chunks: list[DocumentChunk]) -> str:
    text = " ".join(
        f"{chunk.title_hint} {' '.join(chunk.key_terms)} {chunk.text[:700]}"
        for chunk in chunks
    ).lower()
    cloud_hits = sum(text.count(token) for token in ("bulut", "cloud", "saas", "paas", "iaas", "veri merkezi"))
    ai_hits = sum(text.count(token) for token in ("artificial intelligence", "knowledge representation", "inference", "scheme", "problem set", "search"))
    return "cloud" if cloud_hits >= ai_hits else "generic"


def _assign_chunks_to_topics(chunks: list[DocumentChunk], topics: list[dict]) -> dict[str, list[DocumentChunk]]:
    assignments: dict[str, list[DocumentChunk]] = defaultdict(list)
    for chunk in chunks:
        chunk_text = _fold(" ".join([chunk.title_hint, " ".join(chunk.key_terms), chunk.text[:1200]]))
        topic_scores: list[tuple[str, int]] = []
        for topic in topics:
            score = _topic_score(chunk_text, topic["patterns"])
            topic_scores.append((topic["id"], score))

        assigned_any = False
        for topic_id, score in topic_scores:
            if score >= 2:
                assignments[topic_id].append(chunk)
                assigned_any = True

        if not assigned_any:
            best_topic_id, best_score = max(topic_scores, key=lambda item: item[1])
            if best_score > 0:
                assignments[best_topic_id].append(chunk)
            else:
                assignments["_unassigned"].append(chunk)
    return assignments


def _topic_score(chunk_text: str, patterns: tuple[str, ...]) -> int:
    score = 0
    for pattern in patterns:
        folded_pattern = _fold(pattern)
        if not folded_pattern:
            continue
        if folded_pattern in chunk_text:
            score += 3 if " " in folded_pattern else 1
    return score


def _build_sections(topics: list[dict], assignments: dict[str, list[DocumentChunk]]) -> list[dict]:
    sections: list[dict] = []
    for topic in topics:
        matched_chunks = assignments.get(topic["id"], [])
        if not matched_chunks:
            continue
        sections.append(
            {
                "heading": topic["heading"],
                "purpose": topic["purpose"],
                "source_chunk_ids": _unique_chunk_ids(matched_chunks),
                "key_concepts": _collect_key_concepts(matched_chunks, topic["patterns"]),
            }
        )
    return sections


def _normalize_section_count(
    chunks: list[DocumentChunk],
    sections: list[dict],
    topics: list[dict],
    assignments: dict[str, list[DocumentChunk]],
) -> list[dict]:
    if len(sections) > TARGET_MAX_SECTIONS:
        return sections[:TARGET_MAX_SECTIONS]

    if len(sections) < TARGET_MIN_SECTIONS:
        missing_topics = [topic for topic in topics if topic["heading"] not in {section["heading"] for section in sections}]
        for topic in missing_topics:
            fallback_chunks = _fallback_chunks_for_topic(chunks, topic["patterns"])
            if not fallback_chunks:
                continue
            sections.append(
                {
                    "heading": topic["heading"],
                    "purpose": topic["purpose"],
                    "source_chunk_ids": _unique_chunk_ids(fallback_chunks),
                    "key_concepts": _collect_key_concepts(fallback_chunks, topic["patterns"]),
                }
            )
            if len(sections) >= TARGET_MIN_SECTIONS:
                break

    if len(sections) < TARGET_MIN_SECTIONS:
        added_labels: set[str] = set(section["heading"] for section in sections)
        for chunk in chunks:
            if len(sections) >= TARGET_MIN_SECTIONS:
                break
            heading = _fallback_heading(chunk)
            if heading in added_labels:
                continue
            sections.append(
                {
                    "heading": heading,
                    "purpose": "Belgenin kapsamini dengelemek icin eklenen destekleyici bolum.",
                    "source_chunk_ids": [chunk.chunk_id],
                    "key_concepts": _collect_key_concepts([chunk], tuple()),
                }
            )
            added_labels.add(heading)

    if len(sections) > TARGET_MAX_SECTIONS:
        sections = sections[:TARGET_MAX_SECTIONS]
    return sections


def _fallback_chunks_for_topic(chunks: list[DocumentChunk], patterns: tuple[str, ...]) -> list[DocumentChunk]:
    matched: list[DocumentChunk] = []
    for chunk in chunks:
        text = _fold(" ".join([chunk.title_hint, " ".join(chunk.key_terms), chunk.text[:1200]]))
        if _topic_score(text, patterns) > 0:
            matched.append(chunk)
    return matched


def _collect_key_concepts(chunks: list[DocumentChunk], patterns: tuple[str, ...]) -> list[str]:
    counter: Counter[str] = Counter()
    folded_patterns = {_fold(pattern) for pattern in patterns if _fold(pattern)}

    for chunk in chunks:
        for term in chunk.key_terms:
            cleaned = term.strip(" ,.;:-")
            if _is_weak_concept(cleaned):
                continue
            weight = 4
            if any(pattern in _fold(cleaned) for pattern in folded_patterns):
                weight += 4
            counter[cleaned] += weight

        phrase_candidates = re.findall(
            r"[A-Za-z0-9ÇĞİÖŞÜçğıöşü]{4,}(?:\s+[A-Za-z0-9ÇĞİÖŞÜçğıöşü]{4,}){0,2}",
            chunk.text,
        )
        for candidate in phrase_candidates[:160]:
            cleaned = candidate.strip(" ,.;:-")
            if _is_weak_concept(cleaned):
                continue
            weight = 1
            if " " in cleaned:
                weight += 1
            if any(pattern in _fold(cleaned) for pattern in folded_patterns):
                weight += 3
            counter[cleaned] += weight

    concepts = [item for item, _ in counter.most_common(20)]
    return _dedupe_concepts(concepts)[:8]


def _is_weak_concept(concept: str) -> bool:
    folded = _fold(concept)
    if not folded:
        return True
    if folded in GENERIC_NOISE_CONCEPTS:
        return True
    words = folded.split()
    if len(words) == 1 and (len(words[0]) < 5 or words[0].isdigit()):
        return True
    if len(words) == 1 and words[0] in {"cloud", "bulut", "hizmeti", "bilişim", "bilişimin"}:
        return True
    return False


def _dedupe_concepts(concepts: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for concept in concepts:
        cleaned = concept.strip(" ,.;:-")
        folded = _fold(cleaned)
        if not folded or folded in seen:
            continue
        if any(folded in existing or existing in folded for existing in seen):
            continue
        seen.add(folded)
        result.append(cleaned)
    return result


def _fallback_heading(chunk: DocumentChunk) -> str:
    title = chunk.title_hint.strip(" #:")
    if title and len(title.split()) <= 10:
        return title
    if chunk.key_terms:
        return f"Konu: {chunk.key_terms[0].title()}"
    return "Destekleyici Bolum"


def _select_document_title(chunks: list[DocumentChunk], sections: list[dict], profile: str) -> str:
    for chunk in chunks:
        candidate = chunk.title_hint.strip(" #:")
        folded = _fold(candidate)
        if candidate and len(candidate.split()) <= 12 and not folded.startswith(("kaynak", "references")):
            return candidate
    if sections:
        return f"PDF Notu: {sections[0]['heading']}"
    return "PDF Notu: Bulut Bilisim" if profile == "cloud" else "PDF Notu: Genel Akademik Icerik"


def _unique_chunk_ids(chunks: list[DocumentChunk]) -> list[str]:
    seen: set[str] = set()
    chunk_ids: list[str] = []
    for chunk in chunks:
        if chunk.chunk_id in seen:
            continue
        seen.add(chunk.chunk_id)
        chunk_ids.append(chunk.chunk_id)
    return chunk_ids


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
