"""
schemas/financial_data.py
──────────────────────────
Pydantic v2 models representing the structured JSON output of PDF parsing.

These schemas are the **contract** between the PDF processing service and the
AI model layer.  Every field carries a description so the LLM knows what it's
receiving.

Document hierarchy
──────────────────
FinancialData
├── BankStatementData   (6 months)
│   ├── AccountInfo
│   └── List[Transaction]
├── ITReturnData        (3 years)
│   └── List[ITYear]
└── CIBILData
    └── List[CIBILAccount]
"""

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════════
# Shared / primitive types
# ═══════════════════════════════════════════════════════════════════════════════

class TransactionType(StrEnum):
    CREDIT = "credit"
    DEBIT = "debit"


class AccountType(StrEnum):
    SAVINGS = "savings"
    CURRENT = "current"
    SALARY = "salary"
    NRE = "nre"
    NRO = "nro"
    OTHER = "other"


# ═══════════════════════════════════════════════════════════════════════════════
# Bank Statement
# ═══════════════════════════════════════════════════════════════════════════════

class AccountInfo(BaseModel):
    """Metadata extracted from the bank statement header."""

    account_holder: str = Field(..., description="Full name of account holder")
    account_number: str = Field(..., description="Masked or full account number")
    bank_name: str = Field(..., description="Name of the bank (e.g. 'HDFC Bank')")
    ifsc_code: str | None = Field(None, description="Branch IFSC code")
    account_type: AccountType = Field(..., description="Type of bank account")
    statement_period_from: str = Field(..., description="Statement start date (YYYY-MM-DD)")
    statement_period_to: str = Field(..., description="Statement end date (YYYY-MM-DD)")
    opening_balance: Decimal = Field(..., description="Balance at statement start (INR)")
    closing_balance: Decimal = Field(..., description="Balance at statement end (INR)")


class Transaction(BaseModel):
    """A single debit or credit row in a bank statement."""

    date: str = Field(..., description="Transaction date (YYYY-MM-DD)")
    description: str = Field(..., description="Narration / reference text")
    amount: Decimal = Field(..., gt=0, description="Transaction amount (INR, always positive)")
    transaction_type: TransactionType = Field(..., description="'credit' or 'debit'")
    balance: Decimal = Field(..., description="Running balance after this transaction (INR)")
    category: str | None = Field(
        None,
        description=(
            "Auto-classified category: 'salary', 'emi', 'utilities', 'food', "
            "'entertainment', 'investment', 'transfer', 'other'"
        ),
    )


class BankStatementData(BaseModel):
    """Structured representation of a 6-month bank statement PDF."""

    account_info: AccountInfo
    transactions: list[Transaction] = Field(default_factory=list)

    # ── Derived aggregates (computed in pdf_service, used by health engine) ──
    total_credits: Decimal = Field(Decimal("0"), description="Sum of all credits (INR)")
    total_debits: Decimal = Field(Decimal("0"), description="Sum of all debits (INR)")
    average_monthly_credit: Decimal = Field(
        Decimal("0"), description="Average monthly inflow (INR)"
    )
    average_monthly_debit: Decimal = Field(
        Decimal("0"), description="Average monthly outflow (INR)"
    )
    emi_transactions: list[Transaction] = Field(
        default_factory=list,
        description="Transactions auto-tagged as EMI payments",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# IT Return
# ═══════════════════════════════════════════════════════════════════════════════

class ITYear(BaseModel):
    """Financial data for a single assessment year from the ITR."""

    assessment_year: str = Field(..., description="e.g. '2023-24'")
    gross_total_income: Decimal = Field(..., description="Gross total income (INR)")
    total_deductions: Decimal = Field(Decimal("0"), description="Total deductions u/s 80C etc.")
    taxable_income: Decimal = Field(..., description="Net taxable income (INR)")
    tax_payable: Decimal = Field(Decimal("0"), description="Tax payable before relief (INR)")
    tax_paid: Decimal = Field(Decimal("0"), description="TDS + advance tax paid (INR)")
    refund_due: Decimal = Field(Decimal("0"), description="Refund due if any (INR)")
    income_sources: dict[str, Decimal] = Field(
        default_factory=dict,
        description=(
            "Breakdown by source: e.g. {'salary': 800000, 'house_property': -20000, "
            "'capital_gains': 50000, 'other_sources': 10000}"
        ),
    )


class ITReturnData(BaseModel):
    """Structured representation of up to 3 years of ITR PDFs."""

    pan_number: str | None = Field(None, description="PAN of the taxpayer (masked)")
    taxpayer_name: str | None = Field(None, description="Name as per ITR")
    years: list[ITYear] = Field(default_factory=list, description="One entry per AY")


# ═══════════════════════════════════════════════════════════════════════════════
# CIBIL Report
# ═══════════════════════════════════════════════════════════════════════════════

class CIBILAccount(BaseModel):
    """A single credit account from the CIBIL report."""

    account_type: str = Field(..., description="e.g. 'Credit Card', 'Personal Loan', 'Home Loan'")
    lender: str = Field(..., description="Name of the lending institution")
    account_number: str = Field(..., description="Masked account number")
    opened_date: str | None = Field(None, description="Date account was opened (YYYY-MM-DD)")
    credit_limit_or_sanction: Decimal | None = Field(
        None, description="Credit limit (cards) or sanctioned amount (loans) in INR"
    )
    current_balance: Decimal = Field(..., description="Outstanding balance (INR)")
    overdue_amount: Decimal = Field(Decimal("0"), description="Amount overdue (INR)")
    dpd_history: list[int] = Field(
        default_factory=list,
        description="Days Past Due for last 12 months (0 = on-time)",
    )
    account_status: str = Field(..., description="e.g. 'Active', 'Closed', 'Written Off'")


class CIBILData(BaseModel):
    """Structured representation of the CIBIL credit report PDF."""

    cibil_score: int = Field(..., ge=300, le=900, description="CIBIL score (300–900)")
    report_date: str = Field(..., description="Date of report generation (YYYY-MM-DD)")
    total_accounts: int = Field(0, description="Total number of credit accounts")
    active_accounts: int = Field(0, description="Number of currently active accounts")
    closed_accounts: int = Field(0, description="Number of closed accounts")
    total_overdue: Decimal = Field(Decimal("0"), description="Total overdue amount across all accounts (INR)")
    accounts: list[CIBILAccount] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# Top-level Envelope
# ═══════════════════════════════════════════════════════════════════════════════

class FinancialData(BaseModel):
    """
    Master envelope returned after processing all uploaded PDFs.

    This is the object passed to the AI health-scoring engine.
    Fields are optional because users may upload documents in multiple steps.
    """

    user_id: int = Field(..., description="Owner of this financial snapshot")
    bank_statement: BankStatementData | None = Field(
        None, description="Parsed bank statement data"
    )
    it_return: ITReturnData | None = Field(
        None, description="Parsed IT return data (up to 3 AYs)"
    )
    cibil: CIBILData | None = Field(None, description="Parsed CIBIL report data")

    model_config = {"json_encoders": {Decimal: str}}
