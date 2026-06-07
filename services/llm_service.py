from __future__ import annotations

import os
from pathlib import Path

from services.providers.ollama_provider import generate_with_ollama
from services.providers.openai_provider import generate_with_openai
from services.providers.prompt_export_provider import generate_prompt_export


def generate_study_pack(source_pack: dict, provider: str | None = None) -> dict:
    selected_provider = (provider or os.getenv("LLM_PROVIDER") or "local_ollama").strip().lower()

    if selected_provider in {"ollama", "local_ollama"}:
        try:
            return generate_with_ollama(source_pack)
        except Exception as exc:
            pack = generate_prompt_export(source_pack, fallback_reason=f"Ollama kullanilamadi: {exc}")
            _attach_llm_diagnostics(pack, exc)
            return pack

    if selected_provider == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            return generate_prompt_export(source_pack, fallback_reason="OPENAI_API_KEY bulunamadi.")
        try:
            return generate_with_openai(source_pack)
        except Exception as exc:
            pack = generate_prompt_export(source_pack, fallback_reason=f"OpenAI API kullanilamadi: {exc}")
            _attach_llm_diagnostics(pack, exc)
            return pack

    return generate_prompt_export(source_pack, fallback_reason=f"Bilinmeyen LLM_PROVIDER: {selected_provider}")


def _attach_llm_diagnostics(pack: dict, exc: Exception) -> None:
    for key in ("provider_attempted", "llm_error_type", "llm_error_message", "raw_response_preview"):
        value = getattr(exc, key, "")
        if value:
            pack[key] = value


def load_env_file(base_dir: Path) -> None:
    env_path = base_dir / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)
