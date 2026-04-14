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
