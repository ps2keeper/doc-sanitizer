"""Text file (.txt) processing handler with regex-based replacement."""
import re
from io import BytesIO

from engine.audit_engine import AuditEngine, AuditResult


class TxtHandler:
    """Handles .txt file processing: read, replace sensitive words, audit."""

    def process(self, file_path: str, replacements: dict[str, str]) -> tuple[BytesIO, AuditResult]:
        """Process a text file by replacing sensitive words and auditing the result."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Perform replacements
        processed = content
        for word, replacement in replacements.items():
            pattern = re.compile(re.escape(word), re.IGNORECASE)
            processed = pattern.sub(replacement, processed)

        result = BytesIO(processed.encode('utf-8'))

        # Audit
        audit_engine = AuditEngine(replacements)
        audit_result = audit_engine.scan(processed)

        return result, audit_result
