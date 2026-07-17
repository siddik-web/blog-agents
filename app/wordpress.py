"""WordPress API Client and Gutenberg Block Converter.

Handles conversion of markdown content into Gutenberg block-comment HTML and
publishing drafts to local or remote WordPress sites using basic authentication.
"""

from __future__ import annotations

import base64
import json
import re
import urllib.error
import urllib.parse
import urllib.request


def markdown_to_gutenberg(markdown_text: str) -> str:
    """Convert standard markdown text to WordPress Gutenberg block HTML comments."""
    if not markdown_text:
        return ""

    # Normalize newlines
    text = markdown_text.replace("\r\n", "\n")
    # Split by double newlines to find paragraphs/blocks
    blocks = re.split(r'\n{2,}', text)
    
    gutenberg_blocks = []
    
    for block in blocks:
        block = block.strip()
        if not block:
            continue
            
        # Parse block type
        # 1. Heading
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', block)
        if heading_match:
            hashes, content = heading_match.groups()
            level = len(hashes)
            content_html = _parse_inline_markdown(content)
            gutenberg_blocks.append(
                f'<!-- wp:heading {{"level":{level}}} -->\n'
                f'<h{level}>{content_html}</h{level}>\n'
                f'<!-- /wp:heading -->'
            )
            continue
            
        # 2. Blockquote
        if block.startswith('>'):
            # Extract lines and remove the leading '>' and space
            lines = [line.lstrip('> ').strip() for line in block.split('\n')]
            quote_content = " ".join(lines)
            content_html = _parse_inline_markdown(quote_content)
            gutenberg_blocks.append(
                '<!-- wp:quote -->\n'
                f'<blockquote class="wp-block-quote"><p>{content_html}</p></blockquote>\n'
                '<!-- /wp:quote -->'
            )
            continue
            
        # 3. Unordered List (lines starting with - or *)
        if block.startswith('- ') or block.startswith('* '):
            list_items = []
            for line in block.split('\n'):
                line = line.strip()
                if line.startswith('- ') or line.startswith('* '):
                    item_text = line[2:].strip()
                    list_items.append(f'<li>{_parse_inline_markdown(item_text)}</li>')
            
            items_html = "\n".join(list_items)
            gutenberg_blocks.append(
                '<!-- wp:list -->\n'
                f'<ul>\n{items_html}\n</ul>\n'
                '<!-- /wp:list -->'
            )
            continue

        # 4. Ordered List (lines starting with number followed by period)
        if re.match(r'^\d+\.\s+', block):
            list_items = []
            for line in block.split('\n'):
                line = line.strip()
                item_match = re.match(r'^\d+\.\s+(.+)$', line)
                if item_match:
                    item_text = item_match.group(1).strip()
                    list_items.append(f'<li>{_parse_inline_markdown(item_text)}</li>')
            
            items_html = "\n".join(list_items)
            gutenberg_blocks.append(
                '<!-- wp:list {"ordered":true} -->\n'
                f'<ol>\n{items_html}\n</ol>\n'
                '<!-- /wp:list -->'
            )
            continue
            
        # 5. Default Paragraph
        content_html = _parse_inline_markdown(block)
        # If there are internal single newlines, replace them with space
        content_html = content_html.replace('\n', ' ')
        gutenberg_blocks.append(
            '<!-- wp:paragraph -->\n'
            f'<p>{content_html}</p>\n'
            '<!-- /wp:paragraph -->'
        )
        
    return "\n\n".join(gutenberg_blocks)


def _parse_inline_markdown(text: str) -> str:
    """Parse inline markdown tags such as bold, italic, code, and links to HTML."""
    html = text
    
    # 1. Bold: **text** or __text__
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'__(.*?)__', r'<strong>\1</strong>', html)
    
    # 2. Italic: *text* or _text_
    html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)
    html = re.sub(r'_(.*?)_', r'<em>\1</em>', html)
    
    # 3. Inline code: `code`
    html = re.sub(r'`(.*?)`', r'<code>\1</code>', html)
    
    # 4. Links: [anchor](url)
    html = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', html)
    
    return html


def _get_or_create_tag(wp_url: str, headers: dict, tag_name: str) -> int | None:
    """Retrieve tag ID by name, creating it if it doesn't exist."""
    tag_name_encoded = urllib.parse.quote_plus(tag_name)
    search_url = f"{wp_url}/wp-json/wp/v2/tags?search={tag_name_encoded}"
    
    try:
        req = urllib.request.Request(search_url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=8) as response:
            results = json.loads(response.read().decode("utf-8"))
            for term in results:
                if term.get("name", "").lower() == tag_name.lower():
                    return term.get("id")
    except Exception:
        pass
        
    create_url = f"{wp_url}/wp-json/wp/v2/tags"
    payload = {"name": tag_name}
    data = json.dumps(payload).encode("utf-8")
    
    try:
        req = urllib.request.Request(create_url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=8) as response:
            res = json.loads(response.read().decode("utf-8"))
            return res.get("id")
    except urllib.error.HTTPError as e:
        try:
            err_data = json.loads(e.read().decode("utf-8"))
            if err_data.get("code") == "term_exists":
                return err_data.get("data", {}).get("term_id")
        except Exception:
            pass
    except Exception:
        pass
    return None


def _get_or_create_category(wp_url: str, headers: dict, cat_name: str) -> int | None:
    """Retrieve category ID by name, creating it if it doesn't exist."""
    cat_name_encoded = urllib.parse.quote_plus(cat_name)
    search_url = f"{wp_url}/wp-json/wp/v2/categories?search={cat_name_encoded}"
    
    try:
        req = urllib.request.Request(search_url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=8) as response:
            results = json.loads(response.read().decode("utf-8"))
            for term in results:
                if term.get("name", "").lower() == cat_name.lower():
                    return term.get("id")
    except Exception:
        pass
        
    create_url = f"{wp_url}/wp-json/wp/v2/categories"
    payload = {"name": cat_name}
    data = json.dumps(payload).encode("utf-8")
    
    try:
        req = urllib.request.Request(create_url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=8) as response:
            res = json.loads(response.read().decode("utf-8"))
            return res.get("id")
    except urllib.error.HTTPError as e:
        try:
            err_data = json.loads(e.read().decode("utf-8"))
            if err_data.get("code") == "term_exists":
                return err_data.get("data", {}).get("term_id")
        except Exception:
            pass
    except Exception:
        pass
    return None


def publish_to_wordpress(
    wp_url: str,
    username: str,
    app_password: str,
    title: str,
    markdown_content: str,
    excerpt: str,
    slug: str,
    tags: list[str],
    categories: list[str] = None
) -> str:
    """Publish the post content to WordPress as a draft.

    Returns the URL/link of the generated draft.
    """
    wp_url = wp_url.rstrip("/")
    api_url = f"{wp_url}/wp-json/wp/v2/posts"
    
    html_content = markdown_to_gutenberg(markdown_content)
    
    auth_str = f"{username}:{app_password}"
    auth_bytes = auth_str.encode("utf-8")
    auth_base64 = base64.b64encode(auth_bytes).decode("utf-8")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {auth_base64}",
        "User-Agent": "Loop-Engineering-Blog-Agent/1.0"
    }
    
    tag_ids = []
    if tags:
        for tag_name in tags:
            tag_id = _get_or_create_tag(wp_url, headers, tag_name)
            if tag_id:
                tag_ids.append(tag_id)
                
    cat_ids = []
    if categories:
        for cat_name in categories:
            cat_id = _get_or_create_category(wp_url, headers, cat_name)
            if cat_id:
                cat_ids.append(cat_id)
                
    payload = {
        "title": title,
        "content": html_content,
        "status": "draft",
        "excerpt": excerpt,
        "slug": slug,
    }
    if tag_ids:
        payload["tags"] = tag_ids
    if cat_ids:
        payload["categories"] = cat_ids
        
    data = json.dumps(payload).encode("utf-8")
    
    req = urllib.request.Request(api_url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=10) as response:
        res = json.loads(response.read().decode("utf-8"))
        
    return res.get("link")
