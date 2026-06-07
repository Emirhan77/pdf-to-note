# PDF to Note

A Flask-based web application that turns PDF course documents into structured study notes, key concepts, and question-answer pairs.

The project uses a hybrid pipeline: it first extracts and cleans PDF text with deterministic text-processing steps, then sends a balanced source package to an LLM provider. It can run with a local Ollama model, an optional OpenAI provider, or a prompt-export fallback when no model is available.

## Features

- PDF upload and validation through a Flask web interface
- Text extraction with PyMuPDF
- Rule-based text cleaning for page numbers, slide noise, references, URLs, captions, and broken spacing
- Sentence scoring and keyword extraction before LLM generation
- Topic-aware source package generation for cloud-computing and generic academic PDFs
- Local LLM generation with Ollama
- Optional OpenAI provider support
- Prompt-export fallback when no LLM provider is available
- Structured study notes, key concepts, and question-answer output
- SQLite storage for uploaded documents, analysis results, and generated questions
- Analysis history page
- JSON and Markdown export for each analysis
- Optional AWS S3 private-bucket upload with presigned PDF URLs

## Tech Stack

- Python 3.12
- Flask
- PyMuPDF
- SQLite
- Ollama API
- Optional OpenAI API
- Optional AWS S3 via boto3
- HTML, CSS, and JavaScript frontend

## Project Structure

```text
.
|-- app.py
|-- database/
|   |-- db.py
|   `-- models.sql
|-- services/
|   |-- pdf_service.py
|   |-- text_cleaner.py
|   |-- source_pack_builder.py
|   |-- llm_service.py
|   |-- result_exporter.py
|   `-- providers/
|-- static/
|-- templates/
|-- experiments/
|-- uploads/
|-- .env.example
|-- requirements.txt
`-- README.md
```

Runtime-generated files such as uploaded PDFs, SQLite databases, analysis exports, logs, and local environment files are intentionally ignored by Git.

## Requirements

- Python 3.12 or newer
- pip
- Optional: Ollama for local LLM generation
- Optional: AWS credentials for S3 storage
- Optional: OpenAI API key for OpenAI generation mode

## Installation

Clone the repository:

```powershell
git clone https://github.com/Emirhan77/pdf-to-note.git
cd pdf-to-note
```

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Create a local environment file:

```powershell
Copy-Item .env.example .env
```

Start the application:

```powershell
python app.py
```

Open the app in your browser:

```text
http://127.0.0.1:5000
```

The login screen accepts an email address for the demo session.

## Running with Ollama

Install Ollama, pull the default model, and start the Ollama server:

```powershell
ollama pull qwen2.5:7b
ollama serve
```

Use these settings in `.env`:

```text
LLM_PROVIDER=local_ollama
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_TIMEOUT=420
OLLAMA_NUM_CTX=8192
OLLAMA_NUM_PREDICT=3072
OLLAMA_TEMPERATURE=0.2
LLM_MAX_SOURCE_CHARS=9000
```

Then run:

```powershell
python app.py
```

If Ollama is not available, the application can still continue with a fallback flow depending on the selected provider configuration.

## Prompt Export Fallback

For a lightweight setup without a local or paid LLM provider, use:

```text
LLM_PROVIDER=prompt_export
```

In this mode, the system prepares a structured prompt from the cleaned PDF content. The prompt can be copied into another LLM interface manually.

## Optional OpenAI Mode

OpenAI support is optional. Install the OpenAI package if needed:

```powershell
pip install openai
```

Then configure `.env`:

```text
LLM_PROVIDER=openai
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=gpt-5.4-mini
```

Do not commit `.env` or any real API keys.

## Optional AWS S3 Storage

By default, PDFs are stored locally in `uploads/`. For cloud-storage evidence, the app can upload PDFs to a private AWS S3 bucket and generate presigned URLs.

Example `.env` settings:

```text
CLOUD_STORAGE_PROVIDER=aws_s3
AWS_S3_BUCKET=your-private-bucket-name
AWS_REGION=eu-central-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_S3_KEY_PREFIX=uploads
AWS_PRESIGNED_URL_EXPIRES=604800
```

Keep the bucket private. The application is designed to access uploaded PDFs through temporary presigned URLs.

## Usage

1. Start the Flask app.
2. Open `http://127.0.0.1:5000`.
3. Log in with an email address.
4. Upload a text-based PDF.
5. Select the note length and number of questions.
6. Start the analysis.
7. Review the generated study notes, key concepts, and questions.
8. Download JSON or Markdown exports from the result page.
9. Use the history page to access previous analyses.

## Data and Generated Files

The following files and folders are ignored intentionally:

- `.env`
- `.venv/`
- `database/*.db`
- `uploads/`
- `experiments/results/*.json`
- `experiments/results/*.md`
- `sample_pdfs/`
- local report/planning files

This keeps the public repository focused on source code and avoids publishing private data, generated outputs, uploaded PDFs, or credentials.

## Limitations

- Scanned image-only PDFs are not supported because OCR is not included.
- Local Ollama generation can be slow on low-resource machines.
- LLM output may occasionally require post-processing or manual review.
- The fallback mode is useful for continuity, but it is not equivalent to full model-generated output.
- AWS and OpenAI modes require correctly configured external credentials.

## Security Notes

- Never commit `.env`.
- Rotate or revoke any cloud keys that were ever exposed locally.
- Keep S3 buckets private.
- Use least-privilege IAM permissions for S3 upload and read access.
- Use a strong `FLASK_SECRET_KEY` outside local development.

## License

No license file is currently included. Add a license before allowing broad reuse.
