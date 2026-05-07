from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional

from services.auth_service import register_user, login_user, refresh_access_token, decode_token
from infrastructure.logging.logger import logger

router = APIRouter(prefix="/api/auth", tags=["认证"])


# ==================== Request Models ====================

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


# ==================== Dependency ====================

async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """Extract and validate user from Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供认证令牌")

    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)

    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="无效的访问令牌")

    return {"user_id": payload["user_id"], "username": payload["username"]}


# ==================== Routes ====================

@router.post("/register", summary="用户注册")
async def register(request: RegisterRequest):
    """Register a new user."""
    if len(request.password) < 6:
        raise HTTPException(status_code=400, detail="密码长度不能少于6位")

    result = register_user(request.username, request.email, request.password)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return {"success": True, "message": "注册成功", "user": result["user"]}


@router.post("/login", summary="用户登录")
async def login(request: LoginRequest):
    """Login and get access + refresh tokens."""
    result = login_user(request.username, request.password)

    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["error"])

    return result


@router.post("/refresh", summary="刷新令牌")
async def refresh(request: RefreshRequest):
    """Refresh access token using refresh token."""
    result = refresh_access_token(request.refresh_token)

    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["error"])

    return result


@router.get("/me", summary="获取当前用户")
async def me(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user info."""
    return {"success": True, "user": current_user}
