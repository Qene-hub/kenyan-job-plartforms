from django.core.management.base import BaseCommand

from apps.jobs.tasks import expire_jobs


class Command(BaseCommand):
    help = "Close published jobs whose application deadline has passed."

    def handle(self, *args, **options):
        closed = expire_jobs()
        self.stdout.write(self.style.SUCCESS(f"Closed {closed} expired job(s)."))