from datetime import date
from ami import get_registered_aors

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from security import require_global, require_tenant_access

# Auth par tenant basculee sur JWT (login /auth/login) depuis cette session.
# /summary (vue globale) reste reserve au role "global". Les routes
# /tenants/{slug}/... acceptent un JWT global ou un JWT tenant dont le
# tenant_slug correspond au slug demande dans l'URL (voir
# security.require_tenant_access), sinon 403.
router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _get_tenant_or_404(db: Session, slug: str) -> models.Tenant:
    tenant = db.query(models.Tenant).filter(models.Tenant.slug == slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant '{slug}' introuvable")
    return tenant


def _tenant_summary(db: Session, tenant: models.Tenant) -> schemas.TenantDashboardSummary:
    nb_endpoints = (
        db.query(func.count(models.PsEndpoint.id))
        .filter(
            models.PsEndpoint.tenant_id == tenant.id,
            models.PsEndpoint.context.like("from-internal-%"),
        )
        .scalar()
    ) or 0

    nb_trunks = (
        db.query(func.count(models.PsEndpoint.id))
        .filter(
            models.PsEndpoint.tenant_id == tenant.id,
            models.PsEndpoint.context.like("from-trunk-%"),
        )
        .scalar()
    ) or 0

    today = date.today()
    appels_du_jour = (
        db.query(models.CdrFacture)
        .filter(
            models.CdrFacture.tenant_id == tenant.id,
            func.date(models.CdrFacture.date_heure_debut) == today,
        )
        .all()
    )

    duree_totale = sum(c.duree_secondes or 0 for c in appels_du_jour)
    cout_total = sum(float(c.cout_facture) for c in appels_du_jour if c.cout_facture is not None)
    devise = next((c.devise for c in appels_du_jour if c.devise), None)

    return schemas.TenantDashboardSummary(
        slug=tenant.slug,
        nom=tenant.nom,
        statut=tenant.statut,
        nb_endpoints=nb_endpoints,
        nb_trunks=nb_trunks,
        appels_aujourdhui=len(appels_du_jour),
        duree_totale_aujourdhui_secondes=duree_totale,
        cout_total_aujourdhui=cout_total,
        devise=devise,
    )


@router.get("/summary", response_model=schemas.GlobalDashboardSummary, dependencies=[Depends(require_global)])
def global_summary(db: Session = Depends(get_db)):
    """Vue admin global : résumé de tous les tenants (endpoints, trunks, activité du jour)."""
    tenants = db.query(models.Tenant).all()
    return schemas.GlobalDashboardSummary(
        nb_tenants=len(tenants),
        tenants=[_tenant_summary(db, t) for t in tenants],
    )


@router.get("/tenants/{slug}/summary", response_model=schemas.TenantDashboardSummary, dependencies=[Depends(require_tenant_access)])
def tenant_summary(slug: str, db: Session = Depends(get_db)):
    """Résumé d'un tenant précis. Accessible via JWT global ou JWT du tenant lui-même."""
    tenant = _get_tenant_or_404(db, slug)
    return _tenant_summary(db, tenant)


@router.get("/tenants/{slug}/calls", response_model=list[schemas.CallLogOut], dependencies=[Depends(require_tenant_access)])
def tenant_calls(slug: str, limit: int = 50, db: Session = Depends(get_db)):
    """Derniers appels facturés d'un tenant, du plus récent au plus ancien."""
    tenant = _get_tenant_or_404(db, slug)

    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit doit être entre 1 et 500")

    return (
        db.query(models.CdrFacture)
        .filter(models.CdrFacture.tenant_id == tenant.id)
        .order_by(models.CdrFacture.id.desc())
        .limit(limit)
        .all()
    )


@router.get("/tenants/{slug}/endpoints", response_model=list[schemas.EndpointStatusOut], dependencies=[Depends(require_tenant_access)])
async def tenant_endpoints_status(slug: str, db: Session = Depends(get_db)):
    """
    Postes actifs d'un tenant, avec statut d'enregistrement en direct
    (interrogation AMI). Si Asterisk est injoignable, on renvoie quand
    même la liste des postes configurés, juste sans statut live plutôt
    que de faire échouer toute la route.
    """
    tenant = _get_tenant_or_404(db, slug)

    ps_endpoints = (
        db.query(models.PsEndpoint)
        .filter(
            models.PsEndpoint.tenant_id == tenant.id,
            models.PsEndpoint.context.like("from-internal-%"),
        )
        .all()
    )

    try:
        registered = await get_registered_aors()
    except Exception:
        registered = {}

    users_by_extension = {
        u.extension: u
        for u in db.query(models.User).filter(models.User.tenant_id == tenant.id).all()
    }

    result = []
    for ep in ps_endpoints:
        extension = None
        try:
            extension = int(ep.id.split("-")[0])
        except (ValueError, IndexError):
            pass

        user = users_by_extension.get(extension) if extension is not None else None
        status = registered.get(ep.aors)

        result.append(schemas.EndpointStatusOut(
            endpoint_id=ep.id,
            extension=extension,
            nom=user.nom if user else None,
            registered=status is not None,
            status=status,
        ))

    return result
