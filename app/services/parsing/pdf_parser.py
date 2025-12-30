from __future__ import annotations

import io

from pypdf import PdfReader


class PdfParseError(RuntimeError):
    pass


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """
    Extract text from a PDF byte stream using pypdf.

    Notes:
    - Many resumes are digitally generated PDFs: this works well.
    - Scanned-image PDFs require OCR; that's intentionally not included unless requested.
    """
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
    except Exception as e:  # pragma: no cover
        raise PdfParseError(f"Failed to read PDF: {e}") from e

    if getattr(reader, "is_encrypted", False):
        try:
            reader.decrypt("")  # common case: encrypted with empty password
        except Exception as e:
            raise PdfParseError("PDF is encrypted and could not be decrypted.") from e

    parts: list[str] = []
    for page in reader.pages:
        try:
            txt = page.extract_text() or ""
        except Exception:
            txt = ""
        if txt:
            parts.append(txt)

    text = "\n".join(parts).strip()
    if not text:
        raise PdfParseError(
            "No extractable text found in PDF. If this is a scanned resume, OCR is required."
        )
    return text






