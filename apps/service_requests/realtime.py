import json
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework.renderers import JSONRenderer

from .serializers import ServiceRequestSerializer

logger = logging.getLogger(__name__)

EVENT_CREATED = "request.created"
EVENT_STATUS_CHANGED = "request.status_changed"
EVENT_PROGRESS = "request.progress"


def user_group(user_id: int) -> str:
    return f"user_{user_id}"


def build_payload(event_type: str, req) -> dict:
    data = json.loads(JSONRenderer().render(ServiceRequestSerializer(req).data))
    return {"type": event_type, "request": data}


def send_payload(req_owner_ids: list, payload: dict) -> None:
    layer = get_channel_layer()
    if layer is None:
        return
    for user_id in {i for i in req_owner_ids if i}:
        try:
            async_to_sync(layer.group_send)(
                user_group(user_id), {"type": "request.event", "payload": payload}
            )
        except Exception: 
            logger.exception("Failed to publish WebSocket event %s", payload.get("type"))
