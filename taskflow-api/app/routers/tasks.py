"""CRUD de tareas con filtros combinables, ordenación y paginación."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, Security
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Category, Project, Task
from app.schemas import TaskCreate, TaskPage, TaskRead, TaskUpdate
from app.security import get_current_user


router = APIRouter(prefix="/tasks", tags=["tasks"])

# Nombre reutilizable para la sesión inyectada por FastAPI.
DbSession = Annotated[Session, Depends(get_db)]


def get_task_or_404(task_id: int, db: Session) -> Task:
    """Busca una tarea y centraliza el error de inexistencia."""
    record = db.get(Task, task_id)

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="La tarea no existe",
        )

    return record


def validate_task_references(
    task: TaskCreate,
    db: DbSession,
) -> TaskCreate:
    """Comprueba que las asociaciones opcionales existan."""
    if task.project_id is not None and db.get(Project, task.project_id) is None:
        raise HTTPException(
            status_code=404,
            detail="El proyecto no existe",
        )

    if task.category_id is not None and db.get(Category, task.category_id) is None:
        raise HTTPException(
            status_code=404,
            detail="La categoría no existe",
        )

    return task


@router.get(
    "",
    response_model=TaskPage,
    summary="Listar tareas",
    dependencies=[Security(get_current_user, scopes=["tasks:read"])],
)
def list_tasks(
    db: DbSession,
    project_id: int | None = None,
    completed: bool | None = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    sort_by: Literal["id", "title", "created_at"] = "id",
    order: Literal["asc", "desc"] = "asc",
):
    # Los filtros presentes se combinan mediante AND.
    # Usamos is not None para aplicar también completed=false.
    filters = []

    if project_id is not None:
        filters.append(Task.project_id == project_id)

    if completed is not None:
        filters.append(Task.completed == completed)

    # SQLite cuenta las tareas que cumplen los filtros.
    # El total corresponde al conjunto completo, antes de paginar.
    total = db.scalar(
        select(func.count(Task.id)).where(*filters)
    )

    # Literal restringe las columnas y direcciones admitidas.
    column = getattr(Task, sort_by)
    sorting = column.desc() if order == "desc" else column.asc()

    # Ordenamos y paginamos en la base de datos.
    # El ID desempata si varias tareas tienen el mismo título o fecha.
    query = (
        select(Task)
        .where(*filters)
        .order_by(sorting, Task.id)
        .offset(skip)
        .limit(limit)
    )

    return {
        "items": db.scalars(query).all(),
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get(
    "/{task_id}",
    response_model=TaskRead,
    summary="Consultar tarea",
    dependencies=[Security(get_current_user, scopes=["tasks:read"])],
)
def read_task(task_id: int, db: DbSession):
    return get_task_or_404(task_id, db)


@router.post(
    "",
    response_model=TaskRead,
    status_code=201,
    summary="Crear tarea",
    dependencies=[Security(get_current_user, scopes=["tasks:write"])],
)
def create_task(
    task: Annotated[TaskCreate, Depends(validate_task_references)],
    db: DbSession,
):
    # FastAPI reutiliza la sesión empleada por la dependencia.
    # model_dump convierte el esquema validado en un diccionario.
    record = Task(**task.model_dump())

    db.add(record)
    db.commit()

    return record


@router.put(
    "/{task_id}",
    response_model=TaskRead,
    summary="Editar tarea",
    dependencies=[Security(get_current_user, scopes=["tasks:write"])],
)
def update_task(
    task_id: int,
    task: TaskUpdate,
    db: DbSession,
):
    # Primero comprobamos la tarea y después sus nuevas referencias.
    record = get_task_or_404(task_id, db)
    validate_task_references(task, db)

    # Asignamos los campos editables del cuerpo recibido.
    # ID y created_at se conservan porque no están en TaskUpdate.
    for field, value in task.model_dump().items():
        setattr(record, field, value)

    db.commit()

    return record


@router.delete(
    "/{task_id}",
    status_code=204,
    summary="Eliminar tarea",
    dependencies=[Security(get_current_user, scopes=["tasks:write"])],
)
def delete_task(task_id: int, db: DbSession):
    record = get_task_or_404(task_id, db)

    db.delete(record)
    db.commit()

    # Una respuesta 204 no lleva cuerpo.
    return Response(status_code=204)