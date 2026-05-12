import uuid
from datetime import datetime, timedelta, timezone

from config.settings import settings
from infrastructure.logging.logger import logger
from jose import JWTError, jwt
from models.refresh_token import is_refresh_token_active, revoke_refresh_token, save_refresh_token
from models.user import create_user, get_user_by_username
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    jti = str(uuid.uuid4())
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh", "jti": jti})
    token = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    save_refresh_token(data["user_id"], token, jti, expire.replace(tzinfo=None))
    return token


def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"Token decode failed: {e}")
        return None


def register_user(username: str, email: str, password: str) -> dict:
    existing = get_user_by_username(username)
    if existing:
        return {"success": False, "error": "用户名已存在"}
    hashed = hash_password(password)
    user = create_user(username, email, hashed)
    if user:
        return {"success": True, "user": user}
    return {"success": False, "error": "注册失败，请稍后重试"}


def login_user(username: str, password: str) -> dict:
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
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        return {"success": False, "error": "无效的刷新令牌"}

    jti = payload.get("jti", "")
    if not is_refresh_token_active(refresh_token, jti):
        return {"success": False, "error": "刷新令牌已失效或已撤销"}

    token_data = {"user_id": payload["user_id"], "username": payload["username"]}
    new_access_token = create_access_token(token_data)

    return {
        "success": True,
        "access_token": new_access_token,
        "token_type": "bearer",
    }


def logout_user(refresh_token: str) -> dict:
    payload = decode_token(refresh_token)
    if payload and payload.get("type") == "refresh":
        jti = payload.get("jti", "")
        revoke_refresh_token(refresh_token, jti)
    return {"success": True}
