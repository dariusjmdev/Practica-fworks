from datetime import datetime

from fastapi import FastAPI
from pydantic import BaseModel

from app.routers.tasks import router as tasks_router
from app.routers.projects import router as projects_router

from app.schemas import TaskCreate, TaskRead


app = FastAPI(
    title="TaskFlow API",
    description="API inicial del proyecto TaskFlow.",
    version="1.0.0"
)

app.include_router(tasks_router)
app.include_router(projects_router)

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

