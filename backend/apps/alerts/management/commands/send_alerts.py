from django.core.management.base import BaseCommand

from apps.alerts.models import JobAlert
from apps.alerts.tasks import send_job_alerts


class Command(BaseCommand):
    help = "Email users about new jobs that match their saved alerts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--frequency",
            choices=[value for value, _ in JobAlert.Frequency.choices],
            help="Only process alerts with this frequency (default: all).",
        )

    def handle(self, *args, **options):
        stats = send_job_alerts(frequency=options.get("frequency"))
        self.stdout.write(
            self.style.SUCCESS(
                "Alerts processed={processed} sent={sent} no_matches={no_matches} "
                "failed={failed} not_due={not_due}".format(**stats)
            )
        )