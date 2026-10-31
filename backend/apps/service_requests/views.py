from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.decorators import permission_classes
from rest_framework.response import Response

from . import selectors, services
from .serializers import (
    ServiceRequestCreateSerializer,
    ServiceRequestSerializer,
    StatusHistorySerializer,
)


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    return Response({"status": "ok"})


@api_view(["GET", "POST"])
def request_list_create(request):
    if request.method == "GET":
        qs = selectors.filter_requests(selectors.visible_requests(request.user), request.query_params)
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(ServiceRequestSerializer(page, many=True).data)

    if not request.user.is_operator:
        return Response(
            {"error": {"code": "permission_denied", "message": "Only operators can submit requests.", "details": {}}},
            status=status.HTTP_403_FORBIDDEN,
        )
    serializer = ServiceRequestCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    req = services.create_request(request.user, **serializer.validated_data)

    return Response(
        ServiceRequestSerializer(req).data,
        status=status.HTTP_201_CREATED,
        headers={"Location": f"/api/requests/{req.pk}/"},
    )


@api_view(["GET"])
def request_detail(request, pk):
    req = get_object_or_404(selectors.visible_requests(request.user), pk=pk)
    return Response(ServiceRequestSerializer(req).data)


@api_view(["GET"])
def request_history(request, pk):
    req = get_object_or_404(selectors.visible_requests(request.user), pk=pk)
    history = req.history.select_related("changed_by")
    return Response(StatusHistorySerializer(history, many=True).data)


@api_view(["GET"])
def request_stats(request):
    return Response(selectors.status_summary(request.user))


@api_view(["POST"])
def request_cancel(request, pk):
    get_object_or_404(selectors.visible_requests(request.user), pk=pk)
    req = services.cancel_request(pk, request.user)
    return Response(ServiceRequestSerializer(req).data)


@api_view(["POST"])
def request_retry(request, pk):
    get_object_or_404(selectors.visible_requests(request.user), pk=pk)
    req = services.retry_request(pk, request.user)
    return Response(ServiceRequestSerializer(req).data, status=status.HTTP_202_ACCEPTED)
