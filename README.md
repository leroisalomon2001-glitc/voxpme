# VoxPME

**Plateforme de téléphonie d'entreprise UCaaS multi-tenant**, développée dans le cadre du projet d'études de deuxième année — Ingénierie de Conception, option TS (Télécom et Services) — INGC2, ESMT Dakar.

VoxPME permet à plusieurs entreprises de partager une même infrastructure de téléphonie IP tout en conservant une isolation logique complète de leurs utilisateurs, de leurs appels et de leurs données.

---

## Sommaire

- [Aperçu](#aperçu)
- [Architecture](#architecture)
- [Stack technique](#stack-technique)
- [Fonctionnalités](#fonctionnalités)
- [Structure du dépôt](#structure-du-dépôt)
- [Installation](#installation)
- [Configuration](#configuration)
- [Utilisation](#utilisation)
- [Tests](#tests)
- [Supervision](#supervision)
- [État du projet](#état-du-projet)
- [Auteur](#auteur)

---

## Aperçu

VoxPME s'inspire des plateformes UCaaS commerciales (3CX, RingCentral, Teams Phone) et propose, pour des PME :

- des postes téléphoniques SIP et WebRTC ;
- un serveur vocal interactif (SVI/IVR) ;
- des files d'attente ;
- un trunk SIP vers le réseau téléphonique public ;
- une journalisation et une facturation automatique des appels ;
- une API et un tableau de bord d'administration ;
- une supervision complète de l'infrastructure.

L'ensemble repose sur une architecture **dynamique** : la configuration métier (tenants, postes, trunks, dialplan) n'est pas figée dans des fichiers statiques, mais stockée dans PostgreSQL et récupérée en temps réel par Asterisk via l'**Asterisk Realtime Architecture (ARA)**.

## Architecture

```
                         UTILISATEURS
                              │
                 ┌────────────┴────────────┐
                 │                         │
             Softphone                 Navigateur
           (Zoiper/MicroSIP)          (WebRTC/SIP.js)
                 │                         │
                 └────────────┬────────────┘
                              │
                         SIP / WSS
                              │
                              ▼
                         ┌─────────┐
                         │  NGINX  │  (HTTPS / WSS / reverse proxy)
                         └────┬────┘
                              │
                              ▼
                         ┌─────────┐
                         │Asterisk │  (PJSIP / AGI / dialplan)
                         └────┬────┘
                              │
                    ODBC (Asterisk Realtime)
                              │
                              ▼
                        ┌──────────┐
                        │PostgreSQL│  (tenants, users, CDR, tarifs…)
                        └────┬─────┘
                              │
                   ┌──────────┴──────────┐
                   ▼                     ▼
               FastAPI                  CDR
              (API + JWT)          (facturation)
                   │
              Dashboard web

        SUPERVISION : Prometheus + Grafana + cAdvisor + node-exporter
```

## Stack technique

| Composant | Rôle |
|---|---|
| **Asterisk 20 / PJSIP** | Cœur téléphonique — SIP, WebRTC, dialplan |
| **PostgreSQL** | Stockage central des données (tenants, postes, CDR, tarifs) |
| **Asterisk Realtime Architecture (ARA) + ODBC** | Pont dynamique entre Asterisk et PostgreSQL |
| **FastAPI (Python) + SQLAlchemy** | API d'administration et de provisioning |
| **JWT** | Authentification de l'API (admin global / admin tenant) |
| **WebRTC / SIP.js** | Softphone navigateur |
| **AGI (Python)** | Moteur du serveur vocal interactif (SVI) |
| **NGINX** | Reverse proxy, terminaison HTTPS/WSS |
| **Docker Compose** | Conteneurisation et orchestration |
| **Redis** | Composant d'infrastructure applicative |
| **Prometheus / Grafana / cAdvisor / node-exporter** | Supervision technique |
| **SIPp** | Tests de charge |

## Fonctionnalités

- ✅ Architecture multi-tenant avec isolation logique vérifiée
- ✅ Configuration dynamique (PostgreSQL / ODBC / ARA)
- ✅ Appels internes, entrants et sortants
- ✅ Softphone navigateur (WebRTC)
- ✅ Serveur vocal interactif (SVI/IVR) piloté par script AGI
- ✅ Files d'attente avec musique d'attente
- ✅ Journalisation des appels (CDR) et facturation automatique par palier tarifaire
- ✅ Trunk SIP vers un fournisseur externe (Callcentric)
- ✅ API REST sécurisée par JWT (admin global / admin tenant)
- ✅ Tableau de bord web d'administration
- ✅ Conteneurisation complète (8 services Docker)
- ✅ HTTPS / WSS (certificat auto-signé en local)
- ✅ Supervision Prometheus / Grafana / cAdvisor / node-exporter
- ✅ Tests de charge validés avec SIPp (220 appels, 0 échec)

## Structure du dépôt

```
voxpme/
├── asterisk/           # Configuration et Dockerfile Asterisk (PJSIP, ARA, AGI)
├── backend/            # API FastAPI (routers, modèles, auth JWT)
├── db/                 # Schéma et scripts PostgreSQL
├── docker/             # Fichiers liés à l'orchestration Docker
├── frontend/           # Tableau de bord web + softphone WebRTC de test
├── monitoring/         # Configuration Prometheus / Grafana (dashboards, provisioning)
├── nginx/              # Configuration du reverse proxy
├── certbot/            # Gestion des certificats TLS
├── *.xml, run_*.sh     # Scénarios et scripts de tests de charge SIPp
├── docker-compose.yml  # Orchestration de l'ensemble des services
├── .env.example        # Modèle de variables d'environnement (sans valeurs réelles)
└── README.md
```

## Installation

### Prérequis

- Docker et Docker Compose
- Un accès SSH/terminal Linux (testé sur Ubuntu, VirtualBox)

### Étapes

```bash
git clone https://github.com/leroisalomon2001-glitc/voxpme.git
cd voxpme

# Copier le modèle de variables d'environnement et le compléter
cp .env.example .env
nano .env
```

Renseigner dans `.env` :
- les identifiants PostgreSQL (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`)
- le mot de passe admin Grafana (`GRAFANA_ADMIN_PASSWORD`)
- la clé secrète JWT
- les identifiants du trunk SIP externe (Callcentric ou autre fournisseur)

```bash
# Démarrer l'ensemble de la plateforme
docker compose up -d

# Vérifier que tous les services sont opérationnels
docker compose ps
```

## Configuration

- **Extensions par tenant** : convention `<extension>-<tenant>` (ex. `1001-t001`), avec une plage dédiée par entreprise (ex. `t001` → `1000-1999`).
- **WebRTC** : endpoint dédié sur `transport-wss`, port `8089`.
- **SVI** : point d'entrée `900`, options de menu stockées en JSONB dans PostgreSQL.
- **Files d'attente** : stratégie `ringall`, timeout `15s` par défaut (configurable en base).

## Utilisation

### Créer un tenant via l'API

```bash
curl -k -X POST "https://<ip-serveur>/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"***"}'
```

```bash
curl -k -X POST "https://<ip-serveur>/api/tenants" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"slug":"t003","nom":"Entreprise ABC", "plage_debut":3000,"plage_fin":3999}'
```

### Diagnostiquer Asterisk

```bash
docker exec -it voxpme-asterisk asterisk -rx "pjsip show endpoints"
docker exec -it voxpme-asterisk asterisk -rx "pjsip show contacts"
docker exec -it voxpme-asterisk asterisk -rx "odbc show all"
```

## Tests

Des scénarios de test de charge SIPp sont fournis à la racine du dépôt :

```bash
bash run_sipp_single.sh          # test unitaire (1 appel)
bash run_sipp_test1.sh           # test de charge intermédiaire
bash run_sipp_test2_stress.sh    # test de stress (220 appels)
```

Résultats de référence obtenus lors des tests : **220 appels, 0 échec, latence moyenne 27–28 ms**.

## Supervision

- **Prometheus** : collecte des métriques (backend `/metrics`, cAdvisor, node-exporter) toutes les 15 secondes.
- **Grafana** : tableaux de bord *Node Exporter Full* et *cAdvisor*, accessibles via tunnel SSH (`ssh -L 3000:127.0.0.1:3000 <user>@<ip>` puis `http://localhost:3000`).

## État du projet

### Fonctionnel
Cœur Asterisk/PostgreSQL/ARA, multi-tenant, WebRTC, SVI, files d'attente, CDR, facturation, trunk SIP, API JWT, tableau de bord, Docker, HTTPS/WSS local, supervision.

### Points restant à finaliser
- Certificat TLS de production avec nom de domaine réel
- Test d'accès depuis un réseau externe
- Extension des tests de charge
- Export de métriques dédié Asterisk (appels/SIP)
- Amélioration de la reconnexion après expiration du token JWT

## Auteur

**Salomon** — Étudiant en Ingénierie de Conception, option TS (Télécom et Services) — INGC2, ESMT Dakar
Encadrant : Professeur Boudal NIANG

---

> ⚠️ Ce dépôt ne contient aucune information sensible (mots de passe, dumps de base de données, certificats). Le fichier `.env` réel n'est jamais versionné — voir `.env.example` pour la structure attendue.
