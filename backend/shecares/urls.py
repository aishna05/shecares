from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "SheCares"
admin.site.site_title = "SheCares"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("core.urls")),
]
