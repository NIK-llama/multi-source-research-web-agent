"""
agent/snapshot_operations.py

BrightData snapshot polling and download helpers.
These are low-level infrastructure utilities — no business logic here.
"""

import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()


def _safe_print(text: str) -> None:
    """Print text, falling back to ASCII if the terminal can't handle Unicode."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode("ascii"))


def poll_snapshot_status(
    snapshot_id: str,
    max_attempts: int = 120,
    delay: int = 5,
) -> bool:
    """
    Poll BrightData until the snapshot is ready or failed.

    Args:
        snapshot_id:  The snapshot ID returned by the trigger API.
        max_attempts: Maximum number of polling iterations before giving up.
        delay:        Seconds to wait between polling attempts.

    Returns:
        True if the snapshot is ready, False otherwise.
    """
    api_key = os.getenv("BRIGHTDATA_API_KEY")
    if not api_key:
        _safe_print("⚠️  BRIGHTDATA_API_KEY is not configured.")
        return False

    progress_url = f"https://api.brightdata.com/datasets/v3/progress/{snapshot_id}"
    headers = {"Authorization": f"Bearer {api_key}"}

    for attempt in range(max_attempts):
        try:
            _safe_print(
                f"⏳ Checking snapshot progress… (attempt {attempt + 1}/{max_attempts})"
            )

            response = requests.get(progress_url, headers=headers, timeout=30)
            if response.status_code in (401, 403):
                _safe_print(f"❌ BrightData authorization failed ({response.status_code}): {response.text[:120]}")
                return False
            if response.status_code == 404:
                _safe_print(f"❌ Snapshot ID '{snapshot_id}' not found (404).")
                return False

            response.raise_for_status()

            progress_data = response.json()
            status = progress_data.get("status")

            if status == "ready":
                _safe_print("✅ Snapshot completed!")
                return True
            elif status == "failed":
                _safe_print("❌ Snapshot failed")
                return False
            elif status == "running":
                _safe_print("🔄 Still processing…")
                time.sleep(delay)
            else:
                _safe_print(f"❓ Unknown status: {status}")
                time.sleep(delay)

        except (requests.RequestException, ValueError) as exc:
            _safe_print(f"⚠️  Error checking progress: {exc}")
            time.sleep(delay)

    _safe_print("⏰ Timeout waiting for snapshot completion")
    return False


def download_snapshot(
    snapshot_id: str,
    fmt: str = "json",
) -> list[dict] | None:
    """
    Download a completed BrightData snapshot.

    Args:
        snapshot_id: The snapshot ID to download.
        fmt:         Response format (default: "json").

    Returns:
        Parsed JSON list of records, or None on error.
    """
    api_key = os.getenv("BRIGHTDATA_API_KEY")
    if not api_key:
        _safe_print("⚠️  BRIGHTDATA_API_KEY is not configured.")
        return None

    download_url = (
        f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}?format={fmt}"
    )
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        _safe_print("📥 Downloading snapshot data…")

        response = requests.get(download_url, headers=headers, timeout=60)
        if response.status_code in (401, 403):
            _safe_print(f"❌ BrightData authorization failed on download ({response.status_code}).")
            return None

        response.raise_for_status()

        data = response.json()
        if isinstance(data, dict):
            if "error" in data or ("message" in data and "status" in data):
                _safe_print(f"❌ Snapshot download returned error payload: {data}")
                return None
            data = [data]
        elif not isinstance(data, list):
            _safe_print(f"❌ Unexpected snapshot data type: {type(data)}")
            return None

        # Filter out BrightData error records (e.g. {"error": "No results", "error_code": "dead_page"})
        valid_items = [
            item for item in data
            if isinstance(item, dict) and not item.get("error")
        ]
        error_items = [
            item for item in data
            if isinstance(item, dict) and item.get("error")
        ]

        if error_items and not valid_items:
            err_msg = error_items[0].get("error", "No results found")
            err_code = error_items[0].get("error_code", "")
            code_str = f" ({err_code})" if err_code else ""
            _safe_print(f"⚠️  Snapshot completed: BrightData reported '{err_msg}'{code_str}")
            return []

        if not valid_items:
            _safe_print("ℹ️  Snapshot data is empty.")
            return []

        _safe_print(f"🎉 Successfully downloaded {len(valid_items)} item(s)")
        return valid_items

    except (requests.RequestException, ValueError) as exc:
        _safe_print(f"❌ Error downloading snapshot: {exc}")
        return None

