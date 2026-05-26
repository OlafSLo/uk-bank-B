import os
import time
import psycopg2
import psycopg2.errors
from psycopg2.extras import RealDictCursor
from decimal import Decimal
from typing import Optional
from domain.entities import Account, User, UserRole, Card
from domain.value_objects import AccountNumber, Money, Currency
from domain.repositories import AccountRepository, UserRepository, CardRepository


def _wait_for_db(db_url: str, max_retries: int = 30, delay: float = 2.0):
    """Czeka, aż PostgreSQL będzie gotowy do przyjęcia połączeń."""
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            conn = psycopg2.connect(db_url, connect_timeout=2)
            conn.close()
            print(f"[DB] Połączono z PostgreSQL (próba {attempt})")
            return
        except Exception as e:
            last_error = e
            print(f"[DB] PostgreSQL niegotowy, próba {attempt}/{max_retries} za {delay}s... ({e})")
            time.sleep(delay)
    raise ConnectionError(f"[DB] Nie można połączyć się z PostgreSQL po {max_retries} próbach: {last_error}")


def _execute_with_retry(db_url: str, statements: list, max_retries: int = 15, delay: float = 2.0):
    """
    Wykonuje listę instrukcji SQL z ponawianiem.
    Używa autocommit=True, aby DDL (CREATE TABLE, ALTER TABLE) były trwale zatwierdzane.
    """
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            conn = psycopg2.connect(db_url, connect_timeout=3)
            conn.autocommit = True  # DDL zatwierdzane natychmiast
            cursor = conn.cursor()
            for stmt in statements:
                try:
                    cursor.execute(stmt)
                except psycopg2.errors.DuplicateColumn:
                    pass  # Ignoruj: kolumna już istnieje
                except psycopg2.errors.DuplicateTable:
                    pass  # Ignoruj: tabela już istnieje
                except Exception as e:
                    print(f"[DB] Błąd podczas wykonywania SQL: {e}")
                    raise
            cursor.close()
            conn.close()
            return
        except Exception as e:
            last_error = e
            print(f"[DB] Błąd wykonania SQL, próba {attempt}/{max_retries} za {delay}s... ({e})")
            time.sleep(delay)
    raise RuntimeError(f"[DB] Nie udało się wykonać SQL po {max_retries} próbach: {last_error}")


class PostgreSQLTransactionRepository:
    def __init__(self, db_url: str = None):
        if db_url is None:
            db_url = os.getenv("DATABASE_URL", "postgresql://bank_user:bank_pass@localhost:5432/bank_db")
        self.db_url = db_url
        _wait_for_db(self.db_url)
        self._init_db()

    def _init_db(self):
        """Tworzy tabelę transactions z ponawianiem i autocommit=TRUE."""
        _execute_with_retry(self.db_url, [
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id VARCHAR(36) PRIMARY KEY,
                sender_account VARCHAR(50),
                receiver_account VARCHAR(50),
                amount DECIMAL(15,2),
                currency VARCHAR(3),
                transfer_type VARCHAR(20),
                status VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sender_name VARCHAR(100)
            )
            """
        ])
        print("[DB] Tabela 'transactions' gotowa.")

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
            
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [dict(r) for r in rows]

    def get_by_id(self, tx_id: str):
        """Pobiera pojedynczą transakcję po ID."""
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM transactions WHERE id = %s", (tx_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return dict(row) if row else None

    def save(self, tx_id, sender, receiver, amount, currency, tx_type, status):
        """Zapisuje nową (lub aktualizuje status) transakcji w bazie danych."""
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO transactions (id, sender_account, receiver_account, amount, currency, transfer_type, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET status = EXCLUDED.status
        """, (tx_id, sender, receiver, amount, currency, tx_type, status))
        conn.commit()
        cursor.close()
        conn.close()

class PostgreSQLCardRepository(CardRepository):
    def __init__(self, db_url: str = None):
        if db_url is None:
            db_url = os.getenv("DATABASE_URL", "postgresql://bank_user:bank_pass@localhost:5432/bank_db")
        self.db_url = db_url
        _wait_for_db(self.db_url)
        self._init_db()

    def _init_db(self):
        _execute_with_retry(self.db_url, [
            """
            CREATE TABLE IF NOT EXISTS cards (
                card_number VARCHAR(16) PRIMARY KEY,
                account_number VARCHAR(8) NOT NULL,
                expiry_date VARCHAR(5) NOT NULL,
                cvv VARCHAR(3) NOT NULL,
                pin_hash TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                card_type VARCHAR(20) DEFAULT 'debit',
                daily_limit DECIMAL(15,2) DEFAULT 1000.00
            )
            """
        ])
        print("[DB] Tabela 'cards' gotowa.")

    def get_by_account(self, account_number: str) -> list[Card]:
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM cards WHERE account_number = %s", (account_number,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [
            Card(
                card_number=row['card_number'], account_number=row['account_number'],
                expiry_date=row['expiry_date'], cvv=row['cvv'], pin_hash=row['pin_hash'],
                is_active=row['is_active'], card_type=row['card_type'],
                daily_limit=Money(Decimal(str(row['daily_limit'])), Currency.GBP)
            ) for row in rows
        ]

    def get_by_number(self, card_number: str) -> Optional[Card]:
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM cards WHERE card_number = %s", (card_number,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not row:
            return None
        return Card(
            card_number=row['card_number'], account_number=row['account_number'],
            expiry_date=row['expiry_date'], cvv=row['cvv'], pin_hash=row['pin_hash'],
            is_active=row['is_active'], card_type=row['card_type'],
            daily_limit=Money(Decimal(str(row['daily_limit'])), Currency.GBP)
        )

    def save(self, card: Card) -> None:
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO cards (card_number, account_number, expiry_date, cvv, pin_hash, is_active, card_type, daily_limit)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (card_number) DO UPDATE SET
                is_active = EXCLUDED.is_active, pin_hash = EXCLUDED.pin_hash, daily_limit = EXCLUDED.daily_limit
        """, (
            card.card_number, card.account_number, card.expiry_date, card.cvv,
            card.pin_hash, card.is_active, card.card_type, float(card.daily_limit.amount) if card.daily_limit else 1000.00
        ))
        conn.commit()
        cursor.close()
        conn.close()
    

class PostgreSQLAccountRepository(AccountRepository):
    def __init__(self, db_url: str = None):
        if db_url is None:
            db_url = os.getenv("DATABASE_URL", "postgresql://bank_user:bank_pass@localhost:5432/bank_db")
        self.db_url = db_url
        _wait_for_db(self.db_url)
        self._init_db()

    def _init_db(self):
        """Tworzy tabelę accounts z ponawianiem i autocommit=TRUE."""
        _execute_with_retry(self.db_url, [
            """
            CREATE TABLE IF NOT EXISTS accounts (
                sort_code VARCHAR(6),
                account_number VARCHAR(8),
                balance DECIMAL(15,2),
                currency VARCHAR(3),
                debt_limit DECIMAL(15,2) DEFAULT 0.00,
                is_active BOOLEAN DEFAULT TRUE,
                account_type VARCHAR(20) DEFAULT 'standard',
                parent_account_number VARCHAR(8),
                PRIMARY KEY (sort_code, account_number)
            )
            """,
            "ALTER TABLE accounts ADD COLUMN IF NOT EXISTS debt_limit DECIMAL(15,2) DEFAULT 0.00",
            "ALTER TABLE accounts ADD COLUMN IF NOT EXISTS account_type VARCHAR(20) DEFAULT 'standard'",
            "ALTER TABLE accounts ADD COLUMN IF NOT EXISTS parent_account_number VARCHAR(8)"
        ])
        print("[DB] Tabela 'accounts' gotowa.")

    def get_by_id(self, account_id: AccountNumber) -> Optional[Account]:
        """Pobiera konto z bazy PostgreSQL i zamienia je na obiekt Pythonowy."""
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "SELECT balance, currency, debt_limit, is_active, account_type, parent_account_number FROM accounts WHERE sort_code = %s AND account_number = %s",
            (account_id.sort_code, account_id.account_number)
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if row is None:
            return None

        balance = Money(Decimal(str(row['balance'])), Currency(row['currency']))
        debt_limit = Money(Decimal(str(row['debt_limit'])), Currency(row['currency']))

        return Account(
            id=account_id, 
            balance=balance, 
            debt_limit=debt_limit, 
            is_active=row['is_active'],
            account_type=row['account_type'] or "standard",
            parent_account_number=row['parent_account_number']
        )

    def get_all(self) -> list[Account]:
        """Pobiera wszystkie konta z bazy PostgreSQL."""
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT sort_code, account_number, balance, currency, debt_limit, is_active, account_type, parent_account_number FROM accounts")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        accounts = []
        for row in rows:
            balance = Money(Decimal(str(row['balance'])), Currency(row['currency']))
            debt_limit = Money(Decimal(str(row['debt_limit'])), Currency(row['currency']))
            accounts.append(Account(
                id=AccountNumber(row['sort_code'], row['account_number']),
                balance=balance,
                debt_limit=debt_limit,
                is_active=row['is_active'],
                account_type=row['account_type'] or "standard",
                parent_account_number=row['parent_account_number']
            ))
        return accounts

    def save(self, account: Account) -> None:
        """Zapisuje obiekt konta jako wiersz w bazie PostgreSQL (dodaje nowe lub aktualizuje)."""
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO accounts (sort_code, account_number, balance, currency, debt_limit, is_active, account_type, parent_account_number)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (sort_code, account_number)
            DO UPDATE SET
                balance = EXCLUDED.balance,
                currency = EXCLUDED.currency,
                debt_limit = EXCLUDED.debt_limit,
                is_active = EXCLUDED.is_active,
                account_type = EXCLUDED.account_type,
                parent_account_number = EXCLUDED.parent_account_number
        """, (
            account.id.sort_code,
            account.id.account_number,
            float(account.balance.amount),  # Konwertujemy Decimal na float dla PostgreSQL
            account.balance.currency.value,
            float(account.debt_limit.amount),
            account.is_active,
            account.account_type,
            account.parent_account_number
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
        _wait_for_db(self.db_url)
        self._init_db()

    def _init_db(self):
        """Tworzy tabelę users z ponawianiem i autocommit=TRUE."""
        _execute_with_retry(self.db_url, [
            """
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR(36) PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role VARCHAR(20) NOT NULL DEFAULT 'customer',
                is_active BOOLEAN DEFAULT TRUE
            )
            """
        ])
        print("[DB] Tabela 'users' gotowa.")

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
