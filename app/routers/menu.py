from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import CurrentUser, current_user, require_owner
from app.models import AuditLog, MenuItem, Store
from app.schemas import MenuItemIn, MenuItemOut, MenuItemUpdate, StoreOut

router = APIRouter(tags=["menu"])


def _get_own_item(db: Session, item_id: int, store_id: int) -> MenuItem:
    item = db.get(MenuItem, item_id)
    # 別家店的資料一律回 404（不回 403，避免洩漏資源存在與否）
    if item is None or item.store_id != store_id or item.is_archived:
        raise HTTPException(404, "品項不存在")
    return item


# ---------- 後台（需登入） ----------
@router.get("/api/menu", response_model=list[MenuItemOut])
def list_menu(user: CurrentUser = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(select(MenuItem).where(MenuItem.store_id == user.store_id, ~MenuItem.is_archived)
                      .order_by(MenuItem.id)).all()


@router.post("/api/menu", response_model=MenuItemOut, status_code=201)
def create_item(data: MenuItemIn, owner: CurrentUser = Depends(require_owner), db: Session = Depends(get_db)):
    item = MenuItem(store_id=owner.store_id, **data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/api/menu/{item_id}", response_model=MenuItemOut)
def update_item(item_id: int, data: MenuItemUpdate,
                user: CurrentUser = Depends(current_user), db: Session = Depends(get_db)):
    item = _get_own_item(db, item_id, user.store_id)
    changes = data.model_dump(exclude_unset=True)
    # 店員只能切換售完狀態；改名、改價需店主
    if user.role != "owner" and set(changes) - {"is_available"}:
        raise HTTPException(403, "店員僅能切換售完狀態")
    if "price" in changes and changes["price"] != item.price:
        db.add(AuditLog(store_id=user.store_id, user_id=user.id, action="menu.price",
                        detail=f"item={item.id} {item.price}->{changes['price']}"))
    for k, v in changes.items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/api/menu/{item_id}", status_code=204)
def delete_item(item_id: int, owner: CurrentUser = Depends(require_owner), db: Session = Depends(get_db)):
    item = _get_own_item(db, item_id, owner.store_id)
    # 軟刪除：歷史訂單仍引用此品項
    item.is_available = False
    item.is_archived = True
    db.add(AuditLog(store_id=owner.store_id, user_id=owner.id, action="menu.archive", detail=f"item={item.id}"))
    db.commit()


# ---------- 公開（顧客端） ----------
@router.get("/api/public/stores/{slug}/menu", response_model=list[MenuItemOut])
def public_menu(slug: str, db: Session = Depends(get_db)):
    store = db.scalar(select(Store).where(Store.slug == slug))
    if store is None:
        raise HTTPException(404, "店家不存在")
    q = select(MenuItem).where(MenuItem.store_id == store.id, MenuItem.is_available, ~MenuItem.is_archived)
    return db.scalars(q.order_by(MenuItem.id)).all()


@router.get("/api/public/stores/{slug}", response_model=StoreOut)
def public_store(slug: str, db: Session = Depends(get_db)):
    """顧客端：店名、是否營業中。"""
    store = db.scalar(select(Store).where(Store.slug == slug))
    if store is None:
        raise HTTPException(404, "店家不存在")
    return store
