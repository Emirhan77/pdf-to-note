from __future__ import annotations

import json
import re


SOURCE_NOTE = "Bu not, yuklenen PDF metninin temizlenmis ve konu bazli dengelenmis kaynak paketinden LLM yardimiyla uretilmistir."

_SECTION_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "heading": {"type": "string"},
        "content": {"type": "string"},
        "key_points": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["heading", "content", "key_points"],
    "additionalProperties": False,
}

_QUESTION_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "question": {"type": "string"},
        "answer": {"type": "string"},
    },
    "required": ["question", "answer"],
    "additionalProperties": False,
}


def build_study_pack_schema(question_count: int = 10) -> dict:
    count = max(1, int(question_count))
    return {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "sections": {
                "type": "array",
                "minItems": 11,
                "maxItems": 11,
                "items": _SECTION_ITEM_SCHEMA,
            },
            "questions": {
                "type": "array",
                "minItems": count,
                "maxItems": count,
                "items": _QUESTION_ITEM_SCHEMA,
            },
            "keywords": {"type": "array", "items": {"type": "string"}},
            "source_note": {"type": "string"},
        },
        "required": ["title", "sections", "questions", "keywords", "source_note"],
        "additionalProperties": False,
    }


STUDY_PACK_SCHEMA = build_study_pack_schema(10)

QUESTION_REPAIR_SCHEMA = {
    "type": "object",
    "properties": {
        "questions": build_study_pack_schema(10)["properties"]["questions"],
    },
    "required": ["questions"],
    "additionalProperties": False,
}


def build_question_repair_schema(count: int) -> dict:
    target_count = max(1, int(count))
    return {
        "type": "object",
        "properties": {
            "questions": {
                "type": "array",
                "minItems": target_count,
                "maxItems": target_count,
                "items": _QUESTION_ITEM_SCHEMA,
            },
        },
        "required": ["questions"],
        "additionalProperties": False,
    }


def build_generation_prompt(source_pack: dict) -> str:
    question_count = source_pack.get("question_count", 10)
    language = source_pack.get("output_language", "tr")
    language_name = "Turkce" if language == "tr" else language
    source_text = source_pack["source_text"]
    keywords = ", ".join(source_pack.get("keywords", []))
    topic_summary = _render_topic_summary(source_pack.get("topic_sections", []))
    selected_sentences = _render_selected_sentences(source_pack.get("selected_sentences", []))
    section_guidance = _build_section_guidance(source_pack)

    return f"""
Sen universite ogrencileri icin ders calisma notu hazirlayan bir akademik asistansin.
Yalnizca verilen PDF kaynak paketindeki bilgileri kullan. PDF disindan yeni bilgi ekleme.
Kaynak metindeki kopuk cumleleri anlamli hale getir, ama kaynakta olmayan iddia uretme.
Cikti dili: {language_name}.

Zorunlu hedef:
- PDF'in tamamini kapsayan genel bir ders notu uret; tek bir bolume, AB istatistiklerine veya pazar verilerine sikisma.
- Baslik PDF'in gercek konusunu yansitmali; kaynakta olmayan konu adini kullanma.
- Tam 11 bolum uret.
- Tam olarak {question_count} adet calisma sorusu uret.
- Sorular genel ders calismaya uygun olsun; sadece dar tarih/yuzde sorularindan olusmasin.
- Cevaplari 1-2 cumle ve en fazla 35 kelime tut.
- Yarim/kopuk cumle kullanma.
- Ayni cumleyi, ayni paragrafi veya ayni maddeyi farkli bolumlerde tekrar etme.
- Her bolum kendi basligina odaklansin; AB bilgilerini Turkiye, avantaj veya tanim bolumlerine tasima.
- Basliklari dilbilgisi acisindan dogru yaz; "ortaya cikmak nedeni" degil "ortaya cikma nedeni" kullan.
- Anahtar kavramlari genel kelimelerden degil, PDF'in alan kavramlarindan sec.
- Turkce karakter kullan: bilisim degil bilişim, paydas degil paydaş, cikma degil çıkma yaz.

Bolum basligi kurali:
{section_guidance}

Onemli kavram adaylari:
{keywords}

Kaynak kapsam ozeti:
{topic_summary}

Skorlanmis onemli cumleler:
{selected_sentences}

PDF kaynak bilgisi:
Dosya: {source_pack['file_name']}
Sayfa sayisi: {source_pack['page_count']}
Metin kisaltildi mi: {source_pack['source_text_truncated']}

Dengelenmis temiz PDF kaynak paketi:
\"\"\"
{source_text}
\"\"\"
""".strip()


def build_question_repair_prompt(source_pack: dict, existing_questions: list[dict], missing_count: int) -> str:
    existing = "\n".join(f"- {item['question']}" for item in existing_questions)
    return f"""
Asagidaki kaynak paketine dayanarak {missing_count} adet yeni ve tekrar etmeyen calisma sorusu uret.
Onceki sorulari tekrar etme. Sorular genel ders calismaya uygun olsun ve cevaplari kisa olsun.
Cikti yalnizca JSON semasina uygun olsun.

Onceki sorular:
{existing}

Dengelenmis temiz PDF kaynak paketi:
\"\"\"
{source_pack['source_text']}
\"\"\"
""".strip()


def normalize_study_pack(payload: dict, source_pack: dict, provider: str, fallback_reason: str = "") -> dict:
    sections = _normalize_sections(payload.get("sections") or [], source_pack)
    questions = _normalize_questions(payload.get("questions") or [], source_pack.get("question_count", 10), source_pack)
    keywords = _normalize_keywords(payload.get("keywords") or [], source_pack)

    return {
        "title": _normalize_title(payload.get("title"), source_pack),
        "sections": sections,
        "questions": questions,
        "keywords": keywords,
        "source_note": SOURCE_NOTE,
        "provider": provider,
        "fallback_reason": fallback_reason,
    }


def parse_json_payload(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise


def merge_repaired_questions(study_pack: dict, repaired_questions: list[dict], target_count: int) -> dict:
    merged = _normalize_questions(study_pack.get("questions", []) + repaired_questions, target_count)
    study_pack["questions"] = merged[:target_count]
    return study_pack


def fill_missing_questions(source_pack: dict, questions: list[dict], target_count: int) -> list[dict]:
    candidates = _fallback_question_candidates(source_pack)
    return _normalize_questions(questions + candidates, target_count, source_pack)


def render_study_pack_markdown(study_pack: dict) -> str:
    lines = [
        f"## {study_pack.get('title', 'PDF Notu')}",
        "",
        f"**Uretim modu:** {study_pack.get('provider', '-')}",
    ]
    if study_pack.get("fallback_reason"):
        lines.extend(["", f"**Not:** {study_pack['fallback_reason']}"])
    if study_pack.get("provider_attempted"):
        lines.extend(["", f"**Denenen LLM:** {study_pack['provider_attempted']}"])
    if study_pack.get("llm_error_type"):
        lines.extend(["", f"**LLM hata turu:** {study_pack['llm_error_type']}"])
    if study_pack.get("llm_error_message"):
        lines.extend(["", f"**LLM hata mesaji:** {study_pack['llm_error_message']}"])
    if study_pack.get("raw_response_preview"):
        lines.extend(["", "**Ham LLM yanit onizleme:**", "", "```text", study_pack["raw_response_preview"], "```"])

    for index, section in enumerate(study_pack.get("sections", []), start=1):
        lines.extend(["", f"### {index}. {section['heading']}", "", section["content"]])
        if section.get("key_points"):
            lines.append("")
            lines.extend([f"- {point}" for point in section["key_points"]])

    questions = study_pack.get("questions", [])
    if questions:
        lines.extend(["", "---", "", f"## {len(questions)} Calisma Sorusu"])
        for index, question in enumerate(questions, start=1):
            lines.extend(
                [
                    "",
                    f"{index}. **{question['question']}**",
                    f"   Cevap: {question['answer']}",
                ]
            )

    if study_pack.get("keywords"):
        lines.extend(["", "---", "", "## Anahtar Kavramlar", ", ".join(study_pack["keywords"])])

    if study_pack.get("source_note"):
        lines.extend(["", "## Kaynak Notu", study_pack["source_note"]])

    return "\n".join(lines).strip()


def questions_for_database(study_pack: dict) -> list[dict]:
    questions = []
    for question in study_pack.get("questions", []):
        questions.append(
            {
                "question": question["question"],
                "answer": question["answer"],
                "source_sentence": study_pack.get("source_note", SOURCE_NOTE),
                "type": "llm",
                "topic": "",
                "quality_score": 10,
                "quality_reason": f"provider:{study_pack.get('provider', '-')}",
            }
        )
    return questions


def _build_section_guidance(source_pack: dict) -> str:
    if _is_cloud_profile(source_pack):
        return "\n".join(
            [
                'PDF konusu bulut bilisim oldugu icin bolum basliklari asagidaki listeye yakin ve mumkunse ayni olmali:',
                "1. Bulut bilişim nedir?",
                "2. Bulut bilişimin ortaya çıkma nedeni",
                "3. Bulut bilişimin gelişimi",
                "4. Temel paydaşlar",
                "5. Hizmet modelleri: SaaS, PaaS, IaaS",
                "6. Avantajlar",
                "7. Dezavantajlar",
                "8. AB'de bulut bilişim",
                "9. AB'nin bulut bilişim stratejisi",
                "10. Türkiye'de bulut bilişim",
                "11. Sonuç ve öneriler",
            ]
        )
    return "\n".join(
        [
            "PDF konusu bulut bilisim degilse bulut bilisim, SaaS, PaaS, IaaS, AB veya Turkiye basliklarini kullanma.",
            "Bolum basliklarini yalnizca belge iceriginden kendin cikar; mumkunse PDF'deki ana kavramlara ozel basliklar kullan.",
            "Ornek: AI/MIT iceriginde 'Arama', 'Bilgi temsili', 'Cikarim', 'MIT Scheme', 'Problem setleri' gibi belgeye ozgu basliklar daha iyidir.",
            "Ders notu bolumlerine calisma sorusu, soru-cevap, quiz veya test maddesi karistirma; sorular sadece questions alaninda olmali.",
            "Sorulari tek kaliba sikistirma; tanim, aciklama, karsilastirma, onem ve uygulama turlerini dengeli kullan.",
            "Genel akademik iskelet su tur basliklari hedefleyebilir: temel kavramlar, tanimlar, tarihce/arka plan, yontemler/yaklasimlar, onemli problemler, ornekler, avantajlar/sinirliliklar, sonuc/genel degerlendirme.",
        ]
    )


def _is_cloud_profile(source_pack: dict) -> bool:
    return source_pack.get("topic_profile") == "cloud"


def _render_topic_summary(topic_sections: list[dict]) -> str:
    if not topic_sections:
        return "Konu bolumu bulunamadi; ana kaynak metin kullanilacak."
    return "\n".join(f"- {section['heading']}: {len(section.get('text', '').split())} kelime" for section in topic_sections)


def _render_selected_sentences(selected_sentences: list[dict]) -> str:
    lines = []
    for item in selected_sentences[:18]:
        sentence = str(item.get("sentence", "")).strip()
        if sentence:
            lines.append(f"- {sentence}")
    return "\n".join(lines) or "Yok."


def _normalize_title(title: str | None, source_pack: dict) -> str:
    cleaned = _clean_text(title or "")
    if not _is_cloud_profile(source_pack) and (_has_cloud_leak(cleaned) or _looks_too_narrow_generic_title(cleaned)):
        cleaned = _generic_title_from_source(source_pack)
    if not cleaned or _looks_too_narrow_title(cleaned):
        return "PDF Notu: Bulut Bilişim" if _is_cloud_profile(source_pack) else f"PDF Notu: {source_pack['file_name']}"
    if not cleaned.casefold().startswith("pdf notu"):
        cleaned = f"PDF Notu: {cleaned}"
    return cleaned


def _normalize_sections(sections: list[dict], source_pack: dict) -> list[dict]:
    normalized = []
    seen: set[str] = set()
    seen_content_units: set[str] = set()
    for section in sections:
        heading = _canonical_heading(_clean_heading(str(section.get("heading", ""))), source_pack)
        if _is_question_section_heading(heading):
            continue
        content = _dedupe_content(_clean_text(str(section.get("content", ""))), seen_content_units)
        key_points = _dedupe_points(
            [_clean_text(str(point)) for point in section.get("key_points", [])],
            seen_content_units,
        )
        if len(content.split()) < 12 and not key_points:
            continue
        key = _fold_simple(heading)
        if key in seen:
            continue
        seen.add(key)
        normalized.append({"heading": heading, "content": content, "key_points": key_points[:5]})
    return normalized[:12]


def _normalize_questions(questions: list[dict], target_count: int, source_pack: dict | None = None) -> list[dict]:
    normalized = []
    seen_keys: set[str] = set()
    seen_token_sets: list[set[str]] = []
    generic_factor_count = 0
    for question in questions:
        answer_text = _trim_words(_clean_text(str(question.get("answer", "")),), 38)
        question_text = _clean_text(str(question.get("question", "")))
        question_text, answer_text = _improve_question_answer_pair(question_text, answer_text)
        if source_pack is not None and not _is_cloud_profile(source_pack) and _has_cloud_leak(question_text):
            continue
        if _is_generic_factor_question(question_text):
            question_text = _rewrite_generic_factor_question(answer_text, generic_factor_count)
            generic_factor_count += 1
        if not question_text or not answer_text:
            continue
        if len(question_text.split()) < 3 or len(question_text.split()) > 24:
            continue
        key = _fold_simple(question_text)
        token_set = _question_tokens(question_text)
        if key in seen_keys or _is_near_duplicate_question(token_set, seen_token_sets):
            continue
        seen_keys.add(key)
        seen_token_sets.append(token_set)
        normalized.append({"question": question_text, "answer": answer_text})
        if len(normalized) >= target_count:
            break
    return normalized


def _normalize_keywords(payload_keywords: list, source_pack: dict) -> list[str]:
    candidates = [str(keyword) for keyword in payload_keywords]
    candidates.extend(str(keyword) for keyword in source_pack.get("keywords", []))

    if _is_cloud_profile(source_pack):
        candidates.extend(
            [
                "bulut bilişim",
                "veri merkezi",
                "kullandığın kadar öde",
                "SaaS",
                "PaaS",
                "IaaS",
                "özel bulut",
                "genel bulut",
                "hibrit bulut",
                "veri taşınabilirliği",
                "hizmet seviyesi anlaşması",
                "bulut güvenliği",
            ]
        )

    stopwords = {"bulut", "bilişim", "hizmet", "sistem", "model", "konu", "pdf", "not"}
    blocked_generic_keywords = {"bulutbilisim", "saas", "paas", "iaas", "verimerkezi", "hibritbulut", "ozelbulut", "genelbulut"}
    normalized = []
    seen: set[str] = set()
    for keyword in candidates:
        cleaned = _clean_text(str(keyword)).strip(" ,.;:-")
        folded = _fold_simple(cleaned)
        if not _is_cloud_profile(source_pack) and folded in blocked_generic_keywords:
            continue
        if not _is_cloud_profile(source_pack) and _is_generic_keyword_noise(cleaned):
            continue
        if not cleaned or len(cleaned) < 3 or folded in seen or folded in stopwords:
            continue
        seen.add(folded)
        normalized.append(cleaned)
        if len(normalized) >= 14:
            break
    return normalized


def _is_generic_keyword_noise(keyword: str) -> bool:
    folded = _fold_simple_with_spaces(keyword)
    tokens = folded.split()
    if not tokens:
        return True

    noise_phrases = {
        "make sure",
        "someone else",
        "able problem",
        "html javascript",
        "check button",
        "lecture notes",
        "course material",
    }
    if folded in noise_phrases or any(phrase in folded for phrase in noise_phrases):
        return True

    generic_single_words = {
        "able",
        "button",
        "check",
        "else",
        "html",
        "javascript",
        "line",
        "make",
        "material",
        "notes",
        "problem",
        "section",
        "someone",
        "sure",
        "thing",
    }
    if len(tokens) == 1 and tokens[0] in generic_single_words:
        return True
    if len(tokens) <= 3 and all(token in generic_single_words for token in tokens):
        return True
    return False


def _dedupe_content(content: str, seen_content_units: set[str]) -> str:
    content = _strip_embedded_question_blocks(content)
    pieces = re.split(r"(?<=[.!?])\s+", content)
    kept = []
    for piece in pieces:
        cleaned = piece.strip()
        if not cleaned:
            continue
        if _looks_like_question_block(cleaned):
            continue
        key = _content_key(cleaned)
        if key and key in seen_content_units:
            continue
        if key:
            seen_content_units.add(key)
        kept.append(cleaned)
    return " ".join(kept).strip()


def _dedupe_points(points: list[str], seen_content_units: set[str]) -> list[str]:
    kept = []
    local_seen: set[str] = set()
    for point in points:
        cleaned = point.strip()
        if _looks_like_question_block(cleaned):
            continue
        if not _is_meaningful_point(cleaned):
            continue
        key = _content_key(cleaned)
        if not cleaned or key in local_seen or key in seen_content_units:
            continue
        local_seen.add(key)
        if key:
            seen_content_units.add(key)
        kept.append(cleaned)
    return kept


def _content_key(text: str) -> str:
    folded = _fold_simple_with_spaces(text)
    words = [word for word in folded.split() if len(word) > 3]
    return " ".join(words[:18])


def _is_meaningful_point(point: str) -> bool:
    words = point.split()
    if len(words) <= 2:
        return False
    if len(words) <= 3 and not re.search(r"[.!?:]$", point):
        return False
    folded = _fold_simple_with_spaces(point)
    stop_fragments = {
        "bilgi cagi",
        "kurumlarin ve isletmelerin",
        "teknoloji kullanimini arttirmak",
        "teknoloji kullanimini artirmak",
    }
    if folded in stop_fragments:
        return False
    if all(len(word) <= 3 for word in folded.split()):
        return False
    return True


def _strip_embedded_question_blocks(text: str) -> str:
    parts = re.split(
        r"(?i)(?:^|\s)(?:#{1,6}\s*)?(?:\d+[.)]\s*)?(?:calisma|çalışma)\s+sorusu\s*\d*|(?:^|\s)(?:#{1,6}\s*)?(?:soru|question)\s*\d+[.:)]?",
        text,
    )
    return parts[0].strip() if parts else text


def _looks_like_question_block(text: str) -> bool:
    folded = _fold_simple_with_spaces(text)
    if re.search(r"\b(calisma sorusu|soru|question)\s*\d+\b", folded):
        return True
    if folded.startswith(("calisma sorusu", "soru ", "question ")):
        return True
    return False


def _is_question_section_heading(heading: str) -> bool:
    folded = _fold_simple_with_spaces(heading)
    if folded in {
        "calisma sorulari",
        "calisma sorusu",
        "sorular",
        "soru cevaplar",
        "soru cozumu",
        "soru cozumleri",
        "quiz",
        "test",
        "study questions",
        "questions",
    }:
        return True
    if folded.startswith(("calisma sorulari", "sorular", "soru cevap", "soru cozum", "quiz", "test", "study questions", "questions")):
        return True
    return False


def _has_cloud_leak(text: str) -> bool:
    folded = _fold_simple_with_spaces(text)
    if not folded:
        return False
    markers = (
        "bulut bilisim",
        "cloud computing",
        "saas",
        "paas",
        "iaas",
        "ab de bulut",
        "turkiye de bulut",
    )
    return any(marker in folded for marker in markers)


def _generic_title_from_source(source_pack: dict) -> str:
    folded_source = _fold_simple_with_spaces(source_pack.get("source_text", ""))
    ai_markers = ("artificial intelligence", "search", "knowledge representation", "inference", "machine learning")
    if sum(1 for marker in ai_markers if marker in folded_source) >= 2:
        return "PDF Notu: Yapay Zeka, Arama ve Bilgi Temsili"

    useful = []
    blocked = {"pdf", "not", "konu", "ders", "document"}
    for keyword in source_pack.get("keywords", []):
        cleaned = _clean_text(str(keyword)).strip(" ,.;:-")
        folded = _fold_simple_with_spaces(cleaned)
        if not cleaned or folded in blocked or _has_cloud_leak(cleaned) or _is_generic_keyword_noise(cleaned):
            continue
        useful.append(cleaned)
        if len(useful) >= 3:
            break
    if useful:
        return "PDF Notu: " + ", ".join(useful)
    return f"PDF Notu: {source_pack.get('file_name', 'Genel Akademik Icerik')}"


def _looks_too_narrow_generic_title(title: str) -> bool:
    folded = _fold_simple_with_spaces(title)
    if not folded:
        return True
    narrow_titles = {
        "machine learning",
        "pdf notu machine learning",
        "temel kavramlar",
        "pdf notu temel kavramlar",
    }
    if folded in narrow_titles:
        return True
    topic_hits = sum(
        1
        for marker in ("artificial intelligence", "search", "knowledge representation", "inference", "machine learning", "scheme")
        if marker in folded
    )
    return len(folded.split()) <= 4 and topic_hits <= 1


def _canonical_heading(heading: str, source_pack: dict) -> str:
    if not _is_cloud_profile(source_pack):
        return heading
    folded = _fold_simple_with_spaces(heading)
    if "nedir" in folded and "bulut" in folded:
        return "Bulut bilişim nedir?"
    if "ortaya" in folded and ("neden" in folded or "cikmak" in folded or "cikma" in folded):
        return "Bulut bilişimin ortaya çıkma nedeni"
    if "gelisim" in folded:
        return "Bulut bilişimin gelişimi"
    if "paydas" in folded:
        return "Temel paydaşlar"
    if "saas" in folded or "paas" in folded or "iaas" in folded or "hizmet model" in folded:
        return "Hizmet modelleri: SaaS, PaaS, IaaS"
    if "avantaj" in folded and "dezavantaj" not in folded:
        return "Avantajlar"
    if "dezavantaj" in folded:
        return "Dezavantajlar"
    if ("ab" in folded or "avrupa" in folded) and "strateji" in folded:
        return "AB'nin bulut bilişim stratejisi"
    if "ab" in folded or "avrupa" in folded:
        return "AB'de bulut bilişim"
    if "turkiye" in folded:
        return "Türkiye'de bulut bilişim"
    if "sonuc" in folded or "oneri" in folded:
        return "Sonuç ve öneriler"
    return heading


def _improve_question_answer_pair(question_text: str, answer_text: str) -> tuple[str, str]:
    question_text = _polish_question_turkish(question_text)

    answer_folded = _fold_simple_with_spaces(answer_text)
    mentions_stakeholders = all(
        token in answer_folded for token in ("tuketici", "saglayici", "gelistirici")
    )
    if mentions_stakeholders:
        question_text = "Bulut bilişimde hangi temel paydaşlar bulunur?"

    if not question_text.endswith("?"):
        question_text = question_text.rstrip(".!;:") + "?"
    return question_text, answer_text


def _is_generic_factor_question(question_text: str) -> bool:
    folded = _fold_simple_with_spaces(question_text)
    return "hangi faktorler bu durumu etkileyebilir" in folded


def _rewrite_generic_factor_question(answer_text: str, occurrence_index: int) -> str:
    topic = _infer_question_topic(answer_text)
    templates = [
        f"{topic} kavramını kısaca açıklayınız?",
        f"{topic} neden önemlidir?",
        f"{topic} hangi durumda kullanılır?",
        f"{topic} ile ilgili temel yaklaşım nedir?",
        f"{topic} öğrenme sürecinde nasıl uygulanır?",
    ]
    return templates[occurrence_index % len(templates)]


def _infer_question_topic(answer_text: str) -> str:
    folded = _fold_simple_with_spaces(answer_text)
    topic_candidates = [
        ("machine learning", "Machine learning"),
        ("knowledge representation", "Bilgi temsili"),
        ("search", "Arama"),
        ("inference", "Çıkarım"),
        ("scheme", "MIT Scheme"),
        ("problem set", "Problem setleri"),
        ("algorithm", "Algoritmalar"),
        ("artificial intelligence", "Yapay zeka"),
    ]
    for marker, label in topic_candidates:
        if marker in folded:
            return label
    words = [word for word in answer_text.split() if len(word.strip(".,;:()")) > 4]
    return "Bu konu" if not words else " ".join(words[:2]).strip(".,;:()")


def _polish_question_turkish(text: str) -> str:
    cleaned = text.strip()
    folded = _fold_simple_with_spaces(cleaned)

    if "bulut bilisim neyi kapsamli bir sekilde tanimlayabilirsiniz" in folded:
        return "Bulut bilişimi kapsamlı bir şekilde tanımlayınız?"
    if "hangi tur servis saglayicilari bulunmaktadir" in folded:
        return "Bulut bilişimde hangi temel paydaşlar bulunur?"

    if "tanimlayabilirsiniz" in folded:
        cleaned = re.sub(
            r"(?i)tan[ıi]mlayabilirsiniz",
            "tanımlayınız",
            cleaned,
        )
    if "on gerekliliklerini ne olacak" in folded:
        return "Ön gereklilikleri nelerdir?"
    if "ne iceriyor" in folded or "ne içeriyor" in folded:
        cleaned = re.sub(r"(?i)ne\s+i[cç]eriyor", "neyi içerir", cleaned)
    if "neden secilmesi gerektigini aciklayin" in folded or "neden seçilmesi gerektiğini açıklayın" in folded:
        return "Neden seçildiğini açıklayınız."
    return cleaned


def _fallback_question_candidates(source_pack: dict) -> list[dict]:
    keywords = " ".join(source_pack.get("keywords", [])).casefold()
    file_name = source_pack.get("file_name", "").casefold()
    if _is_cloud_profile(source_pack) or "bulut" in keywords or "bulut" in file_name:
        return [
            {
                "question": "Bulut bilişim nedir? Kısaca açıklayınız.",
                "answer": "Bulut bilişim, internet üzerinden bilişim kaynaklarına erişerek veri saklama, işlem gücü ve uygulama hizmeti kullanma modelidir.",
            },
            {
                "question": "Bulut bilişimde kullandığın kadar öde modeli ne anlama gelir?",
                "answer": "Kullanıcının yalnızca kullandığı kaynak veya hizmet miktarı kadar ödeme yapması anlamına gelir.",
            },
            {
                "question": "SaaS, PaaS ve IaaS kavramları neyi ifade eder?",
                "answer": "SaaS yazılım hizmetini, PaaS uygulama geliştirme platformunu, IaaS ise altyapı kaynaklarının hizmet olarak sunulmasını ifade eder.",
            },
            {
                "question": "Bulut bilişimin ortaya çıkmasında hangi ihtiyaçlar etkili olmuştur?",
                "answer": "Artan veri miktarı, donanım maliyetleri, bakım giderleri, esneklik ve ölçeklenebilirlik ihtiyacı etkili olmuştur.",
            },
            {
                "question": "Bulut bilişimin önemli avantajları nelerdir?",
                "answer": "Maliyetleri azaltma, ölçeklenebilirlik, geniş depolama kapasitesi, hızlı erişim ve işbirliğini kolaylaştırma önemli avantajlardır.",
            },
            {
                "question": "Bulut bilişimin dezavantajları nelerdir?",
                "answer": "İnternet bağlantısına bağımlılık, güvenlik riskleri, veri kontrolü ve hizmet sağlayıcıya bağımlılık başlıca dezavantajlardır.",
            },
            {
                "question": "AB'nin bulut bilişim stratejisinde hangi konular öne çıkar?",
                "answer": "Standartlar, veri taşınabilirliği, güvenli sağlayıcı belgelendirmesi, sözleşmeler ve kamu-özel sektör işbirliği öne çıkar.",
            },
            {
                "question": "Türkiye'de bulut bilişimin gelişmesi için neler yapılmalıdır?",
                "answer": "Farkındalık artırılmalı, güvenlik mekanizmaları güçlendirilmeli, standartlar geliştirilmeli ve kamu-özel sektör işbirliği desteklenmelidir.",
            },
        ]

    fallback = []
    for keyword in source_pack.get("keywords", [])[:8]:
        fallback.append(
            {
                "question": f"{keyword} kavramı ders notunda neden önemlidir?",
                "answer": f"{keyword}, PDF kaynak paketinde öne çıkan temel kavramlardan biridir.",
            }
        )
    return fallback


def _clean_heading(text: str) -> str:
    text = _clean_text(text)
    text = text.strip("#:- ")
    return text or "Bolum"


def _clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace("%75'si", "%75'i").replace("%1'ı", "%1'i")
    text = text.replace("%75’si", "%75’i").replace("%1’ı", "%1’i")
    text = _repair_common_turkish_ascii(text)
    text = text.replace("Bilişim'ın", "Bilişim'in").replace("bilişim'ın", "bilişim'in")
    text = text.replace("Bulut Bilişim'ın", "Bulut Bilişim'in").replace("bulut bilişim'ın", "bulut bilişim'in")
    text = _repair_common_word_errors(text)
    text = text.replace(" Calisma ", " Calisma ")
    return text


def _repair_common_word_errors(text: str) -> str:
    replacements = {
        "Tanimlar": "Tanımlar",
        "tanimlar": "tanımlar",
        "Tarihce": "Tarihçe",
        "tarihce": "tarihçe",
        "Ornekler": "Örnekler",
        "ornekler": "örnekler",
        "Sinirlilikler": "Sınırlılıklar",
        "sinirlilikler": "sınırlılıklar",
        "Avantajlar ve Sinirlilikler": "Avantajlar ve Sınırlılıklar",
        "avantajlar ve sinirlilikler": "avantajlar ve sınırlılıklar",
        "genel sonuçunu": "genel sonucunu",
        "Genel sonuçunu": "Genel sonucunu",
        "arttirma": "artırma",
        "Arttirma": "Artırma",
        "arttırma": "artırma",
        "Arttırma": "Artırma",
        "arttirmak": "artırmak",
        "Arttirmak": "Artırmak",
        "arttırmak": "artırmak",
        "Arttırmak": "Artırmak",
        "arttırmaya": "artırmaya",
        "Arttırmaya": "Artırmaya",
        "arttirilmasi": "artırılması",
        "Arttirilmasi": "Artırılması",
        "arttirilmalı": "artırılmalı",
        "Arttirilmalı": "Artırılmalı",
        "standardların": "standartların",
        "Standardların": "Standartların",
        "servis sağlayıcıları bulunmaktadır": "servis sağlayıcılar bulunmaktadır",
        "çıkmak nedeni": "çıkma nedeni",
        "Çıkmak nedeni": "Çıkma nedeni",
        "cikmak nedeni": "çıkma nedeni",
        "Cikmak nedeni": "Çıkma nedeni",
        "ortaya çıkmak nedeni": "ortaya çıkma nedeni",
        "Ortaya çıkmak nedeni": "Ortaya çıkma nedeni",
        "paydas": "paydaş",
        "Paydas": "Paydaş",
        "calisma": "çalışma",
        "Calisma": "Çalışma",
        "gelistirme": "geliştirme",
        "Gelistirme": "Geliştirme",
        "tasınabilirlik": "taşınabilirlik",
        "Tasınabilirlik": "Taşınabilirlik",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def _repair_common_turkish_ascii(text: str) -> str:
    replacements = {
        "Bilisim": "Bilişim",
        "bilisim": "bilişim",
        "Bilisimin": "Bilişimin",
        "bilişimin": "bilişimin",
        "Paydaslar": "Paydaşlar",
        "paydaslar": "paydaşlar",
        "Turkiye": "Türkiye",
        "turkiye": "Türkiye",
        "Cikma": "Çıkma",
        "cikma": "çıkma",
        "Gelisim": "Gelişim",
        "gelisim": "gelişim",
        "Sonuc": "Sonuç",
        "sonuc": "sonuç",
        "Oneriler": "Öneriler",
        "oneriler": "öneriler",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def _trim_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]).rstrip(",;:") + "."


def _question_tokens(question: str) -> set[str]:
    folded = _fold_simple_with_spaces(question)
    stopwords = {
        "aciklayiniz",
        "belirtilmistir",
        "bulut",
        "bilisim",
        "hangi",
        "modeli",
        "modelin",
        "modelinin",
        "nasil",
        "nedir",
        "nelerdir",
        "olabilir",
    }
    return {token for token in folded.split() if len(token) > 3 and token not in stopwords}


def _is_near_duplicate_question(token_set: set[str], seen_token_sets: list[set[str]]) -> bool:
    if not token_set:
        return False
    for seen in seen_token_sets:
        overlap = len(token_set & seen)
        smaller = max(1, min(len(token_set), len(seen)))
        if overlap / smaller >= 0.72:
            return True
    return False


def _looks_too_narrow_title(title: str) -> bool:
    folded = _fold_simple(title)
    narrow_terms = ("avrupa", "abde", "ekonomik", "pazar", "strateji")
    return "bulut" in folded and sum(1 for term in narrow_terms if term in folded) >= 2


def _normalize_turkish_chars(text: str) -> str:
    return text.translate(
        str.maketrans(
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
                "Ö": "o",
                "Ş": "s",
                "Ü": "u",
            }
        )
    )


def _fold_simple(text: str) -> str:
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
    return re.sub(r"[^a-z0-9]+", "", _normalize_turkish_chars(text).translate(table).casefold())


def _fold_simple_with_spaces(text: str) -> str:
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
    return re.sub(r"[^a-z0-9]+", " ", _normalize_turkish_chars(text).translate(table).casefold()).strip()
