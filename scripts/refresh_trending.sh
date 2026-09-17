#!/bin/bash
# Refresh data trending publik: ambil snapshot terbaru + suntik ke dashboard.html.
# Setelah ini selesai, dashboard.html perlu dipublish ulang (dilakukan Claude lewat Artifact tool).
set -e
cd "$(dirname "$0")/.."
python3 scripts/fetch_trending_snapshot.py
python3 scripts/embed_trending_data.py
