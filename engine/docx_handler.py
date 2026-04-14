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

    def process(self, file_path: str, replacements: dict[str, str]) -> tuple[BytesIO, AuditResult, dict[str, int]]:
        """Process a Word document by replacing sensitive words with tracked deletions/insertions.
        
        Returns:
            (BytesIO output, AuditResult, replacement_counts dict)
        """
        self._revision_id = 0
        doc = Document(file_path)

        # Count matches before replacing
        replacement_counts = {}
        for word, replacement in replacements.items():
            count = 0
            for p in doc.paragraphs:
                count += len(re.findall(re.escape(word), p.text, re.IGNORECASE))
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for p in cell.paragraphs:
                            count += len(re.findall(re.escape(word), p.text, re.IGNORECASE))
            if count > 0:
                replacement_counts[word] = count

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

        return output, audit_result, replacement_counts

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

        # Capture paragraph-level run format before rebuilding
        fmt = self._capture_run_format(paragraph)

        # Find all sensitive word positions in the full text
        all_matches = []
        for word, replacement in replacements.items():
            for match in re.finditer(re.escape(word), full_text, re.IGNORECASE):
                all_matches.append((match.start(), match.end(), match.group(), replacement))

        if not all_matches:
            return

        all_matches.sort(key=lambda x: x[0])

        # Rebuild the paragraph's XML children
        self._rebuild_paragraph(paragraph, full_text, all_matches, fmt)

    def _capture_run_format(self, paragraph):
        """Capture the w:rPr (run properties) from the first run in the paragraph."""
        for child in paragraph._p:
            tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            if tag == 'r':
                rPr = child.find(qn('w:rPr'))
                if rPr is not None:
                    from copy import deepcopy
                    return deepcopy(rPr)
        return None

    def _rebuild_paragraph(self, paragraph, full_text: str, matches: list, fmt):
        """Rebuild paragraph XML preserving original run format."""
        from copy import deepcopy
        # Remove all existing child elements
        for child in list(paragraph._p):
            paragraph._p.remove(child)

        pos = 0
        for start, end, original, replacement in matches:
            # Text before match -> normal run with inherited format
            if start > pos:
                self._add_run(paragraph, full_text[pos:start], fmt)

            # Deleted original (tracked deletion) with inherited format
            self._make_del_run(paragraph, original, fmt)

            # Replacement (tracked insertion) with inherited format
            self._make_ins_run(paragraph, replacement, fmt)

            pos = end

        # Remaining text -> normal run with inherited format
        if pos < len(full_text):
            self._add_run(paragraph, full_text[pos:], fmt)

    def _add_run(self, paragraph, text: str, fmt):
        """Add a normal run with copied format properties."""
        from copy import deepcopy
        run = paragraph.add_run(text)
        if fmt is not None:
            rPr = run._element.get_or_add_rPr()
            for child in fmt:
                rPr.append(deepcopy(child))

    def _make_del_run(self, paragraph, text: str, fmt):
        """Create a run marked as a tracked deletion, preserving original format."""
        from copy import deepcopy
        run = paragraph.add_run(text)
        rPr = run._element.get_or_add_rPr()

        # Copy inherited format
        if fmt is not None:
            for child in fmt:
                rPr.append(deepcopy(child))

        # Add strikethrough
        strike = rPr.makeelement(qn('w:strike'), {qn('w:val'): 'true'})
        rPr.append(strike)

        # Add w:del revision marking in rPr
        del_el = rPr.makeelement(qn('w:del'), {
            qn('w:id'): self._next_id(),
            qn('w:author'): 'DocSanitizer',
            qn('w:date'): '2026-04-14T00:00:00Z'
        })
        rPr.append(del_el)

    def _make_ins_run(self, paragraph, text: str, fmt):
        """Create a run marked as a tracked insertion, preserving original format."""
        from copy import deepcopy
        run = paragraph.add_run(text)
        rPr = run._element.get_or_add_rPr()

        # Copy inherited format
        if fmt is not None:
            for child in fmt:
                rPr.append(deepcopy(child))

        # Add yellow highlight via rPr
        highlight = rPr.makeelement(qn('w:highlight'), {qn('w:val'): 'yellow'})
        rPr.append(highlight)

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
