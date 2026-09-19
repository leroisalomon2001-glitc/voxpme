from fastapi import FastAPI
from routers import tenants, endpoints, trunks, dashboard, auth_login
from prometheus_fastapi_instrumentator import Instrumentator


app = FastAPI(title="VoxPME Provisioning API", version="0.2.0")

app.include_router(tenants.router)
app.include_router(endpoints.router)
app.include_router(trunks.router)
app.include_router(dashboard.router)
app.include_router(auth_login.router)

Instrumentator().instrument(app).expose(app)

@app.get("/")
def root():
    return {"status": "ok", "service": "VoxPME Provisioning API"}


# Route ajoutée pour le healthcheck du service "backend" dans docker-compose.yml
# (test: python -c "urllib.request.urlopen('http://localhost:8000/health')").
# Pas de dépendance DB ici volontairement : un problème Postgres ne doit pas
# faire échouer le healthcheck HTTP, sinon docker-compose relance le conteneur
# en boucle même quand seul Postgres est indisponible.
@app.get("/health")
def health():
    return {"status": "ok"}
