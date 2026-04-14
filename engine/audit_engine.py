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
        """Build regex patterns for each sensitive word with word boundaries and whitespace tolerance."""
        patterns = []
        for word in self.replacements:
            # Insert optional whitespace between each character, with word boundaries
            spaced = r'\s*'.join(re.escape(c) for c in word)
            pattern = re.compile(r'\b' + spaced + r'\b', re.IGNORECASE)
            patterns.append((word, pattern))
        return patterns

    def _build_replacement_spans(self, text: str) -> list[tuple[int, int]]:
        """Find all spans in text that correspond to replacement values."""
        spans = []
        for replacement in self.replacements.values():
            start = 0
            while True:
                idx = text.lower().find(replacement.lower(), start)
                if idx == -1:
                    break
                spans.append((idx, idx + len(replacement)))
                start = idx + 1
        return spans

    def _is_within_replacement(self, match_start: int, match_end: int, replacement_spans: list[tuple[int, int]]) -> bool:
        """Check if a match falls within any replacement span."""
        for r_start, r_end in replacement_spans:
            if match_start >= r_start and match_end <= r_end:
                return True
        return False

    def scan(self, text: str) -> AuditResult:
        """Scan text for remaining sensitive words and return audit result."""
        result = AuditResult()
        replacement_spans = self._build_replacement_spans(text)

        for original_word, pattern in self._patterns:
            for match in pattern.finditer(text):
                # Skip matches that fall within known replacement values
                if self._is_within_replacement(match.start(), match.end(), replacement_spans):
                    continue
                result.is_clean = False
                result.total_matches += 1
                start = max(0, match.start() - self.CONTEXT_CHARS)
                end = min(len(text), match.end() + self.CONTEXT_CHARS)
                context = text[start:end]
                # Calculate line number by counting newlines before match
                line_number = text[:match.start()].count('\n') + 1
                result.missed_words.append({
                    'word': match.group(),
                    'original': original_word,
                    'context': ('...' if start > 0 else '') + context + ('...' if end < len(text) else ''),
                    'position': match.start(),
                    'location': f'line {line_number}',
                    'line_number': line_number,
                })

        return result
