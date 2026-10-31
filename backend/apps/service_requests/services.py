import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Count, F, Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.accounts.models import User

from . import realtime
from .exceptions import InvalidTransition
from .models import (
    ACTIVE_STATUSES,
    ALLOWED_TRANSITIONS,
    ServiceRequest,
    Status,
    StatusHistory,
)

logger = logging.getLogger(__name__)


def _record(req, old, new, actor=None, note=""):
    StatusHistory.objects.create(
        request=req, old_status=old, new_status=new, changed_by=actor, note=note
    )


def _publish(event_type, req):
    payload = realtime.build_payload(event_type, req)
    owners = [req.created_by_id, req.assigned_supervisor_id]
    transaction.on_commit(lambda: realtime.send_payload(owners, payload), robust=True)


def _assert_transition(old, new):
    if new not in ALLOWED_TRANSITIONS[Status(old)]:
        raise InvalidTransition(f"Cannot change status from {old} to {new}.")


def dispatch(request_id: int) -> None:
    from .tasks import process_service_request

    process_service_request.delay(request_id)
    ServiceRequest.objects.filter(pk=request_id).update(enqueued_at=timezone.now())


def _dispatch_after_commit(request_id: int):
    transaction.on_commit(lambda: dispatch(request_id), robust=True)


def pick_supervisor():

    return (
        User.objects.filter(role=User.Role.SUPERVISOR, is_active=True)
        .annotate(active=Count("assigned_requests", filter=Q(assigned_requests__status__in=ACTIVE_STATUSES)))
        .order_by("active", "id")
        .first()
    )


@transaction.atomic
def create_request(user, *, title, description, category, priority) -> ServiceRequest:
    req = ServiceRequest.objects.create(
        title=title,
        description=description,
        category=category,
        priority=priority,
        created_by=user,
        assigned_supervisor=pick_supervisor(),
    )
    _record(req, "", Status.PENDING, user, "Request submitted")
    _publish(realtime.EVENT_CREATED, req)
    _dispatch_after_commit(req.pk)
    return req


@transaction.atomic
def cancel_request(request_id: int, actor) -> ServiceRequest:

    req = ServiceRequest.objects.select_for_update().get(pk=request_id)

    if actor.is_supervisor:
        if req.assigned_supervisor_id != actor.id:
            raise PermissionDenied("You can only cancel requests assigned to you.")
    elif req.created_by_id != actor.id:
        raise PermissionDenied("You can only cancel your own requests.")
    elif req.status != Status.PENDING:
        raise InvalidTransition("Operators can only cancel requests that are still pending.")

    _assert_transition(req.status, Status.CANCELLED)
    old = req.status
    req.status = Status.CANCELLED
    req.completed_at = timezone.now()
    req.stage = "Cancelled"
    req.save(update_fields=["status", "completed_at", "stage", "updated_at"])
    _record(req, old, Status.CANCELLED, actor, "Cancelled by user")
    _publish(realtime.EVENT_STATUS_CHANGED, req)
    return req


@transaction.atomic
def retry_request(request_id: int, actor) -> ServiceRequest:
    if not actor.is_supervisor:
        raise PermissionDenied("Only supervisors can retry requests.")
    req = ServiceRequest.objects.select_for_update().get(pk=request_id)
    if req.assigned_supervisor_id != actor.id:
        raise PermissionDenied("You can only retry requests assigned to you.")
    _assert_transition(req.status, Status.PENDING)

    old = req.status
    req.status = Status.PENDING
    req.progress = 0
    req.stage = "Queued for retry"
    req.error_message = ""
    req.retry_count = 0
    req.started_at = None
    req.completed_at = None
    req.save()
    _record(req, old, Status.PENDING, actor, "Retried by supervisor")
    _publish(realtime.EVENT_STATUS_CHANGED, req)
    _dispatch_after_commit(req.pk)
    return req


def claim_request(request_id: int):

    now = timezone.now()
    with transaction.atomic():
        claimed = ServiceRequest.objects.filter(pk=request_id, status=Status.PENDING).update(
            status=Status.PROCESSING,
            attempt=F("attempt") + 1,
            progress=0,
            stage="Claimed by worker",
            started_at=now,
            last_heartbeat=now,
            updated_at=now,
        )
        if not claimed:
            return None
        req = ServiceRequest.objects.select_related("created_by", "assigned_supervisor").get(pk=request_id)
        _record(req, Status.PENDING, Status.PROCESSING, None, f"Worker claimed (attempt {req.attempt})")
        _publish(realtime.EVENT_STATUS_CHANGED, req)
    return req


def update_progress(request_id: int, attempt: int, progress: int, stage: str) -> bool:
    
    now = timezone.now()
    with transaction.atomic():
        updated = ServiceRequest.objects.filter(
            pk=request_id, status=Status.PROCESSING, attempt=attempt
        ).update(progress=progress, stage=stage, last_heartbeat=now, updated_at=now)
        if not updated:
            return False
        req = ServiceRequest.objects.select_related("created_by", "assigned_supervisor").get(pk=request_id)
        _publish(realtime.EVENT_PROGRESS, req)
    return True


def _finish(request_id, attempt, new_status, note, **fields) -> bool:
    now = timezone.now()
    with transaction.atomic():
        updated = ServiceRequest.objects.filter(
            pk=request_id, status=Status.PROCESSING, attempt=attempt
        ).update(status=new_status, completed_at=now, updated_at=now, last_heartbeat=now, **fields)
        if not updated:
            return False
        req = ServiceRequest.objects.select_related("created_by", "assigned_supervisor").get(pk=request_id)
        _record(req, Status.PROCESSING, new_status, None, note)
        _publish(realtime.EVENT_STATUS_CHANGED, req)
    return True


def complete_request(request_id: int, attempt: int, result: str) -> bool:
    return _finish(
        request_id, attempt, Status.COMPLETED, "Processing finished",
        progress=100, stage="Done", result=result,
    )


def fail_request(request_id: int, attempt: int, error: str) -> bool:
    return _finish(
        request_id, attempt, Status.FAILED, "Processing failed",
        stage="Failed", error_message=error[:1000],
    )

def recover_stalled_requests() -> dict:

    now = timezone.now()
    stall_cutoff = now - timedelta(seconds=settings.STALL_TIMEOUT_SECONDS)
    redispatch_cutoff = now - timedelta(seconds=settings.REDISPATCH_AFTER_SECONDS)
    requeued = failed = redispatched = 0

    stalled_ids = list(
        ServiceRequest.objects.filter(status=Status.PROCESSING, last_heartbeat__lt=stall_cutoff)
        .values_list("pk", flat=True)
    )
    for pk in stalled_ids:
        with transaction.atomic():
            req = ServiceRequest.objects.select_for_update().get(pk=pk)

            if req.status != Status.PROCESSING or req.last_heartbeat >= stall_cutoff:
                continue
            if req.retry_count < settings.MAX_PROCESSING_RETRIES:
                req.status, req.progress = Status.PENDING, 0
                req.retry_count += 1
                req.stage = f"Re-queued after stall (retry {req.retry_count})"
                req.save()
                _record(req, Status.PROCESSING, Status.PENDING, None, "Worker stalled; re-queued")
                _dispatch_after_commit(req.pk)
                requeued += 1
            else:
                req.status = Status.FAILED
                req.stage = "Failed"
                req.error_message = "Worker stalled and retries were exhausted."
                req.completed_at = now
                req.save()
                _record(req, Status.PROCESSING, Status.FAILED, None, "Retries exhausted")
                failed += 1
            _publish(realtime.EVENT_STATUS_CHANGED, req)

    undelivered = ServiceRequest.objects.filter(status=Status.PENDING).filter(
        Q(enqueued_at__isnull=True, created_at__lt=redispatch_cutoff) | Q(enqueued_at__lt=redispatch_cutoff)
    ).values_list("pk", flat=True)
    for pk in list(undelivered):
        try:
            dispatch(pk)
            redispatched += 1
        except Exception:
            logger.exception("Could not re-dispatch request %s", pk)

    if requeued or failed or redispatched:
        logger.warning("Recovery: requeued=%s failed=%s redispatched=%s", requeued, failed, redispatched)
    return {"requeued": requeued, "failed": failed, "redispatched": redispatched}