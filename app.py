import os
import json
from flask import Flask, render_template, request, jsonify

from models import (
    init_db, add_word, list_words, delete_word, update_word,
    get_word, export_words, import_words
)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
init_db()


@app.route('/')
def index():
    return render_template('index.html')


def _validate_word_data(data):
    """Validate word/replacement are non-empty strings."""
    if not data or not isinstance(data, dict):
        return None, 'Invalid request body'
    word = data.get('word')
    replacement = data.get('replacement')
    if not isinstance(word, str) or not word.strip():
        return None, 'word must be a non-empty string'
    if not isinstance(replacement, str):
        return None, 'replacement must be a string'
    return word.strip(), replacement


# --- Sensitive Words API ---

@app.route('/api/sensitive-words', methods=['GET'])
def api_list_words():
    return jsonify(list_words())


@app.route('/api/sensitive-words', methods=['POST'])
def api_add_word():
    data = request.get_json()
    result = _validate_word_data(data)
    if result is None:
        return jsonify({'error': 'Invalid request body'}), 400
    word, replacement = result
    try:
        word_id = add_word(word, replacement)
    except ValueError as e:
        return jsonify({'error': str(e)}), 409
    return jsonify({'id': word_id, 'word': word, 'replacement': replacement}), 201


@app.route('/api/sensitive-words/<int:word_id>', methods=['PUT'])
def api_update_word(word_id):
    data = request.get_json()
    result = _validate_word_data(data)
    if result is None:
        return jsonify({'error': 'Invalid request body'}), 400
    word, replacement = result
    if get_word(word_id) is None:
        return jsonify({'error': 'word not found'}), 404
    update_word(word_id, word, replacement)
    return jsonify({'id': word_id, 'word': word, 'replacement': replacement})


@app.route('/api/sensitive-words/<int:word_id>', methods=['DELETE'])
def api_delete_word(word_id):
    if get_word(word_id) is None:
        return jsonify({'error': 'word not found'}), 404
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


if __name__ == '__main__':
    app.run(debug=True, port=5000)
