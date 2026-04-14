"""Text file (.txt) processing handler with regex-based replacement."""
import re
from io import BytesIO

from engine.audit_engine import AuditEngine, AuditResult


class TxtHandler:
    """Handles .txt file processing: read, replace sensitive words, audit."""

    def process(self, file_path: str, replacements: dict[str, str], track_changes: bool = True) -> tuple[BytesIO, AuditResult, dict[str, int]]:
        """Process a text file by replacing sensitive words and auditing the result.
        
        Returns:
            (BytesIO output, AuditResult, replacement_counts dict)
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Perform replacements and count
        replacement_counts = {}
        processed = content
        for word, replacement in replacements.items():
            pattern = re.compile(re.escape(word), re.IGNORECASE)
            count = len(pattern.findall(processed))
            if count > 0:
                replacement_counts[word] = count
            processed = pattern.sub(replacement, processed)

        result = BytesIO(processed.encode('utf-8'))

        # Audit
        audit_engine = AuditEngine(replacements)
        audit_result = audit_engine.scan(processed)

        return result, audit_result, replacement_counts
