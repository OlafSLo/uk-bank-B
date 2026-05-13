import psycopg2
import time

def run_migration():
    # Dane do połączenia - upewnij się, że są zgodne z Twoim docker-compose.env
    conn_params = {
        "dbname": "bank_db",
        "user": "postgres",
        "password": "password",
        "host": "localhost",  # Jeśli odpalasz z venv na Windowsie
        "port": "5432"
    }

    sql_commands = [
        """
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role VARCHAR(20) NOT NULL,
            is_active BOOLEAN DEFAULT TRUE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS accounts (
            sort_code CHAR(6),
            account_number CHAR(8),
            user_id UUID REFERENCES users(id),
            parent_account_number CHAR(8),
            balance_amount DECIMAL(15, 2) DEFAULT 0.00,
            debt_limit DECIMAL(15, 2) DEFAULT 0.00,
            currency VARCHAR(3) DEFAULT 'GBP',
            is_active BOOLEAN DEFAULT TRUE,
            account_type VARCHAR(20) DEFAULT 'standard',
            PRIMARY KEY (sort_code, account_number)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id UUID PRIMARY KEY,
            sender_account CHAR(8),
            receiver_account CHAR(8),
            amount DECIMAL(15, 2) NOT NULL,
            currency VARCHAR(3) NOT NULL,
            transfer_type VARCHAR(20) NOT NULL,
            status VARCHAR(20) DEFAULT 'COMPLETED',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS archived_transactions (
            LIKE transactions INCLUDING ALL
        );
        """
    ]

    print("Łączenie z bazą danych...")
    try:
        # Próbujemy kilka razy, gdyby baza w Dockerze jeszcze wstawała
        for i in range(5):
            try:
                conn = psycopg2.connect(**conn_params)
                cur = conn.cursor()
                
                for command in sql_commands:
                    cur.execute(command)
                
                conn.commit()
                cur.close()
                conn.close()
                print("MIGRACJA ZAKOŃCZONA SUKCESEM! Tabele są gotowe.")
                return
            except Exception as e:
                print(f"Próba {i+1} nieudana, czekam... ({e})")
                time.sleep(2)
                
    except Exception as e:
        print(f"BŁĄD KRYTYCZNY: Nie udało się połączyć z bazą: {e}")

if __name__ == "__main__":
    run_migration()