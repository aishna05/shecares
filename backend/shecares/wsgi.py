import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shecares.settings")

application = get_wsgi_application()

if os.environ.get("VERCEL"):
    from pathlib import Path

    from django.core.management import call_command

    _ready = Path("/tmp/shecares.ready")
    if not _ready.exists():
        call_command("migrate", interactive=False, verbosity=0)
        from core.models import User

        if not User.objects.exists():
            call_command("seed")
        _ready.write_text("ok", encoding="utf-8")
