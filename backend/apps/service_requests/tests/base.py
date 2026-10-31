from datetime import timedelta

from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User
from config.celery import app as celery_app

PAYLOAD = {
    "title": "AC is not cooling",
    "description": "Living room AC runs but does not cool the room.",
    "category": "REPAIR",
    "priority": "HIGH",
}


@override_settings(
    PROCESSING_STAGE_SECONDS=0,
    SIMULATED_FAILURE_RATE=0.0,
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)
class BaseAPITest(APITestCase):
    def setUp(self):
        celery_app.conf.update(CELERY_TASK_ALWAYS_EAGER=False)  
        self.op1 = User.objects.create_user("op1", password="pass12345", role=User.Role.OPERATOR)
        self.op2 = User.objects.create_user("op2", password="pass12345", role=User.Role.OPERATOR)
        self.sup1 = User.objects.create_user("sup1", password="pass12345", role=User.Role.SUPERVISOR)
        self.sup2 = User.objects.create_user("sup2", password="pass12345", role=User.Role.SUPERVISOR)

    def login(self, user):
        self.client.force_authenticate(user)

    def submit(self, user=None, run_tasks=False, **overrides):
        self.login(user or self.op1)
        celery_app.conf.update(CELERY_TASK_ALWAYS_EAGER=run_tasks)
        with self.captureOnCommitCallbacks(execute=run_tasks):
            return self.client.post("/api/requests/", {**PAYLOAD, **overrides}, format="json")

    def age(self, req, **fields):
        type(req).objects.filter(pk=req.pk).update(**fields)
        req.refresh_from_db()

    @staticmethod
    def ago(seconds):
        return timezone.now() - timedelta(seconds=seconds)
