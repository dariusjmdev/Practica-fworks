from datetime import datetime

from fastapi import FastAPI
from pydantic import BaseModel

from app.schemas import TaskCreate, TaskRead


app = FastAPI(
    title="TaskFlow API",
    description="API inicial del proyecto TaskFlow.",
    version="1.0.0"
)


class HealthResponse(BaseModel):
    status: str


class VersionResponse(BaseModel):
    version: str


class PingResponse(BaseModel):
    message: str


@app.get(
    "/health",
    summary="Comprobar el estado de la API",
    description="Devuelve el estado actual del servicio.",
    response_model=HealthResponse
)
def health() -> HealthResponse:
    return {"status": "ok"}


@app.get(
    "/version",
    summary="Consultar la versión de la API",
    description="Devuelve la versión actual de TaskFlow API.",
    response_model=VersionResponse
)
def version() -> VersionResponse:
    return {"version": "1.0.0"}


@app.get(
    "/ping",
    summary="Comprobar conectividad",
    description="Endpoint sencillo para comprobar que la API responde correctamente.",
    response_model=PingResponse
)
def ping() -> PingResponse:
    return {"message": "pong"}

@app.post(
    "/tasks",
    response_model=TaskRead,
    status_code=201,
    summary="Crear una nueva tarea",
)
def create_task(task: TaskCreate) -> TaskRead:
    # Aquí iría la lógica para crear la tarea en la base de datos
    # Por ahora, devolvemos un ejemplo de respuesta
    return TaskRead(
        id=1,
        title=task.title,
        description=task.description,
        project_id=task.project_id,
        completed=False,
        created_at=datetime.now()
    )