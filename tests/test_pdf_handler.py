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
