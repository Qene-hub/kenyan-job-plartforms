"""Shared constants and helpers used across apps."""
from django.db import models
from django.utils.text import slugify

# --- Shared choices -----------------------------------------------------------


class JobType(models.TextChoices):
    FULL_TIME = "full_time", "Full-time"
    PART_TIME = "part_time", "Part-time"
    CONTRACT = "contract", "Contract"
    INTERNSHIP = "internship", "Internship"
    ATTACHMENT = "attachment", "Attachment"
    VOLUNTEER = "volunteer", "Volunteer"
    TEMPORARY = "temporary", "Temporary"


class WorkMode(models.TextChoices):
    ON_SITE = "on_site", "On-site"
    REMOTE = "remote", "Remote"
    HYBRID = "hybrid", "Hybrid"


class ExperienceLevel(models.TextChoices):
    ENTRY = "entry", "Entry level"
    MID = "mid", "Mid level"
    SENIOR = "senior", "Senior"
    EXECUTIVE = "executive", "Executive"


_COUNTY_NAMES = [
    "Baringo", "Bomet", "Bungoma", "Busia", "Elgeyo-Marakwet", "Embu", "Garissa",
    "Homa Bay", "Isiolo", "Kajiado", "Kakamega", "Kericho", "Kiambu", "Kilifi",
    "Kirinyaga", "Kisii", "Kisumu", "Kitui", "Kwale", "Laikipia", "Lamu", "Machakos",
    "Makueni", "Mandera", "Marsabit", "Meru", "Migori", "Mombasa", "Murang'a",
    "Nairobi", "Nakuru", "Nandi", "Narok", "Nyamira", "Nyandarua", "Nyeri",
    "Samburu", "Siaya", "Taita-Taveta", "Tana River", "Tharaka-Nithi", "Trans-Nzoia",
    "Turkana", "Uasin Gishu", "Vihiga", "Wajir", "West Pokot",
]

# Django "choices" format: (stored value, label), e.g. ("uasin-gishu", "Uasin Gishu")
KENYA_COUNTIES = [(slugify(name), name) for name in _COUNTY_NAMES]
_COUNTY_SLUGS = {slug for slug, _ in KENYA_COUNTIES}


# --- Helpers -------------------------------------------------------------------


def generate_unique_slug(instance, value, slug_field="slug"):
    """Build a URL-friendly slug that is unique for this model.

    "Acme Ltd" -> "acme-ltd"; a collision becomes "acme-ltd-2", "acme-ltd-3", ...
    """
    model = instance.__class__
    max_length = model._meta.get_field(slug_field).max_length
    base = slugify(value)[:max_length] or "item"

    slug = base
    counter = 2
    while model._default_manager.filter(**{slug_field: slug}).exclude(pk=instance.pk).exists():
        suffix = f"-{counter}"
        slug = f"{base[: max_length - len(suffix)]}{suffix}"
        counter += 1
    return slug


def normalize_text(value):
    """Lowercase and strip punctuation/extra spaces: "Data  Analyst!" -> "data analyst"."""
    import re

    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def match_county(*values):
    """Return the county slug found in the first matching value, or an empty string."""
    for value in values:
        slug = slugify(value or "")
        if slug in _COUNTY_SLUGS:
            return slug
    return ""


def clean_skill_list(values):
    """Trim whitespace, drop empties and case-insensitive duplicates, keep order."""
    cleaned = []
    seen = set()
    for value in values:
        name = " ".join(str(value).split())
        if name and name.lower() not in seen:
            seen.add(name.lower())
            cleaned.append(name)
    return cleaned