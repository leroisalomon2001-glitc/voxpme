-- ============================================================
-- VoxPME — Correctif SVI : on s'aligne sur le schéma existant
-- (ivr_menus avec colonne options en JSONB), au lieu d'une
-- table séparée ivr_options.
-- ============================================================

-- 1. Supprime la table créée par erreur lors du script précédent
--    (elle ne correspond pas à votre design réel du projet)
DROP TABLE IF EXISTS ivr_options;

-- 2. Ajoute les colonnes manquantes à votre table ivr_menus
--    existante, SANS toucher aux données déjà présentes.
ALTER TABLE ivr_menus
    ADD COLUMN IF NOT EXISTS is_entry_point   BOOLEAN      NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS digit_timeout_s  INTEGER      NOT NULL DEFAULT 5,
    ADD COLUMN IF NOT EXISTS max_attempts     INTEGER      NOT NULL DEFAULT 3,
    ADD COLUMN IF NOT EXISTS invalid_sound    VARCHAR(255) DEFAULT 'ivr/generic/invalid',
    ADD COLUMN IF NOT EXISTS timeout_sound    VARCHAR(255) DEFAULT 'ivr/generic/timeout',
    ADD COLUMN IF NOT EXISTS fallback_action  VARCHAR(32)  NOT NULL DEFAULT 'hangup',
    ADD COLUMN IF NOT EXISTS fallback_value   VARCHAR(64);

-- 3. Un seul menu "point d'entrée" par tenant (celui joué à l'arrivée
--    d'un appel). Empêche d'en activer deux par erreur.
CREATE UNIQUE INDEX IF NOT EXISTS ux_ivr_one_entry_per_tenant
    ON ivr_menus (tenant_id) WHERE is_entry_point;

-- 4. Table de log de navigation (utile pour le tableau de bord et
--    pour le debug) — celle-ci n'existait pas avant, aucun conflit.
CREATE TABLE IF NOT EXISTS ivr_call_events (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       INTEGER      NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    channel         VARCHAR(128) NOT NULL,
    menu_id         INTEGER,
    digit_pressed   VARCHAR(1),
    result          VARCHAR(32),   -- 'ok' | 'timeout' | 'invalid' | 'max_attempts'
    occurred_at     TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_ivr_events_tenant_time ON ivr_call_events (tenant_id, occurred_at);

-- ============================================================
-- Rappel du format attendu dans la colonne ivr_menus.options (JSONB) :
--
-- [
--   {"digit": "1", "action_type": "goto_menu",      "action_value": "3"},
--   {"digit": "2", "action_type": "dial_extension",  "action_value": "1001-t001"},
--   {"digit": "3", "action_type": "dial_queue",      "action_value": "commercial"},
--   {"digit": "0", "action_type": "voicemail",       "action_value": "accueil"},
--   {"digit": "*", "action_type": "go_back",         "action_value": "1"}
-- ]
--
-- Pour "goto_menu"/"go_back", action_value = l'id (colonne id) du
-- menu cible dans ivr_menus, sous forme de texte.
-- ============================================================
