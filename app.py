"""
================================================================================
 REDAZIONE AUTOMATICA IBAN E CODICE FISCALE DA ATTI PDF - Web App (Streamlit)
================================================================================
Deploy gratuito consigliato: Streamlit Community Cloud (share.streamlit.io)

Esecuzione locale:
    pip install -r requirements.txt
    streamlit run app.py
================================================================================
"""

import io
import re
from dataclasses import dataclass
from typing import List

import fitz  # PyMuPDF
import pdfplumber
import streamlit as st


# ------------------------------------------------------------------------
# 1. REGOLE DI IDENTIFICAZIONE
# ------------------------------------------------------------------------

CF_REGEX = re.compile(
    r"\b[A-Za-z]{6}"
    r"[0-9LMNPQRSTUVlmnpqrstuv]{2}"
    r"[A-Za-z]"
    r"[0-9LMNPQRSTUVlmnpqrstuv]{2}"
    r"[A-Za-z]"
    r"[0-9LMNPQRSTUVlmnpqrstuv]{3}"
    r"[A-Za-z]\b"
)

IBAN_REGEX = re.compile(
    r"\b([A-Za-z]{2}[ \t]?\d{2}(?:[ \t]?[A-Za-z0-9]{3,4}){2,7})\b"
)

_CF_ODD_MAP = {
    '0': 1, '1': 0, '2': 5, '3': 7, '4': 9, '5': 13, '6': 15, '7': 17, '8': 19, '9': 21,
    'A': 1, 'B': 0, 'C': 5, 'D': 7, 'E': 9, 'F': 13, 'G': 15, 'H': 17, 'I': 19, 'J': 21,
    'K': 2, 'L': 4, 'M': 18, 'N': 20, 'O': 11, 'P': 3, 'Q': 6, 'R': 8, 'S': 12, 'T': 14,
    'U': 16, 'V': 10, 'W': 22, 'X': 25, 'Y': 24, 'Z': 23,
}
_CF_EVEN_MAP = {
    '0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
    'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9,
    'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18,
    'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25,
}
_CF_REMAINDER_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

_IBAN_LENGTH_BY_COUNTRY = {
    "IT": 27, "FR": 27, "DE": 22, "ES": 24, "NL": 18, "BE": 16, "AT": 20,
    "PT": 25, "GB": 22, "IE": 22, "CH": 21, "LU": 20, "SM": 27, "GR": 27,
}


def is_valid_codice_fiscale(cf: str) -> bool:
    cf = cf.upper()
    if len(cf) != 16:
        return False
    if not re.fullmatch(r"[A-Z]{6}[0-9A-Z]{2}[A-Z][0-9A-Z]{2}[A-Z][0-9A-Z]{3}[A-Z]", cf):
        return False
    total = 0
    for i, ch in enumerate(cf[:15]):
        total += _CF_ODD_MAP.get(ch, -1000) if i % 2 == 0 else _CF_EVEN_MAP.get(ch, -1000)
    if total < 0:
        return False
    return cf[15] == _CF_REMAINDER_LETTERS[total % 26]


def is_valid_iban(raw: str) -> bool:
    iban = re.sub(r"[ \t]", "", raw).upper()
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{11,30}", iban):
        return False
    expected_len = _IBAN_LENGTH_BY_COUNTRY.get(iban[:2])
    if expected_len is not None and len(iban) != expected_len:
        return False
    rearranged = iban[4:] + iban[:4]
    numeric = "".join(str(int(ch, 36)) for ch in rearranged)
    return int(numeric) % 97 == 1


@dataclass
class Finding:
    kind: str
    value: str
    page: int


def pdf_bytes_to_markdown(pdf_bytes: bytes) -> str:
    md_parts = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            md_parts.append(f"## Pagina {i}\n\n{text}\n")
    return "\n".join(md_parts)


def find_sensitive_data(pdf_bytes: bytes) -> List[Finding]:
    findings: List[Finding] = []
    seen = set()
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            for m in CF_REGEX.finditer(text):
                candidate = m.group(0)
                if is_valid_codice_fiscale(candidate):
                    key = ("CF", candidate.upper(), page_num)
                    if key not in seen:
                        seen.add(key)
                        findings.append(Finding("CF", candidate, page_num))
            for m in IBAN_REGEX.finditer(text):
                candidate = m.group(0)
                if is_valid_iban(candidate):
                    key = ("IBAN", re.sub(r"[ \t]", "", candidate).upper(), page_num)
                    if key not in seen:
                        seen.add(key)
                        findings.append(Finding("IBAN", candidate, page_num))
    return findings


def redact_pdf_bytes(pdf_bytes: bytes, extra_terms: List[str] = None):
    markdown_text = pdf_bytes_to_markdown(pdf_bytes)
    findings = find_sensitive_data(pdf_bytes)

    terms_to_redact = {f.value for f in findings}
    if extra_terms:
        terms_to_redact.update(t for t in extra_terms if t.strip())

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    redacted_count = 0

    for page in doc:
        for term in terms_to_redact:
            variants = {term, re.sub(r"[ \t]", "", term)}
            for variant in variants:
                for rect in page.search_for(variant):
                    page.add_redact_annot(rect, fill=(0, 0, 0))
                    redacted_count += 1
        page.apply_redactions()

    output_stream = doc.tobytes(garbage=4, deflate=True)
    doc.close()

    return output_stream, findings, redacted_count, markdown_text


# ------------------------------------------------------------------------
# 2. INTERFACCIA STREAMLIT
# ------------------------------------------------------------------------

st.set_page_config(page_title="Redazione CF/IBAN da PDF", page_icon="🖤", layout="centered")

st.title("🖤 Redazione automatica CF e IBAN")
st.caption(
    "Carica un atto in PDF: lo strumento identifica Codice Fiscale e IBAN "
    "(validati con il carattere di controllo ufficiale) e li oscura in nero, "
    "rimuovendo davvero il testo sottostante — non un semplice rettangolo sopra."
)

st.warning(
    "⚠️ I file caricati vengono elaborati da questa app e non salvati permanentemente, "
    "ma transitano comunque sul server che la ospita. Non caricare documenti riservati "
    "se non sei sicuro delle policy di trattamento dati del tuo ente per questo tipo di strumento.",
    icon="⚠️",
)

uploaded_file = st.file_uploader("Carica il PDF da redigere", type=["pdf"])

extra_terms_input = st.text_input(
    "Altre stringhe esatte da oscurare (opzionale, separate da virgola)",
    placeholder="es. un IBAN scritto in un formato non standard, un nome...",
)

if uploaded_file is not None:
    pdf_bytes = uploaded_file.read()

    if st.button("Avvia redazione", type="primary"):
        with st.spinner("Estrazione, identificazione e redazione in corso..."):
            extra_terms = [t.strip() for t in extra_terms_input.split(",")] if extra_terms_input else None
            output_bytes, findings, redacted_count, markdown_text = redact_pdf_bytes(pdf_bytes, extra_terms)

        st.success(f"Fatto! {redacted_count} occorrenze omissate nel documento.")

        if findings:
            st.subheader("Elementi identificati")
            for f in findings:
                st.write(f"- **[{f.kind}]** pagina {f.page}: `{f.value}`")
        else:
            st.info("Nessun CF o IBAN valido identificato nel testo estratto.")

        st.download_button(
            label="⬇️ Scarica il PDF omissato",
            data=output_bytes,
            file_name=uploaded_file.name.replace(".pdf", "_OMISSIS.pdf"),
            mime="application/pdf",
        )

        with st.expander("Markdown estratto (per revisione)"):
            st.text(markdown_text)

st.divider()
st.caption(
    "Nota: per PDF scansionati (immagini) serve prima l'OCR — questo strumento lavora "
    "sul testo selezionabile del PDF, non su documenti puramente immagine."
)
