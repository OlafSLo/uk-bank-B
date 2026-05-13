import jwt
import datetime
from passlib.hash import bcrypt
from domain.entities import User, UserRole

SECRET_KEY = "TWOJ_TAJNY_KLUCZ_Z_ENV" # W produkcji bierzemy z os.getenv

class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hash(password)

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        return bcrypt.verify(password, hashed)

    @staticmethod
    def generate_token(user: User) -> str:
        payload = {
            "sub": user.id,
            "username": user.username,
            "role": user.role.value,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=8)
        }
        return jwt.encode(payload, SECRET_KEY, algorithm="HS256")