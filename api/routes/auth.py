"""Authentication routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from api.auth import create_access_token, get_current_user
from api.schemas import LoginRequest, TokenResponse
from config.settings import settings

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """用户登录，验证成功返回 JWT 令牌。"""
    if (
        request.username != settings.ADMIN_USERNAME
        or request.password != settings.ADMIN_PASSWORD
    ):
        logger.warning(f"Login failed for user: {request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    token = create_access_token(data={"sub": request.username})
    logger.info(f"User {request.username} logged in successfully.")
    return TokenResponse(access_token=token)


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """获取当前登录用户信息。"""
    return {
        "username": current_user["username"],
        "role": "admin",
    }
