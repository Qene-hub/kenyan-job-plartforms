import tempfile
from pathlib import Path

from .base import *  # noqa: F401,F403

DEBUG = False

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# CV uploads go to a throwaway folder during tests
PRIVATE_MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="kjp_private_"))

REST_FRAMEWORK = {  # noqa: F405
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100000/hour",
        "user": "100000/hour",
        "auth": "100000/hour",
    },
}