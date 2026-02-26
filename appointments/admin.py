from django.contrib import admin
from .models import Client, Appointment, FinanceRecord, PersonalEvent


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("name", "age", "phone", "email", "birth_date", "created_at")
    search_fields = ("name", "phone", "email")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("client", "service_type", "custom_price", "start_time", "is_completed")
    list_filter = ("service_type", "is_completed", "start_time")
    search_fields = ("client__name", "client__phone")


@admin.register(FinanceRecord)
class FinanceRecordAdmin(admin.ModelAdmin):
    list_display = ("record_type", "amount", "date", "category", "appointment")
    list_filter = ("record_type", "date", "category")


@admin.register(PersonalEvent)
class PersonalEventAdmin(admin.ModelAdmin):
    list_display = ("title", "start_time", "end_time")
    list_filter = ("start_time",)