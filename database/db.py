from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable


def get_connection(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db(database_path: Path) -> None:
    schema_path = Path(__file__).with_name("models.sql")
    with get_connection(database_path) as connection:
        connection.executescript(schema_path.read_text(encoding="utf-8"))


def create_document(
    database_path: Path,
    *,
    file_name: str,
    file_path: str,
    cloud_url: str,
    page_count: int,
    processing_status: str,
    document_id: int | None = None,
) -> int:
    with get_connection(database_path) as connection:
        if document_id is None:
            cursor = connection.execute(
                """
                INSERT INTO documents
                    (file_name, file_path, cloud_url, page_count, processing_status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (file_name, file_path, cloud_url, page_count, processing_status),
            )
            return int(cursor.lastrowid)

        connection.execute(
            """
            UPDATE documents
            SET file_name = ?, file_path = ?, cloud_url = ?, page_count = ?,
                processing_status = ?
            WHERE id = ?
            """,
            (file_name, file_path, cloud_url, page_count, processing_status, document_id),
        )
        return document_id


def create_analysis(
    database_path: Path,
    *,
    document_id: int,
    clean_text: str,
    generated_notes: str,
    keywords: str,
    processing_time: float,
) -> int:
    with get_connection(database_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO analysis_results
                (document_id, clean_text, generated_notes, keywords, processing_time)
            VALUES (?, ?, ?, ?, ?)
            """,
            (document_id, clean_text, generated_notes, keywords, processing_time),
        )
        return int(cursor.lastrowid)


def save_questions(database_path: Path, document_id: int, questions: Iterable[dict]) -> None:
    with get_connection(database_path) as connection:
        connection.executemany(
            """
            INSERT INTO questions
                (document_id, question_text, answer_text, source_sentence,
                 question_type, quality_score)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    document_id,
                    question["question"],
                    question["answer"],
                    question["source_sentence"],
                    question["type"],
                    question["quality_score"],
                )
                for question in questions
            ],
        )


def get_document(database_path: Path, document_id: int) -> sqlite3.Row | None:
    with get_connection(database_path) as connection:
        return connection.execute(
            "SELECT * FROM documents WHERE id = ?",
            (document_id,),
        ).fetchone()


def get_analysis(database_path: Path, document_id: int) -> dict | None:
    with get_connection(database_path) as connection:
        analysis = connection.execute(
            "SELECT * FROM analysis_results WHERE document_id = ? ORDER BY id DESC LIMIT 1",
            (document_id,),
        ).fetchone()
        if analysis is None:
            return None

        questions = connection.execute(
            "SELECT * FROM questions WHERE document_id = ? ORDER BY quality_score DESC, id ASC",
            (document_id,),
        ).fetchall()

    return {"analysis": analysis, "questions": questions}


def get_history(database_path: Path) -> list[sqlite3.Row]:
    with get_connection(database_path) as connection:
        return connection.execute(
            """
            SELECT
                d.id,
                d.file_name,
                d.page_count,
                d.processing_status,
                d.upload_date,
                COUNT(q.id) AS question_count
            FROM documents d
            LEFT JOIN questions q ON q.document_id = d.id
            GROUP BY d.id
            ORDER BY d.upload_date DESC
            """
        ).fetchall()
