from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("requests/", views.request_list_create, name="request-list"),
    path("requests/stats/", views.request_stats, name="request-stats"),
    path("requests/<int:pk>/", views.request_detail, name="request-detail"),
    path("requests/<int:pk>/history/", views.request_history, name="request-history"),
    path("requests/<int:pk>/cancel/", views.request_cancel, name="request-cancel"),
    path("requests/<int:pk>/retry/", views.request_retry, name="request-retry"),
]