"""CRUD de categorías con bloqueo del borrado si tienen tareas."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Category
from app.schemas import (
    CategoryCreate,
    CategoryDetail,
    CategoryRead,
    ResourceSummary,
)


router = APIRouter(prefix="/categories", tags=["categories"])
DbSession = Annotated[Session, Depends(get_db)]


def get_category_or_404(category_id: int, db: Session) -> Category:
    """Busca una categoría o devuelve un error 404."""
    record = db.get(Category, category_id)

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="La categoría no existe",
        )

    return record


@router.get(
    "/summary",
    response_model=ResourceSummary,
    summary="Resumen de categorías",
)
def category_summary(db: DbSession):
    # Calculamos el total y cuántas categorías tienen tareas.
    return {
        "total": db.scalar(select(func.count(Category.id))),
        "with_tasks": db.scalar(
            select(func.count(Category.id)).where(Category.tasks.any())
        ),
    }


@router.get(
    "",
    response_model=list[CategoryRead],
    summary="Listar categorías",
)
def list_categories(db: DbSession):
    return db.scalars(
        select(Category).order_by(Category.id)
    ).all()


@router.get(
    "/{category_id}",
    response_model=CategoryDetail,
    summary="Consultar categoría",
)
def read_category(category_id: int, db: DbSession):
    # El detalle carga también las tareas relacionadas.
    query = (
        select(Category)
        .options(selectinload(Category.tasks))
        .where(Category.id == category_id)
    )

    record = db.scalar(query)

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="La categoría no existe",
        )

    return record


@router.post(
    "",
    response_model=CategoryRead,
    status_code=201,
    summary="Crear categoría",
)
def create_category(category: CategoryCreate, db: DbSession):
    record = Category(**category.model_dump())

    db.add(record)
    db.commit()

    return record


@router.put(
    "/{category_id}",
    response_model=CategoryRead,
    summary="Editar categoría",
)
def update_category(
    category_id: int,
    category: CategoryCreate,
    db: DbSession,
):
    record = get_category_or_404(category_id, db)

    record.name = category.name
    record.color = category.color

    db.commit()

    return record


@router.delete(
    "/{category_id}",
    status_code=204,
    summary="Eliminar categoría",
)
def delete_category(category_id: int, db: DbSession):
    # El DELETE exige que la categoría no tenga tareas.
    # La comprobación y el borrado se realizan en una sola sentencia SQL.
    result = db.execute(
        delete(Category)
        .where(
            Category.id == category_id,
            ~Category.tasks.any(),
        )
        .execution_options(synchronize_session=False)
    )

    if result.rowcount == 0:
        # Si no se borró ninguna fila, distinguimos las dos causas:
        # categoría inexistente (404) o categoría con tareas (409).
        db.rollback()
        get_category_or_404(category_id, db)

        raise HTTPException(
            status_code=409,
            detail="La categoría tiene tareas asociadas",
        )

    db.commit()

    return Response(status_code=204)