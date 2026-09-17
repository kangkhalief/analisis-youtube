"""Turns raw video/channel data into competitor-research insights."""
from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from typing import Any

STOPWORDS_ID_EN = {
    "yang", "dan", "di", "ke", "dari", "untuk", "dengan", "ini", "itu", "ada",
    "the", "a", "an", "to", "of", "in", "on", "for", "and", "is", "are",
    "video", "official", "part", "vs",
}


def keyword_frequency(videos: list[dict[str, Any]], top_n: int = 20) -> list[tuple[str, int]]:
    """Kata paling sering muncul di judul video — indikasi topik yang sedang laku di niche ini."""
    counter: Counter[str] = Counter()
    for v in videos:
        words = re.findall(r"[a-zA-Z0-9À-ɏ]+", (v.get("title") or "").lower())
        for w in words:
            if len(w) > 2 and w not in STOPWORDS_ID_EN:
                counter[w] += 1
    return counter.most_common(top_n)


def tag_frequency(videos: list[dict[str, Any]], top_n: int = 20) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    for v in videos:
        for t in v.get("tags", []) or []:
            counter[t.lower()] += 1
    return counter.most_common(top_n)


def upload_day_distribution(videos: list[dict[str, Any]]) -> dict[str, int]:
    """Distribusi hari upload (Senin-Minggu) — cari pola kapan kompetitor rilis konten."""
    days = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    counter = Counter()
    for v in videos:
        ts = v.get("published_at")
        if not ts:
            continue
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        counter[days[dt.weekday()]] += 1
    return {d: counter.get(d, 0) for d in days}


def duration_mix(videos: list[dict[str, Any]]) -> dict[str, Any]:
    shorts = sum(1 for v in videos if v.get("is_short"))
    long_form = len(videos) - shorts
    return {
        "shorts_count": shorts,
        "long_form_count": long_form,
        "shorts_pct": round(shorts / len(videos) * 100, 1) if videos else 0,
    }


def engagement_leaderboard(videos: list[dict[str, Any]], top_n: int = 10) -> list[dict[str, Any]]:
    return sorted(videos, key=lambda v: v.get("engagement_rate_pct", 0), reverse=True)[:top_n]


def views_leaderboard(videos: list[dict[str, Any]], top_n: int = 10) -> list[dict[str, Any]]:
    return sorted(videos, key=lambda v: v.get("views", 0), reverse=True)[:top_n]


def channel_strategy_summary(channel: dict[str, Any], recent_videos: list[dict[str, Any]]) -> dict[str, Any]:
    """Ringkasan strategi satu channel: frekuensi upload, format favorit, performa relatif ke subscriber."""
    if not recent_videos:
        return {"channel": channel.get("title"), "note": "Tidak ada video untuk dianalisis."}

    sorted_videos = sorted(recent_videos, key=lambda v: v.get("published_at") or "", reverse=True)
    dates = [
        datetime.fromisoformat(v["published_at"].replace("Z", "+00:00"))
        for v in sorted_videos
        if v.get("published_at")
    ]
    span_days = (dates[0] - dates[-1]).days if len(dates) > 1 else 0
    upload_freq_per_week = round(len(dates) / (span_days / 7), 2) if span_days > 0 else None

    avg_views = round(sum(v["views"] for v in recent_videos) / len(recent_videos), 1)
    avg_engagement = round(
        sum(v["engagement_rate_pct"] for v in recent_videos) / len(recent_videos), 3
    )
    subs = channel.get("subscribers")
    views_per_sub = round(avg_views / subs, 3) if subs else None

    return {
        "channel": channel.get("title"),
        "channel_id": channel.get("channel_id"),
        "subscribers": subs,
        "videos_analyzed": len(recent_videos),
        "upload_frequency_per_week": upload_freq_per_week,
        "avg_views_recent": avg_views,
        "avg_engagement_rate_pct": avg_engagement,
        "views_per_subscriber": views_per_sub,
        "duration_mix": duration_mix(recent_videos),
        "upload_days": upload_day_distribution(recent_videos),
        "top_video": views_leaderboard(recent_videos, 1)[0] if recent_videos else None,
        "top_titles_keywords": keyword_frequency(recent_videos, 10),
    }


def compare_channels(summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Urutkan channel berdasarkan efisiensi (views per subscriber) untuk lihat siapa paling efektif."""
    return sorted(
        summaries,
        key=lambda s: (s.get("views_per_subscriber") or 0),
        reverse=True,
    )
