from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user from day one: swapping AUTH_USER_MODEL later is painful."""

    class Role(models.TextChoices):
        OPERATOR = "OPERATOR", "Operator"
        SUPERVISOR = "SUPERVISOR", "Supervisor"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.OPERATOR)

    @property
    def is_operator(self) -> bool:
        return self.role == self.Role.OPERATOR

    @property
    def is_supervisor(self) -> bool:
        return self.role == self.Role.SUPERVISOR

    def __str__(self) -> str:
        return f"{self.username} ({self.role})"
