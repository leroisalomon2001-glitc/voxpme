import os
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import Header, HTTPException, Depends

_JWT_SECRET = os.environ.get("JWT_SECRET_KEY")
_JWT_ALGO = "HS256"
_JWT_EXPIRY_HOURS = 12


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(admin_id: int, role: str, tenant_slug: str | None) -> str:
    if not _JWT_SECRET:
        raise HTTPException(status_code=500, detail="JWT_SECRET_KEY non configuree cote serveur")
    payload = {
        "sub": str(admin_id),
        "role": role,
        "tenant_slug": tenant_slug,
        "exp": datetime.now(timezone.utc) + timedelta(hours=_JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGO)


def _decode(token: str) -> dict:
    if not _JWT_SECRET:
        raise HTTPException(status_code=500, detail="JWT_SECRET_KEY non configuree cote serveur")
    try:
        return jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGO])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expiree, reconnecte-toi")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token invalide")


def get_current_admin(authorization: str = Header(None)) -> dict:
    """Lit 'Authorization: Bearer <token>', renvoie {"role", "tenant_slug"}."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentification requise")
    token = authorization.removeprefix("Bearer ").strip()
    payload = _decode(token)
    return {"role": payload["role"], "tenant_slug": payload.get("tenant_slug")}


def require_global(admin: dict = Depends(get_current_admin)) -> dict:
    """A utiliser sur les routes reservees a l'admin global (ex: /dashboard/summary)."""
    if admin["role"] != "global":
        raise HTTPException(status_code=403, detail="Reserve a l'admin global")
    return admin


def require_tenant_access(slug: str, admin: dict = Depends(get_current_admin)) -> dict:
    """
    A utiliser sur les routes /dashboard/tenants/{slug}/... . Autorise :
    - un admin global (accede a tout tenant) ;
    - un admin tenant dont le tenant_slug du JWT correspond au slug demande.
    Bloque un admin tenant qui tenterait de lire un autre tenant (403).
    """
    if admin["role"] == "global":
        return admin
    if admin["role"] == "tenant" and admin["tenant_slug"] == slug:
        return admin
    raise HTTPException(status_code=403, detail="Acces refuse a ce tenant")
