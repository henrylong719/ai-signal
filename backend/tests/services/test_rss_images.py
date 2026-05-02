from app.services.rss_images import extract_image_url


def test_extract_image_url_prefers_media_thumbnail() -> None:
    entry = {
        "link": "https://example.com/posts/article",
        "media_thumbnail": [{"url": "https://cdn.example.com/thumb.webp"}],
        "summary": '<img src="https://cdn.example.com/inline.png">',
    }

    assert (
        extract_image_url(entry, feed_url="https://example.com/feed.xml")
        == "https://cdn.example.com/thumb.webp"
    )


def test_extract_image_url_accepts_media_content_without_extension() -> None:
    entry = {
        "link": "https://example.com/posts/article",
        "media_content": [
            {
                "medium": "image",
                "url": "https://lh3.googleusercontent.com/example=w528-h297",
            }
        ],
    }

    assert (
        extract_image_url(entry, feed_url="https://example.com/feed.xml")
        == "https://lh3.googleusercontent.com/example=w528-h297"
    )


def test_extract_image_url_reads_image_enclosures() -> None:
    entry = {
        "link": "https://example.com/posts/article",
        "enclosures": [
            {
                "href": "https://substack-post-media.s3.amazonaws.com/image.png",
                "type": "image/png",
            }
        ],
    }

    assert (
        extract_image_url(entry, feed_url="https://example.com/feed.xml")
        == "https://substack-post-media.s3.amazonaws.com/image.png"
    )


def test_extract_image_url_normalizes_relative_inline_images() -> None:
    entry = {
        "link": "https://example.com/posts/article/",
        "summary": '<p>Hello</p><img src="/assets/article.png">',
    }

    assert (
        extract_image_url(entry, feed_url="https://example.com/feed.xml")
        == "https://example.com/assets/article.png"
    )


def test_extract_image_url_falls_back_to_content_images() -> None:
    entry = {
        "link": "https://example.com/posts/article/",
        "content": [
            {
                "value": '<figure><img src="figures/overview.jpg"></figure>',
            }
        ],
    }

    assert (
        extract_image_url(entry, feed_url="https://example.com/feed.xml")
        == "https://example.com/posts/article/figures/overview.jpg"
    )


def test_extract_image_url_ignores_non_image_links() -> None:
    entry = {
        "link": "https://example.com/posts/article/",
        "links": [{"href": "https://example.com/posts/article/", "type": "text/html"}],
    }

    assert extract_image_url(entry, feed_url="https://example.com/feed.xml") is None
