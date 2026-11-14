from django.conf import settings
from django.contrib import admin
from django.http import FileResponse, HttpResponse
from django.urls import include, path, re_path

admin.site.site_header = "SheCares"
admin.site.site_title = "SheCares"


def frontend(request, resource=""):
    dist = settings.FRONTEND_DIST
    index = dist / "index.html"
    if not index.is_file():
        return HttpResponse(
            "Frontend build is missing. From the frontend folder, run npm run build.",
            status=503,
            content_type="text/plain",
        )
    if resource:
        candidate = (dist / resource).resolve()
        root = dist.resolve()
        if candidate.is_file() and root in candidate.parents:
            return FileResponse(candidate.open("rb"))
    return FileResponse(index.open("rb"))


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("core.urls")),
    re_path(r"^(?P<resource>.*)$", frontend),
]
