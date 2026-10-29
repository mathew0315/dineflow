"""共用依賴：身分驗證 + 權限控管（OWASP A01 Broken Access Control / A07 Auth Failures）。"""
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db import get_db
from app.models import Role, User

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    id: int
    store_id: int
    role: Role


def current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> CurrentUser:
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "未登入或憑證無效",
                                 headers={"WWW-Authenticate": "Bearer"})
    if cred is None:
        raise unauthorized
    try:
        payload = decode_token(cred.credentials)
    except jwt.PyJWTError:
        raise unauthorized from None

    # 以資料庫為準：帳號被刪除或角色變更後，舊 token 立即失效於權限判斷
    user = db.get(User, int(payload["sub"]))
    if user is None or user.store_id != payload.get("store_id"):
        raise unauthorized
    return CurrentUser(id=user.id, store_id=user.store_id, role=Role(user.role))


def require_owner(user: CurrentUser = Depends(current_user)) -> CurrentUser:
    if user.role != Role.OWNER:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "需要店主權限")
    return user
