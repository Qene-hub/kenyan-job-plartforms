from apps.core.cache import NAMESPACE_JOBS, bump_version, get_version
from apps.core.utils import clean_skill_list, match_county


def test_bump_version_changes_the_version():
    first = get_version(NAMESPACE_JOBS)
    bump_version(NAMESPACE_JOBS)
    assert get_version(NAMESPACE_JOBS) == first + 1


def test_match_county_finds_slug_in_values():
    assert match_county("Kenya", "Uasin Gishu") == "uasin-gishu"
    assert match_county("Atlantis") == ""


def test_clean_skill_list_removes_duplicates_and_blanks():
    assert clean_skill_list(["Python", " python ", "", "Django"]) == ["Python", "Django"]