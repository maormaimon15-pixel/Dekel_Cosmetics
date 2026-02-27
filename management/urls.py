from django.urls import path
from . import views

app_name = "management"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("clients/", views.client_list, name="client_list"),
    path("clients/new/", views.client_create, name="client_create"),
    path("clients/new-ajax/", views.client_create_ajax, name="client_create_ajax"),
    path("clients/<int:pk>/", views.client_detail, name="client_detail"),
    path("clients/<int:pk>/edit/", views.client_edit, name="client_edit"),
    path("clients/<int:pk>/delete/", views.client_delete, name="client_delete"),
    path("appointments/", views.appointment_list, name="appointment_list"),
    path("appointments/new/", views.appointment_create, name="appointment_create"),
    path("appointments/<int:appointment_id>/reschedule/", views.reschedule_appointment, name="reschedule_appointment"),
    path("finance/", views.finance_dashboard, name="finance_dashboard"),
    path("ai-chat/", views.ai_chat, name="ai_chat"),
    path("health-declaration/new/", views.health_declaration_new, name="health_declaration_new"),
    path("health-declaration/<uuid:id>/", views.health_form_view, name="health_form"),
    path("health-declaration/success/", views.health_declaration_success, name="health_declaration_success"),
]

