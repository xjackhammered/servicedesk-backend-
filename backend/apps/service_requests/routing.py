from django.urls import path

from .consumers import RequestEventsConsumer

websocket_urlpatterns = [
    path("ws/requests/", RequestEventsConsumer.as_asgi()),
]
