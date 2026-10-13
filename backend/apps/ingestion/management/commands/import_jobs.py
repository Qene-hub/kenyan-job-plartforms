from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.ingestion.base import ProviderError
from apps.ingestion.importer import import_from_provider
from apps.ingestion.providers import PROVIDERS


class Command(BaseCommand):
    help = (
        "Import jobs from an external provider. Imported jobs are saved as 'pending review' "
        "and are only visible publicly after an admin reviews and publishes them."
    )

    def add_arguments(self, parser):
        parser.add_argument("--source", choices=sorted(PROVIDERS), default="adzuna")
        parser.add_argument("--query", default="", help="Search keywords, e.g. 'python developer'.")
        parser.add_argument("--pages", type=int, default=1, help="Number of result pages to fetch.")
        parser.add_argument("--country", help="Provider country code (default: ADZUNA_COUNTRY).")

    def handle(self, *args, **options):
        provider_class = PROVIDERS[options["source"]]
        country = options.get("country") or settings.ADZUNA_COUNTRY

        try:
            provider = provider_class(country=country)
            stats = import_from_provider(provider, options["query"], max(options["pages"], 1))
        except ProviderError as exc:
            raise CommandError(str(exc))

        self.stdout.write(
            self.style.SUCCESS(
                "Import finished: created={created} duplicates={duplicates} errors={errors}".format(
                    **stats
                )
            )
        )