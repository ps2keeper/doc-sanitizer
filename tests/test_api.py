import os
import sys
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from app import app
from models import init_db


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


def test_process_txt(client, tmp_path):
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


def test_process_no_sensitive_words_configured(client, tmp_path):
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("This is some text.")
    with open(txt_file, 'rb') as f:
        resp = client.post(
            '/api/process',
            data={'file': (f, 'test.txt')},
            content_type='multipart/form-data'
        )
    assert resp.status_code == 400
