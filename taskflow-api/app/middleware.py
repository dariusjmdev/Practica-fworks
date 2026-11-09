# El módulo logging permite registrar información en el servidor.
#
# En este archivo lo utilizamos para guardar los detalles de los errores
# inesperados. Así podemos investigarlos sin enseñárselos al usuario.
import logging


# perf_counter permite medir intervalos de tiempo con precisión.
#
# Lo usamos para calcular cuánto tarda la aplicación en comenzar a
# devolver una respuesta.
from time import perf_counter


# uuid4 genera un identificador único aleatorio.
#
# Lo usamos para asignar un identificador distinto a cada petición y poder
# relacionar la respuesta con los registros del servidor.
from uuid import uuid4


# Request representa la petición HTTP que llega a la aplicación.
#
# Nos permite consultar información como la ruta solicitada y guardar
# datos asociados a esa petición concreta.
from fastapi import Request


# JSONResponse permite crear una respuesta HTTP cuyo contenido es JSON.
#
# La utilizamos para devolver al cliente un mensaje de error controlado.
from fastapi.responses import JSONResponse


# BaseHTTPMiddleware es una clase de Starlette que permite crear
# middlewares HTTP mediante un método llamado dispatch.
from starlette.middleware.base import BaseHTTPMiddleware


# Creamos un logger con un nombre propio para los errores de la aplicación.
#
# Este logger escribirá los errores en el registro configurado del servidor.
# El nombre permite identificar de dónde proceden los mensajes.
logger = logging.getLogger("taskflow.errors")


async def global_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """
    Gestiona una excepción inesperada.

    Recibe:
    - request: la petición durante la cual se produjo el error.
    - exc: la excepción que se ha producido.

    Hace dos cosas:
    1. Registra los detalles completos del error en el servidor.
    2. Devuelve al cliente un mensaje genérico con estado HTTP 500.

    Así el cliente sabe que ha ocurrido un error, pero no recibe el
    stacktrace ni otros detalles internos de la aplicación.
    """

    # request.state permite guardar datos propios durante una petición.
    #
    # Aquí intentamos recuperar el identificador que ha creado el
    # middleware de contexto.
    #
    # getattr recibe:
    # 1. El objeto donde buscar: request.state.
    # 2. El nombre del dato: "request_id".
    # 3. Un valor alternativo: "no-disponible".
    #
    # El valor alternativo se utiliza si, por algún motivo, la petición
    # todavía no tiene un identificador asociado.
    request_id = getattr(
        request.state,
        "request_id",
        "no-disponible",
    )

    # Registramos el error en el servidor.
    #
    # El mensaje incluye:
    # - El identificador de la petición.
    # - La ruta que se estaba intentando utilizar.
    #
    # exc_info indica a logging qué excepción debe registrar, incluyendo
    # su tipo, su mensaje y su stacktrace.
    #
    # El stacktrace se queda en el registro del servidor; no se incluye
    # en el JSON que recibe el cliente.
    logger.exception(
        "Error no controlado. request_id=%s ruta=%s",
        request_id,
        request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )

    # Devolvemos una respuesta HTTP 500 con un mensaje genérico.
    #
    # JSONResponse transforma el diccionario de content en JSON.
    #
    # "error" describe el problema sin exponer información interna.
    # "error_code" proporciona un código estable que permite identificar
    # el tipo de error desde el frontend.
    return JSONResponse(
        status_code=500,
        content={
            "error": "Se ha producido un error interno en el servidor.",
            "error_code": "INTERNAL_SERVER_ERROR",
        },
    )


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware encargado de capturar errores inesperados.

    Su objetivo es convertir esos errores en una respuesta HTTP 500
    segura, utilizando el mismo manejador global definido anteriormente.
    """

    async def dispatch(self, request: Request, call_next):
        """
        Se ejecuta para cada petición que llega a este middleware.

        - request contiene los datos de la petición.
        - call_next continúa el recorrido hacia las siguientes capas
          hasta llegar al endpoint correspondiente.
        """

        try:
            # Dejamos que la petición continúe hacia el endpoint.
            #
            # Si todo funciona correctamente, call_next devuelve una
            # respuesta, que simplemente devolvemos sin modificar.
            return await call_next(request)

        except Exception as exc:
            # Si durante la ejecución aparece una excepción no controlada,
            # llamamos al manejador global.
            #
            # El manejador registra el error y crea una respuesta 500
            # sin mostrar información interna al cliente.
            return await global_exception_handler(request, exc)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware que añade información común a las respuestas HTTP.

    Sus responsabilidades son:
    - Medir el tiempo de procesamiento.
    - Generar un identificador único para cada petición.
    - Añadir ambos valores a las cabeceras de la respuesta.
    """

    async def dispatch(self, request: Request, call_next):
        """
        Se ejecuta alrededor del procesamiento de cada petición.

        Primero prepara los datos; después deja continuar la petición y,
        cuando recibe la respuesta, añade las cabeceras.
        """

        # Guardamos el instante en el que comienza el procesamiento.
        #
        # perf_counter devuelve un valor útil para medir intervalos;
        # no representa una fecha ni una hora que deba mostrarse.
        start_time = perf_counter()

        # Generamos un identificador único aleatorio.
        #
        # str lo convierte en una cadena de texto para poder utilizarlo
        # en una cabecera HTTP y en los registros.
        request_id = str(uuid4())

        # Guardamos el identificador en el estado de la petición.
        #
        # De esta manera, el manejador de errores puede recuperarlo si
        # algo falla durante el procesamiento de esta misma petición.
        request.state.request_id = request_id

        # La petición continúa hacia los demás middlewares y el endpoint.
        #
        # Cuando recibimos la respuesta, la guardamos en esta variable
        # para poder añadirle las cabeceras antes de devolverla.
        response = await call_next(request)

        # Calculamos el tiempo transcurrido desde que comenzó la petición.
        #
        # La diferencia de perf_counter está en segundos, por eso
        # multiplicamos por 1000 para convertirla a milisegundos.
        process_time_ms = (perf_counter() - start_time) * 1000

        # Añadimos el tiempo a la cabecera exigida en la práctica.
        #
        # :.2f muestra el número con dos decimales. Por ejemplo:
        # X-Process-Time: 2.35 ms
        response.headers["X-Process-Time"] = f"{process_time_ms:.2f} ms"

        # Añadimos el identificador de la petición a la respuesta.
        #
        # Si se produce un error, este identificador permite relacionar
        # lo que ve el cliente con la entrada del registro del servidor.
        response.headers["X-Request-ID"] = request_id

        # Devolvemos la respuesta con las dos cabeceras añadidas.
        return response