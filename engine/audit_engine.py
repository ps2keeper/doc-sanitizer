"""Audit engine for regex secondary scanning of processed documents."""
import re
from dataclasses import dataclass, field


@dataclass
class AuditResult:
    is_clean: bool = True
    missed_words: list[dict] = field(default_factory=list)
    total_matches: int = 0


class AuditEngine:
    """Scans processed document text for any remaining sensitive word variants."""

    CONTEXT_CHARS = 50

    def __init__(self, replacements: dict[str, str]):
        self.replacements = replacements
        self._patterns = self._build_patterns()

    def _build_patterns(self) -> list[tuple[str, re.Pattern]]:
        """Build regex patterns for each sensitive word with whitespace tolerance."""
        patterns = []
        for word in self.replacements:
            # Insert optional whitespace between each character
            spaced = r'\s*'.join(re.escape(c) for c in word)
            pattern = re.compile(spaced, re.IGNORECASE)
            patterns.append((word, pattern))
        return patterns

    def scan(self, text: str) -> AuditResult:
        """Scan text for remaining sensitive words and return audit result."""
        result = AuditResult()

        for original_word, pattern in self._patterns:
            for match in pattern.finditer(text):
                result.is_clean = False
                result.total_matches += 1
                start = max(0, match.start() - self.CONTEXT_CHARS)
                end = min(len(text), match.end() + self.CONTEXT_CHARS)
                context = text[start:end]
                result.missed_words.append({
                    'word': match.group(),
                    'original': original_word,
                    'context': ('...' if start > 0 else '') + context + ('...' if end < len(text) else ''),
                    'position': match.start(),
                })

        return result
