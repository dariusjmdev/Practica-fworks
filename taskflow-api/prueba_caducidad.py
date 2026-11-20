import getpass
import json
import os
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from jose import ExpiredSignatureError, JWTError, jwt


# 1. Configuración de la prueba.
# Utilizamos la misma dirección y algoritmo que nuestra API.
BASE_URL = "http://127.0.0.1:8000"
ALGORITHM = "HS256"

# Recuperamos la clave de esta terminal.
# Si no está configurada, la pedimos sin mostrarla en pantalla.
secret_key = os.getenv("TASKFLOW_SECRET_KEY") or getpass.getpass(
    "Introduce la misma TASKFLOW_SECRET_KEY del servidor: "
)


# 2. Función para enviar peticiones.
# También recoge las respuestas de error HTTP para poder comprobar el 401.
def enviar(ruta, datos=None, token=None):
    headers = {}

    if datos is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"

    if token is not None:
        headers["Authorization"] = f"Bearer {token}"

    peticion = Request(
        BASE_URL + ruta,
        data=datos,
        headers=headers,
    )

    try:
        respuesta = urlopen(peticion, timeout=15)
    except HTTPError as error:
        respuesta = error

    with respuesta:
        return (
            respuesta.code,
            respuesta.headers,
            respuesta.read().decode("utf-8"),
        )


# 3. Iniciamos sesión para obtener un token y una sesión nuevos.
# La contraseña se introduce sin aparecer en pantalla.
usuario = input("Usuario [darius_prueba]: ").strip() or "darius_prueba"
password = getpass.getpass("Contraseña: ")

datos_login = urlencode({
    "username": usuario,
    "password": password,
}).encode("utf-8")

codigo, _, cuerpo = enviar("/auth/login", datos=datos_login)

if codigo != 200:
    raise SystemExit(f"El login ha devuelto {codigo}. Revisa las credenciales.")

token_valido = json.loads(cuerpo)["access_token"]


# 4. Validamos la firma con la clave local.
# Así comprobamos que coincide con la utilizada por el servidor.
try:
    contenido = jwt.decode(
        token_valido,
        secret_key,
        algorithms=[ALGORITHM],
    )
except JWTError:
    raise SystemExit(
        "No se pudo validar el token. Comprueba que la clave "
        "es exactamente la misma que utiliza el servidor."
    )

duracion = contenido["exp"] - contenido["iat"]
print(f"Duración del token emitido: {duracion} segundos")


# 5. Comprobamos que el token original permite consultar proyectos.
codigo_valido, _, _ = enviar("/projects", token=token_valido)
print(f"Petición con token vigente: {codigo_valido}")

if codigo_valido != 200:
    raise SystemExit("El token vigente debe funcionar antes de continuar.")


# 6. Cambiamos únicamente la expiración y generamos una firma nueva válida.
# Conservamos usuario, permisos e identificador de sesión.
contenido["exp"] = int(time.time()) - 60

token_caducado = jwt.encode(
    contenido,
    secret_key,
    algorithm=ALGORITHM,
)

# Confirmamos localmente que el motivo del rechazo es la caducidad.
try:
    jwt.decode(token_caducado, secret_key, algorithms=[ALGORITHM])
except ExpiredSignatureError:
    print("Verificación local: firma válida y token caducado")
else:
    raise SystemExit("El token de prueba debería estar caducado.")


# 7. Enviamos el token caducado al mismo endpoint.
codigo_caducado, headers, cuerpo = enviar(
    "/projects",
    token=token_caducado,
)

print(f"Petición con token caducado: {codigo_caducado}")
print("WWW-Authenticate:", headers.get("WWW-Authenticate"))
print("Respuesta:", cuerpo)

if (
    duracion != 1800
    or codigo_caducado != 401
    or headers.get("WWW-Authenticate") != "Bearer"
):
    raise SystemExit("La prueba no ha obtenido todos los resultados esperados.")

print("OK: caducidad del JWT comprobada.")