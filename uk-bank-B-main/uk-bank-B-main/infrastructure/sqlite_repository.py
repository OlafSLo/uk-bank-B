import sqlite3
from decimal import Decimal
from typing import Optional

from domain.entities import Account
from domain.value_objects import AccountNumber, Money, Currency
from domain.repositories import AccountRepository


class SQLiteAccountRepository(AccountRepository):
    def __init__(self, db_path: str = "bank.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Tworzy tabelę w bazie, jeśli jeszcze nie istnieje."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    sort_code TEXT,
                    account_number TEXT,
                    balance TEXT, -- Używamy TEXT dla Decimal, aby nie tracić precyzji w SQLite
                    currency TEXT,
                    debt_limit TEXT DEFAULT '0.00',
                    is_active BOOLEAN,
                    PRIMARY KEY (sort_code, account_number)
                )
            """)
            conn.commit()

    def get_by_id(self, account_id: AccountNumber) -> Optional[Account]:
        """Pobiera konto z bazy SQL i zamienia je z powrotem na obiekt Pythonowy."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT balance, currency, debt_limit, is_active FROM accounts WHERE sort_code = ? AND account_number = ?",
                (account_id.sort_code, account_id.account_number)
            )
            row = cursor.fetchone()

            if row is None:
                return None

            balance_str, currency_str, debt_limit_str, is_active = row
            balance = Money(Decimal(balance_str), Currency(currency_str))
            debt_limit = Money(Decimal(debt_limit_str), Currency(currency_str))

            return Account(id=account_id, balance=balance, debt_limit=debt_limit, is_active=bool(is_active))

    def save(self, account: Account) -> None:
        """Zapisuje obiekt konta jako wiersz w bazie SQL (dodaje nowe lub aktualizuje)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO accounts (sort_code, account_number, balance, currency, debt_limit, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(sort_code, account_number)
                DO UPDATE SET balance=excluded.balance, debt_limit=excluded.debt_limit, is_active=excluded.is_active
            """, (
                account.id.sort_code,
                account.id.account_number,
                str(account.balance.amount),
                account.balance.currency.value,
                str(account.debt_limit.amount),
                account.is_active
            ))
            conn.commit()