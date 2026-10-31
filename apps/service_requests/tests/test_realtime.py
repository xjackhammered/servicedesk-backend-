from asgiref.sync import sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase, override_settings
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import User
from apps.service_requests import services
from apps.service_requests.middleware import JWTAuthMiddleware
from apps.service_requests.routing import websocket_urlpatterns

APP = JWTAuthMiddleware(URLRouter(websocket_urlpatterns))


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"], CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class WebSocketTests(TransactionTestCase):
    def setUp(self):
        self.op = User.objects.create_user("op", password="pass12345", role=User.Role.OPERATOR)
        self.other = User.objects.create_user("other", password="pass12345", role=User.Role.OPERATOR)
        self.sup = User.objects.create_user("sup", password="pass12345", role=User.Role.SUPERVISOR)

    def comm(self, user=None):
        qs = f"?token={AccessToken.for_user(user)}" if user else ""
        return WebsocketCommunicator(APP, f"/ws/requests/{qs}")

    async def test_rejects_anonymous(self):
        comm = self.comm()
        connected, code = await comm.connect()
        self.assertFalse(connected)
        self.assertEqual(code, 4401)

    async def test_owner_and_supervisor_receive_events_but_others_do_not(self):
        owner, sup, other = self.comm(self.op), self.comm(self.sup), self.comm(self.other)
        for c in (owner, sup, other):
            ok, _ = await c.connect()
            self.assertTrue(ok)
            self.assertEqual((await c.receive_json_from())["type"], "connection.ready")

        req = await sync_to_async(services.create_request)(
            self.op, title="Broken pump", description="Water pump will not start.",
            category="REPAIR", priority="NORMAL",
        )
        for c in (owner, sup):
            event = await c.receive_json_from()
            self.assertEqual(event["type"], "request.created")
            self.assertEqual(event["request"]["id"], req.id)
        self.assertTrue(await other.receive_nothing())

        await sync_to_async(services.claim_request)(req.id)
        event = await owner.receive_json_from()
        self.assertEqual(event["type"], "request.status_changed")
        self.assertEqual(event["request"]["status"], "PROCESSING")

        for c in (owner, sup, other):
            await c.disconnect()
