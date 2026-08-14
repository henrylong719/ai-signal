"""Tests for the No Priors → Apple Podcasts episode lookup.

The lookup sits on a user-facing click path with a 2s timeout, so the
behaviour that matters is what happens when it *fails*: the caller must
get None (and fall back to the show landing page), and the failure must
not be cached, or one iTunes blip would pin every No Priors click to the
landing page until the worker restarted.
"""

from typing import Any

import httpx
import pytest

from app.services import article_redirects


@pytest.fixture(autouse=True)
def _clear_episode_cache() -> Any:
    """The cache is process-global; isolate every test from its neighbours."""
    article_redirects._apple_episode_url_cache.clear()
    yield
    article_redirects._apple_episode_url_cache.clear()


class _FakeResponse:
    def __init__(self, payload: Any, *, raises: Exception | None = None) -> None:
        self._payload = payload
        self._raises = raises

    def raise_for_status(self) -> None:
        if self._raises is not None:
            raise self._raises

    def json(self) -> Any:
        return self._payload


def _patch_get(monkeypatch: pytest.MonkeyPatch, response: Any) -> list[dict[str, Any]]:
    """Stub httpx.get, recording the params it was called with."""
    calls: list[dict[str, Any]] = []

    def fake_get(url: str, **kwargs: Any) -> Any:
        calls.append({"url": url, **kwargs})
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(article_redirects.httpx, "get", fake_get)
    return calls


def _episode(url: str, collection_id: int | None = None) -> dict[str, Any]:
    return {
        "collectionId": (
            collection_id
            if collection_id is not None
            else article_redirects._NO_PRIORS_APPLE_COLLECTION_ID
        ),
        "trackViewUrl": url,
    }


def test_resolves_and_caches_a_matching_episode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = "https://podcasts.apple.com/us/podcast/ep-1/id1668002688?i=1"
    calls = _patch_get(monkeypatch, _FakeResponse({"results": [_episode(url)]}))

    resolved = article_redirects._no_priors_apple_episode_url("Ep 1")

    assert resolved == url
    assert article_redirects._apple_episode_url_cache["Ep 1"] == url
    assert calls[0]["params"]["term"] == "No Priors Ep 1"


def test_second_call_is_served_from_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = "https://podcasts.apple.com/us/podcast/ep-2/id1668002688?i=2"
    calls = _patch_get(monkeypatch, _FakeResponse({"results": [_episode(url)]}))

    first = article_redirects._no_priors_apple_episode_url("Ep 2")
    second = article_redirects._no_priors_apple_episode_url("Ep 2")

    assert first == second == url
    assert len(calls) == 1, "cached title should not hit the network again"


def test_http_error_returns_none_and_is_not_cached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A transient outage must not pin the title to the fallback forever."""
    _patch_get(monkeypatch, httpx.ConnectTimeout("boom"))

    resolved = article_redirects._no_priors_apple_episode_url("Ep 3")

    assert resolved is None
    assert "Ep 3" not in article_redirects._apple_episode_url_cache


def test_non_json_body_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    class _BadJson(_FakeResponse):
        def json(self) -> Any:
            raise ValueError("not json")

    _patch_get(monkeypatch, _BadJson(None))

    assert article_redirects._no_priors_apple_episode_url("Ep 4") is None


def test_status_error_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_get(
        monkeypatch,
        _FakeResponse(
            {"results": []},
            raises=httpx.HTTPStatusError(
                "500", request=httpx.Request("GET", "https://x"), response=None
            ),
        ),
    )

    assert article_redirects._no_priors_apple_episode_url("Ep 5") is None


def test_episode_from_another_show_is_ignored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """collectionId is the guard against matching a different podcast."""
    _patch_get(
        monkeypatch,
        _FakeResponse(
            {
                "results": [
                    _episode("https://podcasts.apple.com/us/podcast/x", 999),
                ]
            }
        ),
    )

    assert article_redirects._no_priors_apple_episode_url("Ep 6") is None


def test_non_dict_results_are_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    url = "https://podcasts.apple.com/us/podcast/ep-7/id1668002688?i=7"
    _patch_get(
        monkeypatch,
        _FakeResponse({"results": ["nonsense", None, _episode(url)]}),
    )

    assert article_redirects._no_priors_apple_episode_url("Ep 7") == url


def test_untrusted_host_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Defence in depth: the URL comes from a third party, so it is checked."""
    _patch_get(
        monkeypatch,
        _FakeResponse({"results": [_episode("https://evil.example/ep")]}),
    )

    assert article_redirects._no_priors_apple_episode_url("Ep 8") is None


def test_non_http_scheme_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_get(
        monkeypatch,
        _FakeResponse({"results": [_episode("javascript:alert(1)")]}),
    )

    assert article_redirects._no_priors_apple_episode_url("Ep 9") is None


def test_missing_track_url_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_get(
        monkeypatch,
        _FakeResponse(
            {
                "results": [
                    {"collectionId": (article_redirects._NO_PRIORS_APPLE_COLLECTION_ID)}
                ]
            }
        ),
    )

    assert article_redirects._no_priors_apple_episode_url("Ep 10") is None


def test_raw_audio_url_detection() -> None:
    assert article_redirects._is_no_priors_raw_audio_url(
        "https://traffic.megaphone.fm/abc.mp3"
    )
    assert not article_redirects._is_no_priors_raw_audio_url(
        "https://traffic.megaphone.fm/abc.html"
    )
    assert not article_redirects._is_no_priors_raw_audio_url(
        "https://example.com/abc.mp3"
    )
