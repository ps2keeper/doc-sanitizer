# Document Sanitizer — Design Specification

**Date**: 2026-04-14
**Status**: Draft

## Overview

A web-based tool that processes Word (.docx), text (.txt), and PDF (.pdf) documents to replace sensitive words with custom replacement terms. Word documents are processed in track-changes (revision) mode. After replacement, a regex-based secondary scan audits the result to confirm no sensitive word variants remain.

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

## Components

### 1. Frontend (`templates/index.html`, `static/`)

Single-page Bootstrap UI with three sections:

- **Upload**: Drag-and-drop or file picker for .docx/.txt/.pdf files
- **Sensitive Words Table**: Add/edit/delete rows of `{sensitive_word, replacement_word}`. Supports import/export as JSON.
- **Process & Download**: Triggers processing, shows audit results, provides download link for processed document and audit report.

### 2. Sensitive Word Management (`/api/sensitive-words`)

Flask REST API for CRUD operations on sensitive word → replacement mappings:

- `GET /api/sensitive-words` — list all
- `POST /api/sensitive-words` — add new
- `PUT /api/sensitive-words/<id>` — update
- `DELETE /api/sensitive-words/<id>` — remove
- `POST /api/sensitive-words/import` — bulk import from JSON
- `GET /api/sensitive-words/export` — export as JSON

Storage: SQLite (`sensitive_words.db`) with schema:

```sql
CREATE TABLE IF NOT EXISTS sensitive_words (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT NOT NULL,
    replacement TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3. Document Processing Engine (`engine/`)

Each file type has a dedicated handler with a common interface:

```python
class DocumentHandler:
    def process(self, file_path: str, replacements: dict) -> tuple[BytesIO, AuditResult]
```

#### 3.1 Word Handler (`engine/docx_handler.py`)

- Open `.docx` with `python-docx`
- Enable track-changes: set `document.settings.track_revisions = True`
- Iterate through all **paragraphs** and **tables**, processing at the **run level**:
  - For each run, check if it contains any sensitive word (case-insensitive)
  - On match: split the run into three parts — text before match, matched text, text after match
  - Mark matched text run for deletion (`run.element.rPr` with `del` revision)
  - Insert replacement text as a tracked insertion (`ins` revision)
- Preserve original formatting (font, size, color, bold, italic) on surrounding runs
- Save processed document to `BytesIO`

#### 3.2 Text Handler (`engine/txt_handler.py`)

- Read text content
- Use word-boundary-aware regex (`\b{sensitive_word}\b`) for replacements
- Save result to `BytesIO`

#### 3.3 PDF Handler (`engine/pdf_handler.py`)

- Extract text page-by-page using `PyMuPDF` (fitz)
- Perform replacements on extracted text
- Rebuild PDF with replaced text using `reportlab`:
  - Create new PDF with same page dimensions
  - Place replaced text at approximate original positions
  - Note: Complex formatting and embedded fonts may not be perfectly preserved
- Alternative: annotate original PDF by highlighting original sensitive words and adding replacement notes in margins

### 4. Audit Engine (`engine/audit_engine.py`)

After replacement, performs a secondary scan to confirm all sensitive words have been replaced:

1. **Build regex pattern**: Combine all sensitive words into a single pattern with alternation:
   - `\b(?:word1|word2|word3)\b`
   - Flags: `re.IGNORECASE`
   - Add whitespace tolerance: `\b(?:wor\s*d1|word\s*2)\b` for common evasion patterns

2. **Scan processed document**:
   - For `.docx`: extract all text from paragraphs and tables
   - For `.txt`: read the result file
   - For `.pdf`: extract text from result PDF

3. **Generate audit report**:
   ```python
   class AuditResult:
       is_clean: bool
       missed_words: list[dict]  # [{word, context, location, line_number}]
       total_matches: int
   ```

4. If `is_clean == False`, the frontend displays a warning with the list of missed words and their context.

## Data Flow

```
1. User uploads document (.docx/.txt/.pdf)
2. User configures sensitive words via table (or imports JSON)
3. User clicks "Process"
4. Flask routes to appropriate handler by file extension
5. Handler performs replacements:
   - .docx → track-chapes mode, split runs, mark deletions + insertions
   - .txt → regex replacement
   - .pdf → extract → replace → rebuild
6. Audit Engine runs regex secondary scan on the result
7. If audit finds remaining variants → include in audit report
8. Return processed document + audit report (JSON)
9. Frontend shows audit summary, offers downloads for both files
```

## Error Handling

| Scenario | Behavior |
|---|---|
| Unsupported file type | Reject upload with error toast |
| Corrupted document | Return clear error message, no processing |
| No sensitive words configured | Warn before processing |
| Audit finds remaining words | Show warning with details, allow re-process |
| Large files (>10MB) | Show progress indicator, increase timeout |
| PDF with complex formatting | Warn that formatting may not be fully preserved |

## Project Structure

```
doc-sanitizer/
├── app.py                          # Flask app entry point, routes
├── requirements.txt
├── sensitive_words.db              # SQLite (auto-created)
├── static/
│   ├── css/
│   │   └── style.css              # Custom styles
│   └── js/
│       └── main.js                # Frontend logic (AJAX, table, upload)
├── templates/
│   └── index.html                 # Single page UI (Bootstrap)
├── engine/
│   ├── __init__.py
│   ├── docx_handler.py            # Word processing with track-changes
│   ├── txt_handler.py             # Text file processing
│   ├── pdf_handler.py             # PDF processing
│   └── audit_engine.py            # Regex secondary scan
├── models/
│   └── __init__.py                # Database models (sensitive words)
└── uploads/                       # Temp upload directory (gitignore)
```

## Dependencies

```
Flask>=3.0
python-docx>=1.1
PyMuPDF>=1.23
reportlab>=4.0
```

## Testing Strategy

1. **Unit tests**: Each handler independently tested with sample documents
2. **Integration tests**: Full pipeline (upload → process → audit → download)
3. **Audit tests**: Documents with known sensitive words verify audit catches all
4. **Track-changes verification**: Processed `.docx` opens in Word with visible revisions
