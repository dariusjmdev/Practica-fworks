from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["system"])

class HealthResponse(BaseModel):
    status: str

class VersionResponse(BaseModel):
    version: str

class PingResponse(BaseModel):
    message: str

@router.get(
    "/health",
    summary="Comprobar el estado de la API",
    description="Devuelve el estado actual del servicio.",
    response_model=HealthResponse,
)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get(
    "/version",
    summary="Consultar la versión de la API",
    description="Devuelve la versión actual de TaskFlow API.",
    response_model=VersionResponse,
)
def version() -> VersionResponse:
    return VersionResponse(version="1.0.0")


@router.get(
    "/ping",
    summary="Comprobar conectividad",
    description="Endpoint sencillo para comprobar que la API responde.",
    response_model=PingResponse,
)
def ping() -> PingResponse:
    return PingResponse(message="pong")
