"""
app/services/local_processor.py
─────────────────────────────────
Simulates a local privacy-preserving model layer.
In production this would run Mistral-7B locally.
For now it uses deterministic rules to:
  1. Classify document type
  2. Extract and anonymize PII
  3. Generate a privacy report
  
This ensures ZERO sensitive data leaves the device
before being passed to cloud AI (Gemini).
"""

from dataclasses import dataclass
import re


@dataclass
class LocalProcessingResult:
    document_type: str
    pii_items_removed: int
    anonymized_text: str
    privacy_score: int      # 0-100, how well anonymized
    local_summary: str      # brief summary done locally


def detect_document_type(text: str) -> str:
    text_lower = text.lower()

    if any(word in text_lower for word in ["itr", "income tax", "assessment year", "form 16", "tds certificate"]):
        return "IT Return"
    elif any(word in text_lower for word in ["cibil", "credit score", "credit report", "equifax", "experian"]):
        return "CIBIL Report"
    elif any(word in text_lower for word in ["statement", "account", "debit", "credit", "balance", "transaction"]):
        return "Bank Statement"
    else:
        return "Unknown Document"


def local_anonymize(text: str) -> tuple[str, int]:
    """
    Anonymize text and count how many PII items were removed.
    Returns (anonymized_text, pii_count)
    """
    pii_count = 0

    # PAN
    pan_matches = re.findall(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b', text)
    pii_count += len(pan_matches)
    text = re.sub(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b', '[PAN-REDACTED]', text)

    # Aadhaar
    aadhaar_matches = re.findall(r'\b\d{4}\s?\d{4}\s?\d{4}\b', text)
    pii_count += len(aadhaar_matches)
    text = re.sub(r'\b\d{4}\s?\d{4}\s?\d{4}\b', '[AADHAAR-REDACTED]', text)

    # Account numbers
    acc_matches = re.findall(r'\b\d{9,18}\b', text)
    pii_count += len(acc_matches)
    text = re.sub(r'\b\d{9,18}\b', '[ACCOUNT-REDACTED]', text)

    # Phone numbers
    phone_matches = re.findall(r'\b[6-9]\d{9}\b', text)
    pii_count += len(phone_matches)
    text = re.sub(r'\b[6-9]\d{9}\b', '[PHONE-REDACTED]', text)

    # Email
    email_matches = re.findall(r'\S+@\S+\.\S+', text)
    pii_count += len(email_matches)
    text = re.sub(r'\S+@\S+\.\S+', '[EMAIL-REDACTED]', text)

    # Names
    name_matches = re.findall(r'\b[A-Z][a-z]{2,}\s[A-Z][a-z]{2,}\b', text)
    pii_count += len(name_matches)
    text = re.sub(r'\b[A-Z][a-z]{2,}\s[A-Z][a-z]{2,}\b', '[NAME-REDACTED]', text)

    # Address keywords
    addr_matches = re.findall(r'\b(flat|door|plot|house|no\.?)\s*[\d/\-]+\b', text, re.IGNORECASE)
    pii_count += len(addr_matches)
    text = re.sub(r'\b(flat|door|plot|house|no\.?)\s*[\d/\-]+\b', '[ADDRESS-REDACTED]', text, flags=re.IGNORECASE)

    return text, pii_count


def calculate_privacy_score(pii_removed: int, text_length: int) -> int:
    if text_length == 0:
        return 100
    if pii_removed == 0:
        return 100
    # More PII found and removed = higher privacy score
    base = min(100, 70 + (pii_removed * 5))
    return base


def generate_local_summary(doc_type: str, text: str) -> str:
    text_lower = text.lower()
    points = []

    if "bank statement" in doc_type.lower():
        if "salary" in text_lower or "credit" in text_lower:
            points.append("Regular income credits detected")
        if "emi" in text_lower or "loan" in text_lower:
            points.append("EMI/Loan payments detected")
        if "bounce" in text_lower or "return" in text_lower:
            points.append("Possible cheque bounces detected")

    elif "it return" in doc_type.lower():
        if "tds" in text_lower:
            points.append("TDS deductions found")
        if "refund" in text_lower:
            points.append("Tax refund mentioned")
        if "capital gain" in text_lower:
            points.append("Capital gains present")

    elif "cibil" in doc_type.lower():
        scores = re.findall(r'\b([3-9]\d{2})\b', text)
        if scores:
            points.append(f"Credit score detected: {scores[0]}")
        if "overdue" in text_lower:
            points.append("Overdue payments found")

    if not points:
        points.append("Document processed successfully")

    return " | ".join(points)


def process_locally(raw_text: str) -> LocalProcessingResult:
    """
    Main local processing function.
    Simulates what Mistral-7B would do locally.
    """
    doc_type = detect_document_type(raw_text)
    anonymized_text, pii_count = local_anonymize(raw_text)
    privacy_score = calculate_privacy_score(pii_count, len(raw_text))
    local_summary = generate_local_summary(doc_type, raw_text)

    return LocalProcessingResult(
        document_type=doc_type,
        pii_items_removed=pii_count,
        anonymized_text=anonymized_text,
        privacy_score=privacy_score,
        local_summary=local_summary,
    )