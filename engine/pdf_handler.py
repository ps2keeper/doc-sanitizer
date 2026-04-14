"""PDF file processing handler using PyMuPDF."""
import re
from io import BytesIO

import fitz  # PyMuPDF

from engine.audit_engine import AuditEngine, AuditResult


class PdfHandler:
    """Handles .pdf file processing: replace sensitive words in-place preserving original layout.

    Uses PyMuPDF's text search to find each occurrence, then adds a redaction
    annotation with the replacement text using the built-in Chinese font.
    When redactions are applied, the original text is removed and the
    replacement text is inserted at the exact same position.
    """

    def process(self, file_path: str, replacements: dict[str, str], track_changes: bool = True) -> tuple[BytesIO, AuditResult, dict[str, int]]:
        """Process a PDF by replacing sensitive words while preserving original layout."""
        doc = fitz.open(file_path)

        # Count all matches first across all pages
        replacement_counts = {}
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            for word in replacements:
                count = len(re.findall(re.escape(word), text, re.IGNORECASE))
                if count > 0:
                    replacement_counts[word] = replacement_counts.get(word, 0) + count

        # Perform replacements page by page
        for page_num in range(len(doc)):
            page = doc[page_num]
            self._replace_on_page(page, replacements)

        # Full text for audit
        full_text = '\n'.join(doc[page_num].get_text() for page_num in range(len(doc)))

        # Audit
        audit_engine = AuditEngine(replacements)
        audit_result = audit_engine.scan(full_text)

        # Save
        output = BytesIO()
        doc.save(output)
        output.seek(0)
        doc.close()

        return output, audit_result, replacement_counts

    def _replace_on_page(self, page, replacements: dict[str, str]):
        """Replace sensitive words on a single page using redaction annotations."""
        for word, replacement in replacements.items():
            instances = page.search_for(word)

            if not instances:
                continue

            for rect in instances:
                # Calculate font size from the rect height
                font_size = max(6, int(rect.height * 0.8))

                # Add redaction annotation with replacement text
                # The 'text' parameter sets the replacement text
                # fontname='china-s' provides Chinese Simplified font support
                page.add_redact_annot(
                    rect,
                    text=replacement,
                    fontname='china-s',
                    fontsize=font_size,
                    fill=(1, 1, 1),       # White background
                    text_color=(0, 0, 0), # Black text
                    cross_out=False,      # No strikethrough
                )

        # Apply all redactions: removes original text and inserts replacement
        page.apply_redactions()
