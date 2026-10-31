from apps.service_requests.models import ServiceRequest, Status

from .base import BaseAPITest


class CreateAndValidationTests(BaseAPITest):
    def test_operator_creates_request(self):
        res = self.submit()
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["status"], "PENDING")
        self.assertIn("Location", res.headers)
        req = ServiceRequest.objects.get(pk=res.data["id"])
        self.assertEqual(req.created_by, self.op1)
        self.assertIsNotNone(req.assigned_supervisor)
        self.assertEqual(req.history.count(), 1)

    def test_validation_errors_use_the_error_envelope(self):
        res = self.submit(title="x", category="NOPE")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["error"]["code"], "validation_error")
        self.assertIn("title", res.data["error"]["details"])
        self.assertIn("category", res.data["error"]["details"])

    def test_client_cannot_set_status_or_assignee(self):
        res = self.submit(status="COMPLETED", progress=100, assigned_supervisor=self.sup2.id)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["status"], "PENDING")
        self.assertEqual(res.data["progress"], 0)

    def test_supervisor_cannot_submit(self):
        res = self.submit(user=self.sup1)
        self.assertEqual(res.status_code, 403)

    def test_unauthenticated_is_rejected(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/requests/").status_code, 401)

    def test_supervisors_are_balanced(self):
        ids = [self.submit(title=f"Request number {i}").data["assigned_supervisor"] for i in range(4)]
        self.assertEqual(sorted(ids), ["sup1", "sup1", "sup2", "sup2"])


class VisibilityAndFilteringTests(BaseAPITest):
    def test_operator_sees_only_own_requests(self):
        mine = self.submit(user=self.op1).data["id"]
        theirs = self.submit(user=self.op2).data["id"]
        self.login(self.op1)
        ids = [r["id"] for r in self.client.get("/api/requests/").data["results"]]
        self.assertEqual(ids, [mine])
        self.assertEqual(self.client.get(f"/api/requests/{theirs}/").status_code, 404)

    def test_supervisor_sees_only_assigned(self):
        for i in range(2):
            self.submit(title=f"Request number {i}")
        self.login(self.sup1)
        results = self.client.get("/api/requests/").data["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["assigned_supervisor"], "sup1")

    def test_filter_and_search(self):
        self.submit(title="Pump inspection", category="INSPECTION", priority="LOW")
        self.submit(title="Network outage fix", category="SUPPORT", priority="URGENT")
        self.login(self.op1)
        self.assertEqual(self.client.get("/api/requests/?priority=urgent").data["count"], 1)
        self.assertEqual(self.client.get("/api/requests/?search=pump").data["count"], 1)
        self.assertEqual(self.client.get("/api/requests/?status=PENDING,FAILED").data["count"], 2)
        self.assertEqual(self.client.get("/api/requests/?status=COMPLETED").data["count"], 0)

    def test_stats(self):
        self.submit()
        self.login(self.op1)
        stats = self.client.get("/api/requests/stats/").data
        self.assertEqual(stats["PENDING"], 1)
        self.assertEqual(stats["total"], 1)


class CancelAndRetryTests(BaseAPITest):
    def test_operator_can_cancel_pending(self):
        rid = self.submit().data["id"]
        self.login(self.op1)
        res = self.client.post(f"/api/requests/{rid}/cancel/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], "CANCELLED")

    def test_cannot_cancel_completed(self):
        rid = self.submit(run_tasks=True).data["id"]
        self.assertEqual(ServiceRequest.objects.get(pk=rid).status, Status.COMPLETED)
        self.login(self.op1)
        res = self.client.post(f"/api/requests/{rid}/cancel/")
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.data["error"]["code"], "invalid_transition")

    def test_operator_cannot_cancel_processing(self):
        rid = self.submit().data["id"]
        ServiceRequest.objects.filter(pk=rid).update(status=Status.PROCESSING)
        self.login(self.op1)
        self.assertEqual(self.client.post(f"/api/requests/{rid}/cancel/").status_code, 409)

    def test_supervisor_can_cancel_processing_and_retry_failed(self):
        rid = self.submit().data["id"]
        sup = ServiceRequest.objects.get(pk=rid).assigned_supervisor
        ServiceRequest.objects.filter(pk=rid).update(status=Status.PROCESSING)
        self.login(sup)
        self.assertEqual(self.client.post(f"/api/requests/{rid}/cancel/").data["status"], "CANCELLED")

        rid2 = self.submit(title="Second failing request").data["id"]
        req2 = ServiceRequest.objects.get(pk=rid2)
        ServiceRequest.objects.filter(pk=rid2).update(status=Status.FAILED, error_message="boom")
        self.login(req2.assigned_supervisor)
        res = self.client.post(f"/api/requests/{rid2}/retry/")
        self.assertEqual(res.status_code, 202)
        self.assertEqual(res.data["status"], "PENDING")

    def test_operator_cannot_retry(self):
        rid = self.submit().data["id"]
        ServiceRequest.objects.filter(pk=rid).update(status=Status.FAILED)
        self.login(self.op1)
        self.assertEqual(self.client.post(f"/api/requests/{rid}/retry/").status_code, 403)

    def test_other_supervisor_gets_404(self):
        rid = self.submit().data["id"]
        other = self.sup2 if ServiceRequest.objects.get(pk=rid).assigned_supervisor == self.sup1 else self.sup1
        self.login(other)
        self.assertEqual(self.client.post(f"/api/requests/{rid}/cancel/").status_code, 404)

    def test_history_endpoint(self):
        rid = self.submit(run_tasks=True).data["id"]
        self.login(self.op1)
        statuses = [(h["old_status"], h["new_status"]) for h in self.client.get(f"/api/requests/{rid}/history/").data]
        self.assertEqual(statuses, [("", "PENDING"), ("PENDING", "PROCESSING"), ("PROCESSING", "COMPLETED")])
