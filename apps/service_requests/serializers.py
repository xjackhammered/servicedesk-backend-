from rest_framework import serializers

from .models import ServiceRequest, StatusHistory


class ServiceRequestCreateSerializer(serializers.Serializer):

    title = serializers.CharField(min_length=5, max_length=200)
    description = serializers.CharField(min_length=10, max_length=5000)
    category = serializers.ChoiceField(choices=ServiceRequest._meta.get_field("category").choices)
    priority = serializers.ChoiceField(
        choices=ServiceRequest._meta.get_field("priority").choices, default="NORMAL"
    )


class ServiceRequestSerializer(serializers.ModelSerializer):

    created_by = serializers.CharField(source="created_by.username", read_only=True)
    assigned_supervisor = serializers.CharField(
        source="assigned_supervisor.username", read_only=True, default=None
    )

    class Meta:
        model = ServiceRequest
        fields = (
            "id", "title", "description", "category", "priority",
            "status", "progress", "stage", "result", "error_message",
            "created_by", "assigned_supervisor", "retry_count",
            "created_at", "updated_at", "started_at", "completed_at",
        )
        read_only_fields = fields


class StatusHistorySerializer(serializers.ModelSerializer):
    changed_by = serializers.CharField(source="changed_by.username", read_only=True, default=None)

    class Meta:
        model = StatusHistory
        fields = ("id", "old_status", "new_status", "changed_by", "changed_at", "note")
        read_only_fields = fields
