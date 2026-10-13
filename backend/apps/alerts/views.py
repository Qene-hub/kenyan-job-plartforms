from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.tracker.permissions import IsOwner

from .models import JobAlert
from .serializers import JobAlertSerializer


class JobAlertViewSet(viewsets.ModelViewSet):
    """Your saved searches. Alert emails go out when the alert command is scheduled."""

    serializer_class = JobAlertSerializer
    permission_classes = [IsAuthenticated, IsOwner]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    filterset_fields = ["is_active", "frequency"]
    ordering = ["-created_at", "-id"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return JobAlert.objects.none()
        return JobAlert.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)