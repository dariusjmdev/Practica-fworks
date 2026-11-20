"""Registro, login y renovación con rotación de tokens."""

from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UserRole
from app.schemas import (
    RefreshRequest,
    RegistrationResponse,
    TokenResponse,
    UserCreate,
)
from app.security import (
    DUMMY_HASH,
    REFRESH_TOKEN_EXPIRE_DAYS,
    credentials_error,
    hash_password,
    rotate_refresh_token,
    stage_token_pair,
    user_scopes,
    verify_password,
)


router = APIRouter(prefix="/auth", tags=["auth"])
DbSession = Annotated[Session, Depends(get_db)]

# Se devuelve el mismo texto con nombres nuevos y duplicados.
REGISTRATION_MESSAGE = (
    "Si los datos permiten el registro, "
    "la cuenta está preparada para iniciar sesión."
)


@router.post(
    "/register",
    response_model=RegistrationResponse,
    status_code=201,
    summary="Registrar usuario",
)
def register(user_data: UserCreate, db: DbSession):
    # Calculamos el hash incluso cuando el nombre estaba ocupado.
    user = User(
        username=user_data.username,
        hashed_password=hash_password(user_data.password),
    )

    db.add(user)

    try:
        # flush inserta el usuario y permite obtener su ID.
        db.flush()

        # El registro público asigna el rol member.
        db.add(
            UserRole(
                user_id=user.id,
                role="member",
            )
        )

        db.commit()

    except IntegrityError:
        db.rollback()

        # Si el nombre estaba registrado, devolvemos la misma respuesta.
        # La contraseña de la cuenta existente permanece en la BD.
        existing = db.scalar(
            select(User.id).where(
                User.username == user_data.username
            )
        )

        # Otros errores de integridad se gestionan como errores internos.
        if existing is None:
            raise

    return {"message": REGISTRATION_MESSAGE}


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Iniciar sesión",
)
def login(
    form: Annotated[
        OAuth2PasswordRequestForm,
        Depends(),
    ],
    db: DbSession,
    response: Response,
):
    user = db.scalar(
        select(User).where(User.username == form.username)
    )

    # Si la cuenta no existe, usamos el hash auxiliar para ejecutar
    # igualmente una verificación bcrypt.
    saved_hash = (
        user.hashed_password
        if user is not None
        else DUMMY_HASH
    )

    valid_password = verify_password(
        form.password,
        saved_hash,
    )

    if not valid_password or user is None:
        raise credentials_error()

    allowed = user_scopes(user, db)
    requested = set(form.scopes)

    # Un usuario solo puede solicitar scopes permitidos por su rol.
    if not requested <= allowed:
        raise HTTPException(
            status_code=403,
            detail="Permisos insuficientes",
            headers={
                "WWW-Authenticate": (
                    'Bearer error="insufficient_scope"'
                )
            },
        )

    # Sin petición explícita de scopes se conceden los del rol.
    granted = requested if requested else allowed

    # Vencimiento absoluto de la familia desde este login.
    expires_at = (
        datetime.now(timezone.utc)
        + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    ).replace(tzinfo=None)

    pair = stage_token_pair(
        db,
        user,
        granted,
        str(uuid4()),
        expires_at,
    )

    db.commit()

    # Las respuestas que contienen secretos no deben almacenarse en caché.
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"

    return pair


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Renovar y rotar tokens",
)
def refresh(
    data: RefreshRequest,
    db: DbSession,
    response: Response,
):
    # La función realiza la renovación y confirma su transacción.
    pair = rotate_refresh_token(
        data.refresh_token,
        db,
    )

    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"

    return pair