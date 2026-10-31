from django.conf import settings
from django.db import models
from django.db.models import Q


class Status(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PROCESSING = "PROCESSING", "Processing"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"
    CANCELLED = "CANCELLED", "Cancelled"


ACTIVE_STATUSES = (Status.PENDING, Status.PROCESSING)

ALLOWED_TRANSITIONS = {
    Status.PENDING: {Status.PROCESSING, Status.CANCELLED},
    Status.PROCESSING: {Status.COMPLETED, Status.FAILED, Status.CANCELLED, Status.PENDING},
    Status.FAILED: {Status.PENDING},  # supervisor retry
    Status.COMPLETED: set(),
    Status.CANCELLED: set(),
}


class Category(models.TextChoices):
    REPAIR = "REPAIR", "Repair"
    INSTALLATION = "INSTALLATION", "Installation"
    MAINTENANCE = "MAINTENANCE", "Maintenance"
    INSPECTION = "INSPECTION", "Inspection"
    SUPPORT = "SUPPORT", "Support"


class Priority(models.TextChoices):
    LOW = "LOW", "Low"
    NORMAL = "NORMAL", "Normal"
    HIGH = "HIGH", "High"
    URGENT = "URGENT", "Urgent"


class ServiceRequest(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=Category.choices)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.NORMAL)

    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    progress = models.PositiveSmallIntegerField(default=0)
    stage = models.CharField(max_length=100, blank=True)  # human-readable current step
    result = models.TextField(blank=True)
    error_message = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_requests"
    )
    assigned_supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_requests",
    )

    attempt = models.PositiveIntegerField(default=0)
    retry_count = models.PositiveSmallIntegerField(default=0) 
    enqueued_at = models.DateTimeField(null=True, blank=True)
    last_heartbeat = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(progress__gte=0, progress__lte=100), name="progress_between_0_100"
            ),
        ]
        indexes = [
            models.Index(fields=["status", "last_heartbeat"], name="req_status_heartbeat_idx"),
            models.Index(fields=["created_by", "-created_at"], name="req_creator_created_idx"),
            models.Index(
                fields=["assigned_supervisor", "-created_at"], name="req_supervisor_created_idx"
            ),
        ]

    def __str__(self) -> str:
        return f"#{self.pk} {self.title} [{self.status}]"


class StatusHistory(models.Model):
    request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name="history")
    old_status = models.CharField(max_length=12, choices=Status.choices, blank=True)
    new_status = models.CharField(max_length=12, choices=Status.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    changed_at = models.DateTimeField(auto_now_add=True)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["changed_at", "id"]
        verbose_name_plural = "status history"

    def __str__(self) -> str:
        return f"#{self.request_id}: {self.old_status or '-'} -> {self.new_status}"
