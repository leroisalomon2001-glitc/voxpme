-- ============================================================
-- VoxPME — RESET complet du SVI
-- Annule tout ce qui a été ajouté par 001_ivr_schema.sql et
-- 002_fix_ivr.sql. Après ce script, ivr_menus retrouve
-- exactement sa structure d'origine (celle de voxpme_schema.sql).
-- ============================================================

-- Tables ajoutées par erreur / en trop
DROP TABLE IF EXISTS ivr_options;
DROP TABLE IF EXISTS ivr_call_events;

-- Colonnes ajoutées à ivr_menus : on les retire pour repartir
-- de la structure d'origine (id, tenant_id, nom, message_accueil,
-- options, date_creation)
ALTER TABLE ivr_menus
    DROP COLUMN IF EXISTS is_entry_point,
    DROP COLUMN IF EXISTS digit_timeout_s,
    DROP COLUMN IF EXISTS max_attempts,
    DROP COLUMN IF EXISTS invalid_sound,
    DROP COLUMN IF EXISTS timeout_sound,
    DROP COLUMN IF EXISTS fallback_action,
    DROP COLUMN IF EXISTS fallback_value;

-- Index ajouté
DROP INDEX IF EXISTS ux_ivr_one_entry_per_tenant;

-- Vérification finale : doit afficher uniquement les 6 colonnes
-- d'origine (id, tenant_id, nom, message_accueil, options, date_creation)
