import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from security import require_global, require_tenant_access, hash_password

router = APIRouter(prefix="/tenants", tags=["tenants"])


def _generate_temp_password(length: int = 12) -> str:
    """
    Mot de passe temporaire lisible : lettres + chiffres, sans caracteres
    ambigus (pas de I/l/O/0), pour reduire le risque d'erreur de saisie
    quand l'admin global le communique au client par telephone ou message.
    """
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


@router.post("", response_model=schemas.TenantCreateOut, status_code=201, dependencies=[Depends(require_global)])
def create_tenant(payload: schemas.TenantCreate, db: Session = Depends(get_db)):
    """
    Reserve a l'admin global (voir security.require_global). Cree le tenant
    ET un compte admin-tenant associe (username admin_{slug}, mot de passe
    temporaire genere aleatoirement), pour que le tenant soit utilisable
    immediatement sans etape manuelle supplementaire.
    """
    existing = db.query(models.Tenant).filter(models.Tenant.slug == payload.slug).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Le tenant '{payload.slug}' existe déjà")

    if payload.plage_ext_fin <= payload.plage_ext_debut:
        raise HTTPException(status_code=400, detail="plage_ext_fin doit être supérieur à plage_ext_debut")

    tenant = models.Tenant(
        slug=payload.slug,
        nom=payload.nom,
        plage_ext_debut=payload.plage_ext_debut,
        plage_ext_fin=payload.plage_ext_fin,
        api_key=secrets.token_hex(32),
    )
    db.add(tenant)
    db.flush()

    admin_username = f"admin_{tenant.slug}"
    admin_temp_password = _generate_temp_password()

    existing_admin = db.query(models.AdminUser).filter(models.AdminUser.username == admin_username).first()
    if existing_admin:
        admin_username = f"{admin_username}_{secrets.token_hex(2)}"

    admin = models.AdminUser(
        username=admin_username,
        password_hash=hash_password(admin_temp_password),
        role="tenant",
        tenant_id=tenant.id,
    )
    db.add(admin)

    db.commit()
    db.refresh(tenant)

    return schemas.TenantCreateOut(
        id=tenant.id,
        slug=tenant.slug,
        nom=tenant.nom,
        plage_ext_debut=tenant.plage_ext_debut,
        plage_ext_fin=tenant.plage_ext_fin,
        statut=tenant.statut,
        api_key=tenant.api_key,
        admin_username=admin_username,
        admin_temp_password=admin_temp_password,
    )


@router.get("", response_model=list[schemas.TenantOut], dependencies=[Depends(require_global)])
def list_tenants(db: Session = Depends(get_db)):
    """Reserve a l'admin global : un admin-tenant n'a pas a voir la liste des autres tenants."""
    return db.query(models.Tenant).all()


@router.get("/{slug}", response_model=schemas.TenantOut, dependencies=[Depends(require_tenant_access)])
def get_tenant(slug: str, db: Session = Depends(get_db)):
    """Admin global ou admin du tenant demande (voir security.require_tenant_access)."""
    tenant = db.query(models.Tenant).filter(models.Tenant.slug == slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant introuvable")
    return tenant


@router.patch("/{slug}/statut", response_model=schemas.TenantOut, dependencies=[Depends(require_global)])
def update_tenant_statut(slug: str, payload: schemas.TenantStatutUpdate, db: Session = Depends(get_db)):
    """
    Active/desactive un tenant (reserve a l'admin global). Changement
    reversible, ne supprime aucune donnee : les postes SIP et comptes admin
    du tenant restent en base, seul le champ statut change. A utiliser
    plutot que DELETE pour une suspension temporaire (client en impaye,
    litige, etc.).
    """
    tenant = db.query(models.Tenant).filter(models.Tenant.slug == slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant introuvable")

    tenant.statut = payload.statut
    db.commit()
    db.refresh(tenant)
    return tenant


@router.delete("/{slug}", status_code=204, dependencies=[Depends(require_global)])
def delete_tenant(slug: str, db: Session = Depends(get_db)):
    """
    Suppression definitive (reserve a l'admin global). IRREVERSIBLE.

    AdminUser, User et PsEndpoint ont un ondelete='CASCADE' vers tenants.id
    et seront supprimes automatiquement. En revanche PsAuth/PsAor/
    PsRegistration/PsEndpointIdIp sont lies par convention de nommage
    ('{extension}-{slug}'), pas par cle etrangere : on les nettoie donc
    explicitement ici pour eviter des lignes PJSIP orphelines qui
    resteraient actives cote Asterisk (ARA) apres suppression du tenant.
    Les lignes 'extensions' (dialplan realtime) du contexte du tenant sont
    egalement supprimees.
    """
    tenant = db.query(models.Tenant).filter(models.Tenant.slug == slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant introuvable")

    endpoint_ids = [
        ep.id for ep in
        db.query(models.PsEndpoint).filter(models.PsEndpoint.tenant_id == tenant.id).all()
    ]

    for ep_id in endpoint_ids:
        db.query(models.PsAuth).filter(models.PsAuth.id == ep_id).delete()
        db.query(models.PsAor).filter(models.PsAor.id == ep_id).delete()
        db.query(models.PsRegistration).filter(models.PsRegistration.id == ep_id).delete()
        db.query(models.PsEndpointIdIp).filter(models.PsEndpointIdIp.endpoint == ep_id).delete()

    internal_context = f"from-internal-{tenant.slug}"
    trunk_context = f"from-trunk-{tenant.slug}"
    db.query(models.Extension).filter(
        models.Extension.context.in_([internal_context, trunk_context])
    ).delete(synchronize_session=False)

    db.delete(tenant)  # cascade : admin_users, users, ps_endpoints
    db.commit()
    return None
