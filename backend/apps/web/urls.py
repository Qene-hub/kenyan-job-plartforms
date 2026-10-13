from django.urls import path

from ..web import views

app_name = "web"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("jobs/", views.JobListView.as_view(), name="job-list"),
    path("jobs/<int:pk>/", views.JobDetailView.as_view(), name="job-detail"),
    path("login/", views.LoginPageView.as_view(), name="login"),
    path("register/", views.RegisterPageView.as_view(), name="register"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("dashboard/saved/", views.SavedJobsPageView.as_view(), name="saved-jobs"),
    path("dashboard/applications/", views.ApplicationsPageView.as_view(), name="applications"),
    path("dashboard/alerts/", views.AlertsPageView.as_view(), name="alerts"),
]