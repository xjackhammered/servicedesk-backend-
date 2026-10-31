from unittest.mock import patch

from django.test import override_settings

from apps.service_requests import services
from apps.service_requests.models import ServiceRequest, Status
from apps.service_requests.tasks import process_service_request

from .base import BaseAPITest


class ProcessingTests(BaseAPITest):
    def test_end_to_end_processing_completes(self):
        rid = self.submit(run_tasks=True).data["id"]
        req = ServiceRequest.objects.get(pk=rid)
        self.assertEqual((req.status, req.progress), (Status.COMPLETED, 100))
        self.assertIsNotNone(req.completed_at)

    @override_settings(SIMULATED_FAILURE_RATE=1.0)
    def test_failure_is_persisted(self):
        rid = self.submit(run_tasks=True).data["id"]
        req = ServiceRequest.objects.get(pk=rid)
        self.assertEqual(req.status, Status.FAILED)
        self.assertIn("Simulated failure", req.error_message)

    def test_claim_is_exclusive(self):
        rid = self.submit().data["id"]
        first = services.claim_request(rid)
        second = services.claim_request(rid)  
        self.assertIsNotNone(first)
        self.assertIsNone(second)
        self.assertEqual(first.attempt, 1)

    def test_duplicate_task_is_a_noop(self):
        rid = self.submit(run_tasks=True).data["id"]
        self.assertEqual(process_service_request(rid), "skipped")
        self.assertEqual(ServiceRequest.objects.get(pk=rid).history.count(), 3)

    def test_stale_attempt_cannot_write(self):
        rid = self.submit().data["id"]
        services.claim_request(rid)
        self.assertTrue(services.update_progress(rid, 1, 50, "half"))
        self.assertFalse(services.update_progress(rid, 99, 60, "stale worker"))
        self.assertFalse(services.complete_request(rid, 99, "nope"))
        self.assertEqual(ServiceRequest.objects.get(pk=rid).progress, 50)

    def test_cancel_stops_a_running_worker(self):
        rid = self.submit().data["id"]
        req = services.claim_request(rid)
        sup = req.assigned_supervisor
        services.cancel_request(rid, sup)
        self.assertFalse(services.update_progress(rid, req.attempt, 30, "should not apply"))
        self.assertEqual(ServiceRequest.objects.get(pk=rid).status, Status.CANCELLED)


@override_settings(STALL_TIMEOUT_SECONDS=30, MAX_PROCESSING_RETRIES=1, REDISPATCH_AFTER_SECONDS=30)
class RecoveryTests(BaseAPITest):
    def _processing_request(self):
        rid = self.submit().data["id"]
        req = services.claim_request(rid)
        self.age(req, last_heartbeat=self.ago(120))
        return req

    def test_stalled_request_is_requeued_then_failed(self):
        req = self._processing_request()
        with self.captureOnCommitCallbacks(execute=False):
            self.assertEqual(services.recover_stalled_requests()["requeued"], 1)
        req.refresh_from_db()
        self.assertEqual((req.status, req.retry_count), (Status.PENDING, 1))

        services.claim_request(req.pk)
        self.age(req, last_heartbeat=self.ago(120))
        self.assertEqual(services.recover_stalled_requests()["failed"], 1)
        req.refresh_from_db()
        self.assertEqual(req.status, Status.FAILED)

    def test_healthy_processing_request_is_left_alone(self):
        rid = self.submit().data["id"]
        services.claim_request(rid)
        self.assertEqual(services.recover_stalled_requests(), {"requeued": 0, "failed": 0, "redispatched": 0})

    def test_undelivered_pending_request_is_redispatched(self):
        rid = self.submit().data["id"]
        req = ServiceRequest.objects.get(pk=rid)
        self.age(req, created_at=self.ago(120))
        with patch("apps.service_requests.tasks.process_service_request.delay") as delay:
            self.assertEqual(services.recover_stalled_requests()["redispatched"], 1)
        delay.assert_called_once_with(rid)
        req.refresh_from_db()
        self.assertIsNotNone(req.enqueued_at)

    def test_broker_outage_does_not_break_the_sweeper(self):
        rid = self.submit().data["id"]
        self.age(ServiceRequest.objects.get(pk=rid), created_at=self.ago(120))
        with patch("apps.service_requests.tasks.process_service_request.delay", side_effect=ConnectionError):
            self.assertEqual(services.recover_stalled_requests()["redispatched"], 0)
        self.assertIsNone(ServiceRequest.objects.get(pk=rid).enqueued_at)
