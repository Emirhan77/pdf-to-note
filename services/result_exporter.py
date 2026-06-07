from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path


def export_analysis_result(
    output_dir: Path,
    *,
    document_id: int,
    file_name: str,
    page_count: int,
    clean_text: str,
    generated_notes: str,
    keywords: list[str],
    questions: list[dict],
    processing_time: float,
    cloud_url: str = "",
    study_pack: dict | None = None,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_stem = _safe_stem(file_name)
    base_name = f"{timestamp}_doc{document_id}_{safe_stem}"
    json_path = output_dir / f"{base_name}.json"
    markdown_path = output_dir / f"{base_name}.md"

    payload = {
        "document_id": document_id,
        "file_name": file_name,
        "page_count": page_count,
        "cloud_url": cloud_url,
        "processing_time": round(processing_time, 3),
        "clean_text_word_count": len(clean_text.split()),
        "keywords": keywords,
        "generated_notes": generated_notes,
        "questions": questions,
        "study_pack": study_pack or {},
        "clean_text_preview": clean_text[:4000],
    }

    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    markdown_path.write_text(
        _to_markdown(payload),
        encoding="utf-8",
    )

    return {
        "json_path": str(json_path),
        "markdown_path": str(markdown_path),
    }


def _safe_stem(file_name: str) -> str:
    stem = Path(file_name).stem
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", stem).strip("_")
    return cleaned[:60] or "analysis"


def _to_markdown(payload: dict) -> str:
    question_blocks = []
    for index, question in enumerate(payload["questions"], start=1):
        question_blocks.append(
            "\n".join(
                [
                    f"### {index}. {question['question']}",
                    "",
                    f"**Cevap:** {question['answer']}",
                    "",
                    f"**Tür:** {question['type']}",
                    f"**Konu:** {question.get('topic', '-')}",
                    f"**Kalite puanı:** {question['quality_score']}",
                    f"**Kalite gerekçesi:** {question.get('quality_reason', '-')}",
                    "",
                    f"**Kaynak cümle:** {question['source_sentence']}",
                ]
            )
        )

    return "\n\n".join(
        [
            f"# Analiz Sonucu: {payload['file_name']}",
            "## Metrikler",
            f"- Doküman ID: {payload['document_id']}",
            f"- Sayfa sayısı: {payload['page_count']}",
            f"- Bulut PDF baglantisi: {payload.get('cloud_url') or '-'}",
            f"- İşlem süresi: {payload['processing_time']} sn",
            f"- Temiz metin kelime sayısı: {payload['clean_text_word_count']}",
            f"- Üretilen soru sayısı: {len(payload['questions'])}",
            f"- Üretim modu: {payload.get('study_pack', {}).get('provider', '-')}",
            "",
            "## Anahtar Kavramlar",
            ", ".join(payload["keywords"]) or "Anahtar kavram bulunamadı.",
            "",
            "## Ders Notu",
            payload["generated_notes"],
            "",
            "## Soru-Cevaplar",
            "\n\n".join(question_blocks) or "Kalite filtresinden geçen soru üretilemedi.",
            "",
            "## Temiz Metin Önizleme",
            payload["clean_text_preview"],
        ]
    )
