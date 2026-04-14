# 📝 Document Sanitizer

A web-based tool that replaces sensitive words in Word (.docx), text (.txt), and PDF (.pdf) documents with custom replacement terms. Word documents are processed in **track-changes (revision) mode**, and a **regex-based audit engine** verifies that no sensitive word variants remain after processing.

## Features

- **Multi-format support**: `.docx`, `.txt`, `.pdf`
- **Track-changes mode**: Word documents show revisions as tracked deletions/insertions
- **Audit engine**: Regex secondary scan with whitespace-tolerant, case-insensitive matching
- **Web UI**: Bootstrap-based single-page interface for upload, config, and download
- **REST API**: Full CRUD for sensitive word management with JSON import/export
- **SQLite storage**: Persistent sensitive word database
- **50MB max file size**

## Quick Start

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/doc-sanitizer.git
cd doc-sanitizer

# Install dependencies
pip install -r requirements.txt

# Start the server
python app.py

# Open browser to http://localhost:5000
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Browser (Frontend)                   │
│  ┌───────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Upload    │  │ Sensitive    │  │ Download         │  │
│  │ Document  │  │ Words Table  │  │ Result + Audit   │  │
│  └─────┬─────┘  └──────┬───────┘  └────────┬─────────┘  │
│        └───────────────┴───────────────────┘            │
│                        HTTP (Flask API)                  │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                     Flask Backend                        │
│  ┌────────────────────────────────────────────────────┐  │
│  │              Processing Engine                     │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────────┐  │  │
│  │  │ .docx      │ │ .txt       │ │ .pdf           │  │  │
│  │  │ python-docx│ │ native     │ │ PyMuPDF        │  │  │
│  │  │ + track    │ │ I/O        │ │ extract/replace│  │  │
│  │  │  -changes  │ │            │ │ /rebuild       │  │  │
│  │  └────────────┘ └────────────┘ └────────────────┘  │  │
│  │                                                    │  │
│  │  ┌────────────────────────────────────────────┐    │  │
│  │  │ Audit Engine: Regex secondary scan         │    │  │
│  │  │ - Build regex from sensitive word patterns │    │  │
│  │  │ - Scan processed document for any matches  │    │  │
│  │  │ - Report missed variants (case, spacing)   │    │  │
│  │  └────────────────────────────────────────────┘    │  │
│  └────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## API Reference

### Sensitive Words

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/sensitive-words` | List all sensitive words |
| POST | `/api/sensitive-words` | Add a new word (body: `{word, replacement}`) |
| PUT | `/api/sensitive-words/<id>` | Update a word |
| DELETE | `/api/sensitive-words/<id>` | Delete a word |
| GET | `/api/sensitive-words/export` | Export all words as JSON |
| POST | `/api/sensitive-words/import` | Import words from JSON |
| POST | `/api/sensitive-words/clear` | Clear all words |

### Document Processing

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/process` | Upload and process a document |
| GET | `/api/download/<filename>` | Download processed file |

## Project Structure

```
doc-sanitizer/
├── app.py                          # Flask app entry point, routes
├── requirements.txt
├── models/
│   └── __init__.py                 # SQLite DB models
├── engine/
│   ├── __init__.py                 # Handler factory
│   ├── docx_handler.py             # Word processing with track-changes
│   ├── txt_handler.py              # Text file processing
│   ├── pdf_handler.py              # PDF processing
│   └── audit_engine.py             # Regex secondary scan
├── static/
│   ├── css/style.css
│   └── js/main.js
├── templates/
│   └── index.html
├── tests/
│   ├── test_api.py
│   ├── test_audit_engine.py
│   ├── test_docx_handler.py
│   ├── test_integration.py
│   ├── test_models.py
│   ├── test_pdf_handler.py
│   └── test_txt_handler.py
└── uploads/                        # Temp upload directory (gitignored)
```

## Tech Stack

- **Backend**: Python 3.10+, Flask 3.0
- **Word**: python-docx (track-changes via OOXML revision elements)
- **PDF**: PyMuPDF (fitz) + reportlab
- **Database**: SQLite
- **Frontend**: Bootstrap 5, vanilla JavaScript

## License

MIT
