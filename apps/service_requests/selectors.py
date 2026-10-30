from django.db.models import Count, Q

from .models import ServiceRequest, Status


def visible_requests(user):
    qs = ServiceRequest.objects.select_related("created_by", "assigned_supervisor")
    if user.is_supervisor:
        return qs.filter(assigned_supervisor=user)
    return qs.filter(created_by=user)


ORDERING_FIELDS = {"created_at", "-created_at", "priority", "-priority", "progress", "-progress", "status"}


def filter_requests(qs, params):
    status_ = params.get("status")
    if status_:
        qs = qs.filter(status__in=[s.strip().upper() for s in status_.split(",")])
    if params.get("priority"):
        qs = qs.filter(priority=params["priority"].upper())
    if params.get("category"):
        qs = qs.filter(category=params["category"].upper())
    search = (params.get("search") or "").strip()
    if search:
        qs = qs.filter(Q(title__icontains=search) | Q(description__icontains=search))
    ordering = params.get("ordering")
    if ordering in ORDERING_FIELDS:
        qs = qs.order_by(ordering, "-id")
    return qs


def status_summary(user) -> dict:
    rows = visible_requests(user).values("status").annotate(n=Count("id"))
    summary = {s.value: 0 for s in Status}
    summary.update({r["status"]: r["n"] for r in rows})
    summary["total"] = sum(summary.values())
    return summary
