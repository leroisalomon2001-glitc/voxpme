from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from security import hash_password, verify_password, create_access_token, require_global

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=schemas.LoginResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    admin = db.query(models.AdminUser).filter(models.AdminUser.username == payload.username).first()
    if not admin or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="Identifiants invalides")

    tenant_slug = admin.tenant.slug if admin.tenant_id else None
    token = create_access_token(admin.id, admin.role, tenant_slug)
    return schemas.LoginResponse(access_token=token, role=admin.role, tenant_slug=tenant_slug)


@router.post("/admins", response_model=schemas.AdminOut, status_code=201, dependencies=[Depends(require_global)])
def create_admin(payload: schemas.AdminCreate, db: Session = Depends(get_db)):
    """Reserve a l'admin global : cree un compte admin global ou tenant."""
    if db.query(models.AdminUser).filter(models.AdminUser.username == payload.username).first():
        raise HTTPException(status_code=409, detail="Ce nom d'utilisateur existe deja")

    tenant_id = None
    if payload.role == "tenant":
        if not payload.tenant_slug:
            raise HTTPException(status_code=400, detail="tenant_slug requis pour un role 'tenant'")
        tenant = db.query(models.Tenant).filter(models.Tenant.slug == payload.tenant_slug).first()
        if not tenant:
            raise HTTPException(status_code=404, detail=f"Tenant '{payload.tenant_slug}' introuvable")
        tenant_id = tenant.id

    admin = models.AdminUser(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=payload.role,
        tenant_id=tenant_id,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    return schemas.AdminOut(
        id=admin.id, username=admin.username, role=admin.role,
        tenant_slug=payload.tenant_slug if payload.role == "tenant" else None,
    )
