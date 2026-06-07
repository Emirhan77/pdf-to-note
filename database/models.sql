CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    cloud_url TEXT DEFAULT '',
    page_count INTEGER DEFAULT 0,
    upload_date TEXT DEFAULT CURRENT_TIMESTAMP,
    processing_status TEXT NOT NULL DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS analysis_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    clean_text TEXT NOT NULL,
    generated_notes TEXT NOT NULL,
    keywords TEXT NOT NULL,
    processing_time REAL NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES documents (id)
);

CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    question_text TEXT NOT NULL,
    answer_text TEXT NOT NULL,
    source_sentence TEXT NOT NULL,
    question_type TEXT NOT NULL,
    quality_score INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (document_id) REFERENCES documents (id)
);
