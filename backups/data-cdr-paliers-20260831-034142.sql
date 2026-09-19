--
-- PostgreSQL database dump
--

\restrict yoa1l5jskUP3yN80QfNasY1RYi130xNz22kJMyoRuhQED1wO4UbRj34hlJAar5P

-- Dumped from database version 14.24 (Ubuntu 14.24-0ubuntu0.22.04.1)
-- Dumped by pg_dump version 14.24 (Ubuntu 14.24-0ubuntu0.22.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: cdr; Type: TABLE DATA; Schema: public; Owner: voxpme_app
--

COPY public.cdr (id, tenant_id, appelant, appele, date_heure_debut, duree_secondes, type_appel, statut, cout_calcule, trunk_id, uniqueid_asterisk, disposition_ast, dcontext_ast, accountcode_ast) FROM stdin;
1	1	1002-t001	1001-t001	2026-08-30 01:06:07.579201+00	12	interne	termine	0.0000	\N	test-manuel-1	ANSWERED	from-internal-t001	\N
2	1	1001-t001	1002	2026-08-30 01:09:02+00	31	interne	echec	0.0000	\N	1788052142.3	8	from-internal-t001	\N
3	1	1001-t001	1002	2026-08-30 01:10:57+00	6	interne	echec	0.0000	\N	1788052257.5	8	from-internal-t001	\N
4	1	1001-t001	1002	2026-08-30 01:17:00+00	4	interne	echec	0.0000	\N	1788052620.7	8	from-internal-t001	\N
5	1	1002-t001	1001	2026-08-30 01:19:23+00	5	interne	termine	0.0000	\N	1788052763.9	8	from-internal-t001	\N
6	1	1002-t001	1001	2026-08-30 02:17:28+00	5	interne	termine	0.0000	\N	1788056248.11	8	from-internal-t001	\N
8	1	1001-t001	221771234567	2026-08-30 02:27:57.425219+00	120	sortant	termine	0.0000	\N	\N	8	from-outbound-t001	\N
9	1	1002-t001	101	2026-08-31 01:21:54+00	0	interne	occupe	0.0000	\N	1788139314.13	2	from-internal-t001	\N
10	1	1002-t001	17778369904	2026-08-31 01:22:31+00	0	interne	occupe	0.0000	\N	1788139351.14	2	from-internal-t001	\N
11	1	1002-t001	101	2026-08-31 01:25:55+00	0	interne	occupe	0.0000	\N	1788139555.15	2	from-internal-t001	\N
12	1	1002-t001	101	2026-08-31 01:29:52+00	0	interne	echec	0.0000	\N	1788139792.16	0	from-internal-t001	\N
13	1	1002-t001	101	2026-08-31 01:29:52+00	0	interne	sans_reponse	0.0000	\N	1788139792.16	1	from-internal-t001	\N
14	1	1002-t001	101	2026-08-31 01:31:27+00	0	interne	echec	0.0000	\N	1788139887.18	0	from-internal-t001	\N
15	1	1002-t001	101	2026-08-31 01:31:27+00	0	interne	sans_reponse	0.0000	\N	1788139887.18	1	from-internal-t001	\N
16	1	1002-t001	17778369904101	2026-08-31 01:35:50+00	0	interne	echec	0.0000	\N	1788140150.20	0	from-internal-t001	\N
17	1	1002-t001	17778369904101	2026-08-31 01:35:51+00	0	interne	sans_reponse	0.0000	\N	1788140150.20	1	from-internal-t001	\N
18	1	1002-t001	17778369904101	2026-08-31 01:36:44+00	0	interne	echec	0.0000	\N	1788140204.22	0	from-internal-t001	\N
19	1	1002-t001	17778369904101	2026-08-31 01:36:44+00	0	interne	sans_reponse	0.0000	\N	1788140204.22	1	from-internal-t001	\N
\.


--
-- Data for Name: paliers_tarifaires; Type: TABLE DATA; Schema: public; Owner: voxpme_app
--

COPY public.paliers_tarifaires (id, plan_tarifaire_id, prefixe_destination, prix_par_minute, devise) FROM stdin;
1	1	221	50.0000	XOF
2	1	2217	45.0000	XOF
3	1	33	100.0000	XOF
4	1	221	50.0000	XOF
5	1	2217	45.0000	XOF
6	1	33	100.0000	XOF
\.


--
-- Name: cdr_id_seq; Type: SEQUENCE SET; Schema: public; Owner: voxpme_app
--

SELECT pg_catalog.setval('public.cdr_id_seq', 19, true);


--
-- Name: paliers_tarifaires_id_seq; Type: SEQUENCE SET; Schema: public; Owner: voxpme_app
--

SELECT pg_catalog.setval('public.paliers_tarifaires_id_seq', 6, true);


--
-- PostgreSQL database dump complete
--

\unrestrict yoa1l5jskUP3yN80QfNasY1RYi130xNz22kJMyoRuhQED1wO4UbRj34hlJAar5P

