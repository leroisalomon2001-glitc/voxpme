-- ============================================================
-- VoxPME — SVI multi-niveaux — script final unique
-- Basé sur le schéma réel confirmé (tenants, users, ivr_menus)
-- À exécuter UNE SEULE FOIS sur une base propre (post-reset).
-- ============================================================

-- 1. Colonnes de configuration du SVI, ajoutées à ivr_menus existant
ALTER TABLE ivr_menus
    ADD COLUMN IF NOT EXISTS is_entry_point   BOOLEAN      NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS digit_timeout_s  INTEGER      NOT NULL DEFAULT 5,
    ADD COLUMN IF NOT EXISTS max_attempts     INTEGER      NOT NULL DEFAULT 3,
    ADD COLUMN IF NOT EXISTS invalid_sound    VARCHAR(255) DEFAULT 'ivr/generic/invalid',
    ADD COLUMN IF NOT EXISTS timeout_sound    VARCHAR(255) DEFAULT 'ivr/generic/timeout',
    ADD COLUMN IF NOT EXISTS fallback_action  VARCHAR(32)  NOT NULL DEFAULT 'hangup',
    ADD COLUMN IF NOT EXISTS fallback_value   VARCHAR(64);

-- 2. Un seul menu "point d'entrée" par tenant
CREATE UNIQUE INDEX IF NOT EXISTS ux_ivr_one_entry_per_tenant
    ON ivr_menus (tenant_id) WHERE is_entry_point;

-- 3. Journal de navigation SVI (pour debug + tableau de bord)
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
-- 4. Menu de TEST pour le tenant t001
--    (adapter le slug si besoin ; suppose que t001 existe déjà
--    dans tenants et que l'extension 1001 existe déjà dans users)
-- ============================================================

-- Menu racine : "Tapez 1 pour joindre le 1001, tapez 9 pour raccrocher"
INSERT INTO ivr_menus (tenant_id, nom, message_accueil, options, is_entry_point)
SELECT id, 'Accueil', 'ivr/t001/accueil',
       '[
          {"digit": "1", "action_type": "dial_extension", "action_value": "1001"},
          {"digit": "9", "action_type": "hangup"}
        ]'::jsonb,
       TRUE
FROM tenants WHERE slug = 't001';

-- Vérification : le menu doit apparaître avec is_entry_point = t
-- SELECT id, tenant_id, nom, options, is_entry_point FROM ivr_menus;
