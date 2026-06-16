from django.contrib import admin
from .models import AccessLog, ManualTurnstileAccess

@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ('client', 'timestamp', 'resultado', 'motivo')
    list_filter = ('resultado', 'timestamp')
    search_fields = ('client__nombre', 'client__cedula')
    readonly_fields = ('timestamp',)


@admin.register(ManualTurnstileAccess)
class ManualTurnstileAccessAdmin(admin.ModelAdmin):
    list_display = ('person_name', 'client', 'timestamp', 'opened_by', 'hardware_success')
    list_filter = ('reason', 'hardware_success', 'timestamp')
    search_fields = ('person_name', 'client__nombre', 'client__cedula')
    readonly_fields = ('timestamp',)
