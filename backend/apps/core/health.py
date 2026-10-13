import logging

from django.core.cache import cache
from django.db import connection
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class HealthSerializer(serializers.Serializer):
    status = serializers.CharField()
    database = serializers.CharField()
    cache = serializers.CharField()
    timestamp = serializers.DateTimeField()


def _database_is_up():
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return True
    except Exception:
        logger.exception("Health check: database unreachable")
        return False


def _cache_is_up():
    try:
        cache.set("health:ping", "pong", timeout=5)
        return cache.get("health:ping") == "pong"
    except Exception:
        logger.exception("Health check: cache unreachable")
        return False


class HealthCheckView(APIView):
    """Reports whether the API and its dependencies (MySQL, Redis) are working."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []  # must keep working even when Redis (used by throttling) is down

    @extend_schema(tags=["System"], responses={200: HealthSerializer, 503: HealthSerializer})
    def get(self, request):
        db_ok = _database_is_up()
        cache_ok = _cache_is_up()
        healthy = db_ok and cache_ok

        payload = {
            "status": "ok" if healthy else "degraded",
            "database": "up" if db_ok else "down",
            "cache": "up" if cache_ok else "down",
            "timestamp": timezone.now(),
        }
        code = status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(HealthSerializer(payload).data, status=code)