from datetime import datetime, timedelta, timezone
from typing import Optional

from passlib.context import CryptContext
from jose import JWTError, jwt

from config.settings import settings
from models.user import get_user_by_username, create_user
from infrastructure.logging.logger import logger

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"Token decode failed: {e}")
        return None


def register_user(username: str, email: str, password: str) -> dict:
    """Register a new user."""
    existing = get_user_by_username(username)
    if existing:
        return {"success": False, "error": "用户名已存在"}

    hashed = hash_password(password)
    user = create_user(username, email, hashed)
    if user:
        return {"success": True, "user": user}
    return {"success": False, "error": "注册失败，请稍后重试"}


def login_user(username: str, password: str) -> dict:
    """Authenticate user and return tokens."""
    user = get_user_by_username(username)
    if not user:
        return {"success": False, "error": "用户名或密码错误"}

    if not user["is_active"]:
        return {"success": False, "error": "账号已被禁用"}

    if not verify_password(password, user["hashed_password"]):
        return {"success": False, "error": "用户名或密码错误"}

    token_data = {"user_id": user["id"], "username": user["username"]}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return {
        "success": True,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {"id": user["id"], "username": user["username"]},
    }


def refresh_access_token(refresh_token: str) -> dict:
    """Refresh an access token using a refresh token."""
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        return {"success": False, "error": "无效的刷新令牌"}

    token_data = {"user_id": payload["user_id"], "username": payload["username"]}
    new_access_token = create_access_token(token_data)

    return {
        "success": True,
        "access_token": new_access_token,
        "token_type": "bearer",
    }
