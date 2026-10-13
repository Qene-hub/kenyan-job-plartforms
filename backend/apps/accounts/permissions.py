from rest_framework.permissions import BasePermission

from .models import User


class IsEmployer(BasePermission):
    """Allows access only to authenticated employer accounts."""

    message = "Only employer accounts can perform this action."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == User.Role.EMPLOYER)