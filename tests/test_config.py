"""Direct tests for CSV parsing and normalization in Settings.

Tests Settings() with explicit constructor arguments to avoid relying on
any .env file or the global singleton.
"""

from config import Settings


# ── tech_support_allowed_domains ─────────────────────────────────────────────

def test_allowed_domains_csv_parsed_correctly():
    s = Settings(tech_support_allowed_domains="docs.prozorro.org,infobox.prozorro.org")
    assert s.tech_support_allowed_domains == ["docs.prozorro.org", "infobox.prozorro.org"]


def test_allowed_domains_whitespace_stripped():
    s = Settings(tech_support_allowed_domains=" docs.prozorro.org , infobox.prozorro.org ")
    assert s.tech_support_allowed_domains == ["docs.prozorro.org", "infobox.prozorro.org"]


def test_allowed_domains_empty_string_yields_empty_list():
    s = Settings(tech_support_allowed_domains="")
    assert s.tech_support_allowed_domains == []


def test_allowed_domains_empty_items_removed():
    s = Settings(tech_support_allowed_domains="docs.prozorro.org,,infobox.prozorro.org")
    assert s.tech_support_allowed_domains == ["docs.prozorro.org", "infobox.prozorro.org"]


def test_allowed_domains_url_scheme_normalized_to_host():
    s = Settings(tech_support_allowed_domains="https://docs.prozorro.org")
    assert s.tech_support_allowed_domains == ["docs.prozorro.org"]


def test_allowed_domains_url_with_path_normalized_to_host():
    s = Settings(tech_support_allowed_domains="https://docs.prozorro.org/api/v2")
    assert s.tech_support_allowed_domains == ["docs.prozorro.org"]


def test_allowed_domains_http_scheme_stripped():
    s = Settings(tech_support_allowed_domains="http://infobox.prozorro.org")
    assert s.tech_support_allowed_domains == ["infobox.prozorro.org"]


def test_allowed_domains_bare_host_unchanged():
    s = Settings(tech_support_allowed_domains="github.com")
    assert s.tech_support_allowed_domains == ["github.com"]


# ── tech_support_github_repos ─────────────────────────────────────────────────

def test_github_repos_csv_parsed_correctly():
    s = Settings(tech_support_github_repos="ProzorroUKR/prozorro-eds,ProzorroUKR/prozorro-pdf")
    assert s.tech_support_github_repos == ["ProzorroUKR/prozorro-eds", "ProzorroUKR/prozorro-pdf"]


def test_github_repos_whitespace_stripped():
    s = Settings(tech_support_github_repos=" ProzorroUKR/prozorro-eds , ProzorroUKR/prozorro-pdf ")
    assert s.tech_support_github_repos == ["ProzorroUKR/prozorro-eds", "ProzorroUKR/prozorro-pdf"]


def test_github_repos_empty_string_yields_empty_list():
    s = Settings(tech_support_github_repos="")
    assert s.tech_support_github_repos == []


def test_github_repos_full_url_normalized_to_owner_repo():
    s = Settings(tech_support_github_repos="https://github.com/ProzorroUKR/prozorro-eds")
    assert s.tech_support_github_repos == ["ProzorroUKR/prozorro-eds"]


def test_github_repos_multiple_full_urls_normalized():
    s = Settings(
        tech_support_github_repos=(
            "https://github.com/ProzorroUKR/prozorro-eds,"
            "https://github.com/ProzorroUKR/prozorro-pdf"
        )
    )
    assert s.tech_support_github_repos == ["ProzorroUKR/prozorro-eds", "ProzorroUKR/prozorro-pdf"]


def test_github_repos_owner_repo_unchanged():
    s = Settings(tech_support_github_repos="ProzorroUKR/prozorro-eds")
    assert s.tech_support_github_repos == ["ProzorroUKR/prozorro-eds"]


def test_github_repos_trailing_slash_stripped():
    s = Settings(tech_support_github_repos="https://github.com/ProzorroUKR/prozorro-eds/")
    assert s.tech_support_github_repos == ["ProzorroUKR/prozorro-eds"]
