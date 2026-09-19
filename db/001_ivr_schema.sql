-- ============================================================
-- VoxPME — Schéma SVI (IVR) multi-niveaux, multi-tenant
-- S'ajoute à la base existante (tenants, PJSIP realtime, etc.)
-- ============================================================

-- Un menu = un "niveau" du SVI (menu racine, sous-menu, etc.)
CREATE TABLE IF NOT EXISTS ivr_menus (
    id              SERIAL PRIMARY KEY,
    tenant_id       VARCHAR(16)  NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    menu_key        VARCHAR(64)  NOT NULL,       -- identifiant logique unique dans le tenant (ex. 'root', 'commercial')
    is_entry_point  BOOLEAN      NOT NULL DEFAULT FALSE,  -- un seul TRUE par tenant : menu joué à l'arrivée de l'appel
    greeting_sound  VARCHAR(128) NOT NULL,        -- nom du fichier son (sans extension), ex. 'ivr/t001/root-greeting'
    invalid_sound   VARCHAR(128) NOT NULL DEFAULT 'ivr/generic/invalid',
    timeout_sound   VARCHAR(128) NOT NULL DEFAULT 'ivr/generic/timeout',
    digit_timeout_s INTEGER      NOT NULL DEFAULT 5,   -- délai d'attente d'un chiffre
    max_attempts    INTEGER      NOT NULL DEFAULT 3,   -- tentatives avant fallback
    fallback_action VARCHAR(32)  NOT NULL DEFAULT 'hangup', -- 'hangup' | 'voicemail' | 'dial_extension'
    fallback_value  VARCHAR(64),                        -- ex. extension ou boîte vocale si fallback ≠ hangup
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, menu_key)
);

-- Une seule entrée par tenant : contrainte applicative (vérifiée côté API),
-- ici un index partiel garantit qu'il n'y a qu'un point d'entrée actif.
CREATE UNIQUE INDEX IF NOT EXISTS ux_ivr_one_entry_per_tenant
    ON ivr_menus (tenant_id) WHERE is_entry_point;

-- Une option = une touche DTMF (0-9, *, #) dans un menu donné
CREATE TABLE IF NOT EXISTS ivr_options (
    id              SERIAL PRIMARY KEY,
    menu_id         INTEGER      NOT NULL REFERENCES ivr_menus(id) ON DELETE CASCADE,
    digit           VARCHAR(1)   NOT NULL,   -- '0'..'9', '*', '#'
    label           VARCHAR(128),            -- libellé affiché dans le portail (pas joué à l'appelant)
    action_type     VARCHAR(32)  NOT NULL,   -- voir liste ci-dessous
    action_value    VARCHAR(128),            -- dépend du action_type
    position        INTEGER      NOT NULL DEFAULT 0,  -- ordre d'affichage dans le portail
    UNIQUE (menu_id, digit)
);

-- action_type possibles :
--   'goto_menu'        -> action_value = menu_key du sous-menu à jouer
--   'dial_extension'    -> action_value = extension interne (ex. '1001-t001')
--   'dial_queue'         -> action_value = nom de la file d'attente (cf. étape suivante)
--   'voicemail'          -> action_value = boîte vocale cible
--   'dial_external'      -> action_value = numéro externe (via trunk sortant)
--   'repeat_menu'        -> rejoue le message courant (action_value ignoré)
--   'go_back'            -> revient au menu parent (action_value = menu_key parent)
--   'hangup'             -> raccroche

-- Historique/log de navigation (utile pour debug + KPI "temps de provisioning"/UX)
CREATE TABLE IF NOT EXISTS ivr_call_events (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       VARCHAR(16)  NOT NULL,
    channel         VARCHAR(128) NOT NULL,
    menu_key        VARCHAR(64)  NOT NULL,
    digit_pressed   VARCHAR(1),
    result          VARCHAR(32),   -- 'ok' | 'timeout' | 'invalid' | 'max_attempts'
    occurred_at     TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_ivr_events_tenant_time ON ivr_call_events (tenant_id, occurred_at);
