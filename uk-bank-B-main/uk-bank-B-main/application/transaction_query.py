from dataclasses import dataclass
from infrastructure.archive_service import ArchivingService


@dataclass
class GetTransactionHistoryUseCase:
    archive_service: ArchivingService

    def execute(self, filters: dict):
        return self.archive_service.get_all_history(
            sender_name=filters.get("sender"),
            start_date=filters.get("from"),
            end_date=filters.get("to")
        )
