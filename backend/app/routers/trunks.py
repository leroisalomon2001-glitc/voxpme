from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from auth import require_api_key

router = APIRouter(prefix="/trunks", tags=["trunks"])


@router.post("", response_model=schemas.TrunkOut, status_code=201, dependencies=[Depends(require_api_key)])
def create_trunk(payload: schemas.TrunkCreate, db: Session = Depends(get_db)):
    tenant = db.query(models.Tenant).filter(models.Tenant.slug == payload.tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant '{payload.tenant_slug}' introuvable")

    existing = db.query(models.PsEndpoint).filter(models.PsEndpoint.id == payload.trunk_id).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Le trunk '{payload.trunk_id}' existe déjà")

    context = f"from-trunk-{tenant.slug}"
    auth_id = f"{payload.trunk_id}-auth"
    aor_id = f"{payload.trunk_id}-aor"
    identify_id = f"{payload.trunk_id}-identify"
    registration_id = f"{payload.trunk_id}-reg"

    auth = models.PsAuth(
        id=auth_id,
        auth_type="userpass",
        username=payload.sip_username,
        password=payload.sip_password,
    )
    db.add(auth)

    # Pas de contact statique : peuple dynamiquement par la registration
    # sortante (meme pattern que callcentric-trunk, voir journal J22).
    aor = models.PsAor(id=aor_id, max_contacts=1)
    db.add(aor)

    endpoint = models.PsEndpoint(
        id=payload.trunk_id,
        tenant_id=tenant.id,
        context=context,
        transport="transport-udp",
        outbound_auth=auth_id,
        aors=aor_id,
        disallow="all",
        allow=payload.allow,
        identify_by="username,ip",
    )
    db.add(endpoint)

    identify = models.PsEndpointIdIp(
        id=identify_id,
        endpoint=payload.trunk_id,
        match=payload.identify_match,
    )
    db.add(identify)

    registration = models.PsRegistration(
        id=registration_id,
        transport="transport-udp",
        outbound_auth=auth_id,
        server_uri=payload.server_uri,
        client_uri=payload.client_uri,
        retry_interval=payload.retry_interval,
    )
    db.add(registration)

    db.commit()

    return schemas.TrunkOut(
        trunk_id=payload.trunk_id,
        tenant_slug=tenant.slug,
        context=context,
        server_uri=payload.server_uri,
        client_uri=payload.client_uri,
        identify_match=payload.identify_match,
    )


@router.get("")
def list_trunks(db: Session = Depends(get_db)):
    return db.query(models.PsEndpoint).filter(models.PsEndpoint.context.like("from-trunk-%")).all()
