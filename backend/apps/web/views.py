from django.shortcuts import render
from django.views.generic import TemplateView


class HomeView(TemplateView):
    template_name = "pages/home.html"


class JobListView(TemplateView):
    template_name = "pages/job_list.html"


class JobDetailView(TemplateView):
    template_name = "pages/job_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["job_id"] = kwargs["pk"]
        return context


class LoginPageView(TemplateView):
    template_name = "pages/login.html"


class RegisterPageView(TemplateView):
    template_name = "pages/register.html"


class DashboardView(TemplateView):
    template_name = "pages/dashboard.html"


class SavedJobsPageView(TemplateView):
    template_name = "pages/saved_jobs.html"


class ApplicationsPageView(TemplateView):
    template_name = "pages/applications.html"


class AlertsPageView(TemplateView):
    template_name = "pages/alerts.html"


def page_not_found(request, exception):
    return render(request, "errors/404.html", status=404)


def server_error(request):
    return render(request, "errors/500.html", status=500)