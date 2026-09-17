#!/usr/bin/env python3
"""Ambil snapshot trending untuk beberapa negara & kategori, simpan sebagai satu JSON ringkas.

Dipakai untuk mengisi dashboard publik (dashboard/dashboard.html) tanpa dashboard
perlu memanggil YouTube API langsung dari browser (API key tetap di server/lokal).

Jalankan manual:
  python3 scripts/fetch_trending_snapshot.py

Atau dipanggil oleh scripts/build_public_dashboard.py yang juga meng-embed hasilnya
ke dashboard.html.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from youtube_api import YouTubeAPIError, YouTubeClient  # noqa: E402

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_PATH = DATA_DIR / "public_trending_snapshot.json"

COUNTRIES = {
    "ID": "Indonesia",
    "US": "Amerika Serikat",
    "GB": "Inggris",
    "IN": "India",
    "JP": "Jepang",
    "KR": "Korea Selatan",
}

CATEGORIES = {
    "all": "Semua Kategori",
    "20": "Gaming",
    "10": "Musik",
    "23": "Komedi",
    "24": "Hiburan",
    "22": "Blog & Orang",
    "17": "Olahraga",
    "26": "Cara & Gaya",
    "28": "Sains & Teknologi",
    "25": "Berita & Politik",
}

VIDEOS_PER_BUCKET = 10


def load_dotenv_if_present():
    import os

    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


def slim_video(v: dict) -> dict:
    return {
        "id": v["video_id"],
        "t": v["title"],
        "c": v["channel_title"],
        "v": v["views"],
        "e": v["engagement_rate_pct"],
        "s": v["is_short"],
        "u": v["url"],
        "th": v.get("thumbnail"),
        "dur": v.get("duration_sec", 0),
        "pub": v.get("published_at"),
        "desc": (v.get("description") or "")[:300],
    }


def fetch_snapshot(client: YouTubeClient) -> dict:
    countries_out = {}
    for cc, cname in COUNTRIES.items():
        categories_out = {}
        for cat_id, cat_label in CATEGORIES.items():
            try:
                videos = client.get_trending(
                    region_code=cc,
                    category_id=None if cat_id == "all" else cat_id,
                    max_results=VIDEOS_PER_BUCKET,
                )
            except YouTubeAPIError as e:
                print(f"  [!] {cc}/{cat_label}: {e}", file=sys.stderr)
                videos = []
            categories_out[cat_id] = [slim_video(v) for v in videos]
            print(f"  {cc} / {cat_label}: {len(videos)} video")
        countries_out[cc] = {"name": cname, "categories": categories_out}
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "countries": countries_out,
        "category_labels": CATEGORIES,
        "country_names": COUNTRIES,
    }


def main():
    load_dotenv_if_present()
    client = YouTubeClient()
    print("Mengambil snapshot trending...")
    snapshot = fetch_snapshot(client)
    DATA_DIR.mkdir(exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2))
    print(f"\nSnapshot tersimpan: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
