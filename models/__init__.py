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
