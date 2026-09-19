from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from security import get_current_admin, require_tenant_access

router = APIRouter(tags=["endpoints"])


@router.post("/endpoints", response_model=schemas.EndpointOut, status_code=201)
def create_endpoint(
    payload: schemas.EndpointCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin),
):
    # tenant_slug vient du body (pas de l'URL), donc verif de role manuelle ici
    # plutot que via require_tenant_access (qui attend un parametre 'slug' de path).
    if admin["role"] == "tenant" and admin["tenant_slug"] != payload.tenant_slug:
        raise HTTPException(status_code=403, detail="Acces refuse a ce tenant")

    tenant = db.query(models.Tenant).filter(models.Tenant.slug == payload.tenant_slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant '{payload.tenant_slug}' introuvable")

    if not (tenant.plage_ext_debut <= payload.extension <= tenant.plage_ext_fin):
        raise HTTPException(
            status_code=400,
            detail=f"Extension {payload.extension} hors de la plage autorisée "
                   f"[{tenant.plage_ext_debut}-{tenant.plage_ext_fin}] pour le tenant {tenant.slug}",
        )

    endpoint_id = f"{payload.extension}-{tenant.slug}"

    existing = db.query(models.PsEndpoint).filter(models.PsEndpoint.id == endpoint_id).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"L'endpoint '{endpoint_id}' existe déjà")

    context = f"from-internal-{tenant.slug}"

    aor = models.PsAor(id=endpoint_id, max_contacts=1)
    db.add(aor)

    auth = models.PsAuth(
        id=endpoint_id,
        auth_type="userpass",
        username=endpoint_id,
        password=payload.password,
    )
    db.add(auth)

    endpoint = models.PsEndpoint(
        id=endpoint_id,
        tenant_id=tenant.id,
        context=context,
        transport="transport-udp",
        auth=endpoint_id,
        aors=endpoint_id,
        disallow="all",
        allow="ulaw,alaw,opus",
        webrtc="yes",
        media_encryption="dtls",
        ice_support="yes",
        use_avpf="yes",
        rtcp_mux="yes",
        dtls_verify="fingerprint",
        dtls_setup="actpass",
        dtls_cert_file="/etc/asterisk/certs/asterisk.crt",
        dtls_private_key="/etc/asterisk/certs/asterisk.key",
    )
    db.add(endpoint)
 

    user = models.User(
        tenant_id=tenant.id,
        extension=payload.extension,
        nom=payload.nom,
        email=payload.email,
        mot_de_passe_sip=payload.password,
    )
    db.add(user)

    _ensure_dialplan_extension(db, context, payload.extension, endpoint_id)

    db.commit()

    return schemas.EndpointOut(
        endpoint_id=endpoint_id,
        extension=payload.extension,
        tenant_slug=tenant.slug,
        context=context,
        nom=payload.nom,
    )


def _ensure_dialplan_extension(db: Session, context: str, extension: int, endpoint_id: str):
    """
    Insere l'extension dans la table 'extensions' (dialplan realtime, module
    pbx_realtime cote Asterisk). Remplace l'ancienne methode qui ecrivait
    directement dans extensions.conf + `sudo asterisk -rx dialplan reload`,
    incompatible avec des conteneurs backend/asterisk separes (section 13.9
    / J22). Chaque contexte tenant declare `switch => Realtime` dans
    extensions.conf pour que ce fallback soit consulte.

    Pas de reload necessaire : pbx_realtime interroge la base a chaque appel,
    sans cache par defaut.
    """
    exten = str(extension)

    already_exists = (
        db.query(models.Extension)
        .filter(models.Extension.context == context, models.Extension.exten == exten)
        .first()
    )
    if already_exists:
        return

    steps = [
        (1, "NoOp", f"Appel vers extension {extension}"),
        (2, "Dial", f"PJSIP/{endpoint_id},20"),
        (3, "Hangup", ""),
    ]
    for priority, app, appdata in steps:
        db.add(models.Extension(
            context=context,
            exten=exten,
            priority=priority,
            app=app,
            appdata=appdata,
        ))


@router.get("/tenants/{slug}/endpoints", dependencies=[Depends(require_tenant_access)])
def list_tenant_endpoints(slug: str, db: Session = Depends(get_db)):
    """
    Admin global ou admin du tenant demande. Note : cette route liste les
    ps_endpoints bruts (config PJSIP) ; distincte de
    /dashboard/tenants/{slug}/endpoints (dashboard.py) qui renvoie un statut
    d'enregistrement live enrichi via AMI, pour affichage dans le dashboard.
    """
    tenant = db.query(models.Tenant).filter(models.Tenant.slug == slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant introuvable")
    return db.query(models.PsEndpoint).filter(models.PsEndpoint.tenant_id == tenant.id).all()


@router.delete("/endpoints/{slug}/{extension}", status_code=204, dependencies=[Depends(require_tenant_access)])
def delete_endpoint(slug: str, extension: int, db: Session = Depends(get_db)):
    """
    Supprime un poste SIP : nettoie l'endpoint PJSIP (AOR, Auth, Endpoint),
    l'utilisateur metier associe et les lignes de dialplan realtime generees
    par _ensure_dialplan_extension a la creation. Meme logique de controle
    d'acces que list_tenant_endpoints (require_tenant_access sur 'slug').
    """
    tenant = db.query(models.Tenant).filter(models.Tenant.slug == slug).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant introuvable")

    endpoint_id = f"{extension}-{slug}"
    context = f"from-internal-{slug}"

    endpoint = (
        db.query(models.PsEndpoint)
        .filter(models.PsEndpoint.id == endpoint_id, models.PsEndpoint.tenant_id == tenant.id)
        .first()
    )
    if not endpoint:
        raise HTTPException(status_code=404, detail=f"Poste '{endpoint_id}' introuvable pour ce tenant")

    db.query(models.PsAor).filter(models.PsAor.id == endpoint_id).delete()
    db.query(models.PsAuth).filter(models.PsAuth.id == endpoint_id).delete()
    db.query(models.User).filter(
        models.User.tenant_id == tenant.id, models.User.extension == extension
    ).delete()
    db.query(models.Extension).filter(
        models.Extension.context == context, models.Extension.exten == str(extension)
    ).delete()
    db.query(models.PsEndpoint).filter(models.PsEndpoint.id == endpoint_id).delete()

    db.commit()
    return None
