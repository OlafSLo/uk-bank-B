from dataclasses import dataclass
from decimal import Decimal
from domain.value_objects import AccountNumber, Money
from domain.repositories import AccountRepository
from domain.entities import User, UserRole

@dataclass
class EmployeeUseCase:
    account_repository: AccountRepository

    def _verify_employee(self, user: User):
        """Zabezpieczenie przed nieautoryzowanym dostępem."""
        if not user or user.role != UserRole.BANK_EMPLOYEE:
            raise PermissionError("Brak uprawnień. Akcja wymaga autoryzacji pracownika banku.")

    def get_all_accounts(self, employee: User):
        self._verify_employee(employee)
        return self.account_repository.get_all()

    def toggle_account_status(self, employee: User, sort_code: str, account_number: str, is_active: bool):
        """Zamraża (blokuje) lub odmraża konto klienta."""
        self._verify_employee(employee)
        acc = self.account_repository.get_by_id(AccountNumber(sort_code, account_number))
        if not acc:
            raise ValueError("Konto nie istnieje.")
        
        acc.is_active = is_active
        self.account_repository.save(acc)

    def set_debt_limit(self, employee: User, sort_code: str, account_number: str, limit_amount: Decimal):
        """Ustawia limit zadłużenia (overdraft) na koncie."""
        self._verify_employee(employee)
        acc = self.account_repository.get_by_id(AccountNumber(sort_code, account_number))
        if not acc:
            raise ValueError("Konto nie istnieje.")
            
        acc.debt_limit = Money(limit_amount, acc.balance.currency)
        self.account_repository.save(acc)