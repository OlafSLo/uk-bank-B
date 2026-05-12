class DomainException(Exception):
    """Główna klasa dla błędów domenowych."""
    pass

class InsufficientFundsError(DomainException):
    """Błąd wyrzucany, gdy na koncie nie ma wystarczających środków."""
    pass

class InactiveAccountError(DomainException):
    """Błąd wyrzucany, gdy operacja jest wykonywana na nieaktywnym koncie."""
    pass