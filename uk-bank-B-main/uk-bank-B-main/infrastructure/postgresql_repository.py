import os
import psycopg2
from psycopg2.extras import RealDictCursor
from decimal import Decimal
from typing import Optional

from domain.entities import Account
from domain.value_objects import AccountNumber, Money, Currency
from domain.repositories import AccountRepository


class PostgreSQLAccountRepository(AccountRepository):
    def __init__(self, db_url: str = None):
        if db_url is None:
            db_url = os.getenv("DATABASE_URL", "postgresql://bank_user:bank_pass@localhost:5432/bank_db")
        self.db_url = db_url
        self._init_db()

    def _init_db(self):
        """Tworzy tabelę w bazie, jeśli jeszcze nie istnieje."""
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                sort_code VARCHAR(6),
                account_number VARCHAR(8),
                balance DECIMAL(15,2),  -- Używamy DECIMAL dla precyzji pieniężnej
                currency VARCHAR(3),
                is_active BOOLEAN DEFAULT TRUE,
                PRIMARY KEY (sort_code, account_number)
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()

    def get_by_id(self, account_id: AccountNumber) -> Optional[Account]:
        """Pobiera konto z bazy PostgreSQL i zamienia je na obiekt Pythonowy."""
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "SELECT balance, currency, is_active FROM accounts WHERE sort_code = %s AND account_number = %s",
            (account_id.sort_code, account_id.account_number)
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if row is None:
            return None

        balance = Money(Decimal(str(row['balance'])), Currency(row['currency']))

        return Account(id=account_id, balance=balance, is_active=row['is_active'])

    def save(self, account: Account) -> None:
        """Zapisuje obiekt konta jako wiersz w bazie PostgreSQL (dodaje nowe lub aktualizuje)."""
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO accounts (sort_code, account_number, balance, currency, is_active)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (sort_code, account_number)
            DO UPDATE SET
                balance = EXCLUDED.balance,
                currency = EXCLUDED.currency,
                is_active = EXCLUDED.is_active
        """, (
            account.id.sort_code,
            account.id.account_number,
            float(account.balance.amount),  # Konwertujemy Decimal na float dla PostgreSQL
            account.balance.currency.value,
            account.is_active
        ))
        conn.commit()
        cursor.close()
        conn.close()