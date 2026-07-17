"""Unit and integration tests for WordPress publishing features."""

from __future__ import annotations

import json
import urllib.error
from unittest.mock import MagicMock, patch
from app.wordpress import markdown_to_gutenberg, publish_to_wordpress


def test_markdown_to_gutenberg():
    markdown = (
        "# Main Title\n\n"
        "## Sub Heading\n\n"
        "This is a paragraph with **bold** text and a [link](https://example.com).\n\n"
        "> Quote text here\n\n"
        "- List item 1\n"
        "- List item 2\n\n"
        "1. Ordered item 1\n"
        "2. Ordered item 2"
    )
    
    html = markdown_to_gutenberg(markdown)
    
    # Assert headers
    assert '<!-- wp:heading {"level":1} -->' in html
    assert "<h1>Main Title</h1>" in html
    assert '<!-- wp:heading {"level":2} -->' in html
    assert "<h2>Sub Heading</h2>" in html
    
    # Assert paragraph and inline formats
    assert "<!-- wp:paragraph -->" in html
    assert "<strong>bold</strong>" in html
    assert '<a href="https://example.com">link</a>' in html
    
    # Assert blockquote
    assert "<!-- wp:quote -->" in html
    assert '<blockquote class="wp-block-quote"><p>Quote text here</p></blockquote>' in html
    
    # Assert lists
    assert "<!-- wp:list -->" in html
    assert "<ul>\n<li>List item 1</li>\n<li>List item 2</li>\n</ul>" in html
    assert '<!-- wp:list {"ordered":true} -->' in html
    assert "<ol>\n<li>Ordered item 1</li>\n<li>Ordered item 2</li>\n</ol>" in html


def make_mock_response(json_bytes):
    mock = MagicMock()
    mock.read.return_value = json_bytes
    mock.__enter__.return_value = mock
    return mock


@patch("urllib.request.urlopen")
def test_publish_to_wordpress_success(mock_urlopen):
    # Mocking taxonomy searches and post creation responses
    responses = [
        # Search tag "agent" -> not found
        make_mock_response(b"[]"),
        # Create tag "agent" -> returns ID 10
        make_mock_response(b'{"id": 10}'),
        # Search category "Tech" -> found ID 5
        make_mock_response(b'[{"id": 5, "name": "Tech"}]'),
        # Create post -> returns link
        make_mock_response(b'{"id": 101, "link": "http://wordpress.test/?p=101"}')
    ]
    mock_urlopen.side_effect = lambda req, *args, **kwargs: responses.pop(0)
    
    link = publish_to_wordpress(
        wp_url="http://wordpress.test",
        username="admin",
        app_password="app-password",
        title="Test Title",
        markdown_content="Hello World",
        excerpt="Test Excerpt",
        slug="test-slug",
        tags=["agent"],
        categories=["Tech"]
    )
    
    assert link == "http://wordpress.test/?p=101"
    assert mock_urlopen.call_count == 4  # (Search tag + Create tag) + (Search category) + (Create post)



def test_publish_node_skipped():
    import app.config as config
    from app.pipeline import publish_node
    
    # Clear settings to force a skip
    with patch.object(config, "get_wp_config", return_value={"url": "", "username": "", "password": ""}):
        events = []
        from app import pipeline
        pipeline.set_emitter(events.append)
        
        state = {
            "draft": MagicMock(title="T", markdown="M"),
            "seo": MagicMock(meta_description="D", slug="S", primary_keyword="K", secondary_keywords=[])
        }
        res = publish_node(state)
        
        assert res == {}
        assert any(e["kind"] == "done" and e["stage"] == "publish" and e["detail"]["status"] == "skipped" for e in events)


@patch("app.wordpress.publish_to_wordpress")
def test_publish_node_handles_failure_gracefully(mock_publish):
    import app.config as config
    from app.pipeline import publish_node
    
    mock_publish.side_effect = RuntimeError("WordPress down")
    
    with patch.object(config, "get_wp_config", return_value={"url": "http://wordpress.test", "username": "admin", "password": "pwd", "default_categories": []}):
        events = []
        from app import pipeline
        pipeline.set_emitter(events.append)
        
        state = {
            "draft": MagicMock(title="T", markdown="M"),
            "seo": MagicMock(meta_description="D", slug="S", primary_keyword="K", secondary_keywords=[])
        }
        res = publish_node(state)
        
        # Must execute cleanly and emit failed done status
        assert res == {}
        assert any(e["kind"] == "done" and e["stage"] == "publish" and e["detail"]["status"] == "failed" for e in events)


if __name__ == "__main__":
    test_markdown_to_gutenberg()
    print("PASS test_markdown_to_gutenberg")
    # Using dummy mock_urlopen since patch isn't executing decorators on direct runs without unittest runner
    # We will let the test runner run it.
