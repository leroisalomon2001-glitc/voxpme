-- =========================================================
-- VoxPME — Schéma PostgreSQL multi-tenant
-- Plateforme UCaaS (Asterisk / PJSIP / ARA)
-- =========================================================

-- Extension pour générer des UUID si besoin
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =========================================================
-- 1. TENANTS
-- =========================================================
CREATE TABLE tenants (
    id                  SERIAL PRIMARY KEY,
    slug                VARCHAR(20) UNIQUE NOT NULL,      -- ex: 't001'
    nom                 VARCHAR(150) NOT NULL,
    plage_ext_debut     INTEGER NOT NULL,                 -- ex: 1000
    plage_ext_fin       INTEGER NOT NULL,                 -- ex: 1999
    statut              VARCHAR(20) NOT NULL DEFAULT 'actif'
                         CHECK (statut IN ('actif','suspendu','resilie')),
    plan_tarifaire_id   INTEGER,
    date_creation       TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT chk_plage_valide CHECK (plage_ext_fin > plage_ext_debut)
);

-- =========================================================
-- 2. PLANS TARIFAIRES
-- =========================================================
CREATE TABLE plans_tarifaires (
    id              SERIAL PRIMARY KEY,
    nom             VARCHAR(100) NOT NULL,
    description     TEXT
);

-- Paliers de taxation : un plan tarifaire a plusieurs paliers
-- (préfixe destination -> prix/minute)
CREATE TABLE paliers_tarifaires (
    id                  SERIAL PRIMARY KEY,
    plan_tarifaire_id   INTEGER NOT NULL REFERENCES plans_tarifaires(id) ON DELETE CASCADE,
    prefixe_destination VARCHAR(20) NOT NULL,   -- ex: '221' (Sénégal), '33' (France)
    prix_par_minute     NUMERIC(10,4) NOT NULL,
    devise              VARCHAR(10) NOT NULL DEFAULT 'XOF'
);

-- Ajout de la FK maintenant que plans_tarifaires existe
ALTER TABLE tenants
    ADD CONSTRAINT fk_tenant_plan
    FOREIGN KEY (plan_tarifaire_id) REFERENCES plans_tarifaires(id);

-- =========================================================
-- 3. UTILISATEURS / POSTES TÉLÉPHONIQUES
-- =========================================================
CREATE TABLE users (
    id              SERIAL PRIMARY KEY,
    tenant_id       INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    extension       INTEGER NOT NULL,          -- doit être dans la plage du tenant
    nom             VARCHAR(150) NOT NULL,
    email           VARCHAR(150),
    mot_de_passe_sip VARCHAR(255) NOT NULL,    -- hashé
    type            VARCHAR(20) NOT NULL DEFAULT 'agent'
                    CHECK (type IN ('agent','admin','superviseur')),
    statut          VARCHAR(20) NOT NULL DEFAULT 'actif'
                    CHECK (statut IN ('actif','inactif')),
    date_creation   TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (tenant_id, extension)
);

-- =========================================================
-- 4. TRUNKS (accès sortant : GoIP ou SIP trunk)
-- =========================================================
CREATE TABLE trunks (
    id                  SERIAL PRIMARY KEY,
    tenant_id           INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    type                VARCHAR(20) NOT NULL CHECK (type IN ('goip','sip_trunk')),
    hote                VARCHAR(255),           -- IP/hostname du trunk
    identifiant         VARCHAR(150),
    mot_de_passe        VARCHAR(255),
    contexte_sortant    VARCHAR(100) NOT NULL,  -- ex: 'from-trunk-t001'
    statut              VARCHAR(20) NOT NULL DEFAULT 'actif',
    date_creation       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =========================================================
-- 5. SVI / IVR
-- =========================================================
CREATE TABLE ivr_menus (
    id                  SERIAL PRIMARY KEY,
    tenant_id           INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    nom                 VARCHAR(150) NOT NULL,
    message_accueil     VARCHAR(255),          -- chemin du fichier audio
    options             JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- options exemple: {"1": {"action": "queue", "cible": "commercial"},
    --                   "2": {"action": "extension", "cible": "1005"},
    --                   "0": {"action": "ivr", "cible": "menu_secondaire"}}
    date_creation       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =========================================================
-- 6. FILES D'ATTENTE
-- =========================================================
CREATE TABLE queues (
    id                  SERIAL PRIMARY KEY,
    tenant_id           INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    nom                 VARCHAR(150) NOT NULL,
    musique_attente     VARCHAR(150) DEFAULT 'default',
    strategie           VARCHAR(30) NOT NULL DEFAULT 'ringall'
                        CHECK (strategie IN ('ringall','leastrecent','fewestcalls','random','rrmemory')),
    timeout_secondes    INTEGER DEFAULT 30,
    date_creation       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Association agents <-> files d'attente (plusieurs-à-plusieurs)
CREATE TABLE queue_membres (
    id          SERIAL PRIMARY KEY,
    queue_id    INTEGER NOT NULL REFERENCES queues(id) ON DELETE CASCADE,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    penalite    INTEGER DEFAULT 0,

    UNIQUE (queue_id, user_id)
);

-- =========================================================
-- 7. CDR (Journal d'appels)
-- =========================================================
CREATE TABLE cdr (
    id                  BIGSERIAL PRIMARY KEY,
    tenant_id           INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    appelant            VARCHAR(50) NOT NULL,
    appele              VARCHAR(50) NOT NULL,
    date_heure_debut    TIMESTAMPTZ NOT NULL,
    duree_secondes      INTEGER NOT NULL DEFAULT 0,
    type_appel          VARCHAR(20) NOT NULL
                        CHECK (type_appel IN ('interne','entrant','sortant')),
    statut              VARCHAR(20) NOT NULL DEFAULT 'termine'
                        CHECK (statut IN ('termine','echec','occupe','sans_reponse')),
    cout_calcule        NUMERIC(10,4) DEFAULT 0,
    trunk_id            INTEGER REFERENCES trunks(id),

    -- utile pour les exports et le dashboard temps réel
    uniqueid_asterisk   VARCHAR(100)
);

-- Index pour accélérer les requêtes fréquentes (export CSV, dashboard)
CREATE INDEX idx_cdr_tenant_date ON cdr (tenant_id, date_heure_debut);
CREATE INDEX idx_cdr_tenant_type ON cdr (tenant_id, type_appel);

-- =========================================================
-- 7bis. TRIGGER : vérifier que l'extension appartient
--       bien à la plage définie pour le tenant
-- =========================================================
CREATE OR REPLACE FUNCTION verifier_extension_dans_plage()
RETURNS TRIGGER AS $$
DECLARE
    v_debut INTEGER;
    v_fin   INTEGER;
BEGIN
    SELECT plage_ext_debut, plage_ext_fin
      INTO v_debut, v_fin
      FROM tenants
     WHERE id = NEW.tenant_id;

    IF NEW.extension < v_debut OR NEW.extension > v_fin THEN
        RAISE EXCEPTION
            'Extension % hors de la plage autorisée [% - %] pour le tenant %',
            NEW.extension, v_debut, v_fin, NEW.tenant_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_verifier_extension
BEFORE INSERT OR UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION verifier_extension_dans_plage();

-- =========================================================
-- 8. TABLES ASTERISK REALTIME ARCHITECTURE (ARA) — optionnel
-- =========================================================
-- Si tu choisis ARA, Asterisk lira directement ces tables
-- au lieu de pjsip.conf / extensions.conf statiques.

CREATE TABLE ps_endpoints (
    id                  VARCHAR(100) PRIMARY KEY,   -- ex: '1001-t001'
    tenant_id           INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    context             VARCHAR(100) NOT NULL,      -- ex: 'from-internal-t001'
    transport           VARCHAR(100),
    auth                VARCHAR(100),
    aors                VARCHAR(100),
    disallow            VARCHAR(100) DEFAULT 'all',
    allow               VARCHAR(100) DEFAULT 'ulaw,alaw,opus'
);

CREATE TABLE ps_auths (
    id                  VARCHAR(100) PRIMARY KEY,
    auth_type           VARCHAR(20) DEFAULT 'userpass',
    password            VARCHAR(255),
    username            VARCHAR(100)
);

CREATE TABLE ps_aors (
    id                  VARCHAR(100) PRIMARY KEY,
    max_contacts        INTEGER DEFAULT 1
);

-- =========================================================
-- Fin du schéma
-- =========================================================