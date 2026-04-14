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
    result = engine.scan(text)
    assert result.is_clean is False


def test_no_sensitive_words():
    engine = AuditEngine({})
    text = "This is a clean document."
    result = engine.scan(text)
    assert result.is_clean is True
    assert result.total_matches == 0


def test_missed_words_context():
    engine = AuditEngine({'confidential': '[CONF]'})
    text = "This is confidential information."
    result = engine.scan(text)
    assert len(result.missed_words) == 1
    assert 'confidential' in result.missed_words[0]['word'].lower()
    assert 'context' in result.missed_words[0]
