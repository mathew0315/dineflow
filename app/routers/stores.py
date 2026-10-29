from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import CurrentUser, current_user, require_owner
from app.models import AuditLog, Store
from app.schemas import StoreOut, StoreUpdate

router = APIRouter(prefix="/api/store", tags=["store"])


@router.get("", response_model=StoreOut)
def my_store(user: CurrentUser = Depends(current_user), db: Session = Depends(get_db)):
    return db.get(Store, user.store_id)


@router.patch("", response_model=StoreOut)
def update_store(data: StoreUpdate, owner: CurrentUser = Depends(require_owner), db: Session = Depends(get_db)):
    store = db.get(Store, owner.store_id)
    changes = data.model_dump(exclude_unset=True)
    for k, v in changes.items():
        setattr(store, k, v)
    db.add(AuditLog(store_id=store.id, user_id=owner.id, action="store.update",
                    detail=",".join(sorted(changes))))
    db.commit()
    db.refresh(store)
    return store
