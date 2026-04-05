"""
services/pdf_service.py
────────────────────────
PDF parsing service for FinArmor.

Responsibilities
────────────────
1. Receive a file path and a document_type hint.
2. Open the PDF with pdfplumber.
3. Dispatch to the correct private extractor.
4. Return a fully populated Pydantic schema ready for AI consumption.

Design principles
─────────────────
• Each extractor is a standalone private function → easy to unit-test.
• All monetary amounts are parsed to Decimal → no floating-point rounding errors.
• Regex patterns are compiled once at module level → performance.
• Unknown / unparseable values default to safe nulls rather than crashing.
"""

import logging
import re
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pdfplumber

from app.schemas.financial_data import (
    AccountInfo,
    AccountType,
    BankStatementData,
    CIBILAccount,
    CIBILData,
    FinancialData,
    ITReturnData,
    ITYear,
    Transaction,
    TransactionType,
)

logger = logging.getLogger(__name__)

# ── Compiled regex patterns ───────────────────────────────────────────────────
_RE_DATE = re.compile(r"\b(\d{2}[/-]\d{2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})\b")
_RE_AMOUNT = re.compile(r"[\d,]+\.\d{2}")
_RE_ACCOUNT_NO = re.compile(r"\b[Xx*\d]{4,20}\b")
_RE_IFSC = re.compile(r"[A-Z]{4}0[A-Z0-9]{6}")
_RE_PAN = re.compile(r"[A-Z]{5}\d{4}[A-Z]")
_RE_CIBIL_SCORE = re.compile(r"\b([3-9]\d{2})\b")
_RE_AY = re.compile(r"\b(20\d{2}-\d{2,4})\b")

# EMI keyword patterns for transaction categorisation
_EMI_KEYWORDS = re.compile(
    r"\b(emi|loan|repay|equated|installment|instalment)\b", re.IGNORECASE
)
_SALARY_KEYWORDS = re.compile(r"\b(salary|sal|payroll|stipend)\b", re.IGNORECASE)
_INVESTMENT_KEYWORDS = re.compile(
    r"\b(mutual fund|mf|sip|nifty|sensex|elss|ppf|nps|fd|fixed deposit)\b", re.IGNORECASE
)
_UTILITY_KEYWORDS = re.compile(
    r"\b(electricity|water|gas|mobile|internet|broadband|recharge|insurance)\b", re.IGNORECASE
)
_FOOD_KEYWORDS = re.compile(
    r"\b(swiggy|zomato|hotel|restaurant|cafe|food|grocery|bigbasket|blinkit)\b",
    re.IGNORECASE,
)
_ENTERTAINMENT_KEYWORDS = re.compile(
    r"\b(netflix|prime|hotstar|spotify|youtube|bookmyshow|pvr)\b", re.IGNORECASE
)

# ── Supported document types ──────────────────────────────────────────────────
DOCUMENT_TYPES = frozenset({"bank_statement", "it_return", "cibil"})


# ═══════════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════════

async def process_pdf(
    file_path: Path,
    document_type: str,
    user_id: int,
) -> FinancialData:
    """
    Main entry point: parse a PDF file and return a FinancialData envelope.

    Args:
        file_path    : Absolute path to the saved PDF on disk.
        document_type: One of 'bank_statement', 'it_return', 'cibil'.
        user_id      : ID of the requesting user (embedded in envelope).

    Returns:
        FinancialData with the relevant nested field populated.

    Raises:
        ValueError: If document_type is unrecognised or PDF cannot be opened.
    """
    if document_type not in DOCUMENT_TYPES:
        raise ValueError(
            f"Unknown document_type '{document_type}'. "
            f"Must be one of: {', '.join(DOCUMENT_TYPES)}"
        )

    logger.info("Processing %s PDF for user %d: %s", document_type, user_id, file_path.name)

    try:
        with pdfplumber.open(file_path) as pdf:
            full_text = "\n".join(
                page.extract_text() or "" for page in pdf.pages
            )
            all_tables = []
            for page in pdf.pages:
                tables = page.extract_tables()
                if tables:
                    all_tables.extend(tables)
    except Exception as exc:
        logger.exception("Failed to open PDF: %s", file_path)
        raise ValueError(f"Could not open or parse PDF: {exc}") from exc

    # ── Dispatch ──────────────────────────────────────────────────────────────
    financial_data = FinancialData(user_id=user_id)

    if document_type == "bank_statement":
        financial_data.bank_statement = _extract_bank_statement(full_text, all_tables)
    elif document_type == "it_return":
        financial_data.it_return = _extract_it_return(full_text, all_tables)
    elif document_type == "cibil":
        financial_data.cibil = _extract_cibil(full_text, all_tables)

    logger.info("Finished processing %s PDF for user %d.", document_type, user_id)
    return financial_data


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _safe_decimal(value: str | None) -> Decimal:
    """Convert a string like '1,23,456.78' to Decimal. Returns 0 on failure."""
    if not value:
        return Decimal("0")
    cleaned = re.sub(r"[^\d.]", "", value.replace(",", ""))
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return Decimal("0")


def _normalise_date(raw: str) -> str:
    """
    Normalise various date formats to YYYY-MM-DD.
    Handles: DD/MM/YYYY, DD-MM-YYYY, DD/MM/YY, YYYY-MM-DD.
    """
    raw = raw.strip()
    # Already ISO
    if re.match(r"\d{4}-\d{2}-\d{2}", raw):
        return raw
    parts = re.split(r"[/-]", raw)
    if len(parts) == 3:
        day, month, year = parts
        if len(year) == 2:
            year = "20" + year
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    return raw


def _categorise_transaction(description: str, txn_type: TransactionType) -> str:
    """
    Heuristically classify a bank transaction into a human-readable category.

    Priority: salary > emi > investment > utilities > food > entertainment > transfer > other.
    """
    if txn_type == TransactionType.CREDIT and _SALARY_KEYWORDS.search(description):
        return "salary"
    if _EMI_KEYWORDS.search(description):
        return "emi"
    if _INVESTMENT_KEYWORDS.search(description):
        return "investment"
    if _UTILITY_KEYWORDS.search(description):
        return "utilities"
    if _FOOD_KEYWORDS.search(description):
        return "food"
    if _ENTERTAINMENT_KEYWORDS.search(description):
        return "entertainment"
    # Transfers between accounts
    if re.search(r"\b(neft|imps|rtgs|upi|transfer|trf)\b", description, re.IGNORECASE):
        return "transfer"
    return "other"


# ═══════════════════════════════════════════════════════════════════════════════
# Bank Statement Extractor
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_bank_statement(text: str, tables: list[list]) -> BankStatementData:
    """
    Parse raw pdfplumber output into a BankStatementData object.

    Strategy
    ────────
    1. Extract account metadata from the text header.
    2. Try table rows first (structured); fall back to line-by-line regex.
    3. Compute aggregates (totals, averages, EMI list).
    """
    account_info = _parse_account_info(text)
    transactions = _parse_transactions_from_tables(tables) or _parse_transactions_from_text(text)

    # ── Aggregate calculations ────────────────────────────────────────────────
    total_credits = sum((t.amount for t in transactions if t.transaction_type == TransactionType.CREDIT), Decimal("0"))
    total_debits = sum((t.amount for t in transactions if t.transaction_type == TransactionType.DEBIT), Decimal("0"))

    # Approximate monthly averages over ~6-month window
    months = Decimal("6")
    avg_credit = (total_credits / months).quantize(Decimal("0.01"))
    avg_debit = (total_debits / months).quantize(Decimal("0.01"))

    emi_txns = [t for t in transactions if t.category == "emi"]

    return BankStatementData(
        account_info=account_info,
        transactions=transactions,
        total_credits=total_credits,
        total_debits=total_debits,
        average_monthly_credit=avg_credit,
        average_monthly_debit=avg_debit,
        emi_transactions=emi_txns,
    )


def _parse_account_info(text: str) -> AccountInfo:
    """Extract account metadata from statement header text."""

    def _find(pattern: str, fallback: str = "Unknown") -> str:
        m = re.search(pattern, text, re.IGNORECASE)
        return m.group(1).strip() if m else fallback

    # Account number — take first plausible match
    acc_match = _RE_ACCOUNT_NO.search(text)
    account_number = acc_match.group() if acc_match else "Unknown"

    # Opening / closing balances
    opening = _safe_decimal(_find(r"opening\s+balance[:\s]+([\d,]+\.\d{2})"))
    closing = _safe_decimal(_find(r"closing\s+balance[:\s]+([\d,]+\.\d{2})"))

    # Statement period dates
    dates = _RE_DATE.findall(text)
    period_from = _normalise_date(dates[0]) if dates else "Unknown"
    period_to = _normalise_date(dates[1]) if len(dates) > 1 else "Unknown"

    # Bank name heuristic — look for common Indian bank names
    bank_name = "Unknown"
    for name in ["HDFC", "SBI", "ICICI", "Axis", "Kotak", "Bank of Baroda", "Canara", "PNB"]:
        if name.lower() in text.lower():
            bank_name = name
            break

    # IFSC
    ifsc_match = _RE_IFSC.search(text)

    # Account type
    acc_type = AccountType.OTHER
    for atype in AccountType:
        if atype.value.upper() in text.upper():
            acc_type = atype
            break

    # Account holder name — often "Name: XXXX" or first line of statement
    holder = _find(r"(?:account\s+holder|name)[:\s]+([A-Za-z\s]+)")

    return AccountInfo(
        account_holder=holder,
        account_number=account_number,
        bank_name=bank_name,
        ifsc_code=ifsc_match.group() if ifsc_match else None,
        account_type=acc_type,
        statement_period_from=period_from,
        statement_period_to=period_to,
        opening_balance=opening,
        closing_balance=closing,
    )


def _parse_transactions_from_tables(tables: list[list]) -> list[Transaction]:
    """
    Attempt to extract transactions from pdfplumber table objects.

    Expected columns (order varies by bank):
        Date | Description/Narration | Debit | Credit | Balance
    """
    transactions: list[Transaction] = []

    for table in tables:
        if not table or len(table) < 2:
            continue

        # Identify column indices from header row
        header = [str(cell or "").lower() for cell in table[0]]
        try:
            date_idx = next(i for i, h in enumerate(header) if "date" in h)
            desc_idx = next(
                i for i, h in enumerate(header)
                if any(k in h for k in ("narration", "description", "particulars", "remark"))
            )
            debit_idx = next((i for i, h in enumerate(header) if "debit" in h or "withdrawal" in h), None)
            credit_idx = next((i for i, h in enumerate(header) if "credit" in h or "deposit" in h), None)
            balance_idx = next((i for i, h in enumerate(header) if "balance" in h), None)
        except StopIteration:
            logger.debug("Could not identify transaction table columns in header: %s", header)
            continue

        for row in table[1:]:
            if not row or all(cell is None or str(cell).strip() == "" for cell in row):
                continue

            raw_date = str(row[date_idx] or "").strip()
            if not raw_date or not _RE_DATE.search(raw_date):
                continue

            description = str(row[desc_idx] or "").strip()
            debit_val = _safe_decimal(str(row[debit_idx] or "")) if debit_idx is not None else Decimal("0")
            credit_val = _safe_decimal(str(row[credit_idx] or "")) if credit_idx is not None else Decimal("0")
            balance_val = _safe_decimal(str(row[balance_idx] or "")) if balance_idx is not None else Decimal("0")

            if debit_val > 0:
                txn_type = TransactionType.DEBIT
                amount = debit_val
            elif credit_val > 0:
                txn_type = TransactionType.CREDIT
                amount = credit_val
            else:
                continue  # Skip rows with no amount

            category = _categorise_transaction(description, txn_type)

            transactions.append(
                Transaction(
                    date=_normalise_date(raw_date),
                    description=description,
                    amount=amount,
                    transaction_type=txn_type,
                    balance=balance_val,
                    category=category,
                )
            )

    return transactions


def _parse_transactions_from_text(text: str) -> list[Transaction]:
    """
    Fallback: regex line scan when no tables could be parsed.
    Matches lines that start with a date and contain at least one amount.
    """
    transactions: list[Transaction] = []
    for line in text.splitlines():
        date_match = _RE_DATE.search(line)
        if not date_match:
            continue
        amounts = _RE_AMOUNT.findall(line)
        if len(amounts) < 2:
            continue

        # Heuristic: if multiple amounts, last is balance, second-to-last is transaction
        balance = _safe_decimal(amounts[-1])
        amount = _safe_decimal(amounts[-2])
        description = line[date_match.end():].strip()

        # Determine type: if balance went up it's a credit
        txn_type = TransactionType.CREDIT if amount > Decimal("0") else TransactionType.DEBIT
        category = _categorise_transaction(description, txn_type)

        transactions.append(
            Transaction(
                date=_normalise_date(date_match.group()),
                description=description[:200],
                amount=amount,
                transaction_type=txn_type,
                balance=balance,
                category=category,
            )
        )

    return transactions


# ═══════════════════════════════════════════════════════════════════════════════
# IT Return Extractor
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_it_return(text: str, tables: list[list]) -> ITReturnData:
    """Parse ITR PDF text and tables into ITReturnData."""

    pan_match = _RE_PAN.search(text)
    pan = pan_match.group() if pan_match else None

    # Taxpayer name — common patterns in ITR acknowledgements
    name_match = re.search(r"name[:\s]+([A-Za-z\s]{3,60})", text, re.IGNORECASE)
    taxpayer_name = name_match.group(1).strip() if name_match else None

    years = _parse_it_years(text, tables)

    return ITReturnData(
        pan_number=pan,
        taxpayer_name=taxpayer_name,
        years=years,
    )


def _parse_it_years(text: str, tables: list[list]) -> list[ITYear]:
    """
    Extract per-assessment-year financial data.

    First tries to find structured table rows, then falls back to text search.
    """
    years_data: dict[str, dict] = defaultdict(dict)

    # ── Table-based extraction ────────────────────────────────────────────────
    for table in tables:
        for row in (table or []):
            row_text = " ".join(str(c or "") for c in row)
            ay_match = _RE_AY.search(row_text)
            if not ay_match:
                continue
            ay = ay_match.group(1)
            amounts = _RE_AMOUNT.findall(row_text)
            if amounts:
                years_data[ay]["gross_total_income"] = _safe_decimal(amounts[0])
                if len(amounts) > 1:
                    years_data[ay]["taxable_income"] = _safe_decimal(amounts[1])
                if len(amounts) > 2:
                    years_data[ay]["tax_payable"] = _safe_decimal(amounts[2])

    # ── Text-based extraction ─────────────────────────────────────────────────
    def _grab_after(label: str) -> Decimal:
        m = re.search(label + r"[:\s]+([\d,]+\.\d{2})", text, re.IGNORECASE)
        return _safe_decimal(m.group(1)) if m else Decimal("0")

    # Build at least one year entry from plain text if tables gave nothing
    if not years_data:
        ay_matches = _RE_AY.findall(text)
        primary_ay = ay_matches[0] if ay_matches else "Unknown AY"
        years_data[primary_ay] = {}

    result: list[ITYear] = []
    for ay, data in years_data.items():
        gross = data.get("gross_total_income") or _grab_after("gross total income")
        taxable = data.get("taxable_income") or _grab_after("net taxable income")
        payable = data.get("tax_payable") or _grab_after("tax payable")
        deductions = _grab_after("total deductions")
        tax_paid = _grab_after("total tax paid")
        refund = _grab_after("refund due")

        result.append(
            ITYear(
                assessment_year=ay,
                gross_total_income=gross,
                total_deductions=deductions,
                taxable_income=taxable,
                tax_payable=payable,
                tax_paid=tax_paid,
                refund_due=refund,
            )
        )

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# CIBIL Extractor
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_cibil(text: str, tables: list[list]) -> CIBILData:
    """Parse CIBIL credit report PDF into CIBILData."""

    # ── Score ─────────────────────────────────────────────────────────────────
    score = 300
    score_match = _RE_CIBIL_SCORE.search(text)
    if score_match:
        candidate = int(score_match.group(1))
        if 300 <= candidate <= 900:
            score = candidate

    # ── Report date ───────────────────────────────────────────────────────────
    date_matches = _RE_DATE.findall(text)
    report_date = _normalise_date(date_matches[0]) if date_matches else "Unknown"

    # ── Accounts ──────────────────────────────────────────────────────────────
    accounts = _parse_cibil_accounts(tables, text)

    total_overdue = sum((a.overdue_amount for a in accounts), Decimal("0"))
    active = sum(1 for a in accounts if a.account_status.lower() == "active")
    closed = sum(1 for a in accounts if a.account_status.lower() == "closed")

    return CIBILData(
        cibil_score=score,
        report_date=report_date,
        total_accounts=len(accounts),
        active_accounts=active,
        closed_accounts=closed,
        total_overdue=total_overdue,
        accounts=accounts,
    )


def _parse_cibil_accounts(tables: list[list], text: str) -> list[CIBILAccount]:
    """
    Extract individual credit account rows from CIBIL tables.

    CIBIL reports vary significantly by bureau (TransUnion, Equifax, Experian).
    This implementation targets the TransUnion CIBIL layout.
    """
    accounts: list[CIBILAccount] = []

    for table in tables:
        if not table or len(table) < 2:
            continue
        header = [str(c or "").lower() for c in table[0]]

        # Must look like a credit account table
        if not any("account" in h or "lender" in h or "member" in h for h in header):
            continue

        for row in table[1:]:
            if not row or len(row) < 3:
                continue
            row_str = " ".join(str(c or "") for c in row)
            amounts = _RE_AMOUNT.findall(row_str)

            account_type = str(row[0] or "").strip() or "Unknown"
            lender = str(row[1] or "").strip() or "Unknown"
            acc_no_match = _RE_ACCOUNT_NO.search(row_str)
            acc_no = acc_no_match.group() if acc_no_match else "XXXX"

            current_balance = _safe_decimal(amounts[0]) if amounts else Decimal("0")
            overdue = _safe_decimal(amounts[1]) if len(amounts) > 1 else Decimal("0")

            # DPD: look for numbers in a "DPD" column or trailing digits
            dpd_raw = re.findall(r"\b(\d{1,3})\b", row_str)
            dpd_history = [int(d) for d in dpd_raw if 0 <= int(d) <= 365][:12]

            status = "Active"
            if re.search(r"\bclosed\b", row_str, re.IGNORECASE):
                status = "Closed"
            elif re.search(r"\bwritten.?off\b", row_str, re.IGNORECASE):
                status = "Written Off"

            accounts.append(
                CIBILAccount(
                    account_type=account_type,
                    lender=lender,
                    account_number=acc_no,
                    current_balance=current_balance,
                    overdue_amount=overdue,
                    dpd_history=dpd_history,
                    account_status=status,
                )
            )

    return accounts
