"""Database models for sensitive word management."""
import os
import sqlite3

def get_db():
    db_path = os.environ.get('DATABASE_PATH', 'sensitive_words.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sensitive_words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL UNIQUE,
            replacement TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


def add_word(word: str, replacement: str) -> int:
    conn = get_db()
    try:
        cursor = conn.execute(
            'INSERT INTO sensitive_words (word, replacement) VALUES (?, ?)',
            (word, replacement)
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        raise ValueError(f"Word '{word}' already exists")
    finally:
        conn.close()


def list_words() -> list[dict]:
    conn = get_db()
    rows = conn.execute('SELECT * FROM sensitive_words ORDER BY created_at').fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_word(word_id: int) -> bool:
    """Delete a word by ID. Returns True if a row was deleted, False if not found."""
    conn = get_db()
    cursor = conn.execute('DELETE FROM sensitive_words WHERE id = ?', (word_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def update_word(word_id: int, word: str, replacement: str) -> bool:
    """Update a word. Returns True if updated, False if not found."""
    conn = get_db()
    cursor = conn.execute(
        'UPDATE sensitive_words SET word = ?, replacement = ? WHERE id = ?',
        (word, replacement, word_id)
    )
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return updated


def get_word(word_id: int) -> dict | None:
    """Get a single word by ID. Returns None if not found."""
    conn = get_db()
    row = conn.execute('SELECT * FROM sensitive_words WHERE id = ?', (word_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def export_words() -> str:
    import json
    words = list_words()
    return json.dumps({w['word']: w['replacement'] for w in words}, indent=2)


def import_words(data: dict):
    for word, replacement in data.items():
        try:
            add_word(word, replacement)
        except ValueError:
            pass  # Skip duplicates
