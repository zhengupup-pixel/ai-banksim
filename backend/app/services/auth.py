import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.entities import AuthToken, User


PBKDF2_ITERATIONS = 310_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${derived.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_hex, expected_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        derived = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(derived.hex(), expected_hex)
    except (ValueError, TypeError):
        return False


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class AuthenticationError(Exception):
    pass


class AuthService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()

    def authenticate(self, username: str, password: str) -> User:
        user = self.db.query(User).filter(User.username == username).first()
        if user is None or not user.is_active or not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid username or password")
        return user

    def issue_token(self, user: User) -> tuple[str, datetime]:
        raw_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
            hours=self.settings.auth_token_ttl_hours
        )
        self.db.add(AuthToken(user_id=user.id, token_hash=hash_token(raw_token), expires_at=expires_at))
        self.db.commit()
        return raw_token, expires_at

    def resolve_token(self, raw_token: str) -> tuple[AuthToken, User]:
        token = self.db.query(AuthToken).filter(AuthToken.token_hash == hash_token(raw_token)).first()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if token is None or token.revoked_at is not None or token.expires_at <= now:
            raise AuthenticationError("Invalid or expired access token")
        if not token.user.is_active:
            raise AuthenticationError("User account is disabled")
        return token, token.user

    def revoke(self, token: AuthToken) -> None:
        token.revoked_at = datetime.now(timezone.utc).replace(tzinfo=None)
        self.db.commit()
