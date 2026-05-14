"""Unit tests for tools/github_repo_search.py.

Covers: request construction, allowlist scoping, result formatting,
token header behavior, fallback behavior, and repo injection prevention.
"""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

import tools.github_repo_search as github_module
from tools.github_repo_search import (
    _FALLBACK,
    _build_headers,
    _build_query,
    _format_results,
    _sanitize_query,
    github_repo_search,
)


@pytest.fixture
def github_token_stub(monkeypatch):
    monkeypatch.setattr(
        github_module.settings,
        "github_api_token",
        SimpleNamespace(get_secret_value=lambda: "test-token"),
    )


@pytest.fixture
def no_github_token(monkeypatch):
    monkeypatch.setattr(github_module.settings, "github_api_token", None)


# ── Query construction ────────────────────────────────────────────────────────

def test_build_query_includes_repo_qualifier():
    q = _build_query("prozorro-eds init", ["ProzorroUKR/prozorro-eds"])
    assert "repo:ProzorroUKR/prozorro-eds" in q
    assert "prozorro-eds init" in q


def test_build_query_includes_multiple_repo_qualifiers():
    q = _build_query("sign method", ["ProzorroUKR/prozorro-eds", "ProzorroUKR/prozorro-pdf"])
    assert "repo:ProzorroUKR/prozorro-eds" in q
    assert "repo:ProzorroUKR/prozorro-pdf" in q


def test_sanitize_query_removes_repo_qualifiers():
    sanitized = _sanitize_query("some query repo:attacker/evil")
    assert "repo:" not in sanitized
    assert "some query" in sanitized


def test_build_query_strips_injected_repo_qualifier():
    q = _build_query("some query repo:attacker/evil", ["ProzorroUKR/prozorro-eds"])
    assert "repo:attacker/evil" not in q
    assert "repo:ProzorroUKR/prozorro-eds" in q


# ── Headers ───────────────────────────────────────────────────────────────────

def test_build_headers_includes_auth_when_token_set(github_token_stub):
    headers = _build_headers()
    assert headers["Authorization"] == "Bearer test-token"


def test_build_headers_omits_auth_when_no_token(no_github_token):
    headers = _build_headers()
    assert "Authorization" not in headers


def test_build_headers_always_includes_text_match_accept(no_github_token):
    headers = _build_headers()
    assert "text-match" in headers["Accept"]


def test_build_headers_always_includes_github_api_version(no_github_token):
    headers = _build_headers()
    assert headers["X-GitHub-Api-Version"] == "2022-11-28"


# ── Result formatting ─────────────────────────────────────────────────────────

def test_format_results_includes_repo_path_and_url():
    items = [
        {
            "repository": {"full_name": "ProzorroUKR/prozorro-eds"},
            "path": "README.md",
            "html_url": "https://github.com/ProzorroUKR/prozorro-eds/blob/master/README.md",
            "text_matches": [{"fragment": "ProzorroEds.init() initializes the library"}],
        }
    ]
    result = _format_results(items)
    assert "ProzorroUKR/prozorro-eds" in result
    assert "README.md" in result
    assert "https://github.com/ProzorroUKR/prozorro-eds/blob/master/README.md" in result
    assert "ProzorroEds.init()" in result


def test_format_results_truncates_long_snippet():
    long_fragment = "x" * 500
    items = [
        {
            "repository": {"full_name": "ProzorroUKR/prozorro-eds"},
            "path": "docs/api.md",
            "html_url": "https://github.com/ProzorroUKR/prozorro-eds/blob/master/docs/api.md",
            "text_matches": [{"fragment": long_fragment}],
        }
    ]
    result = _format_results(items)
    # snippet is truncated; the Джерело: line follows it, so result doesn't end with "..."
    assert "..." in result
    x_count = result.count("x")
    assert x_count <= 400


def test_format_results_handles_no_text_matches():
    items = [
        {
            "repository": {"full_name": "ProzorroUKR/prozorro-eds"},
            "path": "src/index.ts",
            "html_url": "https://github.com/ProzorroUKR/prozorro-eds/blob/master/src/index.ts",
            "text_matches": [],
        }
    ]
    result = _format_results(items)
    assert "ProzorroUKR/prozorro-eds" in result
    assert result != _FALLBACK


def test_format_results_limits_to_max_results():
    items = [
        {
            "repository": {"full_name": "ProzorroUKR/prozorro-eds"},
            "path": f"file{i}.ts",
            "html_url": f"https://github.com/ProzorroUKR/prozorro-eds/blob/master/file{i}.ts",
            "text_matches": [],
        }
        for i in range(10)
    ]
    result = _format_results(items)
    assert result.count("---") == 5


# ── Tool behavior ─────────────────────────────────────────────────────────────

def test_github_repo_search_returns_fallback_when_repos_empty(monkeypatch):
    monkeypatch.setattr(github_module.settings, "tech_support_github_repos", [])
    result = github_repo_search.invoke({"query": "prozorro-eds methods"})
    assert result == _FALLBACK


def test_github_repo_search_calls_api_with_allowlisted_repo(monkeypatch, no_github_token):
    monkeypatch.setattr(
        github_module.settings,
        "tech_support_github_repos",
        ["ProzorroUKR/prozorro-eds"],
    )
    mock_resp = Mock()
    mock_resp.json.return_value = {
        "items": [
            {
                "repository": {"full_name": "ProzorroUKR/prozorro-eds"},
                "path": "README.md",
                "html_url": "https://github.com/ProzorroUKR/prozorro-eds/blob/master/README.md",
                "text_matches": [{"fragment": "ProzorroEds.init() — initialize the library"}],
            }
        ]
    }
    mock_resp.raise_for_status = Mock()

    with patch("tools.github_repo_search.httpx.get", return_value=mock_resp) as mock_get:
        result = github_repo_search.invoke({"query": "методи бібліотеки"})

    call_q = mock_get.call_args.kwargs["params"]["q"]
    assert "repo:ProzorroUKR/prozorro-eds" in call_q
    assert result != _FALLBACK


def test_github_repo_search_returns_fallback_on_empty_results(monkeypatch, no_github_token):
    monkeypatch.setattr(
        github_module.settings,
        "tech_support_github_repos",
        ["ProzorroUKR/prozorro-eds"],
    )
    mock_resp = Mock()
    mock_resp.json.return_value = {"items": []}
    mock_resp.raise_for_status = Mock()

    with patch("tools.github_repo_search.httpx.get", return_value=mock_resp):
        result = github_repo_search.invoke({"query": "nonexistent feature"})

    assert result == _FALLBACK


def test_github_repo_search_returns_fallback_on_http_error(monkeypatch, no_github_token):
    monkeypatch.setattr(
        github_module.settings,
        "tech_support_github_repos",
        ["ProzorroUKR/prozorro-eds"],
    )
    with patch("tools.github_repo_search.httpx.get", side_effect=Exception("connection error")):
        result = github_repo_search.invoke({"query": "методи"})

    assert result == _FALLBACK


def test_github_repo_search_query_cannot_escape_to_non_allowlisted_repo(
    monkeypatch, no_github_token
):
    """User-injected repo: qualifiers are stripped so only allowlisted repos are searched."""
    monkeypatch.setattr(
        github_module.settings,
        "tech_support_github_repos",
        ["ProzorroUKR/prozorro-eds"],
    )
    mock_resp = Mock()
    mock_resp.json.return_value = {"items": []}
    mock_resp.raise_for_status = Mock()

    with patch("tools.github_repo_search.httpx.get", return_value=mock_resp) as mock_get:
        github_repo_search.invoke({"query": "query repo:attacker/evil-repo"})

    call_q = mock_get.call_args.kwargs["params"]["q"]
    assert "repo:attacker/evil-repo" not in call_q
    assert "repo:ProzorroUKR/prozorro-eds" in call_q
