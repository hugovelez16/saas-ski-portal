"""
Main API Application Module.

This module defines the FastAPI application, API endpoints, and middleware configuration.
It serves as the entry point for the backend service.
"""
import asyncio
import os
from contextlib import asynccontextmanager

from database import SessionLocal
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# Import modular routers
from routers import auth, companies, modules, users, work_logs
from sqlalchemy import text
from sqlalchemy.exc import OperationalError


def perform_session_cleanup():
    """
    Síncrona: Borra de la base de datos las sesiones inactivas por más de 30 días.
    """
    from datetime import datetime, timedelta

    import models
    db = SessionLocal()
    try:
        limit_date = datetime.utcnow() - timedelta(days=30)
        deleted_count = db.query(models.UserSession).filter(models.UserSession.last_active < limit_date).delete(synchronize_session=False)
        db.commit()
        print(f"Session Cleanup: Borradas {deleted_count} sesiones inactivas expiradas.")
    except Exception as e:
        print(f"Session Cleanup Error: {e}")
        db.rollback()
    finally:
        db.close()

async def cleanup_expired_sessions_loop():
    """
    Bucle en segundo plano para limpiar sesiones cada 24 horas.
    """
    while True:
        try:
            print("Iniciando tarea periódica de limpieza de sesiones...")
            await asyncio.to_thread(perform_session_cleanup)
        except Exception as e:
            print(f"Error en bucle de limpieza de sesiones: {e}")
        # Esperar 24 horas
        await asyncio.sleep(86400)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI.
    Handles startup logic (waiting for DB) and shutdown logic.
    """
    # Verify encryption key presence before startup
    if not os.getenv("ENCRYPTION_KEY"):
        print("CRITICAL ERROR: ENCRYPTION_KEY environment variable is not set!")
        raise RuntimeError("ENCRYPTION_KEY environment variable is not set. Aborting startup.")

    # Database readiness check (Wait for DB)
    # Total timeout: 60 seconds (30 retries * 2 seconds)
    retries = 30
    print("Checking database connection...")
    while retries > 0:
        try:
            db = SessionLocal()
            # Simple query to validate connection
            db.execute(text("SELECT 1"))
            db.close()
            print("Database connection established successfully.")
            break
        except OperationalError:
            retries -= 1
            if retries == 0:
                print("Could not connect to database after 60 seconds. Exiting.")
                # The app will likely fail to start properly, but we've tried our best.
                break
            print(f"Database not ready yet. Retrying in 2 seconds... ({retries} attempts remaining)")
            await asyncio.sleep(2)

    # Sembrado inicial de datos si procede
    try:
        from seed import seed_initial_data
        seed_initial_data()
    except Exception as seed_err:
        print(f"[Seed] No se pudo ejecutar el sembrado inicial en arranque: {seed_err}")

    # Iniciar la tarea periódica de limpieza de sesiones en segundo plano
    cleanup_task = asyncio.create_task(cleanup_expired_sessions_loop())

    yield

    # Cancelar la tarea de limpieza de sesiones al apagar la aplicación
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        print("Tarea periódica de limpieza de sesiones cancelada.")
    # Shutdown logic can be added here if needed (e.g. closing Redis connections)

app = FastAPI(
    title="Vesotel Gestor Jornada API",
    description="API for managing work logs and user settings.",
    root_path="/api",
    lifespan=lifespan
)

@app.get("/health", tags=["system"])
def health_check():
    """Endpoint de comprobacion de salud para Docker Compose y Gateway Nginx."""
    return {"status": "ok"}


@app.middleware("http")
async def log_requests(request: Request, call_next):
    origin = request.headers.get("origin")
    print(f"Incoming Request: {request.method} {request.url.path} | Origin: {origin}")
    try:
        return await call_next(request)
    except Exception as e:
        print(f"Request Failed: {e}")
        raise e

# CORS Configuration
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
origins = [origin.strip() for origin in allowed_origins_env.split(",")] if allowed_origins_env else []

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(work_logs.router)
app.include_router(companies.router)
app.include_router(modules.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
