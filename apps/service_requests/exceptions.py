from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler


class InvalidTransition(APIException):

    status_code = status.HTTP_409_CONFLICT
    default_detail = "This action is not allowed in the request's current state."
    default_code = "invalid_transition"


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    data = response.data
    if isinstance(data, dict) and "detail" in data and len(data) == 1:
        message, details = str(data["detail"]), {}
    elif isinstance(data, dict):
        message, details = "Validation failed.", data
    else:
        message, details = "Validation failed.", {"non_field_errors": data}

    code = getattr(exc, "default_code", "error")
    if response.status_code == 400:
        code = "validation_error"
    response.data = {"error": {"code": code, "message": message, "details": details}}
    return response