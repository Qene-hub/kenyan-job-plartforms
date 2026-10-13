"""Redis-backed response caching with namespace versioning.

Instead of deleting many cache keys when data changes, we bump a per-namespace
version number. Old keys are simply never read again and expire on their own.
Every function degrades gracefully: if Redis is down, the API still works, uncached.
"""
import hashlib
import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)

NAMESPACE_JOBS = "jobs"
NAMESPACE_COMPANIES = "companies"


def _version_key(namespace):
    return f"version:{namespace}"


def get_version(namespace):
    key = _version_key(namespace)
    try:
        version = cache.get(key)
        if version is None:
            cache.add(key, 1, timeout=None)
            version = cache.get(key) or 1
        return int(version)
    except Exception:
        logger.warning("Cache unavailable while reading version for %s", namespace, exc_info=True)
        return 1


def bump_version(namespace):
    key = _version_key(namespace)
    try:
        cache.incr(key)
    except ValueError:
        # Key does not exist yet: version 1 is implied, so the next version is 2.
        try:
            cache.set(key, 2, timeout=None)
        except Exception:
            logger.warning("Cache unavailable while bumping %s", namespace, exc_info=True)
    except Exception:
        logger.warning("Cache unavailable while bumping %s", namespace, exc_info=True)


def build_cache_key(namespace, request):
    version = get_version(namespace)
    digest = hashlib.sha256(request.get_full_path().encode("utf-8")).hexdigest()[:32]
    return f"{namespace}:v{version}:{digest}"


def safe_get(key):
    try:
        return cache.get(key)
    except Exception:
        logger.warning("Cache read failed", exc_info=True)
        return None


def safe_set(key, value, timeout):
    try:
        cache.set(key, value, timeout)
    except Exception:
        logger.warning("Cache write failed", exc_info=True)


class CachedListMixin:
    """Caches the paginated list response of a viewset for `cache_timeout` seconds.

    Only use on views whose output is identical for every visitor (public data).
    """

    cache_namespace = ""
    cache_timeout = 60

    def list(self, request, *args, **kwargs):
        from rest_framework.response import Response

        if not self.cache_namespace:
            return super().list(request, *args, **kwargs)

        key = build_cache_key(self.cache_namespace, request)
        cached = safe_get(key)
        if cached is not None:
            return Response(cached)

        response = super().list(request, *args, **kwargs)
        if response.status_code == 200:
            safe_set(key, response.data, self.cache_timeout)
        return response