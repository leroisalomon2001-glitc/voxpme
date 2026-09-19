import secrets
from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, func, Numeric
from sqlalchemy.orm import relationship


from database import Base

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True)
    slug = Column(String(20), unique=True, nullable=False)
    nom = Column(String(150), nullable=False)
    plage_ext_debut = Column(Integer, nullable=False)
    plage_ext_fin = Column(Integer, nullable=False)
    statut = Column(String(20), default="actif")
    plan_tarifaire_id = Column(Integer, nullable=True)
    date_creation = Column(TIMESTAMP, server_default=func.now())
    api_key = Column(String(64), unique=True, nullable=True)


class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # "global" ou "tenant"
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True)
    date_creation = Column(TIMESTAMP, server_default=func.now())

    tenant = relationship("Tenant")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    extension = Column(Integer, nullable=False)
    nom = Column(String(150), nullable=False)
    email = Column(String(150), nullable=True)
    mot_de_passe_sip = Column(String(255), nullable=False)
    type = Column(String(20), default="agent")
    statut = Column(String(20), default="actif")
    date_creation = Column(TIMESTAMP, server_default=func.now())

class PsEndpoint(Base):
    __tablename__ = "ps_endpoints"
 
    id = Column(String(100), primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    context = Column(String(100), nullable=False)
    transport = Column(String(100))
    auth = Column(String(100))
    aors = Column(String(100))
    disallow = Column(String(100), default="all")
    allow = Column(String(100), default="ulaw,alaw,opus")
    webrtc = Column(String(3), default="no")
    media_encryption = Column(String(20), nullable=True)
    ice_support = Column(String(3), nullable=True)
    use_avpf = Column(String(3), nullable=True)
    rtcp_mux = Column(String(3), nullable=True)
    dtls_verify = Column(String(20), nullable=True)
    dtls_setup = Column(String(20), nullable=True)
    dtls_cert_file = Column(String(255), nullable=True)
    dtls_private_key = Column(String(255), nullable=True)
    dtmf_mode = Column(String(20), default="rfc4733")
    outbound_auth = Column(String(100), nullable=True)
    identify_by = Column(String(80), nullable=True)
 
class PsAuth(Base):
    __tablename__ = "ps_auths"

    id = Column(String(100), primary_key=True)
    auth_type = Column(String(20), default="userpass")
    password = Column(String(255))
    username = Column(String(100))

class PsAor(Base):
    __tablename__ = "ps_aors"

    id = Column(String(100), primary_key=True)
    max_contacts = Column(Integer, default=1)
    contact = Column(String(255), nullable=True)
class PsRegistration(Base):
    __tablename__ = "ps_registrations"
    id = Column(String(100), primary_key=True)
    auth = Column(String(100))
    client_uri = Column(String(255))
    contact_user = Column(String(100))
    expiration = Column(Integer)
    line = Column(String(3))
    endpoint = Column(String(100))
    retry_interval = Column(Integer)
    forbidden_retry_interval = Column(Integer)
    max_retries = Column(Integer)
    outbound_auth = Column(String(100))
    outbound_proxy = Column(String(255))
    server_uri = Column(String(255))
    transport = Column(String(100))
    support_path = Column(String(3))
class PsEndpointIdIp(Base):
    __tablename__ = "ps_endpoint_id_ips"
    id = Column(String(100), primary_key=True)
    endpoint = Column(String(100))
    match = Column(String(100))
    srv_lookups = Column(String(3), default="yes")
    match_header = Column(String(255))
    match_request_uri = Column(String(255))
class Extension(Base):
    __tablename__ = "extensions"
    id = Column(Integer, primary_key=True)
    context = Column(String(80), nullable=False)
    exten = Column(String(80), nullable=False)
    priority = Column(Integer, nullable=False)
    app = Column(String(80), nullable=False)
    appdata = Column(String(256), nullable=True)

class CdrFacture(Base):
    """
    Vue SQL en lecture seule (CREATE OR REPLACE VIEW cdr_facture, voir
    journal 13.5.2/J27). Ne jamais faire db.add()/commit() sur ce modèle :
    la vue n'accepte pas d'écriture, seule la table 'cdr' sous-jacente le
    peut, via le trigger sync_cdr_from_asterisk.
    """
    __tablename__ = "cdr_facture"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    appelant = Column(String(50))
    appele = Column(String(50))
    date_heure_debut = Column(TIMESTAMP)
    duree_secondes = Column(Integer)
    type_appel = Column(String(20))
    statut = Column(String(20))
    prix_par_minute = Column(Numeric)
    devise = Column(String(10))
    prefixe_applique = Column(String(20))
    cout_facture = Column(Numeric)
