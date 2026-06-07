from __future__ import annotations

from services.providers.common import normalize_study_pack


def generate_prompt_export(source_pack: dict, fallback_reason: str = "") -> dict:
    payload = {
        "title": "Analiz Gecici Olarak Hazirlanamadi",
        "sections": [
            {
                "heading": "Sistem Durumu",
                "content": (
                    "LLM yaniti su an alinamadi. Sistem alternatif bir isleme yoluna gecerek "
                    "analiz sonucunu hazirlamayi deneyecek."
                ),
                "key_points": [
                    "Bu mesaj teknik bir fallback bilgisidir.",
                    "Hedef: kullaniciya bos sonuc yerine anlamli not ve soru gostermek.",
                ],
            }
        ],
        "questions": [],
        "keywords": source_pack.get("keywords", []),
        "source_note": source_pack.get("method_note", ""),
    }
    return normalize_study_pack(payload, source_pack, provider="prompt_export", fallback_reason=fallback_reason)
