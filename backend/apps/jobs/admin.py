from django.contrib import admin, messages
from django.utils import timezone

from .models import Job, JobSource, Skill


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)  # required by autocomplete fields in the Job admin
    readonly_fields = ("slug",)


class JobSourceInline(admin.TabularInline):
    model = JobSource
    extra = 1
    fields = ("name", "source_url", "external_id", "last_verified_at")


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    """The manual-entry dashboard: add verified vacancies, review imports, publish."""

    list_display = (
        "title",
        "company",
        "county",
        "job_type",
        "work_mode",
        "status",
        "deadline",
        "published_at",
    )
    list_filter = (
        "status",
        "job_type",
        "work_mode",
        "experience_level",
        "county",
        "company__verification_status",
    )
    search_fields = ("title", "company__name", "description")
    list_select_related = ("company",)
    autocomplete_fields = ("company", "skills")
    readonly_fields = ("slug", "published_at", "posted_by", "created_at", "updated_at")
    inlines = [JobSourceInline]
    actions = ["publish_jobs", "close_jobs", "mark_sources_verified"]

    fieldsets = (
        ("Listing", {"fields": ("company", "title", "status", "description", "requirements", "skills")}),
        ("Details", {"fields": ("job_type", "work_mode", "experience_level", "county", "location_detail")}),
        ("Salary", {"fields": (("salary_min", "salary_max"), "salary_currency", "salary_period")}),
        ("Application", {"fields": ("deadline", "application_url", "application_email")}),
        ("System", {"fields": ("slug", "published_at", "posted_by", "created_at", "updated_at")}),
    )

    def save_model(self, request, obj, form, change):
        if not change and obj.posted_by_id is None:
            obj.posted_by = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description="Publish selected jobs")
    def publish_jobs(self, request, queryset):
        count = 0
        for job in queryset.select_related("company").exclude(status=Job.Status.PUBLISHED):
            job.status = Job.Status.PUBLISHED
            job.save()
            count += 1
        self.message_user(request, f"{count} job(s) published.", messages.SUCCESS)

    @admin.action(description="Close selected jobs")
    def close_jobs(self, request, queryset):
        count = 0
        for job in queryset.select_related("company").exclude(status=Job.Status.CLOSED):
            job.status = Job.Status.CLOSED
            job.save()
            count += 1
        self.message_user(request, f"{count} job(s) closed.", messages.SUCCESS)

    @admin.action(description="Mark sources of selected jobs as verified now")
    def mark_sources_verified(self, request, queryset):
        updated = JobSource.objects.filter(job__in=queryset).update(
            last_verified_at=timezone.now(), updated_at=timezone.now()
        )
        self.message_user(request, f"{updated} source(s) marked as verified.", messages.SUCCESS)