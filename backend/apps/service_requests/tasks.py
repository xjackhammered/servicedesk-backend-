import logging
import random
import time

from celery import shared_task
from django.conf import settings

from . import services

logger = logging.getLogger(__name__)

STAGES = [
    (10, "Validating request details"),
    (30, "Scheduling technician"),
    (55, "Executing service work"),
    (80, "Quality check"),
    (95, "Generating service report"),
]


@shared_task(name="apps.service_requests.tasks.process_service_request")
def process_service_request(request_id: int) -> str:
    req = services.claim_request(request_id)
    if req is None:
        return "skipped"

    attempt = req.attempt
    try:
        for progress, stage in STAGES:
            time.sleep(settings.PROCESSING_STAGE_SECONDS)
            if random.random() < settings.SIMULATED_FAILURE_RATE:
                raise RuntimeError(f"Simulated failure during: {stage}")
            if not services.update_progress(request_id, attempt, progress, stage):
                logger.info("Request %s no longer owned by attempt %s; stopping", request_id, attempt)
                return "aborted"
        services.complete_request(request_id, attempt, "Service completed successfully.")
        return "completed"
    except Exception as exc:
        logger.exception("Request %s failed", request_id)
        services.fail_request(request_id, attempt, str(exc))
        return "failed"


@shared_task(name="apps.service_requests.tasks.recover_stalled_requests_task")
def recover_stalled_requests_task() -> dict:
    return services.recover_stalled_requests()
