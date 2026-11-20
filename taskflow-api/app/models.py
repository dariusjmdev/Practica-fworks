"""Define las tablas y las relaciones del espacio compartido de TaskFlow."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    """Cuenta de usuario con nombre único y contraseña representada por su hash."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    # La restricción unique impide guardar dos usuarios con el mismo nombre.
    username: Mapped[str] = mapped_column(String, unique=True)
    hashed_password: Mapped[str] = mapped_column(String)


class Project(Base):
    """Proyecto del espacio de trabajo compartido."""

    __tablename__ = "projects"

    # El proyecto es compartido, por eso el modelo no tiene owner_id.
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text)

    # Conserva la fecha que ya devolvía POST /projects en la práctica 1.4.
    # Pasamos datetime.now sin paréntesis para calcularla en cada inserción.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # Permite obtener todas las tareas con project.tasks.
    # back_populates enlaza esta lista con el atributo Task.project.
    # Al borrar el proyecto se borran las tareas asociadas. Para las que
    # todavía no están cargadas, SQLite aplica ON DELETE CASCADE.
    tasks: Mapped[list["Task"]] = relationship(
        back_populates="project",
        cascade="all, delete",
        passive_deletes=True,
    )


class Category(Base):
    """Categoría que puede clasificar varias tareas."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)
    color: Mapped[str] = mapped_column(String)

    # Al borrar la categoría conservamos las tareas y las dejamos
    # sin categoría. La clave foránea de Task define ON DELETE SET NULL.
    tasks: Mapped[list["Task"]] = relationship(
        back_populates="category",
        passive_deletes=True,
    )


class Task(Base):
    """Tarea pendiente por defecto, con proyecto y categoría opcionales."""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)

    # String(100) expresa la longitud prevista en el modelo.
    # La API comprueba el límite de 100 caracteres en TaskCreate.
    title: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)

    # Toda tarea nueva empieza pendiente y recibe su fecha de creación.
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # Estas columnas guardan los IDs. El tipo int | None permite NULL,
    # así que una tarea puede crearse sin proyecto, sin categoría o sin ambos.
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),
    )

    # Estas relaciones permiten navegar a los objetos asociados.
    # Cada una apunta al atributo tasks del modelo correspondiente.
    project: Mapped[Project | None] = relationship(back_populates="tasks")
    category: Mapped[Category | None] = relationship(back_populates="tasks")
class UserRole(Base):
    """Guarda el rol de una cuenta en una tabla independiente."""

    __tablename__ = "user_roles"

    # Cada usuario tiene como máximo una asignación de rol.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    role: Mapped[str] = mapped_column(String, default="member")


class RefreshToken(Base):
    """Guarda el estado de los tokens de renovación."""

    __tablename__ = "refresh_tokens"

    # Se almacena la huella SHA-256 del secreto.
    token_hash: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    # Agrupa los tokens procedentes del mismo inicio de sesión.
    family_id: Mapped[str] = mapped_column(
        String(36),
        index=True,
    )

    scopes: Mapped[str] = mapped_column(Text)

    # Fecha UTC sin zona para trabajar con SQLite.
    expires_at: Mapped[datetime] = mapped_column(DateTime)

    consumed: Mapped[bool] = mapped_column(Boolean, default=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)

