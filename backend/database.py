import os

# Database Connection URL
# Defaults to a local PostgreSQL container if not specified in environment variables
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

# Database Connection Configuration
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    SQLALCHEMY_DATABASE_URL = DATABASE_URL
else:
    POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "postgres")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")  # Usar 'postgres' por defecto (nombre del servicio)
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

    # Construir URL escapando caracteres especiales en el password (como '@') si esta definido
    auth_part = POSTGRES_USER
    if POSTGRES_PASSWORD:
        auth_part = f"{POSTGRES_USER}:{quote_plus(POSTGRES_PASSWORD)}"

    SQLALCHEMY_DATABASE_URL = (
        f"postgresql://{auth_part}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )

# Create SQLAlchemy engine
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Create SessionLocal class
# Each instance of SessionLocal will be a database session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for ORM models
Base = declarative_base()


def get_db():
    """
    Dependency generator that creates a new database session for a request
    and closes it after the request is finished.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
