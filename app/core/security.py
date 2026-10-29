"""密碼雜湊 + JWT。

- bcrypt：自帶 salt，慢雜湊抵抗暴力破解（OWASP A04 Cryptographic Failures）
- JWT 內只放 user_id / store_id / role，不放敏感資料
"""
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import get_settings


def hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode()


def verify_password(raw: str, hashed: str) -> bool:
    return bcrypt.checkpw(raw.encode(), hashed.encode())


def create_access_token(user_id: int, store_id: int, role: str) -> str:
    s = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "store_id": store_id,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=s.jwt_expire_minutes),
    }
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def decode_token(token: str) -> dict:
    s = get_settings()
    # 明確指定 algorithms，防止 alg=none 攻擊
    return jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
