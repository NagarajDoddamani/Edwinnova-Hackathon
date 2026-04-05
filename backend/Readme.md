# FinArmor Backend

Production-grade FastAPI backend for the FinArmor fintech application.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI + Python 3.11 |
| Database | PostgreSQL 16 via SQLAlchemy 2 (Async) |
| Validation | Pydantic v2 |
| PDF Parsing | pdfplumber |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Migrations | Alembic |

---

## Project Structure

```
finarmor/
├── main.py                        # App factory + lifespan
├── alembic.ini
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── migrations/
│   └── env.py                     # Async Alembic config
└── app/
    ├── core/
    │   ├── config.py              # Pydantic-settings singleton
    │   ├── database.py            # Async engine + get_db dependency
    │   ├── security.py            # JWT + bcrypt helpers
    │   └── dependencies.py        # get_current_user dependency
    ├── models/
    │   ├── user.py                # User ORM model
    │   ├── loan.py                # Loan ORM model
    │   ├── investment.py          # Investment ORM model
    │   └── snapshot.py            # FinancialSnapshot ORM model
    ├── schemas/
    │   ├── financial_data.py      # FinancialData + nested Pydantic models
    │   └── schemas.py             # CRUD + Auth + HealthReport schemas
    ├── services/
    │   ├── pdf_service.py         # pdfplumber extractors (bank/ITR/CIBIL)
    │   ├── health_service.py      # Financial health scoring engine
    │   ├── snapshot_service.py    # Persist/retrieve parsed PDF data
    │   ├── user_service.py        # User DB operations
    │   ├── loan_service.py        # Loan CRUD DB operations
    │   └── investment_service.py  # Investment CRUD + referrals
    └── routes/
        ├── auth.py                # POST /auth/register, /auth/login
        ├── pdf_upload.py          # POST /documents/upload, GET /documents/status
        ├── loans.py               # Full CRUD + summary
        ├── investments.py         # Full CRUD + referrals + summary
        └── health_report.py       # GET /health-report
```

---

## Quick Start (Local)

### 1. Clone and setup environment

```bash
git clone <your-repo>
cd finarmor
cp .env.example .env
# Edit .env — set DATABASE_URL and SECRET_KEY
```

### 2. Install dependencies

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Start PostgreSQL

```bash
# Option A — Docker (easiest)
docker compose up db -d

# Option B — local postgres, create the DB manually:
# createdb finarmor
```

### 4. Run migrations

```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

### 5. Start the server

```bash
uvicorn main:app --reload
```

Open **http://localhost:8000/docs** for the interactive Swagger UI.

---

## Docker (full stack)

```bash
cp .env.example .env   # fill in SECRET_KEY
docker compose up --build
```

Both the API (`localhost:8000`) and PostgreSQL (`localhost:5432`) start together.

---

## API Reference

### Auth
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Create account |
| POST | `/api/v1/auth/login` | Get JWT token |

### PDF Upload
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/documents/upload` | Upload PDF (multipart/form-data) |
| GET | `/api/v1/documents/status` | Check processing status |

**document_type values:** `bank_statement` · `it_return` · `cibil`

### Loans
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/loans` | List all loans |
| POST | `/api/v1/loans` | Create loan |
| GET | `/api/v1/loans/summary` | Portfolio summary |
| GET | `/api/v1/loans/{id}` | Get single loan |
| PUT | `/api/v1/loans/{id}` | Full update |
| PATCH | `/api/v1/loans/{id}` | Partial update |
| DELETE | `/api/v1/loans/{id}` | Delete loan |

### Investments
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/investments` | List all investments |
| POST | `/api/v1/investments` | Create investment |
| GET | `/api/v1/investments/referrals` | 🔗 Get referral links |
| GET | `/api/v1/investments/summary` | Portfolio summary |
| GET | `/api/v1/investments/{id}` | Get single investment |
| PUT | `/api/v1/investments/{id}` | Full update |
| PATCH | `/api/v1/investments/{id}` | Partial update |
| DELETE | `/api/v1/investments/{id}` | Delete investment |

### Financial Health
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health-report` | Get scored health report |

---

## Health Scoring Algorithm

```
Overall Score (0–100) = weighted average of:

  Debt-to-Income Ratio   × 25%   (< 40% = ideal)
  Savings Rate           × 25%   (> 20% = ideal)
  CIBIL Score            × 25%   (750+ = ideal)
  Credit Utilisation     × 15%   (< 30% = ideal)
  Income Growth (ITR)    × 10%   (> 5% YoY = ideal)

Grades: A+ (≥90) · A (≥80) · B (≥70) · C (≥60) · D (≥50) · F (<50)
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Async PostgreSQL URL | **required** |
| `SECRET_KEY` | JWT signing secret (≥32 chars) | **required** |
| `ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token TTL | `60` |
| `ALLOWED_ORIGINS` | CORS origins (comma-separated) | `http://localhost:3000` |
| `UPLOAD_DIR` | Temp PDF storage path | `uploads` |
| `MAX_FILE_SIZE_MB` | Max PDF size | `20` |
| `DEBUG` | SQL logging + debug mode | `False` |

---

## Frontend Integration Notes

- All protected endpoints require `Authorization: Bearer <token>` header.
- PDF upload uses `multipart/form-data` with fields: `file` (PDF) and `document_type` (string).
- Upload returns **202 Accepted** — poll `/documents/status` to confirm processing.
- Health report is available once at least one PDF has been processed.
