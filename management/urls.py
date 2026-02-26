from django.urls import path
from . import views

app_name = "management"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("clients/", views.client_list, name="client_list"),
    path("clients/new/", views.client_create, name="client_create"),
    path("clients/new-ajax/", views.client_create_ajax, name="client_create_ajax"),
    path("clients/<int:pk>/", views.client_detail, name="client_detail"),
    path("appointments/", views.appointment_list, name="appointment_list"),
    path("appointments/new/", views.appointment_create, name="appointment_create"),
    path("finance/", views.finance_dashboard, name="finance_dashboard"),
    path("ai-chat/", views.ai_chat, name="ai_chat"),
]

