from django.contrib import admin
from django.urls import path, include

admin.site.site_header = "Dekel Cosmetics – ניהול"
admin.site.site_title  = "Dekel Cosmetics"
admin.site.index_title = "לוח בקרה"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('management.urls')),
]
