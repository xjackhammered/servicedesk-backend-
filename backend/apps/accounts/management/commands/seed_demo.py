from django.core.management.base import BaseCommand

from apps.accounts.models import User

DEMO_USERS = [
    ("sup1", User.Role.SUPERVISOR),
    ("sup2", User.Role.SUPERVISOR),
    ("op1", User.Role.OPERATOR),
    ("op2", User.Role.OPERATOR),
]


class Command(BaseCommand):
    help = "Create demo supervisors and operators (password: demo12345)."

    def handle(self, *args, **options):
        for username, role in DEMO_USERS:
            user, created = User.objects.get_or_create(
                username=username, defaults={"role": role, "email": f"{username}@example.com"}
            )
            if created:
                user.set_password("demo12345")
                user.save()
            self.stdout.write(f"{'created' if created else 'exists '} {user}")
