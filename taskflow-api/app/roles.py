"""Permisos correspondientes a los roles de TaskFlow."""

# Los scopes de lectura se comparten entre ambos roles.
READ_SCOPES = {
    "tasks:read",
    "projects:read",
    "categories:read",
}

# El rol member añade permisos de escritura.
ALL_SCOPES = READ_SCOPES | {
    "tasks:write",
    "projects:write",
    "categories:write",
}

# El servidor decide qué permisos corresponden a cada rol.
ROLE_SCOPES = {
    "member": ALL_SCOPES,
    "viewer": READ_SCOPES,
}