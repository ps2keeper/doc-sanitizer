import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from engine.txt_handler import TxtHandler


def test_basic_replacement(tmp_path):
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("This is secret information that is confidential.")
    handler = TxtHandler()
    result, audit, _counts = handler.process(str(txt_file), {'secret': 'REDACTED', 'confidential': '[CONF]'})
    processed_text = result.getvalue().decode('utf-8')
    assert 'secret' not in processed_text.lower()
    assert 'confidential' not in processed_text.lower()
    assert 'REDACTED' in processed_text
    assert '[CONF]' in processed_text


def test_case_insensitive_replacement(tmp_path):
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("This is SECRET and also Secret.")
    handler = TxtHandler()
    result, audit, _counts = handler.process(str(txt_file), {'secret': 'REDACTED'})
    processed_text = result.getvalue().decode('utf-8')
    assert 'REDACTED' in processed_text
    assert audit.is_clean is True


def test_no_sensitive_words(tmp_path):
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("This is a clean document.")
    handler = TxtHandler()
    result, audit, _counts = handler.process(str(txt_file), {})
    processed_text = result.getvalue().decode('utf-8')
    assert processed_text == "This is a clean document."
    assert audit.is_clean is True
