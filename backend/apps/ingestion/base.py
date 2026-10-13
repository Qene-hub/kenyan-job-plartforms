"""Contract every external job source follows."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

from apps.core.utils import JobType


class ProviderError(Exception):
    """Raised when a provider is misconfigured or its API call fails."""


@dataclass
class NormalizedJob:
    """A job in our own shape, independent of any provider's format."""

    external_id: str
    title: str
    company_name: str
    description: str
    source_url: str
    application_url: str
    county: str = ""
    location_detail: str = ""
    job_type: str = JobType.FULL_TIME.value
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: str = "KES"
    salary_period: str = "month"
    skills: List[str] = field(default_factory=list)
    deadline: Optional[date] = None


class JobSourceProvider(ABC):
    """Subclass this, set `name`, and implement `fetch`."""

    name: str = ""

    @abstractmethod
    def fetch(self, query: str, page: int = 1) -> List[NormalizedJob]:
        """Return one page of normalised jobs. Raise ProviderError on failure."""