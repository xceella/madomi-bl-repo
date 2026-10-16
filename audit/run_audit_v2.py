#!/usr/bin/env python3
import re
import sys

import run_audit as audit


def strict_declared_chapter_count(text: str) -> int | None:
    """Only accept explicit totals, never ordinary labels such as 'Capítulo 1'."""
    patterns = [
        r"(?:cap[ií]tulos?|chapters?)\s*\(\s*(\d+)\s*\)",
        r"(?:total\s+(?:de\s+)?(?:cap[ií]tulos?|chapters?)|(?:cap[ií]tulos?|chapters?)\s+total)\s*[:\-]?\s*(\d+)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return int(match.group(1))
    return None


audit.declared_chapter_count = strict_declared_chapter_count

if __name__ == "__main__":
    sys.exit(audit.main())
