from __future__ import annotations

import re


_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_MULTI_SPACE = re.compile(r"[ \t]+")
_MULTI_NEWLINE = re.compile(r"\n{3,}")


def clean_text(text: str) -> str:
    """
    Normalize raw extracted text into a stable form for embeddings/extraction.

    - Removes control characters
    - De-hyphenates line-wrapped words (e.g., 'machine-\\nlearning' -> 'machinelearning')
    - Normalizes line endings and collapses excessive whitespace
    """
    if not text:
        return ""

    t = text.replace("\r\n", "\n").replace("\r", "\n")
    t = _CONTROL_CHARS.sub("", t)

    # Common in PDFs: word broken across lines with a hyphen.
    t = re.sub(r"(\w)-\n(\w)", r"\1\2", t)

    # Convert single newlines inside paragraphs into spaces, but keep paragraph breaks.
    t = re.sub(r"(?<!\n)\n(?!\n)", " ", t)

    t = _MULTI_SPACE.sub(" ", t)
    t = _MULTI_NEWLINE.sub("\n\n", t)
    return t.strip()






