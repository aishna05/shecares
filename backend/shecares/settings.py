import base64
import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PRIVATE_MEDIA_ROOT = BASE_DIR / "private_media"


def _file_encryption_key():
    env = os.environ.get("FILE_ENCRYPTION_KEY")
    if env:
        return env.strip()
    path = BASE_DIR / ".fernet_key"
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    key = base64.urlsafe_b64encode(os.urandom(32)).decode()
    try:
        path.write_text(key, encoding="utf-8")
    except OSError:
        tmp = Path("/tmp/.fernet_key")
        if tmp.exists():
            return tmp.read_text(encoding="utf-8").strip()
        tmp.write_text(key, encoding="utf-8")
    return key


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-shecares-local-only-not-for-production")
FILE_ENCRYPTION_KEY = _file_encryption_key()
_on_vercel = bool(os.environ.get("VERCEL"))
DEBUG = os.environ.get("DJANGO_DEBUG", "0" if _on_vercel else "1") == "1"

_hosts = os.environ.get("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost")
ALLOWED_HOSTS = [host.strip() for host in _hosts.split(",") if host.strip()]
for _name in (
    "RENDER_EXTERNAL_HOSTNAME",
    "RAILWAY_PUBLIC_DOMAIN",
    "VERCEL_URL",
    "VERCEL_PROJECT_PRODUCTION_URL",
    "VERCEL_BRANCH_URL",
):
    _public = os.environ.get(_name, "").strip()
    _public = _public.removeprefix("https://").removeprefix("http://").split("/")[0]
    if _public and _public not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_public)
if _on_vercel and ".vercel.app" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(".vercel.app")

FRONTEND_DIST = Path(os.environ.get("FRONTEND_DIST", BASE_DIR.parent / "frontend" / "dist"))

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "shecares.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]
WSGI_APPLICATION = "shecares.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

if _on_vercel:
    import shutil

    _db_copy = Path("/tmp/shecares.sqlite3")
    _bundled_db = BASE_DIR / "db.sqlite3"
    if _bundled_db.exists() and not _db_copy.exists():
        shutil.copy2(_bundled_db, _db_copy)
    DATABASES["default"]["NAME"] = _db_copy
    PRIVATE_MEDIA_ROOT = Path("/tmp/shecares_private_media")
    PRIVATE_MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

AUTH_USER_MODEL = "core.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://shecares-mocha.vercel.app",
    "https://shecares-go1r.vercel.app",
]
_extra_origins = os.environ.get("DJANGO_CORS_ORIGINS", "")
CORS_ALLOWED_ORIGINS += [origin.strip() for origin in _extra_origins.split(",") if origin.strip()]
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://shecares-mocha[\w.-]*\.vercel\.app$",
]

CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "https://shecares-mocha.vercel.app",
    "https://shecares-go1r.vercel.app",
]
for _host in ALLOWED_HOSTS:
    if _host in {"*", "127.0.0.1", "localhost"} or _host.startswith("."):
        continue
    CSRF_TRUSTED_ORIGINS.append(f"https://{_host}")
_extra_csrf = os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "")
CSRF_TRUSTED_ORIGINS += [origin.strip() for origin in _extra_csrf.split(",") if origin.strip()]

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    USE_X_FORWARDED_HOST = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=12),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}
