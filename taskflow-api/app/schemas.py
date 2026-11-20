"""Contratos de entrada y salida de los tres recursos."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TaskCreate(BaseModel):
    """Datos que acepta la creación de una tarea."""

    title: str = Field(min_length=1, max_length=100)
    description: str | None = None
    project_id: int | None = None
    category_id: int | None = None


class TaskUpdate(TaskCreate):
    """PUT permite sustituir los campos editables y cambiar el estado."""

    completed: bool


class TaskRead(TaskCreate):
    """Respuesta construida a partir de una entidad de SQLAlchemy."""

    # Permite a Pydantic leer atributos de un objeto ORM.
    model_config = ConfigDict(from_attributes=True)

    id: int
    completed: bool
    created_at: datetime


class TaskPage(BaseModel):
    """Página de tareas y metadatos para recorrer los resultados."""

    items: list[TaskRead]
    total: int
    skip: int
    limit: int


class ProjectCreate(BaseModel):
    """Datos de creación y sustitución de un proyecto."""

    name: str = Field(min_length=1)
    description: str | None = None


class ProjectRead(ProjectCreate):
    """Datos básicos del proyecto."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class ProjectDetail(ProjectRead):
    """El detalle del proyecto incluye sus tareas asociadas."""

    tasks: list[TaskRead]


class CategoryCreate(BaseModel):
    """Datos de creación y sustitución de una categoría."""

    name: str = Field(min_length=1)
    color: str = Field(min_length=1)


class CategoryRead(CategoryCreate):
    """Datos básicos de la categoría."""

    model_config = ConfigDict(from_attributes=True)

    id: int


class CategoryDetail(CategoryRead):
    """El detalle de la categoría incluye sus tareas asociadas."""

    tasks: list[TaskRead]


class ResourceSummary(BaseModel):
    """Contadores solicitados para el nivel excelente de la rúbrica."""

    total: int
    with_tasks: int

class UserCreate(BaseModel):
    """Datos públicos para registrar una cuenta."""

    # Rechaza campos adicionales, como un role enviado por el cliente.
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        """Evita entradas que bcrypt truncaría o no puede procesar."""
        if len(value.encode("utf-8")) > 72 or "\x00" in value:
            raise ValueError(
                "La contraseña debe ocupar entre 1 y 72 bytes válidos"
            )

        return value


class RegistrationResponse(BaseModel):
    """Respuesta común para un nombre nuevo o ya utilizado."""

    message: str


class TokenResponse(BaseModel):
    """Par de tokens devuelto al iniciar sesión o renovar."""

    access_token: str
    token_type: str = "bearer"
    refresh_token: str

    # Duración del access token en segundos.
    expires_in: int

    # Permisos concedidos, separados por espacios.
    scope: str


class RefreshRequest(BaseModel):
    """Cuerpo recibido por el endpoint de renovación."""

    refresh_token: str = Field(min_length=1, max_length=200)