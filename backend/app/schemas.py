from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class TenantCreate(BaseModel):
    slug: str = Field(..., min_length=2, max_length=20, description="Identifiant court, ex: t001")
    nom: str = Field(..., min_length=2, max_length=150)
    plage_ext_debut: int = Field(..., gt=999, lt=100000)
    plage_ext_fin: int = Field(..., gt=999, lt=100000)


class TenantOut(BaseModel):
    id: int
    slug: str
    nom: str
    plage_ext_debut: int
    plage_ext_fin: int
    statut: str

    class Config:
        from_attributes = True


class TenantCreateOut(TenantOut):
    """
    Reponse de POST /tenants uniquement. C'est le seul moment ou la cle API
    et le mot de passe admin du tenant sortent en clair depuis le serveur :
    notez-les immediatement, aucune route ne les re-affichera ensuite (voir
    GET /tenants et GET /tenants/{slug}, qui utilisent TenantOut, sans ces
    champs).
    """
    api_key: str
    admin_username: str
    admin_temp_password: str


class EndpointCreate(BaseModel):
    tenant_slug: str = Field(..., description="Slug du tenant, ex: t001")
    extension: int = Field(..., gt=999, lt=100000)
    nom: str = Field(..., min_length=2, max_length=150)
    email: Optional[str] = None
    password: str = Field(
        ..., min_length=8,
        description="Mot de passe SIP en clair (stocké tel quel pour PJSIP digest)",
    )


class EndpointOut(BaseModel):
    endpoint_id: str
    extension: int
    tenant_slug: str
    context: str
    nom: str


class TrunkCreate(BaseModel):
    tenant_slug: str = Field(..., description="Slug du tenant proprietaire du trunk, ex: t001")
    trunk_id: str = Field(..., min_length=2, max_length=100, description="Identifiant unique, ex: callcentric-trunk")
    sip_username: str = Field(..., min_length=1, max_length=100, description="Username SIP fourni par le provider")
    sip_password: str = Field(..., min_length=4, description="Secret SIP en clair (stocke tel quel pour PJSIP digest)")
    server_uri: str = Field(..., description="ex: sip:sip.callcentric.net")
    client_uri: str = Field(..., description="ex: sip:17778369904@sip.callcentric.net")
    identify_match: str = Field(..., description="Plage IP ou host du provider pour l'identify, ex: 199.87.144.0/24")
    retry_interval: int = Field(default=60, gt=0)
    allow: str = Field(default="ulaw,alaw")


class TrunkOut(BaseModel):
    trunk_id: str
    tenant_slug: str
    context: str
    server_uri: str
    client_uri: str
    identify_match: str


class TenantStatutUpdate(BaseModel):
    statut: str = Field(..., pattern="^(actif|suspendu|resilie)$")


class TenantDashboardSummary(BaseModel):
    slug: str
    nom: str
    statut: str
    nb_endpoints: int
    nb_trunks: int
    appels_aujourdhui: int
    duree_totale_aujourdhui_secondes: int
    cout_total_aujourdhui: float
    devise: Optional[str] = None


class GlobalDashboardSummary(BaseModel):
    nb_tenants: int
    tenants: list[TenantDashboardSummary]


class CallLogOut(BaseModel):
    id: int
    appelant: str
    appele: str
    date_heure_debut: Optional[datetime]
    duree_secondes: int
    type_appel: str
    statut: str
    cout_facture: Optional[float]
    devise: Optional[str]

    class Config:
        from_attributes = True


class EndpointStatusOut(BaseModel):
    endpoint_id: str
    extension: Optional[int] = None
    nom: Optional[str] = None
    registered: bool
    status: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    role: str
    tenant_slug: Optional[str] = None


class AdminCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8)
    role: str = Field(..., pattern="^(global|tenant)$")
    tenant_slug: Optional[str] = Field(None, description="Requis si role='tenant'")


class AdminOut(BaseModel):
    id: int
    username: str
    role: str
    tenant_slug: Optional[str] = None
