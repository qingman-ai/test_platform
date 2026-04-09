# app/auth.py
# JWT 认证模块：负责 token 生成、验证、密码加密

import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .database import get_db
from . import models

# ========== 配置 ==========
SECRET_KEY = "your-secret-key-change-in-production"  # 生产环境务必改成随机长字符串
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24  # token 有效期 24 小时

# ========== 密码加密 ==========
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """对明文密码进行加密"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码是否匹配"""
    return pwd_context.verify(plain_password, hashed_password)


# ========== JWT Token ==========
def create_access_token(data: dict) -> str:
    """生成 JWT token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """解析 JWT token，失败则抛出异常"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token 已过期，请重新登录")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效的 Token")


# ========== FastAPI 依赖项：获取当前登录用户 ==========
security = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> models.User:
    """
    从请求中提取 token 并验证，返回当前用户对象。
    支持两种方式传 token：
    1. Header: Authorization: Bearer <token>
    2. Cookie: access_token=<token>（前端页面用这种方式）
    """
    token = None

    # 优先从 Header 获取
    if credentials:
        token = credentials.credentials
    else:
        # 从 Cookie 获取（前端页面登录后存在 cookie 里）
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(status_code=401, detail="未登录，请先登录")

    payload = decode_access_token(token)
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="无效的 Token")

    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")

    return user
