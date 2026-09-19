CREATE OR REPLACE FUNCTION public.sync_cdr_from_asterisk()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_slug TEXT;
BEGIN
  v_slug := substring(NEW.dcontext_ast FROM 't[0-9]+$');

  IF v_slug IS NOT NULL THEN
    SELECT id INTO NEW.tenant_id FROM tenants WHERE slug = v_slug;
  END IF;

  NEW.statut := CASE TRIM(NEW.disposition_ast)
    WHEN '8' THEN 'termine'       -- ANSWERED
    WHEN '1' THEN 'sans_reponse'  -- NO ANSWER
    WHEN '2' THEN 'occupe'        -- BUSY
    WHEN '4' THEN 'echec'         -- FAILED
    ELSE 'echec'
  END;

  NEW.type_appel := CASE
    WHEN NEW.dcontext_ast LIKE 'from-internal%' THEN 'interne'
    WHEN NEW.dcontext_ast LIKE 'from-trunk%'     THEN 'entrant'
    WHEN NEW.dcontext_ast LIKE 'from-outbound%'  THEN 'sortant'
    ELSE 'interne'
  END;

  RETURN NEW;
END;
$function$

