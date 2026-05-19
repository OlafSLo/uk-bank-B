import os
import psycopg2
import psycopg2.errors
from psycopg2.extras import RealDictCursor
from decimal import Decimal
from typing import Optional

from domain.entities import Account, User, UserRole
from domain.value_objects import AccountNumber, Money, Currency
from domain.repositories import AccountRepository, UserRepository

class PostgreSQLTransactionRepository:
    def search(self, sender_name=None, start_date=None, end_date=None):
        query = "SELECT * FROM transactions WHERE 1=1"
        params = []
        
        if sender_name:
            query += " AND sender_name ILIKE %s"
            params.append(f"%{sender_name}%")
        if start_date:
            query += " AND created_at >= %s"
            params.append(start_date)
        if end_date:
            query += " AND created_at <= %s"
            params.append(end_date)
            
        
        return self.db.execute(query, params)
    
class PostgreSQLAccountRepository(AccountRepository):
    def __init__(self, db_url: str = None):
        if db_url is None:
            db_url = os.getenv("DATABASE_URL", "postgresql://bank_user:bank_pass@localhost:5432/bank_db")
        self.db_url = db_url
        self._init_db()

    def _init_db(self):
        """Tworzy tabelę w bazie, jeśli jeszcze nie istnieje, i dodaje brakujące kolumny."""
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                sort_code VARCHAR(6),
                account_number VARCHAR(8),
                balance DECIMAL(15,2),
                currency VARCHAR(3),
                debt_limit DECIMAL(15,2) DEFAULT 0.00,
                is_active BOOLEAN DEFAULT TRUE,
                PRIMARY KEY (sort_code, account_number)
            )
        """)
        # Migracja: dodaj kolumnę debt_limit jeśli nie istnieje (dla istniejących tabel)
        try:
            cursor.execute("ALTER TABLE accounts ADD COLUMN debt_limit DECIMAL(15,2) DEFAULT 0.00")
        except psycopg2.errors.DuplicateColumn:
            pass  # Kolumna już istnieje - ignorujemy błąd
        conn.commit()
        cursor.close()
        conn.close()

    def get_by_id(self, account_id: AccountNumber) -> Optional[Account]:
        """Pobiera konto z bazy PostgreSQL i zamienia je na obiekt Pythonowy."""
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "SELECT balance, currency, debt_limit, is_active FROM accounts WHERE sort_code = %s AND account_number = %s",
            (account_id.sort_code, account_id.account_number)
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if row is None:
            return None

        balance = Money(Decimal(str(row['balance'])), Currency(row['currency']))
        debt_limit = Money(Decimal(str(row['debt_limit'])), Currency(row['currency']))

        return Account(id=account_id, balance=balance, debt_limit=debt_limit, is_active=row['is_active'])

    def save(self, account: Account) -> None:
        """Zapisuje obiekt konta jako wiersz w bazie PostgreSQL (dodaje nowe lub aktualizuje)."""
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO accounts (sort_code, account_number, balance, currency, debt_limit, is_active)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (sort_code, account_number)
            DO UPDATE SET
                balance = EXCLUDED.balance,
                currency = EXCLUDED.currency,
                debt_limit = EXCLUDED.debt_limit,
                is_active = EXCLUDED.is_active
        """, (
            account.id.sort_code,
            account.id.account_number,
            float(account.balance.amount),  # Konwertujemy Decimal na float dla PostgreSQL
            account.balance.currency.value,
            float(account.debt_limit.amount),
            account.is_active
        ))
        conn.commit()
        cursor.close()
        conn.close()


class PostgreSQLUserRepository(UserRepository):
    """Repozytorium użytkowników dla PostgreSQL."""

    def __init__(self, db_url: str = None):
        if db_url is None:
            db_url = os.getenv("DATABASE_URL", "postgresql://bank_user:bank_pass@localhost:5432/bank_db")
        self.db_url = db_url
        self._init_db()

    def _init_db(self):
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR(36) PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role VARCHAR(20) NOT NULL DEFAULT 'customer',
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()

    def get_by_id(self, user_id: str) -> Optional[User]:
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "SELECT id, username, password_hash, role, is_active FROM users WHERE id = %s",
            (user_id,)
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if row is None:
            return None

        return User(
            id=row['id'],
            username=row['username'],
            password_hash=row['password_hash'],
            role=UserRole(row['role']),
            is_active=row['is_active']
        )

    def get_by_username(self, username: str) -> Optional[User]:
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "SELECT id, username, password_hash, role, is_active FROM users WHERE username = %s",
            (username,)
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if row is None:
            return None

        return User(
            id=row['id'],
            username=row['username'],
            password_hash=row['password_hash'],
            role=UserRole(row['role']),
            is_active=row['is_active']
        )

    def save(self, user: User) -> None:
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (id, username, password_hash, role, is_active)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (id)
            DO UPDATE SET
                username = EXCLUDED.username,
                password_hash = EXCLUDED.password_hash,
                role = EXCLUDED.role,
                is_active = EXCLUDED.is_active
        """, (
            user.id,
            user.username,
            user.password_hash,
            user.role.value,
            user.is_active
        ))
        conn.commit()
        cursor.close()
        conn.close()