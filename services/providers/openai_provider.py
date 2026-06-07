from __future__ import annotations

import os

from services.providers.common import (
    build_generation_prompt,
    build_study_pack_schema,
    normalize_study_pack,
    parse_json_payload,
)


def generate_with_openai(source_pack: dict) -> dict:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("openai paketi kurulu degil. `pip install openai` gerekir.") from exc

    model = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
    client = OpenAI()
    prompt = build_generation_prompt(source_pack)
    target_count = int(source_pack.get("question_count", 10))

    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": "Ciktiyi yalnizca verilen JSON semasina uygun uret.",
            },
            {"role": "user", "content": prompt},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "study_pack",
                "strict": True,
                "schema": build_study_pack_schema(target_count),
            }
        },
    )
    return normalize_study_pack(parse_json_payload(response.output_text), source_pack, provider=f"openai:{model}")
