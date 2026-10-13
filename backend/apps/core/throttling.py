from rest_framework.throttling import AnonRateThrottle


class AuthRateThrottle(AnonRateThrottle):
    """Strict per-IP limit for register/login endpoints (brute-force protection)."""

    scope = "auth"