from datetime import datetime, timedelta
from domain.repositories import TransactionRepository

class ArchivingService:
    def __init__(self, operational_repo, archive_repo):
        self.op_repo = operational_repo  # Postgres (bieżące)
        self.arc_repo = archive_repo     # Data Lake (archiwum)

    def run_archivization(self):
        """Przenosi transakcje starsze niż 30 dni do Data Lake"""
        cutoff_date = datetime.now() - timedelta(days=30)
        old_transactions = self.op_repo.get_older_than(cutoff_date)
        
        if old_transactions:
            self.arc_repo.save_many(old_transactions)
            self.op_repo.delete_many(old_transactions)
            print(f"Zarchiwizowano {len(old_transactions)} transakcji.")

    def get_all_history(self, sender_name=None, start_date=None, end_date=None):
        """Łączy dane z obu warstw i filtruje (wymóg na 4.0/5.0)"""
        # 1. Pobierz z bazy operacyjnej
        recent = self.op_repo.search(sender_name, start_date, end_date)
        
        # 2. Pobierz z Data Lake
        archived = self.arc_repo.search(sender_name, start_date, end_date)
        
        return recent + archived