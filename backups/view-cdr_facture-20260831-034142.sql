 SELECT c.id,
    c.tenant_id,
    c.appelant,
    c.appele,
    c.date_heure_debut,
    c.duree_secondes,
    c.type_appel,
    c.statut,
    pt.prix_par_minute,
    pt.devise,
    pt.prefixe_destination AS prefixe_applique,
    round(c.duree_secondes::numeric / 60::numeric * pt.prix_par_minute, 4) AS cout_facture
   FROM cdr c
     JOIN tenants t ON t.id = c.tenant_id
     LEFT JOIN LATERAL ( SELECT p.prix_par_minute,
            p.devise,
            p.prefixe_destination
           FROM paliers_tarifaires p
          WHERE p.plan_tarifaire_id = t.plan_tarifaire_id AND c.appele::text ~~ (p.prefixe_destination::text || '%'::text)
          ORDER BY (length(p.prefixe_destination::text)) DESC
         LIMIT 1) pt ON true;
