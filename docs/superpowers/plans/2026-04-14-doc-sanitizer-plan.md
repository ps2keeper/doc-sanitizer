# Document Sanitizer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a web-based tool that replaces sensitive words in .docx, .txt, and .pdf documents, with Word documents processed in track-changes mode and a regex-based audit engine to verify no sensitive words remain.

**Architecture:** Flask backend with dedicated document handlers per file type, a shared audit engine for regex secondary scanning, SQLite for sensitive word storage, and a single-page Bootstrap frontend for upload/configure/download.

**Tech Stack:** Python 3.10+, Flask, python-docx, PyMuPDF, reportlab, Bootstrap 5, vanilla JS

---

## File Structure

```
doc-sanitizer/
├── app.py                          # Flask routes, API endpoints
├── requirements.txt
├── .gitignore
├── models/
│   └── __init__.py                 # DB init, CRUD helpers
├── engine/
│   ├── __init__.py                 # Handler interface, factory
│   ├── docx_handler.py             # Word processing with track-changes
│   ├── txt_handler.py              # Text file processing
│   ├── pdf_handler.py              # PDF extract/replace/rebuild
│   └── audit_engine.py             # Regex secondary scan
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── main.js
├── templates/
│   └── index.html
├── tests/
│   ├── test_audit_engine.py
│   ├── test_txt_handler.py
│   ├── test_docx_handler.py
│   └── test_pdf_handler.py
└── uploads/                        # gitignored
```

---

### Task 1: Project Scaffold + Requirements

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `app.py`
- Create: `models/__init__.py`
- Create: `engine/__init__.py`
- Create: `tests/` (directory)
- Create: `uploads/` (directory)

- [ ] **Step 1: Create requirements.txt**

```txt
Flask>=3.0
python-docx>=1.1
PyMuPDF>=1.23
reportlab>=4.0
pytest>=7.0
```

- [ ] **Step 2: Create .gitignore**

```gitignore
__pycache__/
*.pyc
*.pyo
*.db
uploads/*
!uploads/.gitkeep
venv/
.env
*.egg-info/
```

- [ ] **Step 3: Create app.py with minimal Flask app**

```python
import os
from flask import Flask, render_template

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

- [ ] **Step 4: Create empty package inits**

`models/__init__.py`:
```python
"""Database models for sensitive word management."""
```

`engine/__init__.py`:
```python
"""Document processing engine handlers."""
```

- [ ] **Step 5: Create directories**

```bash
mkdir -p uploads tests static/css static/js templates
touch uploads/.gitkeep
```

- [ ] **Step 6: Verify project structure**

```bash
ls -la
```

Expected: all directories and files present.

- [ ] **Step 7: Install dependencies**

```bash
pip install -r requirements.txt
```

- [ ] **Step 8: Test Flask starts**

```bash
python app.py &
sleep 2
curl -s http://localhost:5000/ | head -5
kill %1
```

Expected: HTML response (will be "template not found" for now, which is fine).

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "feat: scaffold project structure"
```

---

### Task 2: Database Models + Sensitive Word API

**Files:**
- Modify: `models/__init__.py`
- Modify: `app.py`

- [ ] **Step 1: Write failing test for DB model**

Create `tests/test_models.py`:

```python
import os
import sqlite3
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from models import init_db, get_db, add_word, list_words, delete_word, update_word


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    os.environ['DATABASE_PATH'] = path
    init_db()
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_add_and_list_words(db_path):
    add_word("secret", "REDACTED")
    add_word("confidential", "[CONFIDENTIAL]")
    words = list_words()
    assert len(words) == 2
    assert words[0]['word'] == 'secret'
    assert words[0]['replacement'] == 'REDACTED'


def test_delete_word(db_path):
    add_word("temp", "TEMP")
    words = list_words()
    assert len(words) == 1
    delete_word(words[0]['id'])
    words = list_words()
    assert len(words) == 0


def test_update_word(db_path):
    add_word("old", "replacement1")
    words = list_words()
    update_word(words[0]['id'], "old", "replacement2")
    words = list_words()
    assert words[0]['replacement'] == 'replacement2'
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/jiche/Documents/Qwen && python -m pytest tests/test_models.py -v
```

Expected: FAIL with import errors.

- [ ] **Step 3: Implement database models**

Update `models/__init__.py`:

```python
"""Database models for sensitive word management."""
import os
import sqlite3

DATABASE_PATH = os.environ.get('DATABASE_PATH', 'sensitive_words.db')


def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sensitive_words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL,
            replacement TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


def add_word(word: str, replacement: str) -> int:
    conn = get_db()
    cursor = conn.execute(
        'INSERT INTO sensitive_words (word, replacement) VALUES (?, ?)',
        (word, replacement)
    )
    conn.commit()
    word_id = cursor.lastrowid
    conn.close()
    return word_id


def list_words() -> list[dict]:
    conn = get_db()
    rows = conn.execute('SELECT * FROM sensitive_words ORDER BY created_at').fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_word(word_id: int):
    conn = get_db()
    conn.execute('DELETE FROM sensitive_words WHERE id = ?', (word_id,))
    conn.commit()
    conn.close()


def update_word(word_id: int, word: str, replacement: str):
    conn = get_db()
    conn.execute(
        'UPDATE sensitive_words SET word = ?, replacement = ? WHERE id = ?',
        (word, replacement, word_id)
    )
    conn.commit()
    conn.close()


def export_words() -> str:
    import json
    words = list_words()
    return json.dumps({w['word']: w['replacement'] for w in words}, indent=2)


def import_words(data: dict):
    for word, replacement in data.items():
        add_word(word, replacement)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /Users/jiche/Documents/Qwen && python -m pytest tests/test_models.py -v
```

Expected: All 3 tests PASS.

- [ ] **Step 5: Write failing tests for API endpoints**

Create `tests/test_api.py`:

```python
import os
import sys
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from app import app
from models import init_db, DATABASE_PATH


@pytest.fixture
def client(tmp_path):
    db_path = str(tmp_path / "api_test.db")
    os.environ['DATABASE_PATH'] = db_path
    init_db()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client
    if os.path.exists(db_path):
        os.remove(db_path)


def test_list_words_empty(client):
    resp = client.get('/api/sensitive-words')
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_add_word(client):
    resp = client.post('/api/sensitive-words', json={'word': 'secret', 'replacement': 'REDACTED'})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['word'] == 'secret'


def test_list_words_after_add(client):
    client.post('/api/sensitive-words', json={'word': 'a', 'replacement': 'A'})
    client.post('/api/sensitive-words', json={'word': 'b', 'replacement': 'B'})
    resp = client.get('/api/sensitive-words')
    words = resp.get_json()
    assert len(words) == 2


def test_delete_word(client):
    resp = client.post('/api/sensitive-words', json={'word': 'x', 'replacement': 'X'})
    word_id = resp.get_json()['id']
    resp = client.delete(f'/api/sensitive-words/{word_id}')
    assert resp.status_code == 200
    resp = client.get('/api/sensitive-words')
    assert len(resp.get_json()) == 0


def test_update_word(client):
    resp = client.post('/api/sensitive-words', json={'word': 'old', 'replacement': 'r1'})
    word_id = resp.get_json()['id']
    resp = client.put(f'/api/sensitive-words/{word_id}', json={'word': 'old', 'replacement': 'r2'})
    assert resp.status_code == 200
    resp = client.get('/api/sensitive-words')
    assert resp.get_json()[0]['replacement'] == 'r2'


def test_export_words(client):
    client.post('/api/sensitive-words', json={'word': 'a', 'replacement': 'A'})
    resp = client.get('/api/sensitive-words/export')
    data = json.loads(resp.get_data(as_text=True))
    assert data == {'a': 'A'}


def test_import_words(client):
    payload = {'key1': 'val1', 'key2': 'val2'}
    resp = client.post('/api/sensitive-words/import', json=payload)
    assert resp.status_code == 200
    resp = client.get('/api/sensitive-words')
    words = resp.get_json()
    assert len(words) == 2
```

- [ ] **Step 6: Run API tests to verify they fail**

```bash
cd /Users/jiche/Documents/Qwen && python -m pytest tests/test_api.py -v
```

Expected: FAIL (routes don't exist yet).

- [ ] **Step 7: Implement API routes in app.py**

Update `app.py`:

```python
import os
from flask import Flask, render_template, request, jsonify

from models import init_db, add_word, list_words, delete_word, update_word, export_words, import_words

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
init_db()


@app.route('/')
def index():
    return render_template('index.html')


# --- Sensitive Words API ---

@app.route('/api/sensitive-words', methods=['GET'])
def api_list_words():
    return jsonify(list_words())


@app.route('/api/sensitive-words', methods=['POST'])
def api_add_word():
    data = request.get_json()
    if not data or 'word' not in data or 'replacement' not in data:
        return jsonify({'error': 'word and replacement required'}), 400
    word_id = add_word(data['word'], data['replacement'])
    return jsonify({'id': word_id, 'word': data['word'], 'replacement': data['replacement']}), 201


@app.route('/api/sensitive-words/<int:word_id>', methods=['PUT'])
def api_update_word(word_id):
    data = request.get_json()
    if not data or 'word' not in data or 'replacement' not in data:
        return jsonify({'error': 'word and replacement required'}), 400
    update_word(word_id, data['word'], data['replacement'])
    return jsonify({'id': word_id, 'word': data['word'], 'replacement': data['replacement']})


@app.route('/api/sensitive-words/<int:word_id>', methods=['DELETE'])
def api_delete_word(word_id):
    delete_word(word_id)
    return jsonify({'status': 'ok'})


@app.route('/api/sensitive-words/export', methods=['GET'])
def api_export_words():
    return jsonify(json.loads(export_words()))


@app.route('/api/sensitive-words/import', methods=['POST'])
def api_import_words():
    data = request.get_json()
    if not data or not isinstance(data, dict):
        return jsonify({'error': 'JSON object required'}), 400
    import_words(data)
    return jsonify({'status': 'ok', 'imported': len(data)})


import json  # noqa: E402 (needed for jsonify in export)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

Fix: move `import json` to top:

```python
import os
import json
from flask import Flask, render_template, request, jsonify

from models import init_db, add_word, list_words, delete_word, update_word, export_words, import_words
```

- [ ] **Step 8: Run API tests to verify they pass**

```bash
cd /Users/jiche/Documents/Qwen && python -m pytest tests/test_api.py -v
```

Expected: All 7 tests PASS.

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "feat: add sensitive word DB model and REST API"
```

---

### Task 3: Audit Engine

**Files:**
- Create: `engine/audit_engine.py`
- Create: `tests/test_audit_engine.py`

- [ ] **Step 1: Write failing tests for audit engine**

Create `tests/test_audit_engine.py`:

```python
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from engine.audit_engine import AuditResult, AuditEngine


def test_clean_document():
    engine = AuditEngine({'apple': 'fruit', 'banana': 'tropical'})
    text = "I like fruit and tropical fruits."
    result = engine.scan(text)
    assert result.is_clean is True
    assert result.total_matches == 0


def test_dirty_document():
    engine = AuditEngine({'apple': 'fruit', 'banana': 'tropical'})
    text = "I like apple and banana."
    result = engine.scan(text)
    assert result.is_clean is False
    assert result.total_matches == 2


def test_case_insensitive():
    engine = AuditEngine({'Secret': 'REDACTED'})
    text = "This is SECRET and also secret."
    result = engine.scan(text)
    assert result.is_clean is False
    assert result.total_matches == 2


def test_whitespace_tolerance():
    engine = AuditEngine({'password': '****'})
    text = "This is pass word with space."
    # With whitespace tolerance, "pass word" should match "password"
    result = engine.scan(text)
    # This tests the whitespace tolerance feature
    # Note: basic pattern without whitespace tolerance won't catch this
    # but our engine should support it
    assert result.is_clean is False


def test_no_sensitive_words():
    engine = AuditEngine({})
    text = "This is a clean document."
    result = engine.scan(text)
    assert result.is_clean is True
    assert result.total_matches == 0


def test_missed_words_context():
    engine = AuditEngine({'confidential': '[CONF]})
    text = "This is confidential information."
    result = engine.scan(text)
    assert len(result.missed_words) == 1
    assert 'confidential' in result.missed_words[0]['word'].lower()
    assert 'context' in result.missed_words[0]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/jiche/Documents/Qwen && python -m pytest tests/test_audit_engine.py -v
```

Expected: FAIL with import errors.

- [ ] **Step 3: Implement audit engine**

Create `engine/audit_engine.py`:

```python
"""Audit engine for regex secondary scanning of processed documents."""
import re
from dataclasses import dataclass, field


@dataclass
class AuditResult:
    is_clean: bool = True
    missed_words: list[dict] = field(default_factory=list)
    total_matches: int = 0


class AuditEngine:
    """Scans processed document text for any remaining sensitive word variants."""

    CONTEXT_CHARS = 50

    def __init__(self, replacements: dict[str, str]):
        self.replacements = replacements
        self._patterns = self._build_patterns()

    def _build_patterns(self) -> list[tuple[str, re.Pattern]]:
        """Build regex patterns for each sensitive word with whitespace tolerance."""
        patterns = []
        for word in self.replacements:
            # Insert optional whitespace between each character
            spaced = r'\s*'.join(re.escape(c) for c in word)
            pattern = re.compile(spaced, re.IGNORECASE)
            patterns.append((word, pattern))
        return patterns

    def scan(self, text: str) -> AuditResult:
        """Scan text for remaining sensitive words and return audit result."""
        result = AuditResult()

        for original_word, pattern in self._patterns:
            for match in pattern.finditer(text):
                result.is_clean = False
                result.total_matches += 1
                start = max(0, match.start() - self.CONTEXT_CHARS)
                end = min(len(text), match.end() + self.CONTEXT_CHARS)
                context = text[start:end]
                result.missed_words.append({
                    'word': match.group(),
                    'original': original_word,
                    'context': ('...' if start > 0 else '') + context + ('...' if end < len(text) else ''),
                    'position': match.start(),
                })

        return result
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/jiche/Documents/Qwen && python -m pytest tests/test_audit_engine.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: add audit engine with whitespace-tolerant regex scanning"
```

---

### Task 4: Text Handler

**Files:**
- Create: `engine/txt_handler.py`
- Create: `tests/test_txt_handler.py`

- [ ] **Step 1: Write failing tests for text handler**

Create `tests/test_txt_handler.py`:

```python
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from engine.txt_handler import TxtHandler


def test_basic_replacement(tmp_path):
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("This is secret information that is confidential.")
    handler = TxtHandler()
    result, audit = handler.process(str(txt_file), {'secret': 'REDACTED', 'confidential': '[CONF]'})
    processed_text = result.getvalue().decode('utf-8')
    assert 'secret' not in processed_text.lower()
    assert 'confidential' not in processed_text.lower()
    assert 'REDACTED' in processed_text
    assert '[CONF]' in processed_text


def test_case_insensitive_replacement(tmp_path):
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("This is SECRET and also Secret.")
    handler = TxtHandler()
    result, audit = handler.process(str(txt_file), {'secret': 'REDACTED'})
    processed_text = result.getvalue().decode('utf-8')
    assert 'REDACTED' in processed_text
    assert audit.is_clean is True


def test_no_sensitive_words(tmp_path):
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("This is a clean document.")
    handler = TxtHandler()
    result, audit = handler.process(str(txt_file), {})
    processed_text = result.getvalue().decode('utf-8')
    assert processed_text == "This is a clean document."
    assert audit.is_clean is True
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/jiche/Documents/Qwen && python -m pytest tests/test_txt_handler.py -v
```

Expected: FAIL with import errors.

- [ ] **Step 3: Implement text handler**

Create `engine/txt_handler.py`:

```python
"""Text file (.txt) processing handler with regex-based replacement."""
import re
from io import BytesIO

from engine.audit_engine import AuditEngine, AuditResult


class TxtHandler:
    """Handles .txt file processing: read, replace sensitive words, audit."""

    def process(self, file_path: str, replacements: dict[str, str]) -> tuple[BytesIO, AuditResult]:
        """Process a text file by replacing sensitive words and auditing the result."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Perform replacements using word-boundary regex
        processed = content
        for word, replacement in replacements.items():
            pattern = re.compile(re.escape(word), re.IGNORECASE)
            processed = pattern.sub(replacement, processed)

        result = BytesIO(processed.encode('utf-8'))

        # Audit
        audit_engine = AuditEngine(replacements)
        audit_result = audit_engine.scan(processed)

        return result, audit_result
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/jiche/Documents/Qwen && python -m pytest tests/test_txt_handler.py -v
```

Expected: All 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: add text handler with regex replacement and audit"
```

---

### Task 5: Word (.docx) Handler

**Files:**
- Create: `engine/docx_handler.py`
- Create: `tests/test_docx_handler.py`

- [ ] **Step 1: Write failing tests for docx handler**

Create `tests/test_docx_handler.py`:

```python
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from engine.docx_handler import DocxHandler


def test_basic_replacement_track_changes(tmp_path):
    from docx import Document
    # Create test document
    doc = Document()
    doc.add_paragraph("This is secret information.")
    doc_path = str(tmp_path / "test.docx")
    doc.save(doc_path)

    handler = DocxHandler()
    result, audit = handler.process(doc_path, {'secret': 'REDACTED'})
    processed_content = result.getvalue()

    # Result should be a valid .docx
    assert processed_content is not None
    assert len(processed_content) > 0

    # Audit should confirm no "secret" remains
    assert audit.is_clean is True


def test_replacement_in_table(tmp_path):
    from docx import Document
    doc = Document()
    table = doc.add_table(rows=1, cols=1)
    table.cell(0, 0).text = "confidential data"
    doc_path = str(tmp_path / "test.docx")
    doc.save(doc_path)

    handler = DocxHandler()
    result, audit = handler.process(doc_path, {'confidential': '[CONF]', 'data': '[DATA]'})
    assert audit.is_clean is True


def test_no_sensitive_words(tmp_path):
    from docx import Document
    doc = Document()
    doc.add_paragraph("This is a clean document.")
    doc_path = str(tmp_path / "test.docx")
    doc.save(doc_path)

    handler = DocxHandler()
    result, audit = handler.process(doc_path, {})
    assert audit.is_clean is True
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/jiche/Documents/Qwen && python -m pytest tests/test_docx_handler.py -v
```

Expected: FAIL with import errors.

- [ ] **Step 3: Implement docx handler**

Create `engine/docx_handler.py`:

```python
"""Word document (.docx) processing handler with track-changes support."""
import re
from io import BytesIO
from copy import deepcopy

from docx import Document
from docx.oxml.ns import qn
from docx.text.run import Run

from engine.audit_engine import AuditEngine, AuditResult


class DocxHandler:
    """Handles .docx file processing: replaces sensitive words with track-changes."""

    def process(self, file_path: str, replacements: dict[str, str]) -> tuple[BytesIO, AuditResult]:
        """Process a Word document by replacing sensitive words with tracked deletions/insertions."""
        doc = Document(file_path)

        # Enable track changes
        settings = doc.settings.element
        track_el = settings.find(qn('w:trackRevisions'))
        if track_el is None:
            settings.append(
                Document().settings.element.makeelement(qn('w:trackRevisions'))
            )

        # Process all paragraphs
        for paragraph in doc.paragraphs:
            self._process_runs(paragraph.runs, replacements)

        # Process all tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        self._process_runs(paragraph.runs, replacements)

        # Save to BytesIO
        output = BytesIO()
        doc.save(output)
        output.seek(0)

        # Audit: extract text and scan
        full_text = '\n'.join(p.text for p in doc.paragraphs)
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        full_text += '\n' + p.text

        audit_engine = AuditEngine(replacements)
        audit_result = audit_engine.scan(full_text)

        return output, audit_result

    def _process_runs(self, runs, replacements: dict[str, str]):
        """Process runs in-place, replacing sensitive words with tracked changes."""
        if not runs:
            # No runs, nothing to do
            return

        # Concatenate all run texts to find matches spanning runs
        # For simplicity, process each run individually
        # This handles the common case where sensitive words are within a single run
        new_runs = []
        for run in runs:
            text = run.text
            matched = False
            for word, replacement in replacements.items():
                pattern = re.compile(re.escape(word), re.IGNORECASE)
                match = pattern.search(text)
                if match:
                    matched = True
                    self._split_run_with_revisions(run, match, word, replacement, new_runs)
                    break  # Process one match at a time, re-process remaining
            if not matched:
                new_runs.append(run)

        # Replace runs in paragraph with new runs
        # This is handled by modifying the run's XML directly
        # The runs list is modified in-place via the parent paragraph
        # For python-docx, we need to manipulate the paragraph's XML

    def _split_run_with_revisions(self, run, match, word, replacement, new_runs):
        """Split a run around a match and add tracked deletion/insertion."""
        text = run.text
        before = text[:match.start()]
        after = text[match.end():]

        # Copy run formatting
        r_pr = deepcopy(run.element.rPr) if run.element.rPr is not None else None

        # Before part (unchanged)
        if before:
            new_run = Run(
                run._element.makeelement(qn('w:r')),
                run._parent
            )
            new_run.text = before
            if r_pr is not None:
                new_run._element.append(deepcopy(r_pr))
            new_runs.append(new_run)

        # Deleted text (tracked deletion)
        del_run = Run(
            run._element.makeelement(qn('w:r')),
            run._parent
        )
        del_run.text = match.group()
        if r_pr is not None:
            del_run._element.append(deepcopy(r_pr))
        # Add deletion revision
        del_el = del_run._element.makeelement(qn('w:del'), {
            qn('w:id'): '0',
            qn('w:author'): 'Sanitizer',
            qn('w:date'): '2026-04-14T00:00:00Z'
        })
        del_run._element.append(del_el)
        new_runs.append(del_run)

        # Inserted replacement (tracked insertion)
        ins_run = Run(
            run._element.makeelement(qn('w:r')),
            run._parent
        )
        ins_run.text = replacement
        if r_pr is not None:
            ins_run._element.append(deepcopy(r_pr))
        # Add insertion revision
        ins_el = ins_run._element.makeelement(qn('w:ins'), {
            qn('w:id'): '1',
            qn('w:author'): 'Sanitizer',
            qn('w:date'): '2026-04-14T00:00:00Z'
        })
        ins_run._element.append(ins_el)
        new_runs.append(ins_run)

        # After part (unchanged)
        if after:
            # Check for more matches in after text
            after_run = Run(
                run._element.makeelement(qn('w:r')),
                run._parent
            )
            after_run.text = after
            if r_pr is not None:
                after_run._element.append(deepcopy(r_pr))
            new_runs.append(after_run)
```

The initial implementation above has a known issue: runs aren't being properly replaced in the paragraph. Let me provide a corrected, simpler approach that works with python-docx's API:

```python
"""Word document (.docx) processing handler with track-changes support."""
import re
from io import BytesIO
from copy import deepcopy

from docx import Document
from docx.oxml.ns import qn

from engine.audit_engine import AuditEngine, AuditResult


class DocxHandler:
    """Handles .docx file processing: replaces sensitive words with track-changes."""

    def process(self, file_path: str, replacements: dict[str, str]) -> tuple[BytesIO, AuditResult]:
        """Process a Word document by replacing sensitive words with tracked deletions/insertions."""
        doc = Document(file_path)

        # Enable track changes
        self._enable_track_changes(doc)

        # Process all paragraphs (including table cells)
        self._process_document(doc, replacements)

        # Save to BytesIO
        output = BytesIO()
        doc.save(output)
        output.seek(0)

        # Audit: extract all text and scan
        full_text = self._extract_text(doc)
        audit_engine = AuditEngine(replacements)
        audit_result = audit_engine.scan(full_text)

        return output, audit_result

    def _enable_track_changes(self, doc):
        """Enable track changes in the document settings."""
        settings = doc.settings.element
        track_el = settings.find(qn('w:trackRevisions'))
        if track_el is None:
            new_settings = Document().settings.element
            track_el = new_settings.makeelement(qn('w:trackRevisions'), {})
            settings.append(track_el)

    def _process_document(self, doc, replacements):
        """Process all paragraphs and tables in the document."""
        for paragraph in doc.paragraphs:
            self._process_paragraph(paragraph, replacements)

        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        self._process_paragraph(paragraph, replacements)

    def _process_paragraph(self, paragraph, replacements):
        """Process a single paragraph, replacing sensitive words in runs."""
        # Build combined text to find matches
        full_text = paragraph.text
        if not full_text:
            return

        # Find all sensitive word positions in the full text
        all_matches = []
        for word, replacement in replacements.items():
            for match in re.finditer(re.escape(word), full_text, re.IGNORECASE):
                all_matches.append((match.start(), match.end(), match.group(), replacement))

        if not all_matches:
            return

        all_matches.sort(key=lambda x: x[0])

        # Clear existing runs and rebuild
        # Get run formatting info
        run_formats = []
        for run in paragraph.runs:
            run_formats.append({
                'bold': run.bold,
                'italic': run.italic,
                'underline': run.underline,
                'font': run.font.name,
                'size': run.font.size,
                'color': run.font.color.rgb if run.font.color.rgb else None,
            })

        # Clear paragraph runs
        for run in paragraph.runs:
            run.text = ''

        # Rebuild runs with replacements
        pos = 0
        default_fmt = {'bold': False, 'italic': False, 'underline': None, 'font': None, 'size': None, 'color': None}

        for start, end, original, replacement in all_matches:
            # Text before match
            if start > pos:
                run = paragraph.add_run(full_text[pos:start])
                self._apply_format(run, default_fmt)

            # Deleted original (tracked)
            del_run = paragraph.add_run(original)
            self._mark_deletion(del_run)

            # Replacement (tracked insertion)
            ins_run = paragraph.add_run(replacement)
            self._mark_insertion(ins_run)

            pos = end

        # Remaining text
        if pos < len(full_text):
            run = paragraph.add_run(full_text[pos:])
            self._apply_format(run, default_fmt)

    def _apply_format(self, run, fmt):
        """Apply formatting to a run."""
        if fmt.get('bold') is not None:
            run.bold = fmt['bold']
        if fmt.get('italic') is not None:
            run.italic = fmt['italic']
        if fmt.get('underline') is not None:
            run.underline = fmt['underline']
        if fmt.get('font'):
            run.font.name = fmt['font']
        if fmt.get('size'):
            run.font.size = fmt['size']
        if fmt.get('color'):
            run.font.color.rgb = fmt['color']

    def _mark_deletion(self, run):
        """Mark a run as a tracked deletion."""
        rPr = run.element.makeelement(qn('w:rPr'), {})
        # Add deletion
        del_el = run.element.makeelement(qn('w:del'), {
            qn('w:id'): str(hash(run.text)),
            qn('w:author'): 'DocSanitizer',
            qn('w:date'): '2026-04-14T00:00:00Z'
        })
        run.element.append(del_el)
        run.font.strike = True  # Visual strikethrough as fallback

    def _mark_insertion(self, run):
        """Mark a run as a tracked insertion."""
        ins_el = run.element.makeelement(qn('w:ins'), {
            qn('w:id'): str(hash(run.text) + 1),
            qn('w:author'): 'DocSanitizer',
            qn('w:date'): '2026-04-14T00:00:00Z'
        })
        run.element.append(ins_el)
        run.font.highlight_color = 6  # Yellow highlight

    def _extract_text(self, doc) -> str:
        """Extract all text from a document."""
        parts = []
        for p in doc.paragraphs:
            parts.append(p.text)
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        parts.append(p.text)
        return '\n'.join(parts)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/jiche/Documents/Qwen && python -m pytest tests/test_docx_handler.py -v
```

Expected: All 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: add Word handler with track-changes replacement"
```

---

### Task 6: PDF Handler

**Files:**
- Create: `engine/pdf_handler.py`
- Create: `tests/test_pdf_handler.py`

- [ ] **Step 1: Write failing tests for PDF handler**

Create `tests/test_pdf_handler.py`:

```python
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from engine.pdf_handler import PdfHandler


def test_basic_replacement(tmp_path):
    import fitz
    # Create test PDF
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "This is secret information.")
    pdf_path = str(tmp_path / "test.pdf")
    doc.save(pdf_path)
    doc.close()

    handler = PdfHandler()
    result, audit = handler.process(pdf_path, {'secret': 'REDACTED'})
    assert result is not None
    assert audit.is_clean is True


def test_no_sensitive_words(tmp_path):
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "This is a clean document.")
    pdf_path = str(tmp_path / "test.pdf")
    doc.save(pdf_path)
    doc.close()

    handler = PdfHandler()
    result, audit = handler.process(pdf_path, {})
    assert audit.is_clean is True
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/jiche/Documents/Qwen && python -m pytest tests/test_pdf_handler.py -v
```

Expected: FAIL with import errors.

- [ ] **Step 3: Implement PDF handler**

Create `engine/pdf_handler.py`:

```python
"""PDF file processing handler using PyMuPDF and reportlab."""
import re
from io import BytesIO

import fitz  # PyMuPDF
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas as rl_canvas

from engine.audit_engine import AuditEngine, AuditResult


class PdfHandler:
    """Handles .pdf file processing: extract text, replace, rebuild PDF."""

    def process(self, file_path: str, replacements: dict[str, str]) -> tuple[BytesIO, AuditResult]:
        """Process a PDF file by extracting text, replacing sensitive words, and rebuilding."""
        # Extract text page by page
        doc = fitz.open(file_path)
        pages_text = []
        page_sizes = []

        for page in doc:
            text = page.get_text()
            pages_text.append(text)
            # Get page dimensions
            rect = page.rect
            page_sizes.append((rect.width, rect.height))

        doc.close()

        # Perform replacements
        processed_pages = []
        for text in pages_text:
            processed = text
            for word, replacement in replacements.items():
                pattern = re.compile(re.escape(word), re.IGNORECASE)
                processed = pattern.sub(replacement, processed)
            processed_pages.append(processed)

        # Full text for audit
        full_text = '\n'.join(processed_pages)

        # Audit
        audit_engine = AuditEngine(replacements)
        audit_result = audit_engine.scan(full_text)

        # Rebuild PDF
        output = BytesIO()
        for i, (text, (width, height)) in enumerate(zip(processed_pages, page_sizes)):
            if i == 0:
                c = rl_canvas.Canvas(output, pagesize=(width, height))
            else:
                c.showPage()
                c = rl_canvas.Canvas(output, pagesize=(width, height))

            # Place text at standard position (top-left with margin)
            c.setFont("Helvetica", 12)
            y = height - 72  # 1 inch margin from top
            lines = text.split('\n')
            for line in lines:
                if line.strip():
                    c.drawString(72, y, line.strip())
                y -= 14  # line spacing
                if y < 72:
                    c.showPage()
                    c = rl_canvas.Canvas(output, pagesize=(width, height))
                    y = height - 72

        c.save()
        output.seek(0)

        return output, audit_result
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/jiche/Documents/Qwen && python -m pytest tests/test_pdf_handler.py -v
```

Expected: All 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: add PDF handler with extract/replace/rebuild"
```

---

### Task 7: Processing Endpoint + Handler Factory

**Files:**
- Modify: `engine/__init__.py`
- Modify: `app.py`
- Create: `templates/index.html`
- Create: `static/css/style.css`
- Create: `static/js/main.js`

- [ ] **Step 1: Create handler factory**

Update `engine/__init__.py`:

```python
"""Document processing engine handlers."""
from engine.docx_handler import DocxHandler
from engine.txt_handler import TxtHandler
from engine.pdf_handler import PdfHandler
from engine.audit_engine import AuditEngine, AuditResult


def get_handler(file_path: str):
    """Get the appropriate handler based on file extension."""
    ext = file_path.rsplit('.', 1)[-1].lower()
    handlers = {
        'docx': DocxHandler(),
        'txt': TxtHandler(),
        'pdf': PdfHandler(),
    }
    handler = handlers.get(ext)
    if handler is None:
        raise ValueError(f"Unsupported file type: .{ext}")
    return handler
```

- [ ] **Step 2: Write failing test for processing endpoint**

Add to `tests/test_api.py`:

```python
def test_process_txt(client, tmp_path):
    import os
    # Add a sensitive word
    client.post('/api/sensitive-words', json={'word': 'secret', 'replacement': 'REDACTED'})

    # Create test file
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("This is secret info.")

    # Upload and process
    with open(txt_file, 'rb') as f:
        resp = client.post(
            '/api/process',
            data={'file': (f, 'test.txt')},
            content_type='multipart/form-data'
        )
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'download_url' in data
    assert 'audit' in data
    assert data['audit']['is_clean'] is True


def test_process_unsupported_type(client, tmp_path):
    bad_file = tmp_path / "test.xls"
    bad_file.write_text("test")
    with open(bad_file, 'rb') as f:
        resp = client.post(
            '/api/process',
            data={'file': (f, 'test.xls')},
            content_type='multipart/form-data'
        )
    assert resp.status_code == 400
```

- [ ] **Step 3: Implement process endpoint**

Add to `app.py`:

```python
import tempfile
import uuid
from flask import send_file, after_this_request

# ... existing imports ...

# Store processed files temporarily
PROCESSED_DIR = os.path.join(os.path.dirname(__file__), 'processed')
os.makedirs(PROCESSED_DIR, exist_ok=True)


@app.route('/api/process', methods=['POST'])
def api_process():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Get sensitive words from DB
    replacements = {w['word']: w['replacement'] for w in list_words()}
    if not replacements:
        return jsonify({'error': 'No sensitive words configured'}), 400

    # Validate file type
    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in ('docx', 'txt', 'pdf'):
        return jsonify({'error': f'Unsupported file type: .{ext}'}), 400

    # Save uploaded file
    upload_id = str(uuid.uuid4())
    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{upload_id}.{ext}")
    file.save(upload_path)

    try:
        from engine import get_handler
        handler = get_handler(upload_path)
        result, audit_result = handler.process(upload_path, replacements)

        # Save processed result
        output_filename = f"processed_{upload_id}.{ext}"
        output_path = os.path.join(PROCESSED_DIR, output_filename)
        with open(output_path, 'wb') as f:
            f.write(result.getvalue())

        # Save audit report
        audit_path = os.path.join(PROCESSED_DIR, f"audit_{upload_id}.json")
        with open(audit_path, 'w') as f:
            json.dump(audit_result.__dict__, f, default=str)

        return jsonify({
            'download_url': f'/api/download/{output_filename}',
            'audit_url': f'/api/download/audit_{upload_id}.json',
            'audit': {
                'is_clean': audit_result.is_clean,
                'total_matches': audit_result.total_matches,
                'missed_words': audit_result.missed_words[:10],  # Limit for display
            }
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # Clean up uploaded file
        if os.path.exists(upload_path):
            os.remove(upload_path)


@app.route('/api/download/<filename>')
def api_download(filename):
    filepath = os.path.join(PROCESSED_DIR, filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    return send_file(filepath, as_attachment=True, download_name=filename)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/jiche/Documents/Qwen && python -m pytest tests/test_api.py -v
```

Expected: All tests PASS (including new ones).

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: add processing endpoint with handler factory"
```

---

### Task 8: Frontend UI

**Files:**
- Create: `templates/index.html`
- Create: `static/css/style.css`
- Create: `static/js/main.js`

- [ ] **Step 1: Create HTML template**

Create `templates/index.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Document Sanitizer</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
    <div class="container py-4">
        <h1 class="mb-4">🔒 Document Sanitizer</h1>

        <div class="row g-4">
            <!-- Sensitive Words Panel -->
            <div class="col-md-5">
                <div class="card">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h5 class="mb-0">Sensitive Words</h5>
                        <div>
                            <button class="btn btn-sm btn-outline-secondary" onclick="importWords()">Import</button>
                            <button class="btn btn-sm btn-outline-secondary" onclick="exportWords()">Export</button>
                        </div>
                    </div>
                    <div class="card-body">
                        <div class="input-group mb-3">
                            <input type="text" id="newWord" class="form-control" placeholder="Sensitive word">
                            <input type="text" id="newReplacement" class="form-control" placeholder="Replacement">
                            <button class="btn btn-primary" onclick="addWord()">Add</button>
                        </div>
                        <table class="table table-sm">
                            <thead><tr><th>Word</th><th>Replacement</th><th></th></tr></thead>
                            <tbody id="wordsTable"></tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- Upload & Process Panel -->
            <div class="col-md-7">
                <div class="card">
                    <div class="card-header"><h5 class="mb-0">Upload & Process</h5></div>
                    <div class="card-body">
                        <div id="dropZone" class="border rounded p-4 text-center mb-3">
                            <p class="mb-0 text-muted">Drag & drop a .docx, .txt, or .pdf file here, or</p>
                            <input type="file" id="fileInput" accept=".docx,.txt,.pdf" class="form-control mt-2">
                        </div>
                        <button id="processBtn" class="btn btn-success w-100" onclick="processDocument()" disabled>
                            Process Document
                        </button>
                        <div id="progress" class="mt-3 d-none">
                            <div class="progress"><div class="progress-bar progress-bar-striped progress-bar-animated" style="width:100%">Processing...</div></div>
                        </div>
                        <div id="auditResult" class="mt-3 d-none"></div>
                        <div id="downloadLinks" class="mt-3 d-none"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <input type="file" id="importInput" accept=".json" style="display:none" onchange="handleImport(event)">
    <script src="/static/js/main.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create CSS**

Create `static/css/style.css`:

```css
#dropZone.dragover {
    background-color: #e9ecef;
    border-color: #0d6efd !important;
}

#dropZone p {
    margin-bottom: 0.5rem;
}

.table td {
    vertical-align: middle;
}

#auditResult .alert {
    margin-bottom: 0.5rem;
}
```

- [ ] **Step 3: Create JavaScript**

Create `static/js/main.js`:

```javascript
const API = '/api/sensitive-words';
let selectedFile = null;

// --- Sensitive Words Management ---

async function loadWords() {
    const resp = await fetch(API);
    const words = await resp.json();
    const tbody = document.getElementById('wordsTable');
    tbody.innerHTML = '';
    words.forEach(w => {
        tbody.innerHTML += `
            <tr>
                <td><input class="form-control form-control-sm" value="${escapeHtml(w.word)}" onchange="updateWord(${w.id}, this, this.parentElement.previousElementSibling.firstElementChild)"></td>
                <td><input class="form-control form-control-sm" value="${escapeHtml(w.replacement)}" onchange="updateWord(${w.id}, this.previousElementSibling.firstElementChild, this)"></td>
                <td><button class="btn btn-sm btn-danger" onclick="deleteWord(${w.id})">&times;</button></td>
            </tr>`;
    });
    updateProcessButton();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function addWord() {
    const word = document.getElementById('newWord').value.trim();
    const replacement = document.getElementById('newReplacement').value.trim();
    if (!word || !replacement) return alert('Both fields required');

    await fetch(API, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({word, replacement})
    });
    document.getElementById('newWord').value = '';
    document.getElementById('newReplacement').value = '';
    await loadWords();
}

async function updateWord(id, wordInput, replacementInput) {
    await fetch(`${API}/${id}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({word: wordInput.value, replacement: replacementInput.value})
    });
}

async function deleteWord(id) {
    await fetch(`${API}/${id}`, {method: 'DELETE'});
    await loadWords();
}

async function exportWords() {
    const resp = await fetch(`${API}/export`);
    const data = await resp.json();
    const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'sensitive_words.json';
    a.click();
    URL.revokeObjectURL(url);
}

function importWords() {
    document.getElementById('importInput').click();
}

async function handleImport(event) {
    const file = event.target.files[0];
    if (!file) return;
    const text = await file.text();
    const data = JSON.parse(text);
    await fetch(`${API}/import`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });
    await loadWords();
    event.target.value = '';
}

// --- File Upload & Processing ---

const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');

dropZone.addEventListener('dragover', e => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length) {
        selectedFile = e.dataTransfer.files[0];
        fileInput.files = e.dataTransfer.files;
        updateProcessButton();
    }
});

fileInput.addEventListener('change', () => {
    if (fileInput.files.length) {
        selectedFile = fileInput.files[0];
        updateProcessButton();
    }
});

function updateProcessButton() {
    const words = document.getElementById('wordsTable').children.length;
    document.getElementById('processBtn').disabled = !(selectedFile && words > 0);
}

async function processDocument() {
    if (!selectedFile) return;

    const progress = document.getElementById('progress');
    const auditResult = document.getElementById('auditResult');
    const downloadLinks = document.getElementById('downloadLinks');

    progress.classList.remove('d-none');
    auditResult.classList.add('d-none');
    downloadLinks.classList.add('d-none');

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
        const resp = await fetch('/api/process', {method: 'POST', body: formData});
        const data = await resp.json();

        if (data.error) {
            auditResult.innerHTML = `<div class="alert alert-danger">${escapeHtml(data.error)}</div>`;
            auditResult.classList.remove('d-none');
            return;
        }

        // Show audit
        const audit = data.audit;
        if (audit.is_clean) {
            auditResult.innerHTML = `<div class="alert alert-success">✅ Audit passed: no sensitive words remaining.</div>`;
        } else {
            auditResult.innerHTML = `
                <div class="alert alert-warning">
                    ⚠️ Audit found ${audit.total_matches} remaining match(es):
                    <ul>${audit.missed_words.map(m => `<li><strong>${escapeHtml(m.word)}</strong> — ${escapeHtml(m.context)}</li>`).join('')}</ul>
                </div>`;
        }
        auditResult.classList.remove('d-none');

        // Show download links
        downloadLinks.innerHTML = `
            <a href="${data.download_url}" class="btn btn-primary me-2">Download Processed Document</a>
            <a href="${data.audit_url}" class="btn btn-outline-secondary">Download Audit Report</a>`;
        downloadLinks.classList.remove('d-none');

    } catch (err) {
        auditResult.innerHTML = `<div class="alert alert-danger">Error: ${escapeHtml(err.message)}</div>`;
        auditResult.classList.remove('d-none');
    } finally {
        progress.classList.add('d-none');
    }
}

// Init
loadWords();
```

- [ ] **Step 4: Manual verification**

```bash
cd /Users/jiche/Documents/Qwen && python app.py &
sleep 2
echo "Open http://localhost:5000 in browser"
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: add Bootstrap frontend with upload, config, and process UI"
```

---

### Task 9: Integration Test + Final Polish

**Files:**
- Create: `tests/test_integration.py`
- Modify: `.gitignore` (if needed)

- [ ] **Step 1: Write integration test**

Create `tests/test_integration.py`:

```python
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from app import app
from models import init_db


def test_full_pipeline_txt(client, tmp_path):
    """Test full pipeline: add words -> upload -> process -> download."""
    # Add sensitive words
    client.post('/api/sensitive-words', json={'word': 'secret', 'replacement': 'REDACTED'})
    client.post('/api/sensitive-words', json={'word': 'password', 'replacement': '****'})

    # Create test file
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("My secret password is 12345.")

    # Process
    with open(txt_file, 'rb') as f:
        resp = client.post('/api/process', data={'file': (f, 'test.txt')}, content_type='multipart/form-data')

    assert resp.status_code == 200
    data = resp.get_json()
    assert data['audit']['is_clean'] is True
    assert 'download_url' in data

    # Download processed file
    resp = client.get(data['download_url'])
    assert resp.status_code == 200
    content = resp.get_data(as_text=True)
    assert 'secret' not in content.lower()
    assert 'password' not in content.lower()
    assert 'REDACTED' in content


def test_full_pipeline_docx(client, tmp_path):
    """Test full pipeline with .docx file."""
    from docx import Document
    client.post('/api/sensitive-words', json={'word': 'confidential', 'replacement': '[CONF]'})

    doc = Document()
    doc.add_paragraph("This is confidential material.")
    doc_path = str(tmp_path / "test.docx")
    doc.save(doc_path)

    with open(doc_path, 'rb') as f:
        resp = client.post('/api/process', data={'file': (f, 'test.docx')}, content_type='multipart/form-data')

    assert resp.status_code == 200
    data = resp.get_json()
    assert data['audit']['is_clean'] is True
    assert 'download_url' in data
```

- [ ] **Step 2: Run all tests**

```bash
cd /Users/jiche/Documents/Qwen && python -m pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat: add integration tests and finalize"
```

---

## Self-Review

### 1. Spec Coverage Check

| Spec Requirement | Implementing Task | Status |
|---|---|---|
| Flask + Bootstrap frontend | Task 8 | ✅ |
| .docx with track-changes | Task 5 | ✅ |
| .txt processing | Task 4 | ✅ |
| .pdf processing | Task 6 | ✅ |
| Sensitive word CRUD API | Task 2 | ✅ |
| Import/export JSON | Task 2, Task 8 | ✅ |
| Audit engine (regex secondary scan) | Task 3 | ✅ |
| Whitespace tolerance in audit | Task 3 | ✅ |
| Error handling (unsupported type, no words, etc.) | Task 7, Task 8 | ✅ |
| SQLite storage | Task 2 | ✅ |
| Testing strategy (unit + integration) | All tasks, Task 9 | ✅ |

### 2. Placeholder Scan
No "TBD", "TODO", or incomplete steps found.

### 3. Type Consistency
- `AuditResult` dataclass is consistent across `audit_engine.py` and all handlers
- All handlers return `tuple[BytesIO, AuditResult]`
- API responses use consistent JSON structure

### 4. Potential Issues
- The docx handler's track-changes XML manipulation may need adjustment based on how `python-docx` actually handles revision marks. The `_mark_deletion` and `_mark_insertion` methods use direct XML element insertion which is the correct approach, but the exact `w:del`/`w:ins` element structure may need minor tuning during implementation.
- The PDF handler rebuilds the PDF from scratch, losing original formatting. This is acceptable per the spec's note about formatting limitations.

---

Plan complete and saved to `docs/superpowers/plans/2026-04-14-doc-sanitizer-plan.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints for review

Which approach?
