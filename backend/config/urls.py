from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from apps.core.health import HealthCheckView

admin.site.site_header = "Kenya Job Platform"
admin.site.site_title = "Kenya Job Platform"
admin.site.index_title = "Administration"

urlpatterns = [
    path("admin/", admin.site.urls),
    # API v1
    path("api/v1/health/", HealthCheckView.as_view(), name="health"),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.companies.urls")),
    path("api/v1/", include("apps.jobs.urls")),
    path("api/v1/", include("apps.tracker.urls")),
    path("api/v1/", include("apps.alerts.urls")),
    # API documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    # Website pages (must stay last)
    path("", include("apps.web.urls")),
]

# Used when DEBUG is False (production)
handler404 = "apps.web.views.page_not_found"
handler500 = "apps.web.views.server_error"