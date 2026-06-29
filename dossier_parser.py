"""
Builds an ICP either from a PDF dossier or from the user's own LinkedIn profile data.
AI calls are handled by ai_writer to keep Claude client in one place.
"""

import pdfplumber


def extract_pdf_text(pdf_path: str) -> str:
    text = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text.append(t)
    return "\n".join(text)
