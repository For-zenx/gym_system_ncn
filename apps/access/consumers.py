import datetime
import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from apps.access import ai_engine
from apps.access.services import (
    build_tablet_access_payload,
    check_access_integrity,
    pulse_turnstile_if_granted,
)

logger = logging.getLogger(__name__)

DASHBOARD_GROUP = "dashboard"
TABLET_GROUP = "tablet"

ENROLLMENT_COMMAND_TYPES = frozenset({
    "ENROLLMENT_START",
    "ENROLLMENT_END",
    "ENROLLMENT_SKIP_TERMS",
    "ENROLLMENT_REQUIRE_TERMS",
})


class TabletConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        await self.accept()
        await self.channel_layer.group_add(TABLET_GROUP, self.channel_name)
        logger.info("Tablet conectada. Canal: %s", self.channel_name)
        await self._notify_dashboard(True)

    async def disconnect(self, code):
        await self.channel_layer.group_discard(TABLET_GROUP, self.channel_name)
        logger.info("Tablet desconectada. Canal: %s — Código: %s", self.channel_name, code)
        await self._notify_dashboard(False)

    async def receive(self, text_data=None, bytes_data=None):
        try:
            payload = json.loads(text_data)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Mensaje inválido recibido desde la tablet: %s", text_data)
            await self.send(json.dumps({
                "status": "ERROR",
                "reason": "Formato de mensaje inválido. Se esperaba JSON.",
            }))
            return

        message_type = payload.get("type")

        if message_type == "FRAME":
            await self._handle_frame(payload)
        elif message_type == "ENROLLMENT_PHOTO":
            await self.channel_layer.group_send(
                DASHBOARD_GROUP,
                {
                    "type": "enrollment_photo_forward",
                    "photoType": payload.get("photoType"),
                    "image": payload.get("image"),
                },
            )
        elif message_type == "ENROLLMENT_TERMS_ACCEPTED":
            await self.channel_layer.group_send(
                DASHBOARD_GROUP,
                {"type": "enrollment_terms_forward"},
            )
        else:
            logger.warning("Tipo de mensaje desconocido en tablet: %s", message_type)
            await self.send(json.dumps({
                "status": "ERROR",
                "reason": "Tipo de mensaje no reconocido: '{0}'".format(message_type),
            }))

    async def _handle_frame(self, payload):
        base64_image = payload.get("image", "")
        if not base64_image:
            await self.send(json.dumps({"status": "ERROR", "reason": "Campo 'image' vacío."}))
            return

        client = await database_sync_to_async(ai_engine.recognize_face)(base64_image)

        if client is None:
            await self.send(json.dumps({
                "status": "DENIED",
                "variant": "denied_unknown",
                "name": "",
                "detail": "No reconocido",
            }))
            return

        def get_membership_data(client_obj):
            from django.utils import timezone

            active_mems = client_obj.active_memberships
            if not active_mems.exists():
                return None

            current_time = timezone.localtime().time()
            valid_now = [m for m in active_mems if m.is_valid_now(current_time)]
            mem = valid_now[0] if valid_now else active_mems.order_by('-fecha_fin').first()

            return {
                "plan_name": mem.plan.nombre,
                "fecha_fin": mem.fecha_fin.strftime('%d/%m/%Y'),
                "days_left": (mem.fecha_fin - datetime.date.today()).days,
            }

        mem_data = await database_sync_to_async(get_membership_data)(client)
        granted, detail = await database_sync_to_async(check_access_integrity)(client)

        await database_sync_to_async(pulse_turnstile_if_granted)(granted)

        tablet_payload = await database_sync_to_async(build_tablet_access_payload)(
            client, granted, detail, mem_data
        )
        await self.send(json.dumps(tablet_payload))

        photo_url = client.foto_frente.url if client.foto_frente else ""
        from apps.billing.services import get_membership_feed_lines

        membership_lines = await database_sync_to_async(get_membership_feed_lines)(client)

        await self.channel_layer.group_send(
            DASHBOARD_GROUP,
            {
                "type": "new_access_log",
                "name": client.nombre,
                "cedula": client.cedula,
                "codigo": client.codigo_afiliado,
                "telefono": client.telefono,
                "fecha_ingreso": client.fecha_ingreso.strftime('%d/%m/%Y'),
                "photo_url": photo_url,
                "granted": granted,
                "detail": detail,
                "membership_lines": membership_lines,
                "timestamp": datetime.datetime.now().strftime('%d/%m/%Y - %H:%M:%S'),
            },
        )

    async def tablet_command(self, event):
        await self.send(json.dumps(event.get("data", {})))

    async def tablet_status_request(self, event):
        await self._notify_dashboard(True)

    async def _notify_dashboard(self, online):
        await self.channel_layer.group_send(
            DASHBOARD_GROUP,
            {"type": "tablet_status", "online": online},
        )


# DEPRECATED: TASK-002 — tablet única NCN; reemplazado por TabletConsumer.
AccessTabletConsumer = TabletConsumer

# DEPRECATED: TASK-002 — tablet única NCN; reemplazado por TabletConsumer.
EnrollmentTabletConsumer = TabletConsumer


class DashboardConsumer(AsyncWebsocketConsumer):
    """WebSocket pasivo para la interfaz administrativa (PC)."""

    async def connect(self):
        await self.accept()
        await self.channel_layer.group_add(DASHBOARD_GROUP, self.channel_name)
        logger.info("Dashboard (PC) conectado. Canal: %s", self.channel_name)
        await self.channel_layer.group_send(TABLET_GROUP, {"type": "tablet_status_request"})

    async def disconnect(self, code):
        await self.channel_layer.group_discard(DASHBOARD_GROUP, self.channel_name)
        logger.info("Dashboard (PC) desconectado. Canal: %s", self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        try:
            payload = json.loads(text_data)
        except (json.JSONDecodeError, TypeError) as exc:
            logger.error("Error procesando mensaje desde Dashboard: %s", exc)
            return

        msg_type = payload.get("type")
        if msg_type in ENROLLMENT_COMMAND_TYPES:
            await self.channel_layer.group_send(
                TABLET_GROUP,
                {"type": "tablet_command", "data": payload},
            )

    async def tablet_status(self, event):
        await self.send(json.dumps({
            "type": "tablet_status",
            "online": event.get("online", False),
        }))

    async def enrollment_photo_forward(self, event):
        await self.send(json.dumps({
            "type": "ENROLLMENT_PHOTO",
            "photoType": event.get("photoType"),
            "image": event.get("image"),
        }))

    async def enrollment_terms_forward(self, event):
        await self.send(json.dumps({
            "type": "ENROLLMENT_TERMS_ACCEPTED",
        }))

    async def new_access_log(self, event):
        await self.send(json.dumps({
            "type": "NEW_ACCESS_LOG",
            "name": event.get("name"),
            "cedula": event.get("cedula"),
            "codigo": event.get("codigo"),
            "telefono": event.get("telefono"),
            "fecha_ingreso": event.get("fecha_ingreso"),
            "photo_url": event.get("photo_url"),
            "granted": event.get("granted"),
            "detail": event.get("detail"),
            "membership_lines": event.get("membership_lines", []),
            "timestamp": event.get("timestamp"),
        }))
