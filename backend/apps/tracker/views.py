from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Application, SavedJob
from .permissions import IsOwner
from .serializers import (
    ApplicationNoteSerializer,
    ApplicationSerializer,
    SavedJobSerializer,
)


class SavedJobViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Your bookmarked jobs. DELETE uses the saved-job id returned by the list."""

    serializer_class = SavedJobSerializer
    permission_classes = [IsAuthenticated, IsOwner]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return SavedJob.objects.none()
        return (
            SavedJob.objects.filter(user=self.request.user)
            .select_related("job__company")
            .prefetch_related("job__skills")
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ApplicationViewSet(viewsets.ModelViewSet):
    """Track applications, update their status, and keep private notes."""

    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated, IsOwner]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    filterset_fields = {
        "status": ["exact"],
        "follow_up_date": ["lte", "gte"],
        "applied_date": ["lte", "gte"],
    }
    ordering_fields = ["updated_at", "created_at", "applied_date", "follow_up_date", "status"]
    ordering = ["-updated_at", "-id"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Application.objects.none()
        return (
            Application.objects.filter(user=self.request.user)
            .select_related("job__company")
            .prefetch_related("job__skills")
            .annotate(notes_count=Count("notes"))
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @extend_schema(responses=OpenApiTypes.OBJECT)
    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Counts for the dashboard: applications per status, due follow-ups, saved jobs."""
        applications = Application.objects.filter(user=request.user)
        by_status = {value: 0 for value in Application.Status.values}
        for row in applications.values("status").annotate(total=Count("id")).order_by():
            by_status[row["status"]] = row["total"]

        follow_ups_due = (
            applications.filter(follow_up_date__lte=timezone.localdate())
            .exclude(status__in=[Application.Status.OFFER, Application.Status.REJECTED])
            .count()
        )
        return Response(
            {
                "total": sum(by_status.values()),
                "by_status": by_status,
                "follow_ups_due": follow_ups_due,
                "saved_jobs": SavedJob.objects.filter(user=request.user).count(),
            }
        )

    @extend_schema(methods=["GET"], responses=ApplicationNoteSerializer(many=True))
    @extend_schema(
        methods=["POST"], request=ApplicationNoteSerializer, responses={201: ApplicationNoteSerializer}
    )
    @action(detail=True, methods=["get", "post"], url_path="notes")
    def notes(self, request, pk=None):
        application = self.get_object()
        if request.method == "POST":
            serializer = ApplicationNoteSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(application=application)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(ApplicationNoteSerializer(application.notes.all(), many=True).data)

    @extend_schema(
        parameters=[OpenApiParameter("note_id", OpenApiTypes.INT, OpenApiParameter.PATH)],
        responses={204: None},
    )
    @action(detail=True, methods=["delete"], url_path=r"notes/(?P<note_id>[0-9]+)")
    def delete_note(self, request, pk=None, note_id=None):
        application = self.get_object()
        note = get_object_or_404(application.notes, pk=note_id)
        note.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)