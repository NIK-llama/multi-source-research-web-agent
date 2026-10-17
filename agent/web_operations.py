"""
agent/web_operations.py

External API wrappers for Google/Bing SERP search and Reddit data retrieval.
All network calls go through BrightData's proxy/dataset APIs.
"""

import os
import time
from urllib.parse import quote_plus

import requests
from dotenv import load_dotenv

from agent.snapshot_operations import (
    _safe_print,
    download_snapshot,
    poll_snapshot_status,
)

load_dotenv()

# ── Constants ────────────────────────────────────────────────────────────────
_REDDIT_SEARCH_DATASET_ID = "gd_lvz8ah06191smkebj4"
_REDDIT_POSTS_DATASET_ID  = "gd_lvzdpsdlw09j6t702"
_BRIGHTDATA_REQUEST_URL   = "https://api.brightdata.com/request"
_BRIGHTDATA_TRIGGER_URL   = "https://api.brightdata.com/datasets/v3/trigger"


# ── Internal helpers ─────────────────────────────────────────────────────────

def _get_auth_headers() -> dict[str, str]:
    """Build BrightData authorization headers from the environment."""
    api_key = os.getenv("BRIGHTDATA_API_KEY")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _make_api_request(url: str, max_retries: int = 3, **kwargs) -> dict | None:
    """
    POST to a BrightData endpoint with automatic retry on transient errors.

    Args:
        url:         Endpoint URL.
        max_retries: Number of attempts before giving up.
        **kwargs:    Extra keyword arguments forwarded to ``requests.post``.

    Returns:
        Parsed JSON response dict, or None on failure.
    """
    api_key = os.getenv("BRIGHTDATA_API_KEY")
    if not api_key:
        _safe_print("⚠️  BRIGHTDATA_API_KEY is not configured in environment.")
        return None

    headers = _get_auth_headers()

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(url, headers=headers, timeout=30, **kwargs)
            if response.status_code in (401, 403):
                _safe_print(f"❌ BrightData authentication failed ({response.status_code}): {response.text[:120]}")
                return None

            response.raise_for_status()

            if not response.text or not response.text.strip():
                if attempt < max_retries:
                    time.sleep(1.5)
                    continue
                _safe_print(f"API request returned empty response after {max_retries} attempts.")
                return None

            return response.json()

        except requests.exceptions.JSONDecodeError as exc:
            if attempt < max_retries:
                time.sleep(1.5)
                continue
            _safe_print(f"API request failed to decode JSON: {exc}")
            return None

        except requests.exceptions.RequestException as exc:
            if attempt < max_retries:
                time.sleep(1.5)
                continue
            _safe_print(f"API request failed: {exc}")
            return None

    return None


def _trigger_and_download_snapshot(
    trigger_url: str,
    params: dict,
    data: list,
    operation_name: str = "operation",
    max_attempts: int = 120,
) -> list | None:
    """
    Trigger a BrightData dataset job and wait for the snapshot to be ready.

    Args:
        trigger_url:    BrightData trigger endpoint.
        params:         Query parameters for the trigger request.
        data:           JSON body for the trigger request.
        operation_name: Human-readable label used in log messages.
        max_attempts:   Passed directly to :func:`poll_snapshot_status`.

    Returns:
        Raw snapshot data list, or None on error.
    """
    trigger_result = _make_api_request(trigger_url, params=params, json=data)
    if not trigger_result or not isinstance(trigger_result, dict):
        return None

    snapshot_id = trigger_result.get("snapshot_id")
    if not snapshot_id:
        _safe_print(f"⚠️  No snapshot_id returned for {operation_name}")
        return None

    if not poll_snapshot_status(snapshot_id, max_attempts=max_attempts):
        return None

    return download_snapshot(snapshot_id)


# ── Public API ───────────────────────────────────────────────────────────────

def serp_search(query: str, engine: str = "google") -> dict | None:
    """
    Perform a SERP search via BrightData and return organic results.

    Args:
        query:  The search query string.
        engine: ``"google"`` or ``"bing"``.

    Returns:
        Dict with ``"knowledge"`` and ``"organic"`` keys, or None on error.

    Raises:
        ValueError: If ``engine`` is not ``"google"`` or ``"bing"``.
    """
    if not query or not query.strip():
        _safe_print(f"⚠️  Empty search query provided for {engine}")
        return None


    engine_urls = {
        "google": "https://www.google.com/search",
        "bing":   "https://www.bing.com/search",
    }
    if engine not in engine_urls:
        raise ValueError(f"Unknown engine '{engine}'. Choose 'google' or 'bing'.")

    payload = {
        "zone":   "ai_agent",
        "url":    f"{engine_urls[engine]}?q={quote_plus(query.strip())}&brd_json=1",
        "format": "raw",
    }

    full_response = _make_api_request(_BRIGHTDATA_REQUEST_URL, json=payload)
    if not full_response or not isinstance(full_response, dict):
        return None

    return {
        "knowledge": full_response.get("knowledge", {}),
        "organic":   full_response.get("organic", []),
    }


def reddit_search_api(
    keyword: str,
    date: str = "All time",
    sort_by: str = "Hot",
    num_of_posts: int = 20,
) -> dict | None:
    """
    Search Reddit for posts matching a keyword via BrightData.

    Args:
        keyword:      Search term.
        date:         Date filter (e.g. ``"All time"``, ``"Past week"``).
        sort_by:      Sort order (e.g. ``"Hot"``, ``"New"``, ``"Top"``).
        num_of_posts: Maximum number of posts to retrieve.

    Returns:
        Dict with ``"parsed_data"`` (list of title/url dicts) and
        ``"total_found"`` (int), or None on error.
    """
    if not keyword or not keyword.strip():
        return None

    params = {
        "dataset_id":    _REDDIT_SEARCH_DATASET_ID,
        "include_errors": "true",
        "type":           "discover_new",
        "discover_by":    "keyword",
    }
    data = [
        {
            "keyword":      keyword.strip(),
            "date":         date,
            "sort_by":      sort_by,
            "num_of_posts": num_of_posts,
        }
    ]

    raw_data = _trigger_and_download_snapshot(
        _BRIGHTDATA_TRIGGER_URL, params, data, operation_name="reddit search"
    )
    if not raw_data:
        return None

    parsed_data: list[dict[str, str]] = []
    if isinstance(raw_data, list):
        for post in raw_data:
            if isinstance(post, dict):
                title = (post.get("title") or "").strip()
                url = (post.get("url") or "").strip()
                if url and not url.startswith("http"):
                    url = f"https://www.reddit.com{url}" if url.startswith("/") else f"https://www.reddit.com/{url}"
                if url:
                    parsed_data.append({"title": title or "Untitled", "url": url})

    return {"parsed_data": parsed_data, "total_found": len(parsed_data)}


def reddit_post_retrieval(
    urls: list[str],
    days_back: int = 10,
    load_all_replies: bool = False,
    comment_limit: str = "",
) -> dict | None:
    """
    Retrieve comments for a list of Reddit post URLs via BrightData.

    Args:
        urls:             List of Reddit post URLs to fetch.
        days_back:        How many days of comments to retrieve.
        load_all_replies: Whether to recursively load all nested replies.
        comment_limit:    Optional cap on the number of comments returned.

    Returns:
        Dict with ``"comments"`` (list) and ``"total_found"`` (int),
        or None on error.
    """
    if not urls:
        return None

    # Clean and normalize URLs to absolute URLs
    clean_urls: list[str] = []
    for raw_u in urls:
        if isinstance(raw_u, str) and raw_u.strip():
            u = raw_u.strip()
            if not u.startswith("http"):
                u = f"https://www.reddit.com{u}" if u.startswith("/") else f"https://www.reddit.com/{u}"
            if u not in clean_urls:
                clean_urls.append(u)

    if not clean_urls:
        return None

    params = {
        "dataset_id":     _REDDIT_POSTS_DATASET_ID,
        "include_errors": "true",
    }
    data = [
        {
            "url":              url,
            "days_back":        days_back,
            "load_all_replies": load_all_replies,
            "comment_limit":    comment_limit,
        }
        for url in clean_urls
    ]

    raw_data = _trigger_and_download_snapshot(
        _BRIGHTDATA_TRIGGER_URL,
        params,
        data,
        operation_name="reddit comments",
        max_attempts=30,
    )
    if not raw_data:
        return None

    parsed_comments: list[dict[str, str]] = []
    if isinstance(raw_data, list):
        for comment in raw_data:
            if isinstance(comment, dict):
                content = (
                    comment.get("comment")
                    or comment.get("body")
                    or comment.get("text")
                    or ""
                )
                if content and isinstance(content, str) and content.strip():
                    parsed_comments.append({
                        "comment_id": str(comment.get("comment_id") or comment.get("id") or ""),
                        "content":    content.strip(),
                        "date":       str(comment.get("date_posted") or comment.get("created_utc") or ""),
                    })

    return {"comments": parsed_comments, "total_found": len(parsed_comments)}

