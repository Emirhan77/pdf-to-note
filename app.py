from __future__ import annotations

import re
import time
import json
import os
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.utils import secure_filename

from database.db import (
    create_analysis,
    create_document,
    get_analysis,
    get_document,
    get_history,
    init_db,
    save_questions,
)
from services.cloud_storage import upload_pdf
from services.llm_service import generate_study_pack, load_env_file
from services.note_generator import generate_notes
from services.pdf_service import extract_pdf_text, validate_pdf_upload
from services.quality_filter import filter_questions
from services.question_generator import generate_questions
from services.result_exporter import export_analysis_result
from services.sentence_scorer import score_sentences
from services.source_pack_builder import build_source_pack
from services.text_cleaner import clean_blocks, clean_text, split_sentences, units_to_text
from services.providers.common import (
    SOURCE_NOTE,
    fill_missing_questions,
    questions_for_database,
    render_study_pack_markdown,
)


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
DATABASE_PATH = BASE_DIR / "database" / "app.db"
RESULTS_DIR = BASE_DIR / "experiments" / "results"
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

load_env_file(BASE_DIR)


def is_valid_email(value: str) -> bool:
    return bool(EMAIL_PATTERN.match(value.strip()))


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY") or "local-development-secret"
    app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    init_db(DATABASE_PATH)

    PUBLIC_ENDPOINTS = frozenset({"login", "login_submit", "static"})

    @app.before_request
    def require_login():
        if request.endpoint in PUBLIC_ENDPOINTS:
            return None
        if session.get("authenticated"):
            return None
        return redirect(url_for("login"))

    @app.route("/")
    def login():
        if session.get("authenticated"):
            return redirect(url_for("app_index"))
        return render_template("login.html")

    @app.route("/login", methods=["POST"])
    def login_submit():
        email = (request.form.get("email") or "").strip()
        if not email:
            flash("E-posta adresi gereklidir.")
            return redirect(url_for("login"))
        if not is_valid_email(email):
            flash("Geçerli bir e-posta adresi girin (örnek: ad@universite.edu.tr).")
            return redirect(url_for("login"))
        session["authenticated"] = True
        session["user_display"] = email
        return redirect(url_for("app_index"))

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/app")
    def app_index():
        return render_template("index.html", user_display=session.get("user_display", ""))

    @app.route("/analyze", methods=["POST"])
    def analyze():
        uploaded_file = request.files.get("pdf_file")
        summary_length = request.form.get("summary_length", "medium")
        question_count = int(request.form.get("question_count", "10"))

        validation_error = validate_pdf_upload(uploaded_file)
        if validation_error:
            flash(validation_error)
            return redirect(url_for("app_index"))

        assert uploaded_file is not None
        safe_name = secure_filename(uploaded_file.filename or "document.pdf")
        saved_name = f"{int(time.time())}_{safe_name}"
        saved_path = UPLOAD_DIR / saved_name
        uploaded_file.save(saved_path)
        cloud_url = ""
        cloud_warning = ""
        try:
            cloud_url = upload_pdf(saved_path)
        except Exception as exc:
            cloud_warning = f"S3 yukleme basarisiz, lokal dosya kullanildi: {exc}"

        started_at = time.perf_counter()
        document_id = create_document(
            DATABASE_PATH,
            file_name=safe_name,
            file_path=str(saved_path),
            cloud_url=cloud_url,
            page_count=0,
            processing_status="processing",
        )

        try:
            extraction = extract_pdf_text(saved_path)
            cleaned_units = clean_blocks(extraction.blocks)
            cleaned_text = units_to_text(cleaned_units) if cleaned_units else clean_text(extraction.text)
            sentences = split_sentences(cleaned_units if cleaned_units else cleaned_text)
            scored_sentences = score_sentences(sentences)
            notes = generate_notes(scored_sentences, summary_length=summary_length)
            source_pack = build_source_pack(
                file_name=safe_name,
                page_count=extraction.page_count,
                clean_text=cleaned_text,
                keywords=notes["keywords"],
                scored_sentences=scored_sentences,
                question_count=question_count,
                output_language="tr",
            )
            study_pack = generate_study_pack(source_pack)
            if study_pack.get("provider") == "prompt_export":
                prompt_export_pack = study_pack
                study_pack = _build_rule_based_fallback_pack(
                    scored_sentences=scored_sentences,
                    summary_length=summary_length,
                    question_count=question_count,
                    fallback_reason=prompt_export_pack.get("fallback_reason", ""),
                    fallback_metadata=prompt_export_pack,
                )
            generated_markdown = render_study_pack_markdown(study_pack)
            generated_display_text = _markdown_to_display_text(generated_markdown)
            questions = questions_for_database(study_pack)
            keywords = study_pack["keywords"] or notes["keywords"]
            processing_time = time.perf_counter() - started_at

            create_analysis(
                DATABASE_PATH,
                document_id=document_id,
                clean_text=cleaned_text,
                generated_notes=generated_display_text,
                keywords=", ".join(keywords),
                processing_time=processing_time,
            )
            save_questions(DATABASE_PATH, document_id, questions)
            export_paths = export_analysis_result(
                RESULTS_DIR,
                document_id=document_id,
                file_name=safe_name,
                page_count=extraction.page_count,
                clean_text=cleaned_text,
                generated_notes=generated_markdown,
                keywords=keywords,
                questions=questions,
                processing_time=processing_time,
                study_pack=study_pack,
                cloud_url=cloud_url,
            )

            create_document(
                DATABASE_PATH,
                file_name=safe_name,
                file_path=str(saved_path),
                cloud_url=cloud_url,
                page_count=extraction.page_count,
                processing_status="completed",
                document_id=document_id,
            )
            flash(f"Analiz sonucu kaydedildi: {export_paths['markdown_path']}")
            if cloud_warning:
                flash(cloud_warning)
        except Exception as exc:
            create_document(
                DATABASE_PATH,
                file_name=safe_name,
                file_path=str(saved_path),
                cloud_url=cloud_url,
                page_count=0,
                processing_status=f"failed: {exc}",
                document_id=document_id,
            )
            flash(f"PDF analiz edilemedi: {exc}")
            return redirect(url_for("app_index"))

        return redirect(url_for("result", document_id=document_id))

    @app.route("/result/<int:document_id>")
    def result(document_id: int):
        document = get_document(DATABASE_PATH, document_id)
        analysis = get_analysis(DATABASE_PATH, document_id)
        if not document or not analysis:
            flash("Analiz sonucu bulunamadi.")
            return redirect(url_for("app_index"))
        export_context = _load_export_context(document_id)
        return render_template(
            "result.html",
            document=document,
            analysis=analysis,
            study_pack=export_context["study_pack"],
            export_links=export_context["links"],
        )

    @app.route("/exports/<path:filename>")
    def download_export(filename: str):
        return send_from_directory(str(RESULTS_DIR), filename, as_attachment=True)

    @app.route("/history")
    def history():
        return render_template("history.html", documents=get_history(DATABASE_PATH))

    return app


app = create_app()


def _build_rule_based_fallback_pack(
    *,
    scored_sentences: list,
    summary_length: str,
    question_count: int,
    fallback_reason: str,
    fallback_metadata: dict | None = None,
) -> dict:
    notes = generate_notes(scored_sentences, summary_length=summary_length)
    raw_questions = generate_questions(scored_sentences, keywords=notes["keywords"], limit=question_count * 4)
    filtered_questions = filter_questions(raw_questions, limit=question_count, keywords=notes["keywords"])

    sections = _sections_from_markdown(notes["markdown"])
    questions = [{"question": item["question"], "answer": item["answer"]} for item in filtered_questions]
    questions = fill_missing_questions(
        {"file_name": "fallback.pdf", "keywords": notes["keywords"]},
        questions,
        question_count,
    )

    study_pack = {
        "title": "PDF Notu: Bulut Bilisim",
        "sections": sections,
        "questions": questions,
        "keywords": notes["keywords"],
        "source_note": SOURCE_NOTE,
        "provider": "rule_based_fallback",
        "fallback_reason": f"{fallback_reason} (Yerel kural tabanli fallback kullanildi.)",
    }
    if fallback_metadata:
        for key in ("provider_attempted", "llm_error_type", "llm_error_message", "raw_response_preview"):
            if fallback_metadata.get(key):
                study_pack[key] = fallback_metadata[key]
    return study_pack


def _sections_from_markdown(markdown: str) -> list[dict]:
    sections: list[dict] = []
    current_heading = ""
    content_lines: list[str] = []
    key_points: list[str] = []

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("## "):
            continue
        if line.startswith("### "):
            if current_heading:
                sections.append(
                    {
                        "heading": current_heading,
                        "content": " ".join(content_lines).strip(),
                        "key_points": key_points[:6],
                    }
                )
            current_heading = line.replace("### ", "", 1).strip()
            content_lines = []
            key_points = []
            continue
        if line.startswith("- "):
            key_points.append(line[2:].strip())
            continue
        content_lines.append(line)

    if current_heading:
        sections.append(
            {
                "heading": current_heading,
                "content": " ".join(content_lines).strip(),
                "key_points": key_points[:6],
            }
        )

    return sections or [{"heading": "Konu Ozeti", "content": markdown, "key_points": []}]


def _markdown_to_display_text(markdown: str) -> str:
    lines = []
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            lines.append("")
            continue
        line = line.replace("```text", "").replace("```", "")
        line = line.replace("## ", "").replace("### ", "")
        line = line.replace("**", "")
        lines.append(line)
    return "\n".join(lines).strip()


def _load_export_context(document_id: int) -> dict:
    json_files = sorted(
        RESULTS_DIR.glob(f"*doc{document_id}_*.json"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    if not json_files:
        return {"study_pack": {}, "links": {}}

    json_path = json_files[0]
    markdown_path = json_path.with_suffix(".md")
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        study_pack = payload.get("study_pack", {}) or {}
    except Exception:
        study_pack = {}

    links = {
        "json_url": url_for("download_export", filename=json_path.name),
    }
    if markdown_path.exists():
        links["markdown_url"] = url_for("download_export", filename=markdown_path.name)

    return {"study_pack": study_pack, "links": links}


if __name__ == "__main__":
    debug_enabled = os.getenv("FLASK_DEBUG", "1").strip().lower() in {"1", "true", "yes", "on"}
    app.run(debug=debug_enabled)
