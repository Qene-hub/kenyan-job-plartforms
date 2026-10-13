"""Adzuna job search API (https://developer.adzuna.com).

Confirm that Adzuna covers the country you query and that its terms allow your use.
"""
from typing import Optional

import requests
from django.conf import settings

from apps.core.utils import JobType, match_county

from ..base import JobSourceProvider, NormalizedJob, ProviderError

# Adzuna reports salaries in the local currency of the country searched.
CURRENCIES = {
    "gb": "GBP", "us": "USD", "au": "AUD", "ca": "CAD", "de": "EUR", "fr": "EUR",
    "it": "EUR", "es": "EUR", "nl": "EUR", "at": "EUR", "be": "EUR", "pl": "PLN",
    "br": "BRL", "in": "INR", "mx": "MXN", "nz": "NZD", "sg": "SGD", "za": "ZAR",
    "ch": "CHF", "ke": "KES",
}


def _to_int(value) -> Optional[int]:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


class AdzunaProvider(JobSourceProvider):
    name = "adzuna"
    base_url = "https://api.adzuna.com/v1/api/jobs"

    def __init__(self, app_id=None, app_key=None, country=None, session=None, timeout=15):
        self.app_id = app_id or settings.ADZUNA_APP_ID
        self.app_key = app_key or settings.ADZUNA_APP_KEY
        self.country = (country or settings.ADZUNA_COUNTRY or "").lower()
        self.session = session or requests.Session()
        self.timeout = timeout

        if not self.app_id or not self.app_key:
            raise ProviderError("Set ADZUNA_APP_ID and ADZUNA_APP_KEY to use the Adzuna provider.")
        if not self.country:
            raise ProviderError("Set ADZUNA_COUNTRY or pass --country (for example: gb).")

    def fetch(self, query: str, page: int = 1):
        url = f"{self.base_url}/{self.country}/search/{page}"
        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "what": query,
            "results_per_page": 50,
            "content-type": "application/json",
        }
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise ProviderError(f"Adzuna request failed for country '{self.country}': {exc}") from exc

        jobs = (self._normalize(item) for item in payload.get("results", []))
        return [job for job in jobs if job is not None]

    def _normalize(self, item):
        external_id = str(item.get("id") or "")
        title = (item.get("title") or "").strip()
        company_name = ((item.get("company") or {}).get("display_name") or "").strip()
        url = item.get("redirect_url") or ""
        if not (external_id and title and company_name and url):
            return None

        location = item.get("location") or {}
        areas = list(location.get("area") or [])
        county = match_county(*reversed(areas), location.get("display_name"))

        currency = CURRENCIES.get(self.country)
        predicted = str(item.get("salary_is_predicted", "0")) == "1"
        salary_min = salary_max = None
        if currency and not predicted:
            salary_min = _to_int(item.get("salary_min"))
            salary_max = _to_int(item.get("salary_max"))

        if item.get("contract_time") == "part_time":
            job_type = JobType.PART_TIME.value
        elif item.get("contract_type") == "contract":
            job_type = JobType.CONTRACT.value
        else:
            job_type = JobType.FULL_TIME.value

        return NormalizedJob(
            external_id=external_id,
            title=title,
            company_name=company_name,
            description=(item.get("description") or "").strip() or title,
            source_url=url,
            application_url=url,
            county=county,
            location_detail=(location.get("display_name") or "")[:150],
            job_type=job_type,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=currency or "KES",
            salary_period="year",
        )