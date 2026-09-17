#!/usr/bin/env python3
"""CLI riset kompetitor & tren YouTube.

Contoh pakai:
  python3 scripts/research.py niche-search --query "review skincare" --max 30 --order viewCount --days 30
  python3 scripts/research.py trending --region ID --max 25
  python3 scripts/research.py channel --handle @mrbeast --max-videos 25
  python3 scripts/research.py compare --handles @channel1,@channel2,@channel3
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import analysis
from youtube_api import YouTubeAPIError, YouTubeClient

DATA_DIR = Path(__file__).parent.parent / "data"


def load_dotenv_if_present():
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


def save_json(name: str, payload: dict) -> Path:
    DATA_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = DATA_DIR / f"{name}_{ts}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
    return path


def print_leaderboard(title: str, videos: list[dict], fields=("views", "engagement_rate_pct")):
    print(f"\n== {title} ==")
    for i, v in enumerate(videos, 1):
        extra = "  ".join(f"{f}={v.get(f)}" for f in fields)
        print(f"{i:>2}. {v['title'][:70]:<70} | {extra} | {v['channel_title']}")


def print_freq(title: str, pairs: list[tuple[str, int]]):
    print(f"\n== {title} ==")
    print(", ".join(f"{w}({c})" for w, c in pairs))


def cmd_niche_search(client: YouTubeClient, args):
    videos = client.search_videos(
        query=args.query,
        order=args.order,
        max_results=args.max,
        published_after_days=args.days,
        region_code=args.region,
        video_duration=args.duration,
    )
    if not videos:
        print("Tidak ada hasil. Coba keyword lain atau perbesar rentang --days.")
        return

    print_leaderboard(f"Top video untuk niche '{args.query}'", analysis.views_leaderboard(videos, 15))
    print_freq("Kata paling sering di judul (topik yang sedang laku)", analysis.keyword_frequency(videos))
    print_freq("Tag paling sering dipakai", analysis.tag_frequency(videos))
    print("\n== Format (Shorts vs Long-form) ==")
    print(analysis.duration_mix(videos))
    print("\n== Channel dengan engagement rate tertinggi di hasil ini ==")
    print_leaderboard("Top engagement", analysis.engagement_leaderboard(videos, 10))

    path = save_json(
        f"niche_{args.query.replace(' ', '_')}",
        {
            "query": args.query,
            "order": args.order,
            "videos": videos,
            "keyword_frequency": analysis.keyword_frequency(videos),
            "tag_frequency": analysis.tag_frequency(videos),
            "duration_mix": analysis.duration_mix(videos),
        },
    )
    print(f"\nData tersimpan: {path}")


def cmd_trending(client: YouTubeClient, args):
    videos = client.get_trending(region_code=args.region, category_id=args.category, max_results=args.max)
    print_leaderboard(f"Trending sekarang (region={args.region})", videos)
    print_freq("Kata paling sering di judul trending", analysis.keyword_frequency(videos))
    print("\n== Format (Shorts vs Long-form) di trending ==")
    print(analysis.duration_mix(videos))

    path = save_json(
        f"trending_{args.region}",
        {
            "region": args.region,
            "category": args.category,
            "videos": videos,
            "keyword_frequency": analysis.keyword_frequency(videos),
            "duration_mix": analysis.duration_mix(videos),
        },
    )
    print(f"\nData tersimpan: {path}")


def _resolve_channel(client: YouTubeClient, handle: str | None, channel_id: str | None) -> dict:
    if channel_id:
        ch = client.get_channels([channel_id])
        if not ch:
            raise SystemExit(f"Channel ID tidak ditemukan: {channel_id}")
        return ch[0]
    if handle:
        ch = client.get_channel_by_handle(handle)
        if not ch:
            raise SystemExit(f"Handle tidak ditemukan: {handle}")
        return ch
    raise SystemExit("Berikan --handle @nama atau --id UCxxxx")


def cmd_channel(client: YouTubeClient, args):
    channel = _resolve_channel(client, args.handle, args.id)
    recent = client.get_channel_recent_videos(channel["uploads_playlist_id"], max_results=args.max_videos)
    summary = analysis.channel_strategy_summary(channel, recent)

    print(f"\n== Profil: {channel['title']} ==")
    for k, v in channel.items():
        if k != "description":
            print(f"  {k}: {v}")
    print(f"\n== Ringkasan Strategi ({len(recent)} video terakhir) ==")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print_leaderboard("Video performa terbaik", analysis.views_leaderboard(recent, 10))

    path = save_json(
        f"channel_{channel['title'].replace(' ', '_')}",
        {"channel": channel, "recent_videos": recent, "strategy_summary": summary},
    )
    print(f"\nData tersimpan: {path}")


def cmd_compare(client: YouTubeClient, args):
    handles = [h.strip() for h in (args.handles or "").split(",") if h.strip()]
    ids = [i.strip() for i in (args.ids or "").split(",") if i.strip()]
    if not handles and not ids:
        raise SystemExit("Berikan --handles @a,@b atau --ids UCx,UCy")

    channels = []
    for h in handles:
        ch = client.get_channel_by_handle(h)
        if ch:
            channels.append(ch)
    if ids:
        channels.extend(client.get_channels(ids))

    summaries = []
    for ch in channels:
        recent = client.get_channel_recent_videos(ch["uploads_playlist_id"], max_results=args.max_videos)
        summaries.append(analysis.channel_strategy_summary(ch, recent))

    ranked = analysis.compare_channels(summaries)
    print("\n== Perbandingan Kompetitor (diurutkan dari paling efisien: views per subscriber) ==")
    for i, s in enumerate(ranked, 1):
        print(f"\n#{i} {s['channel']}")
        for k, v in s.items():
            if k != "channel":
                print(f"    {k}: {v}")

    path = save_json("compare", {"channels": ranked})
    print(f"\nData tersimpan: {path}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Riset kompetitor & tren YouTube")
    sub = p.add_subparsers(dest="command", required=True)

    ns = sub.add_parser("niche-search", help="Cari & analisis video berdasarkan niche/keyword")
    ns.add_argument("--query", required=True)
    ns.add_argument("--max", type=int, default=25)
    ns.add_argument("--order", choices=["relevance", "date", "viewCount", "rating"], default="viewCount")
    ns.add_argument("--days", type=int, default=None, help="Hanya video yang publish N hari terakhir")
    ns.add_argument("--region", default=None)
    ns.add_argument("--duration", choices=["short", "medium", "long"], default=None)
    ns.set_defaults(func=cmd_niche_search)

    tr = sub.add_parser("trending", help="Lihat video trending realtime")
    tr.add_argument("--region", default="ID")
    tr.add_argument("--category", default=None, help="ID kategori YouTube, kosongkan untuk semua")
    tr.add_argument("--max", type=int, default=25)
    tr.set_defaults(func=cmd_trending)

    ch = sub.add_parser("channel", help="Analisis performa & strategi satu channel")
    ch.add_argument("--handle", default=None, help="contoh: @namachannel")
    ch.add_argument("--id", default=None, help="Channel ID (UCxxxx)")
    ch.add_argument("--max-videos", type=int, default=20)
    ch.set_defaults(func=cmd_channel)

    cmp_ = sub.add_parser("compare", help="Bandingkan beberapa channel kompetitor sekaligus")
    cmp_.add_argument("--handles", default=None, help="@a,@b,@c")
    cmp_.add_argument("--ids", default=None, help="UCxxx,UCyyy")
    cmp_.add_argument("--max-videos", type=int, default=20)
    cmp_.set_defaults(func=cmd_compare)

    return p


def main():
    load_dotenv_if_present()
    parser = build_parser()
    args = parser.parse_args()
    try:
        client = YouTubeClient()
        args.func(client, args)
    except YouTubeAPIError as e:
        print(f"Error API: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
