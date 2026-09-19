import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Lu depuis l'environnement (injecté par docker-compose.yml : voir service
# "backend" -> environment -> DATABASE_URL). Valeur de repli utile uniquement
# pour du dev hors conteneur.
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://voxpme_app:voxpme@localhost:5432/voxpme",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
