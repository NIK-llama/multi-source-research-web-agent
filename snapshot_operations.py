import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()


def _safe_print(text: str):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode("ascii"))


def poll_snapshot_status(
    snapshot_id: str, max_attempts: int = 120, delay: int = 5
) -> bool:
    api_key = os.getenv("BRIGHTDATA_API_KEY")
    if not api_key:
        raise RuntimeError("BRIGHTDATA_API_KEY is not configured.")

    progress_url = f"https://api.brightdata.com/datasets/v3/progress/{snapshot_id}"
    headers = {"Authorization": f"Bearer {api_key}"}

    for attempt in range(max_attempts):
        try:
            _safe_print(
                f"⏳ Checking snapshot progress... (attempt {attempt + 1}/{max_attempts})"
            )

            response = requests.get(progress_url, headers=headers)
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
                _safe_print("🔄 Still processing...")
                time.sleep(delay)
            else:
                _safe_print(f"❓ Unknown status: {status}")
                time.sleep(delay)

        except requests.RequestException as e:
            _safe_print(f"⚠️ Error checking progress: {e}")
            time.sleep(delay)

    _safe_print("⏰ Timeout waiting for snapshot completion")
    return False


def download_snapshot(
    snapshot_id: str, format: str = "json"
) -> list[dict[any, any]] | None:
    api_key = os.getenv("BRIGHTDATA_API_KEY")
    if not api_key:
        raise RuntimeError("BRIGHTDATA_API_KEY is not configured.")

    download_url = (
        f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}?format={format}"
    )
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        _safe_print("📥 Downloading snapshot data...")

        response = requests.get(download_url, headers=headers)
        response.raise_for_status()

        data = response.json()
        _safe_print(
            f"🎉 Successfully downloaded {len(data) if isinstance(data, list) else 1} items"
        )

        return data

    except requests.RequestException as e:
        _safe_print(f"❌ Error downloading snapshot: {e}")
        return None
