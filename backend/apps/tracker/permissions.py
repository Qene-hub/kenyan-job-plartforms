from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    """Object-level rule: users may only touch their own records."""

    def has_object_permission(self, request, view, obj):
        owner_id = getattr(obj, "user_id", None)
        if owner_id is None and hasattr(obj, "application"):
            owner_id = obj.application.user_id
        return owner_id == request.user.id