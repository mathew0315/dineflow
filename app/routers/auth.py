from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.db import get_db
from app.deps import CurrentUser, current_user, require_owner
from app.models import AuditLog, Role, Store, User
from app.schemas import LoginIn, RegisterStoreIn, StaffIn, TokenOut, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])

# 預先計算的假雜湊：帳號不存在時也跑一次 bcrypt，避免以回應時間探測帳號是否存在
_DUMMY_HASH = hash_password("dummy-password-for-timing")


@router.post("/register", response_model=TokenOut, status_code=201)
def register_store(data: RegisterStoreIn, db: Session = Depends(get_db)):
    """開店：建立租戶（店家）+ 店主帳號。"""
    if db.scalar(select(Store).where(Store.slug == data.slug)):
        raise HTTPException(409, "此店家代號已被使用")
    if db.scalar(select(User).where(User.email == data.email)):
        raise HTTPException(409, "此 Email 已註冊")
    store = Store(name=data.store_name, slug=data.slug)
    db.add(store)
    db.flush()
    owner = User(store_id=store.id, email=data.email,
                 password_hash=hash_password(data.password), role=Role.OWNER)
    db.add(owner)
    db.flush()
    db.add(AuditLog(store_id=store.id, user_id=owner.id, action="store.register"))
    db.commit()
    return TokenOut(access_token=create_access_token(owner.id, store.id, owner.role))


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email))
    ok = verify_password(data.password, user.password_hash if user else _DUMMY_HASH)
    if not user or not ok:
        # 統一錯誤訊息，不透露是帳號還是密碼錯（OWASP A07）
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "帳號或密碼錯誤")
    return TokenOut(access_token=create_access_token(user.id, user.store_id, user.role))


@router.post("/staff", response_model=UserOut, status_code=201)
def create_staff(data: StaffIn, owner: CurrentUser = Depends(require_owner), db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == data.email)):
        raise HTTPException(409, "此 Email 已註冊")
    staff = User(store_id=owner.store_id, email=data.email,
                 password_hash=hash_password(data.password), role=Role.STAFF)
    db.add(staff)
    db.flush()
    db.add(AuditLog(store_id=owner.store_id, user_id=owner.id, action="staff.create",
                    detail=f"staff={staff.id}"))
    db.commit()
    return staff


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser = Depends(current_user), db: Session = Depends(get_db)):
    return db.get(User, user.id)
