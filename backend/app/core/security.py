"""安全工具：JWT 签发/解析与密码哈希。

- 密码：passlib + bcrypt（不可逆哈希）
- JWT：python-jose + HS256，payload 固定包含 sub / uid / username / role / iat / exp

注意：bcrypt 只使用密码的前 72 字节，超长密码必须先拦截，
否则「前 72 字节相同」的不同密码会被判定为同一密码。
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from loguru import logger
from passlib.context import CryptContext

from app.core.config import settings

__all__ = [
    "BCRYPT_MAX_PASSWORD_BYTES",
    "create_access_token",
    "decode_token",
    "hash_password",
    "pwd_context",
    "verify_password",
]

# bcrypt 支持的密码最大字节数
BCRYPT_MAX_PASSWORD_BYTES: int = 72

pwd_context: CryptContext = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """生成 bcrypt 哈希；密码超过 72 字节时抛 `ValueError`。"""
    if len(password.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError(f"密码过长，bcrypt 最多支持 {BCRYPT_MAX_PASSWORD_BYTES} 字节")
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """校验明文密码；哈希为空或格式非法时返回 False，不抛异常。"""
    if not password_hash:
        return False
    try:
        return pwd_context.verify(plain_password, password_hash)
    except (TypeError, ValueError) as exc:
        logger.warning("密码校验失败（哈希格式非法）：{}", exc)
        return False


def create_access_token(
    user_id: int,
    username: str,
    role: str,
    expires_minutes: int | None = None,
) -> str:
    """签发 HS256 access token。"""
    minutes = expires_minutes or settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "uid": user_id,
        "username": username,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_token(token: str) -> dict[str, Any] | None:
    """解析并校验 token；签名错误、已过期或格式非法时返回 None。"""
    if not token:
        return None
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError as exc:
        logger.info("token 解析失败：{}", exc)
        return None
