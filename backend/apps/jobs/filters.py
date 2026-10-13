from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from django_filters import rest_framework as filters

from apps.core.utils import KENYA_COUNTIES, ExperienceLevel, JobType, WorkMode

from .models import Job


def salary_at_least_q(value):
    """Jobs paying at least `value`: the top of the range qualifies, else the single figure."""
    return Q(salary_max__gte=value) | Q(salary_max__isnull=True, salary_min__gte=value)


class JobFilter(filters.FilterSet):
    county = filters.MultipleChoiceFilter(choices=KENYA_COUNTIES)
    job_type = filters.MultipleChoiceFilter(choices=JobType.choices)
    work_mode = filters.MultipleChoiceFilter(choices=WorkMode.choices)
    experience_level = filters.MultipleChoiceFilter(choices=ExperienceLevel.choices)
    company = filters.CharFilter(field_name="company__slug", help_text="Company slug.")
    skills = filters.CharFilter(
        method="filter_skills", help_text="Comma-separated skill names; matches any."
    )
    min_salary = filters.NumberFilter(method="filter_min_salary")
    has_salary = filters.BooleanFilter(method="filter_has_salary")
    posted_within = filters.NumberFilter(
        method="filter_posted_within", help_text="Only jobs published in the last N days."
    )
    deadline_before = filters.DateFilter(field_name="deadline", lookup_expr="lte")
    deadline_after = filters.DateFilter(field_name="deadline", lookup_expr="gte")

    class Meta:
        model = Job
        fields = []

    def filter_skills(self, queryset, name, value):
        names = [part.strip() for part in value.split(",") if part.strip()]
        if not names:
            return queryset
        query = Q()
        for skill_name in names:
            query |= Q(skills__name__iexact=skill_name)
        return queryset.filter(query).distinct()

    def filter_min_salary(self, queryset, name, value):
        return queryset.filter(salary_at_least_q(value))

    def filter_has_salary(self, queryset, name, value):
        with_salary = Q(salary_min__isnull=False) | Q(salary_max__isnull=False)
        return queryset.filter(with_salary) if value else queryset.exclude(with_salary)

    def filter_posted_within(self, queryset, name, value):
        cutoff = timezone.now() - timedelta(days=float(value))
        return queryset.filter(published_at__gte=cutoff)