import re
from collections.abc import Iterable, Mapping, Sequence
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse

_IMAGE_URL_RE = re.compile(
    r"https?://[^\s\"'<>]+?\.(?:avif|gif|jpe?g|png|svg|webp)(?:\?[^\s\"'<>]*)?",
    re.I,
)
_IMAGE_EXTENSIONS = (".avif", ".gif", ".jpeg", ".jpg", ".png", ".svg", ".webp")
_MEDIA_FIELDS = ("media_thumbnail", "media_content", "enclosures", "links")
_HTML_FIELDS = ("summary", "description")


class _HTMLImageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {name.lower(): value for name, value in attrs if value}

        if tag in {"img", "source"}:
            for attr_name in ("src", "data-src", "data-original", "data-lazy-src"):
                self._append(attr_map.get(attr_name))
            self._append_srcset(attr_map.get("srcset"))
            return

        if tag == "a":
            href = attr_map.get("href")
            if href and _has_image_extension(href):
                self._append(href)

    def handle_data(self, data: str) -> None:
        self.urls.extend(_IMAGE_URL_RE.findall(data))

    def _append_srcset(self, srcset: str | None) -> None:
        if not srcset:
            return
        for candidate in srcset.split(","):
            url = candidate.strip().split(" ", maxsplit=1)[0]
            self._append(url)

    def _append(self, url: str | None) -> None:
        if url:
            self.urls.append(url)


def extract_image_url(entry: Mapping[str, Any], *, feed_url: str) -> str | None:
    base_url = _base_url(entry, feed_url)

    for field in _MEDIA_FIELDS:
        image_url = _first_url(_media_image_urls(entry.get(field), field), base_url)
        if image_url:
            return image_url

    for field in _HTML_FIELDS:
        image_url = _first_url(_html_image_urls(entry.get(field)), base_url)
        if image_url:
            return image_url

    return _first_url(_content_image_urls(entry.get("content")), base_url)


def _base_url(entry: Mapping[str, Any], feed_url: str) -> str:
    link = entry.get("link")
    if isinstance(link, str) and link:
        return link
    return feed_url


def _media_image_urls(value: Any, field: str) -> Iterable[str]:
    for item in _mapping_items(value):
        url = _string_value(item.get("url") or item.get("href"))
        if not url:
            continue

        if field == "media_thumbnail":
            yield url
            continue

        kind = _string_value(item.get("type")).lower()
        medium = _string_value(item.get("medium")).lower()
        if kind.startswith("image/") or medium == "image" or _has_image_extension(url):
            yield url


def _mapping_items(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        return

    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return

    for item in value:
        if isinstance(item, Mapping):
            yield item


def _html_image_urls(value: Any) -> Iterable[str]:
    if not isinstance(value, str) or not value:
        return []

    parser = _HTMLImageParser()
    parser.feed(value)
    parser.close()
    return parser.urls


def _content_image_urls(value: Any) -> Iterable[str]:
    urls: list[str] = []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return urls

    for item in value:
        if not isinstance(item, Mapping):
            continue
        urls.extend(_html_image_urls(item.get("value")))

    return urls


def _first_url(candidates: Iterable[str], base_url: str) -> str | None:
    seen: set[str] = set()
    for candidate in candidates:
        image_url = _normalize_url(candidate, base_url)
        if not image_url or image_url in seen:
            continue
        seen.add(image_url)
        return image_url
    return None


def _normalize_url(candidate: str, base_url: str) -> str | None:
    url = candidate.strip()
    if not url or url.startswith(("cid:", "data:", "mailto:")):
        return None

    parsed = urlparse(urljoin(base_url, url))
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None

    return parsed.geturl()


def _has_image_extension(url: str) -> bool:
    path = urlparse(url).path.lower()
    return path.endswith(_IMAGE_EXTENSIONS)


def _string_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    return ""
