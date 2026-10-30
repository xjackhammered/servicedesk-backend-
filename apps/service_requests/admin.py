from django.contrib import admin

from .models import ServiceRequest, StatusHistory


class StatusHistoryInline(admin.TabularInline):
    model = StatusHistory
    extra = 0
    readonly_fields = ("old_status", "new_status", "changed_by", "changed_at", "note")
    can_delete = False


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "status", "progress", "priority", "created_by", "assigned_supervisor")
    list_filter = ("status", "priority", "category")
    search_fields = ("title", "description")
    inlines = [StatusHistoryInline]
