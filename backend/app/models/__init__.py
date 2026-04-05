"""
models/__init__.py
──────────────────
Re-export all ORM models so Alembic's `env.py` only needs:

    from app.models import *  # noqa: F401, F403
"""

from app.models.investment import Investment as Investment
from app.models.loan import Loan as Loan
from app.models.user import User as User

__all__ = ["User", "Loan", "Investment"]
