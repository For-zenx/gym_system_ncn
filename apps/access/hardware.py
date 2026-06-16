import logging
import time
from dataclasses import dataclass

import serial
from django.conf import settings

logger = logging.getLogger(__name__)

MSG_NOT_CONFIGURED = (
    "El torniquete no está configurado en este equipo. Avise al administrador."
)
MSG_NOT_CONNECTED = (
    "No se pudo conectar con el torniquete. Verifique que esté encendido y conectado, "
    "o avise al administrador."
)
MSG_GENERIC = (
    "No se pudo abrir el torniquete. Intente nuevamente o avise al administrador."
)


@dataclass
class TurnstilePulseResult:
    success: bool
    port: str
    seconds: float
    message: str = ""


def _friendly_error(exc):
    exc_text = str(exc).lower()
    if "filenotfounderror" in exc_text or "could not open port" in exc_text:
        return MSG_NOT_CONNECTED
    if "access is denied" in exc_text or "permission" in exc_text:
        return (
            "No hay permiso para usar el dispositivo del torniquete. "
            "Avise al administrador."
        )
    if "no hay puerto com configurado" in exc_text:
        return MSG_NOT_CONFIGURED
    return MSG_GENERIC


def open_turnstile(port=None, pulse_seconds=None):
    resolved_port = (port or getattr(settings, "TURNSTILE_COM_PORT", "") or "").strip()
    resolved_seconds = float(
        pulse_seconds
        if pulse_seconds is not None
        else getattr(settings, "TURNSTILE_PULSE_SECONDS", 1.0)
    )

    if not resolved_port:
        logger.error("Torniquete sin TURNSTILE_COM_PORT configurado.")
        return TurnstilePulseResult(False, "", resolved_seconds, MSG_NOT_CONFIGURED)

    connection = serial.Serial()
    connection.port = resolved_port
    connection.rts = False
    connection.dtr = False

    try:
        connection.open()
        connection.setRTS(True)
        time.sleep(resolved_seconds)
        connection.setRTS(False)
        return TurnstilePulseResult(True, resolved_port, resolved_seconds)
    except serial.SerialException as exc:
        message = _friendly_error(exc)
        logger.exception("No se pudo activar el torniquete por %s", resolved_port)
        return TurnstilePulseResult(False, resolved_port, resolved_seconds, message)
    except Exception as exc:
        message = _friendly_error(exc)
        logger.exception("Fallo inesperado al activar el torniquete por %s", resolved_port)
        return TurnstilePulseResult(False, resolved_port, resolved_seconds, message)
    finally:
        try:
            connection.rts = False
            connection.dtr = False
        except Exception:
            logger.exception("No se pudo restaurar el estado seguro del FT232.")
        if connection.is_open:
            connection.close()
