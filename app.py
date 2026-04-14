import os
import json
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


if __name__ == '__main__':
    app.run(debug=True, port=5000)
