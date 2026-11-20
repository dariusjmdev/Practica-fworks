"""Hashing, JWT, scopes y rotación de refresh tokens."""

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import RefreshToken, User, UserRole
from app.roles import ALL_SCOPES, ROLE_SCOPES


# La clave permanece en el entorno del servidor.
# Exigimos una longitud mínima para evitar claves demasiado cortas.
SECRET_KEY = os.getenv("TASKFLOW_SECRET_KEY", "")

if len(SECRET_KEY.encode("utf-8")) < 32:
    raise RuntimeError(
        "TASKFLOW_SECRET_KEY debe tener al menos 32 bytes"
    )


ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# La familia puede renovarse durante siete días desde el login.
# Cada rotación conserva la fecha de vencimiento original.
REFRESH_TOKEN_EXPIRE_DAYS = 7


# bcrypt genera una sal aleatoria para cada hash.
# El coste 12 determina el trabajo necesario para calcularlo.
password_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
)


# Integra la autenticación y los scopes con Swagger.
# auto_error=False permite generar nosotros el 401 con su cabecera.
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login",
    scopes={
        scope: scope.replace(":", " - ")
        for scope in sorted(ALL_SCOPES)
    },
    auto_error=False,
)


def credentials_error() -> HTTPException:
    """Respuesta común para credenciales ausentes o inválidas."""
    return HTTPException(
        status_code=401,
        detail="No se han podido validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )


def hash_password(password: str) -> str:
    """Genera un hash bcrypt con sal aleatoria y coste 12."""
    return password_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verifica una contraseña sin permitir truncamiento."""
    if len(password.encode("utf-8")) > 72 or "\x00" in password:
        return False

    return password_context.verify(password, hashed_password)


# Si un usuario no existe, también verificamos contra un hash.
# Esto reduce diferencias de trabajo respecto a una contraseña errónea.
DUMMY_HASH = hash_password(secrets.token_urlsafe(24))


def user_scopes(user: User, db: Session) -> set[str]:
    """Obtiene los permisos actuales de la cuenta."""
    assignment = db.get(UserRole, user.id)

    # Compatibilidad con las cuentas creadas en la versión anterior.
    role = assignment.role if assignment is not None else "member"

    # Un rol desconocido obtiene cero permisos.
    return set(ROLE_SCOPES.get(role, set()))


def create_access_token(
    username: str,
    scopes: set[str],
    family_id: str,
) -> str:
    """Crea un JWT firmado con identidad, permisos y expiración."""
    now = datetime.now(timezone.utc)

    return jwt.encode(
        {
            "sub": username,
            "iat": now,
            "exp": now + timedelta(
                minutes=ACCESS_TOKEN_EXPIRE_MINUTES
            ),
            "jti": str(uuid4()),
            "type": "access",
            "scope": " ".join(sorted(scopes)),
            "sid": family_id,
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def refresh_hash(raw_token: str) -> str:
    """Calcula la huella del secreto de renovación."""
    return hashlib.sha256(
        raw_token.encode("utf-8")
    ).hexdigest()


def stage_token_pair(
    db: Session,
    user: User,
    scopes: set[str],
    family_id: str,
    expires_at: datetime,
) -> dict:
    """Prepara un par de tokens dentro de la transacción actual."""

    # Generamos un secreto aleatorio con 32 bytes de entropía.
    raw_refresh = secrets.token_urlsafe(32)

    # La base de datos recibe únicamente su huella.
    db.add(
        RefreshToken(
            token_hash=refresh_hash(raw_refresh),
            user_id=user.id,
            family_id=family_id,
            scopes=" ".join(sorted(scopes)),
            expires_at=expires_at,
        )
    )

    return {
        "access_token": create_access_token(
            user.username,
            scopes,
            family_id,
        ),
        "token_type": "bearer",
        "refresh_token": raw_refresh,
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "scope": " ".join(sorted(scopes)),
    }


def rotate_refresh_token(
    raw_token: str,
    db: Session,
) -> dict:
    """Consume el refresh una vez y entrega un nuevo par."""
    digest = refresh_hash(raw_token)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # La comprobación y el consumo se realizan en un único UPDATE.
    # Dos solicitudes concurrentes no pueden consumir válidamente
    # el mismo token.
    result = db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.token_hash == digest,
            RefreshToken.consumed.is_(False),
            RefreshToken.revoked.is_(False),
            RefreshToken.expires_at > now,
        )
        .values(consumed=True)
        .execution_options(synchronize_session=False)
    )

    record = db.get(RefreshToken, digest)

    if result.rowcount != 1:
        if record is not None and record.consumed:
            # Reutilizar un refresh consumido indica un posible robo.
            # Revocamos todos los tokens de su familia.
            db.execute(
                update(RefreshToken)
                .where(
                    RefreshToken.family_id == record.family_id
                )
                .values(revoked=True)
                .execution_options(synchronize_session=False)
            )

            # Confirmamos la revocación antes de responder con 401.
            db.commit()
        else:
            db.rollback()

        raise credentials_error()

    user = db.get(User, record.user_id)

    if user is None:
        db.rollback()
        raise credentials_error()

    # La renovación conserva como máximo los permisos iniciales
    # y también respeta cualquier reducción del rol.
    scopes = set(record.scopes.split()) & user_scopes(user, db)

    pair = stage_token_pair(
        db,
        user,
        scopes,
        record.family_id,
        record.expires_at,
    )

    # Confirma juntos el consumo del anterior y el nuevo refresh.
    db.commit()

    return pair


def get_current_user(
    security_scopes: SecurityScopes,
    token: Annotated[
        str | None,
        Depends(oauth2_scheme),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Valida el JWT, la familia de sesión y los permisos."""
    if token is None:
        raise credentials_error()

    try:
        # El algoritmo está fijado en el servidor.
        # Además de verificar la firma, exigimos sub y exp.
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={
                "require_exp": True,
                "require_sub": True,
            },
        )
    except JWTError:
        raise credentials_error()

    username = payload.get("sub")
    scope = payload.get("scope")
    family_id = payload.get("sid")

    # Comprobamos los campos necesarios antes de consultar la BD.
    if (
        payload.get("type") != "access"
        or not isinstance(username, str)
        or not username
        or not isinstance(scope, str)
        or not isinstance(family_id, str)
    ):
        raise credentials_error()

    user = db.scalar(
        select(User).where(User.username == username)
    )

    if user is None:
        raise credentials_error()

    # Debe existir un refresh activo en la familia.
    # Esto permite invalidar inmediatamente los access tokens
    # cuando se detecta una reutilización del refresh.
    session_token = db.scalar(
        select(RefreshToken.token_hash)
        .where(
            RefreshToken.family_id == family_id,
            RefreshToken.user_id == user.id,
            RefreshToken.revoked.is_(False),
            RefreshToken.consumed.is_(False),
            RefreshToken.expires_at
            > datetime.now(timezone.utc).replace(tzinfo=None),
        )
        .limit(1)
    )

    if session_token is None:
        raise credentials_error()

    # El permiso debe estar tanto en el JWT como en el rol actual.
    required = set(security_scopes.scopes)
    available = set(scope.split()) & user_scopes(user, db)

    if not required <= available:
        raise HTTPException(
            status_code=403,
            detail="Permisos insuficientes",
            headers={
                "WWW-Authenticate": (
                    'Bearer error="insufficient_scope", '
                    f'scope="{security_scopes.scope_str}"'
                )
            },
        )

    return user