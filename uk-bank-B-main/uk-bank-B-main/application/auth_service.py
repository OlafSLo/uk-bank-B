import jwt
import datetime
import uuid
import bcrypt as _bcrypt
from domain.entities import User, UserRole
from domain.repositories import UserRepository

SECRET_KEY = "TWOJ_TAJNY_KLUCZ_Z_ENV" # W produkcji bierzemy z os.getenv

class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        return _bcrypt.hashpw(password.encode('utf-8'), _bcrypt.gensalt()).decode('utf-8')

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        return _bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

    @staticmethod
    def generate_token(user: User) -> str:
        payload = {
            "sub": user.id,
            "username": user.username,
            "role": user.role.value,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=8)
        }
        return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

    @staticmethod
    def decode_token(token: str) -> dict:
        try:
            return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None


class AuthUseCase:
    """Przypadek użycia: rejestracja i logowanie użytkowników."""

    def __init__(self, user_repository: UserRepository, auth_service: AuthService):
        self.user_repo = user_repository
        self.auth_service = auth_service

    def register(self, username: str, password: str, role: str = "customer") -> dict:
        existing = self.user_repo.get_by_username(username)
        if existing:
            raise ValueError(f"Użytkownik '{username}' już istnieje.")

        user_id = str(uuid.uuid4())
        password_hash = self.auth_service.hash_password(password)
        user_role = UserRole(role) if role in [e.value for e in UserRole] else UserRole.CUSTOMER

        user = User(
            id=user_id,
            username=username,
            password_hash=password_hash,
            role=user_role
        )
        self.user_repo.save(user)
        return {
            "status": "OK",
            "message": f"Użytkownik '{username}' zarejestrowany pomyślnie.",
            "user_id": user_id
        }

    def login(self, username: str, password: str) -> dict:
        user = self.user_repo.get_by_username(username)
        if not user:
            raise ValueError("Nieprawidłowa nazwa użytkownika lub hasło.")

        if not self.auth_service.verify_password(password, user.password_hash):
            raise ValueError("Nieprawidłowa nazwa użytkownika lub hasło.")

        token = self.auth_service.generate_token(user)
        return {
            "status": "OK",
            "token": token,
            "username": user.username,
            "role": user.role.value
        }

    def get_user_from_token(self, token: str) -> User:
        payload = self.auth_service.decode_token(token)
        if not payload:
            return None
        return self.user_repo.get_by_id(payload["sub"])