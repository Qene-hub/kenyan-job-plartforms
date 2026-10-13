from django.contrib import admin, messages
from django.db.models import Count
from django.utils import timezone

from apps.core.cache import NAMESPACE_COMPANIES, NAMESPACE_JOBS, bump_version

from .models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "county", "industry", "verification_status", "jobs_total", "created_at")
    list_filter = ("verification_status", "county")
    search_fields = ("name", "industry")  # required by autocomplete fields in the Job admin
    readonly_fields = ("slug", "created_at", "updated_at")
    autocomplete_fields = ("owner",)
    actions = ["mark_verified", "mark_pending", "mark_rejected"]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_jobs_total=Count("jobs"))

    @admin.display(description="Jobs", ordering="_jobs_total")
    def jobs_total(self, obj):
        return obj._jobs_total

    def _set_status(self, request, queryset, new_status, label):
        pks = list(queryset.values_list("pk", flat=True))
        updated = Company.objects.filter(pk__in=pks).update(
            verification_status=new_status, updated_at=timezone.now()
        )
        bump_version(NAMESPACE_JOBS)
        bump_version(NAMESPACE_COMPANIES)
        self.message_user(request, f"{updated} company(ies) marked {label}.", messages.SUCCESS)

    @admin.action(description="Mark selected companies as verified")
    def mark_verified(self, request, queryset):
        self._set_status(request, queryset, Company.VerificationStatus.VERIFIED, "verified")

    @admin.action(description="Mark selected companies as pending")
    def mark_pending(self, request, queryset):
        self._set_status(request, queryset, Company.VerificationStatus.PENDING, "pending")

    @admin.action(description="Mark selected companies as rejected")
    def mark_rejected(self, request, queryset):
        self._set_status(request, queryset, Company.VerificationStatus.REJECTED, "rejected")