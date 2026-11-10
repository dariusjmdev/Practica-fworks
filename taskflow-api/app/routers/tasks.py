from typing import Annotated


from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Task, Project, Category
from app.schemas import TaskCreate, TaskRead

router = APIRouter( 
    prefix="/tasks",
    tags=["tasks"]
)

def validate_task_references(
        task: TaskCreate,
        db: Annotated[Session, Depends(get_db)]
)-> TaskCreate:

    if task.project_id is not None and db.get(Project, task.project_id) is None:
        raise HTTPException(
            status_code=404,
            detail=f"El proyecto no existe."
        )

    if task.category_id is not None and db.get(Category, task.category_id) is None:
        raise HTTPException(
            status_code=404,
            detail=f"La categoría no existe."
        )

    return task 

@router.post(
    "",
    response_model=TaskRead,
    status_code=201,
    summary="Crear tarea"
)
def create_task(
    task: Annotated[TaskCreate, Depends(validate_task_references)],
    db: Annotated[Session, Depends(get_db)],
) -> TaskRead:
    record = Task(
        title=task.title,
        description=task.description,
        project_id=task.project_id,
        category_id=task.category_id  
    )
    db.add(record)
    db.commit()
    return TaskRead.model_validate(
        record,
        from_attributes=True
    )