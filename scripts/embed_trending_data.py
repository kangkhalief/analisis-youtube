#!/usr/bin/env python3
"""Suntik data/public_trending_snapshot.json ke dalam dashboard/dashboard.html.

Dijalankan setelah fetch_trending_snapshot.py, sebelum dashboard dipublish ulang
sebagai Artifact. Memisahkan "ambil data" dan "suntik ke halaman" supaya masing-masing
bisa diuji/dijalankan terpisah.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SNAPSHOT_PATH = ROOT / "data" / "public_trending_snapshot.json"
DASHBOARD_PATH = ROOT / "dashboard" / "dashboard.html"

PATTERN = re.compile(
    r'(<script id="trending-data" type="application/json">)(.*?)(</script>)',
    re.DOTALL,
)


def main():
    if not SNAPSHOT_PATH.exists():
        print(f"Snapshot tidak ditemukan: {SNAPSHOT_PATH}. Jalankan fetch_trending_snapshot.py dulu.", file=sys.stderr)
        sys.exit(1)

    snapshot = json.loads(SNAPSHOT_PATH.read_text())
    payload = json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"))
    # Hindari '</script>' tidak sengaja menutup tag lebih awal di dalam JSON string.
    payload = payload.replace("</", "<\\/")

    html = DASHBOARD_PATH.read_text()
    if not PATTERN.search(html):
        print("Marker <script id=\"trending-data\"> tidak ditemukan di dashboard.html", file=sys.stderr)
        sys.exit(1)

    new_html = PATTERN.sub(lambda m: m.group(1) + payload + m.group(3), html, count=1)
    DASHBOARD_PATH.write_text(new_html)
    print(f"Data trending ({len(payload):,} bytes) berhasil disuntik ke {DASHBOARD_PATH}")


if __name__ == "__main__":
    main()
