"""Configura SQLite y proporciona una sesión de base de datos por petición."""

import os
from collections.abc import Generator
from pathlib import Path
from sqlite3 import Connection

from sqlalchemy import URL, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Base común de los modelos. Reúne las tablas que SQLAlchemy conoce."""


# Por defecto, taskflow.db se guarda junto a requirements.txt.
# Usamos una ruta absoluta para que el archivo quede en el mismo sitio
# aunque arranquemos Uvicorn desde otro directorio.
default_db_path = Path(__file__).resolve().parents[1] / "taskflow.db"

# Una variable de entorno permite usar otro archivo, por ejemplo para pruebas.
db_path = Path(os.getenv("TASKFLOW_DB_PATH", str(default_db_path))).resolve()


# El motor configura el acceso a SQLite y administra las conexiones.
# El pool reutiliza conexiones para evitar abrir una nueva en cada petición.
engine = create_engine(
    URL.create("sqlite", database=str(db_path)),
    connect_args={
        # FastAPI puede ejecutar una dependencia y su ruta síncrona
        # en hilos distintos durante la misma petición.
        "check_same_thread": False,

        # Segundos que SQLite espera si otro proceso bloquea el archivo.
        "timeout": float(os.getenv("TASKFLOW_SQLITE_TIMEOUT", "5")),
    },

    # Comprueba la conexión al sacarla del pool antes de reutilizarla.
    pool_pre_ping=True,

    # Segundos que se espera una conexión libre si el pool está ocupado.
    pool_timeout=float(os.getenv("TASKFLOW_POOL_TIMEOUT", "10")),
)


@event.listens_for(engine, "connect")
def enable_sqlite_foreign_keys(connection: Connection, _record: object) -> None:
    """Activa las claves foráneas en cada conexión nueva de SQLite."""
    # SQLite configura esta opción por conexión. El evento garantiza
    # que todas comprueben las referencias y apliquen CASCADE o SET NULL.
    cursor = connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()


# SessionLocal es una fábrica. Cada llamada crea una sesión independiente.
# expire_on_commit=False permite leer los atributos cargados después de
# commit() al construir la respuesta, sin volver a consultarlos.
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Entrega una sesión a FastAPI y la cierra al acabar la petición."""
    session = SessionLocal()
    try:
        # FastAPI entrega esta sesión a las rutas que usan Depends(get_db).
        yield session
    finally:
        # Se ejecuta incluso si la ruta lanza una excepción.
        session.close()