"""PDF file processing handler using PyMuPDF and reportlab."""
import re
from io import BytesIO

import fitz  # PyMuPDF
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas as rl_canvas

from engine.audit_engine import AuditEngine, AuditResult


class PdfHandler:
    """Handles .pdf file processing: extract text, replace, rebuild PDF."""

    def process(self, file_path: str, replacements: dict[str, str]) -> tuple[BytesIO, AuditResult]:
        """Process a PDF file by extracting text, replacing sensitive words, and rebuilding."""
        # Extract text page by page
        doc = fitz.open(file_path)
        pages_text = []
        page_sizes = []

        for page in doc:
            text = page.get_text()
            pages_text.append(text)
            # Get page dimensions
            rect = page.rect
            page_sizes.append((rect.width, rect.height))

        doc.close()

        # Perform replacements
        processed_pages = []
        for text in pages_text:
            processed = text
            for word, replacement in replacements.items():
                pattern = re.compile(re.escape(word), re.IGNORECASE)
                processed = pattern.sub(replacement, processed)
            processed_pages.append(processed)

        # Full text for audit
        full_text = '\n'.join(processed_pages)

        # Audit
        audit_engine = AuditEngine(replacements)
        audit_result = audit_engine.scan(full_text)

        # Rebuild PDF
        output = BytesIO()
        c = None
        for i, (text, (width, height)) in enumerate(zip(processed_pages, page_sizes)):
            if c is not None:
                c.showPage()
            c = rl_canvas.Canvas(output, pagesize=(width, height))

            # Place text at standard position (top-left with margin)
            c.setFont("Helvetica", 12)
            y = height - 72  # 1 inch margin from top
            lines = text.split('\n')
            for line in lines:
                if line.strip():
                    c.drawString(72, y, line.strip())
                y -= 14  # line spacing
                if y < 72:
                    c.showPage()
                    c = rl_canvas.Canvas(output, pagesize=(width, height))
                    y = height - 72

        if c is not None:
            c.save()
        output.seek(0)

        return output, audit_result
