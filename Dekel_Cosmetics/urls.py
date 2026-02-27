from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include

admin.site.site_header = "Dekel Cosmetics – ניהול"
admin.site.site_title  = "Dekel Cosmetics"
admin.site.index_title = "לוח בקרה"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', include('management.urls')),
]
