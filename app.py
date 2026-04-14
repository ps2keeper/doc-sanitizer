import os
import json
import uuid
import tempfile
from flask import Flask, render_template, request, jsonify, send_file

from models import (
    init_db, add_word, list_words, delete_word, update_word,
    get_word, export_words, import_words, clear_all,
    list_enabled_words, update_enabled
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
    imported = import_words(data)
    return jsonify({'status': 'ok', 'imported': imported})


@app.route('/api/sensitive-words/clear', methods=['POST'])
def api_clear_words():
    count = clear_all()
    return jsonify({'status': 'ok', 'cleared': count})


@app.route('/api/sensitive-words/<int:word_id>/toggle', methods=['POST'])
def api_toggle_word(word_id):
    data = request.get_json() or {}
    enabled = data.get('enabled', True)
    if get_word(word_id) is None:
        return jsonify({'error': '词条不存在'}), 404
    update_enabled(word_id, enabled)
    return jsonify({'status': 'ok', 'id': word_id, 'enabled': enabled})


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

    # Get sensitive words from DB (only enabled ones)
    replacements = {w['word']: w['replacement'] for w in list_enabled_words()}
    if not replacements:
        return jsonify({'error': '没有配置可用的敏感词，请先添加并启用'}), 400

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
        result, audit_result, replacement_counts = handler.process(upload_path, replacements)

        # Save processed result
        output_filename = f"processed_{upload_id}.{ext}"
        output_path = os.path.join(PROCESSED_DIR, output_filename)
        with open(output_path, 'wb') as f:
            f.write(result.getvalue())

        # Save audit report
        audit_path = os.path.join(PROCESSED_DIR, f"audit_{upload_id}.json")
        with open(audit_path, 'w') as f:
            json.dump({
                'is_clean': audit_result.is_clean,
                'total_matches': audit_result.total_matches,
                'missed_words': audit_result.missed_words,
            }, f, default=str)

        return jsonify({
            'download_url': f'/api/download/{output_filename}',
            'audit_url': f'/api/download/audit_{upload_id}.json',
            'total_replacements': sum(replacement_counts.values()),
            'replacement_counts': replacement_counts,
            'audit': {
                'is_clean': audit_result.is_clean,
                'total_matches': audit_result.total_matches,
                'missed_words': audit_result.missed_words[:10],
            }
        })

    except Exception as e:
        import logging
        logging.exception('Error processing document')
        return jsonify({'error': 'Internal server error during processing'}), 500
    finally:
        # Clean up uploaded file
        if os.path.exists(upload_path):
            os.remove(upload_path)


@app.route('/api/download/<filename>')
def api_download(filename):
    filepath = os.path.realpath(os.path.join(PROCESSED_DIR, filename))
    if not filepath.startswith(os.path.realpath(PROCESSED_DIR)):
        return jsonify({'error': 'Invalid filename'}), 400
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    return send_file(filepath, as_attachment=True, download_name=filename)


if __name__ == '__main__':
    import socket
    # Get local IP for LAN access
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = '127.0.0.1'
    finally:
        s.close()

    print(f"\n{'='*50}")
    print(f"  文档敏感词替换工具已启动")
    print(f"{'='*50}")
    print(f"  本机访问: http://127.0.0.1:5000")
    print(f"  同网段访问: http://{local_ip}:5000")
    print(f"{'='*50}\n")

    app.run(debug=True, host='0.0.0.0', port=5000)
