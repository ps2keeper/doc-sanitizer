"""Word document (.docx) processing handler with track-changes support."""
import re
from io import BytesIO

from docx import Document
from docx.oxml.ns import qn
from docx.shared import RGBColor

from engine.audit_engine import AuditEngine, AuditResult


class DocxHandler:
    """Handles .docx file processing: replaces sensitive words with track-changes."""

    def __init__(self):
        self._revision_id = 0

    def _next_id(self) -> str:
        self._revision_id += 1
        return str(self._revision_id)

    def process(self, file_path: str, replacements: dict[str, str]) -> tuple[BytesIO, AuditResult]:
        """Process a Word document by replacing sensitive words with tracked deletions/insertions."""
        self._revision_id = 0
        doc = Document(file_path)

        # Enable track changes
        self._enable_track_changes(doc)

        # Process all paragraphs (including table cells)
        self._process_document(doc, replacements)

        # Save to BytesIO
        output = BytesIO()
        doc.save(output)
        output.seek(0)

        # Audit: extract all text and scan
        full_text = self._extract_text(doc)
        audit_engine = AuditEngine(replacements)
        audit_result = audit_engine.scan(full_text)

        return output, audit_result

    def _enable_track_changes(self, doc):
        """Enable track changes in the document settings."""
        settings = doc.settings.element
        track_el = settings.find(qn('w:trackRevisions'))
        if track_el is None:
            new_settings = Document().settings.element
            track_el = new_settings.makeelement(qn('w:trackRevisions'), {})
            settings.append(track_el)

    def _process_document(self, doc, replacements):
        """Process all paragraphs and tables in the document."""
        for paragraph in doc.paragraphs:
            self._process_paragraph(paragraph, replacements)

        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        self._process_paragraph(paragraph, replacements)

    def _process_paragraph(self, paragraph, replacements):
        """Process a single paragraph, replacing sensitive words with tracked changes."""
        full_text = paragraph.text
        if not full_text:
            return

        # Find all sensitive word positions in the full text
        all_matches = []
        for word, replacement in replacements.items():
            for match in re.finditer(re.escape(word), full_text, re.IGNORECASE):
                all_matches.append((match.start(), match.end(), match.group(), replacement))

        if not all_matches:
            return

        all_matches.sort(key=lambda x: x[0])

        # Rebuild the paragraph's XML children
        self._rebuild_paragraph(paragraph, full_text, all_matches)

    def _rebuild_paragraph(self, paragraph, full_text: str, matches: list):
        """Rebuild paragraph XML: keep non-matching text as normal runs, wrap matches in w:del/w:ins."""
        # Remove all existing child elements
        for child in list(paragraph._p):
            paragraph._p.remove(child)

        pos = 0
        for start, end, original, replacement in matches:
            # Text before match -> normal run
            if start > pos:
                paragraph.add_run(full_text[pos:start])

            # Deleted original (tracked deletion)
            self._make_del_run(paragraph, original)

            # Replacement (tracked insertion)
            self._make_ins_run(paragraph, replacement)

            pos = end

        # Remaining text -> normal run
        if pos < len(full_text):
            paragraph.add_run(full_text[pos:])

    def _make_del_run(self, paragraph, text: str):
        """Create a run marked as a tracked deletion."""
        run = paragraph.add_run(text)
        run.font.strike = True
        rPr = run._element.get_or_add_rPr()

        # Add w:del revision marking in rPr
        del_el = rPr.makeelement(qn('w:del'), {
            qn('w:id'): self._next_id(),
            qn('w:author'): 'DocSanitizer',
            qn('w:date'): '2026-04-14T00:00:00Z'
        })
        rPr.append(del_el)

    def _make_ins_run(self, paragraph, text: str):
        """Create a run marked as a tracked insertion."""
        run = paragraph.add_run(text)
        run.font.highlight_color = 6  # Yellow highlight
        rPr = run._element.get_or_add_rPr()

        # Add w:ins revision marking in rPr
        ins_el = rPr.makeelement(qn('w:ins'), {
            qn('w:id'): self._next_id(),
            qn('w:author'): 'DocSanitizer',
            qn('w:date'): '2026-04-14T00:00:00Z'
        })
        rPr.append(ins_el)

    def _extract_text(self, doc) -> str:
        """Extract all text from a document, skipping deleted (w:del) text."""
        parts = []
        for p in doc.paragraphs:
            parts.append(self._extract_paragraph_text(p))
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        parts.append(self._extract_paragraph_text(p))
        return '\n'.join(parts)

    def _extract_paragraph_text(self, paragraph) -> str:
        """Extract text from a paragraph, skipping text inside deleted runs."""
        texts = []
        for child in paragraph._p:
            tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            if tag != 'r':
                continue
            # Check if this run has a w:del in its rPr
            rPr = child.find(qn('w:rPr'))
            if rPr is not None and rPr.find(qn('w:del')) is not None:
                continue  # Skip deleted runs
            # Extract text from this run
            for t in child:
                if t.tag.split('}')[-1] == 't' and t.text:
                    texts.append(t.text)
        return ''.join(texts)
