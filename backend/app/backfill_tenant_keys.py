import secrets
from database import SessionLocal
import models

db = SessionLocal()
for tenant in db.query(models.Tenant).filter(models.Tenant.api_key.is_(None)).all():
    tenant.api_key = secrets.token_hex(32)
    print(f"{tenant.slug}: {tenant.api_key}")
db.commit()
db.close()
