import uuid
from pathlib import Path

from cryptography.fernet import Fernet
from django.conf import settings

MAX_BYTES = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_TYPES = {"application/pdf", "image/png", "image/jpeg", "image/webp"}
EXT_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


def fernet():
    return Fernet(settings.FILE_ENCRYPTION_KEY.encode())


def safe_filename(name):
    cleaned = Path(name or "report").name.replace('"', "").replace("\r", "").replace("\n", "")
    return cleaned or "report"


def store_bytes(data, original_name, content_type):
    if len(data) > MAX_BYTES:
        raise ValueError("File is larger than 5 MB.")
    ext = Path(original_name or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Upload a PDF or an image (PNG, JPG, WEBP).")
    content_type = (content_type or "").split(";")[0].strip().lower()
    if content_type == "image/jpg":
        content_type = "image/jpeg"
    if content_type not in ALLOWED_TYPES:
        content_type = EXT_TYPES.get(ext, "")
    if content_type not in ALLOWED_TYPES:
        raise ValueError("Upload a PDF or an image (PNG, JPG, WEBP).")
    settings.PRIVATE_MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    stored_name = uuid.uuid4().hex + ".bin"
    path = Path(settings.PRIVATE_MEDIA_ROOT) / stored_name
    path.write_bytes(fernet().encrypt(data))
    return stored_name, content_type


def read_encrypted(stored_name):
    path = Path(settings.PRIVATE_MEDIA_ROOT) / stored_name
    return fernet().decrypt(path.read_bytes())
