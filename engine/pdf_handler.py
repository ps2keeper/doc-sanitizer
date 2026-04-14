"""PDF file processing handler using PyMuPDF."""
import re
from io import BytesIO

import fitz  # PyMuPDF

from engine.audit_engine import AuditEngine, AuditResult


class PdfHandler:
    """Handles .pdf file processing: replace sensitive words in-place preserving original layout.

    Strategy:
    1. Find text positions using search_for (returns screen coordinates)
    2. Insert replacement text at the CORRECT position (convert to PDF coords)
    3. Add redaction annotation to remove the original text
    4. Apply redactions
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
        """Replace sensitive words on a single page."""
        page_height = page.rect.height

        for word, replacement in replacements.items():
            instances = page.search_for(word)

            if not instances:
                continue

            for rect in instances:
                # Convert screen coords to PDF coords (flip y)
                pdf_y0 = page_height - rect.y0
                pdf_y1 = page_height - rect.y1
                # In PDF coords, y0 > y1 (y0 is top, y1 is bottom from page bottom)
                pdf_baseline = pdf_y1  # baseline is at the bottom of the text box

                # Calculate font size from the rect height
                font_size = max(6, int(rect.height * 0.8))

                # Step 1: Insert replacement text at the correct position (PDF coords)
                page.insert_text(
                    fitz.Point(rect.x0, pdf_baseline + font_size * 0.15),
                    replacement,
                    fontsize=font_size,
                    color=(0, 0, 0),
                    fontname="china-s",
                )

                # Step 2: Add redaction annotation to remove original text
                page.add_redact_annot(rect)

        # Step 3: Apply all redactions to remove original text
        page.apply_redactions()
