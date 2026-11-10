import os

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.middleware import (
    ErrorHandlingMiddleware,
    RequestContextMiddleware,
    global_exception_handler,
)
from app.routers.projects import router as projects_router
from app.routers.system import router as system_router
from app.routers.tasks import router as tasks_router
from app.database import Base, engine

@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Prepara SQLite al arrancar y livera conexiones al apagar."""

    # Los routers ya han importado models.py, así que Base conoce las tablas
    #create_all() crea las que falten en la base de datos. No borra las existentes.
    Base.metadata.create_all(bind=engine)

    try:
        yield
    finally:
        engine.dispose()

    
app = FastAPI(
    title="TaskFlow API",
    description="API inicial del proyecto TaskFlow.",
    version="1.0.0",
    debug=False,
    lifespan=lifespan
)


# Registra el manejador global de errores no controlados.
app.add_exception_handler(Exception, global_exception_handler)


# Captura los errores de los endpoints y genera una respuesta segura.
app.add_middleware(ErrorHandlingMiddleware)


# Permite configurar los orígenes según el entorno.
# Por defecto, solo se permite el frontend local indicado en el enunciado.
allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    # Permite al frontend leer estas cabeceras desde JavaScript.
    expose_headers=["X-Process-Time", "X-Request-ID"],
)


# Se añade el último para que sea el primero en recibir la petición
# y pueda añadir sus cabeceras también a las respuestas de error.
app.add_middleware(RequestContextMiddleware)


# Registro de rutas.
app.include_router(system_router)
app.include_router(tasks_router)
app.include_router(projects_router)