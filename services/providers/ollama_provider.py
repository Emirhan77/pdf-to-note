from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from services.providers.common import (
    build_generation_prompt,
    build_question_repair_prompt,
    build_question_repair_schema,
    build_study_pack_schema,
    fill_missing_questions,
    merge_repaired_questions,
    normalize_study_pack,
    parse_json_payload,
)


class OllamaJsonParseError(RuntimeError):
    def __init__(self, message: str, *, raw_response: str, provider_attempted: str) -> None:
        super().__init__(message)
        self.provider_attempted = provider_attempted
        self.llm_error_type = "json_parse_error"
        self.llm_error_message = message
        self.raw_response_preview = raw_response[:1200]


def generate_with_ollama(source_pack: dict) -> dict:
    model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    target_count = int(source_pack.get("question_count", 10))
    prompt = build_generation_prompt(source_pack)
    payload = _chat_with_ollama(
        model=model,
        prompt=prompt,
        schema=build_study_pack_schema(target_count),
        system_message="Ciktiyi yalnizca verilen JSON semasina uygun uret. Tam sayida bolum ve soru uret.",
    )
    study_pack = normalize_study_pack(payload, source_pack, provider=f"ollama:{model}")

    missing_count = max(0, target_count - len(study_pack.get("questions", [])))
    repair_attempts = 0
    while missing_count and repair_attempts < 2:
        repair_attempts += 1
        repair_prompt = build_question_repair_prompt(source_pack, study_pack["questions"], missing_count)
        repaired_payload = _chat_with_ollama(
            model=model,
            prompt=repair_prompt,
            schema=build_question_repair_schema(missing_count),
            system_message="Ciktiyi yalnizca verilen JSON semasina uygun uret. Sadece yeni sorular uret.",
        )
        study_pack = merge_repaired_questions(study_pack, repaired_payload.get("questions", []), target_count)
        missing_count = max(0, target_count - len(study_pack.get("questions", [])))

    if missing_count:
        study_pack["questions"] = fill_missing_questions(source_pack, study_pack.get("questions", []), target_count)

    return study_pack


def _chat_with_ollama(*, model: str, prompt: str, schema: dict, system_message: str) -> dict:
    content = _send_ollama_chat(
        model=model,
        prompt=prompt,
        schema=schema,
        system_message=system_message,
    )
    try:
        return parse_json_payload(content)
    except Exception as parse_exc:
        try:
            repaired_content = _send_ollama_chat(
                model=model,
                prompt=_build_json_repair_prompt(content),
                schema=schema,
                system_message="Yalnizca gecerli JSON dondur. Aciklama, markdown veya ek metin yazma.",
                temperature=0.0,
            )
            return parse_json_payload(repaired_content)
        except Exception as repair_exc:
            message = f"JSON parse ve repair basarisiz: {parse_exc}; repair: {repair_exc}"
            raise OllamaJsonParseError(
                message,
                raw_response=content,
                provider_attempted=f"ollama:{model}",
            ) from repair_exc


def _send_ollama_chat(
    *,
    model: str,
    prompt: str,
    schema: dict,
    system_message: str,
    temperature: float | None = None,
) -> str:
    host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    timeout = int(os.getenv("OLLAMA_TIMEOUT", "180"))
    body = {
        "model": model,
        "stream": False,
        "format": schema,
        "options": {
            "temperature": float(os.getenv("OLLAMA_TEMPERATURE", "0.2")) if temperature is None else temperature,
            "num_ctx": int(os.getenv("OLLAMA_NUM_CTX", "16384")),
            "num_predict": int(os.getenv("OLLAMA_NUM_PREDICT", "3072")),
        },
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt},
        ],
    }
    request = urllib.request.Request(
        f"{host}/api/chat",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError("Ollama sunucusuna ulasilamadi. Ollama kurulu ve calisir durumda olmali.") from exc

    content = payload.get("message", {}).get("content", "")
    if not content:
        raise RuntimeError("Ollama bos yanit dondurdu.")
    return content


def _build_json_repair_prompt(raw_content: str) -> str:
    return f"""
Asagidaki metni yalnizca gecerli JSON olarak duzelt. Aciklama yazma. Schema disina cikma.
Eksik tirnak, virgül veya kapanis karakterlerini onar. JSON disinda hicbir metin dondurme.

METIN:
\"\"\"
{raw_content[:24000]}
\"\"\"
""".strip()
