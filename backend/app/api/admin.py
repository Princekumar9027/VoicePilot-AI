from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.database.session import get_db
from app.models.entities import AuditLog, User
from app.schemas.auth import UserOut

router = APIRouter(prefix="/api/admin", tags=["admin"])


class UserPatch(BaseModel):
    is_active: bool | None = None
    role: str | None = None


@router.get("/users", response_model=list[UserOut])
def users(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return db.scalars(select(User).order_by(User.created_at.desc())).all()


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: str, body: UserPatch, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    if user.id == admin.id:
        raise HTTPException(400, "You cannot change your own role or status")
    detail = {}
    if body.is_active is not None:
        user.is_active = body.is_active
        detail["is_active"] = body.is_active
    if body.role is not None:
        if body.role not in ("USER", "ADMIN", "SUPPORT_AGENT"):
            raise HTTPException(400, "Invalid role")
        user.role = body.role
        detail["role"] = body.role
    db.add(AuditLog(actor_id=admin.id, action="admin.update_user", target=user.id, detail=detail))
    db.commit()
    return user


@router.get("/audit-logs")
def audit_logs(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(200)).all()
    return [
        {"id": r.id, "actor_id": r.actor_id, "action": r.action, "target": r.target, "detail": r.detail, "created_at": r.created_at}
        for r in rows
    ]
