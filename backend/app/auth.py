import os
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session

import models
from database import get_db

# Cle API pour l'API de provisioning (section 13.9 / J22).
# Injectee via .env / docker-compose.yml (PROVISIONING_API_KEY), jamais en dur.
_API_KEY = os.environ.get("PROVISIONING_API_KEY")


def require_api_key(x_api_key: str = Header(None)):
    """
    Dependance FastAPI : verifie le header X-API-Key contre la cle admin
    globale. A utiliser sur chaque route sensible non scopee a un tenant :
    Depends(require_api_key).
    """
    if not _API_KEY:
        raise HTTPException(
            status_code=500,
            detail="PROVISIONING_API_KEY non configuree cote serveur",
        )
    if x_api_key is None or x_api_key != _API_KEY:
        raise HTTPException(status_code=401, detail="Cle API invalide ou manquante")


def require_tenant_key(slug: str, x_api_key: str = Header(None), db: Session = Depends(get_db)):
    """
    Dependance FastAPI pour les routes scopees a un tenant precis (ex:
    /dashboard/tenants/{slug}/...). Autorise :
    - la cle admin globale (PROVISIONING_API_KEY), qui peut lire tout tenant ;
    - la cle propre au tenant demande dans l'URL (tenants.api_key).

    Empeche qu'un tenant lise les donnees d'un autre : la cle de t001 ne
    passe pas sur /tenants/t002/... (ajoute le 13/09/2026, voir J-suite).
    """
    if not _API_KEY:
        raise HTTPException(
            status_code=500,
            detail="PROVISIONING_API_KEY non configuree cote serveur",
        )
    if x_api_key == _API_KEY:
        return

    tenant = db.query(models.Tenant).filter(models.Tenant.slug == slug).first()
    if not tenant or not tenant.api_key or x_api_key != tenant.api_key:
        raise HTTPException(status_code=401, detail="Cle API invalide pour ce tenant")
