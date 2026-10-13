from .adzuna import AdzunaProvider

# Registry used by the import_jobs command. Add new providers here.
PROVIDERS = {AdzunaProvider.name: AdzunaProvider}