"""Asignación local de roles a las cuentas de TaskFlow."""

import argparse

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import User, UserRole
from app.roles import ROLE_SCOPES


def main() -> None:
    """Cambia el rol de una cuenta existente."""
    parser = argparse.ArgumentParser(
        description="Asignar un rol de TaskFlow"
    )

    parser.add_argument(
        "--username",
        required=True,
    )

    parser.add_argument(
        "--role",
        required=True,
        choices=sorted(ROLE_SCOPES),
    )

    args = parser.parse_args()

    # Crea las tablas adicionales si todavía no se ha arrancado la API.
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        user = db.scalar(
            select(User).where(
                User.username == args.username
            )
        )

        if user is None:
            parser.error("No existe ese usuario")

        assignment = db.get(UserRole, user.id)

        # Las cuentas anteriores pueden no tener una fila de rol.
        if assignment is None:
            db.add(
                UserRole(
                    user_id=user.id,
                    role=args.role,
                )
            )
        else:
            assignment.role = args.role

        db.commit()

        print(
            f"Rol actualizado: {user.username} -> {args.role}"
        )


if __name__ == "__main__":
    main()