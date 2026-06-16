import os

from demschooltools.settings import *  # noqa: F403

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "ci-insecure-key")
DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = ["*"]
DJANGO_VITE = {"default": {"dev_mode": False, "manifest_path": BASE_DIR / "static-vite" / "manifest.json"}}  # noqa: F405

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DST_DB_NAME", "school_crm"),
        "USER": os.environ.get("DST_DB_USER", "postgres"),
        "PASSWORD": os.environ.get("DST_DB_PASSWORD", "postgres"),
        "HOST": os.environ.get("DST_DB_HOST", "localhost"),
        "PORT": "5432",
    }
}

APPLICATION_SECRET = os.environ.get("APPLICATION_SECRET", "ci-test-secret")
ROLLBAR = dict(ROLLBAR, access_token="", environment="ci")  # noqa: F405
STATIC_ROOT = os.environ.get("STATIC_ROOT", "/tmp/django-static")
