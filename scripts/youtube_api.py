"""Thin wrapper around the YouTube Data API v3 used by the research CLI."""
from __future__ import annotations

import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

BASE_URL = "https://www.googleapis.com/youtube/v3"


class YouTubeAPIError(RuntimeError):
    pass


class YouTubeClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("YOUTUBE_API_KEY")
        if not self.api_key:
            raise YouTubeAPIError(
                "YOUTUBE_API_KEY tidak ditemukan. Set di file .env atau environment variable."
            )
        self.session = requests.Session()

    def _get(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        params = {**params, "key": self.api_key}
        resp = self.session.get(f"{BASE_URL}/{endpoint}", params=params, timeout=30)
        if resp.status_code != 200:
            try:
                detail = resp.json().get("error", {}).get("message", resp.text)
            except ValueError:
                detail = resp.text
            raise YouTubeAPIError(f"{endpoint} gagal ({resp.status_code}): {detail}")
        return resp.json()

    # ---------- Search ----------

    def search_videos(
        self,
        query: str,
        order: str = "relevance",
        max_results: int = 25,
        published_after_days: int | None = None,
        region_code: str | None = None,
        video_duration: str | None = None,
    ) -> list[dict[str, Any]]:
        """Cari video berdasarkan keyword/niche. order: relevance|date|viewCount|rating"""
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "order": order,
            "maxResults": min(max_results, 50),
        }
        if region_code:
            params["regionCode"] = region_code
        if video_duration:
            params["videoDuration"] = video_duration  # short|medium|long
        if published_after_days:
            after = datetime.now(timezone.utc) - timedelta(days=published_after_days)
            params["publishedAfter"] = after.strftime("%Y-%m-%dT%H:%M:%SZ")

        items: list[dict[str, Any]] = []
        page_token = None
        while len(items) < max_results:
            if page_token:
                params["pageToken"] = page_token
            data = self._get("search", params)
            items.extend(data.get("items", []))
            page_token = data.get("nextPageToken")
            if not page_token:
                break
        video_ids = [it["id"]["videoId"] for it in items[:max_results]]
        return self.get_videos(video_ids)

    def search_channels(self, query: str, max_results: int = 15) -> list[dict[str, Any]]:
        params = {
            "part": "snippet",
            "q": query,
            "type": "channel",
            "maxResults": min(max_results, 50),
        }
        data = self._get("search", params)
        channel_ids = [it["id"]["channelId"] for it in data.get("items", [])]
        return self.get_channels(channel_ids)

    # ---------- Videos ----------

    def get_videos(self, video_ids: list[str]) -> list[dict[str, Any]]:
        if not video_ids:
            return []
        results: list[dict[str, Any]] = []
        for i in range(0, len(video_ids), 50):
            chunk = video_ids[i : i + 50]
            data = self._get(
                "videos",
                {
                    "part": "snippet,statistics,contentDetails",
                    "id": ",".join(chunk),
                },
            )
            results.extend(data.get("items", []))
        return [self._flatten_video(v) for v in results]

    @staticmethod
    def _flatten_video(v: dict[str, Any]) -> dict[str, Any]:
        snippet = v.get("snippet", {})
        stats = v.get("statistics", {})
        content = v.get("contentDetails", {})
        views = int(stats.get("viewCount", 0))
        likes = int(stats.get("likeCount", 0))
        comments = int(stats.get("commentCount", 0))
        duration_sec = _parse_duration(content.get("duration", "PT0S"))
        engagement_rate = round(((likes + comments) / views) * 100, 3) if views else 0.0
        thumbnails = snippet.get("thumbnails", {})
        thumbnail = (
            thumbnails.get("medium") or thumbnails.get("high") or thumbnails.get("default") or {}
        ).get("url")
        return {
            "video_id": v.get("id"),
            "title": snippet.get("title"),
            "channel_id": snippet.get("channelId"),
            "channel_title": snippet.get("channelTitle"),
            "published_at": snippet.get("publishedAt"),
            "views": views,
            "likes": likes,
            "comments": comments,
            "engagement_rate_pct": engagement_rate,
            "duration_sec": duration_sec,
            "is_short": duration_sec > 0 and duration_sec <= 60,
            "tags": snippet.get("tags", []),
            "category_id": snippet.get("categoryId"),
            "thumbnail": thumbnail,
            "description": (snippet.get("description") or "")[:500],
            "url": f"https://www.youtube.com/watch?v={v.get('id')}",
        }

    # ---------- Channels ----------

    def get_channels(self, channel_ids: list[str]) -> list[dict[str, Any]]:
        if not channel_ids:
            return []
        results: list[dict[str, Any]] = []
        for i in range(0, len(channel_ids), 50):
            chunk = channel_ids[i : i + 50]
            data = self._get(
                "channels",
                {
                    "part": "snippet,statistics,contentDetails,brandingSettings",
                    "id": ",".join(chunk),
                },
            )
            results.extend(data.get("items", []))
        return [self._flatten_channel(c) for c in results]

    def get_channel_by_handle(self, handle: str) -> dict[str, Any] | None:
        handle = handle if handle.startswith("@") else f"@{handle}"
        data = self._get(
            "channels",
            {"part": "snippet,statistics,contentDetails,brandingSettings", "forHandle": handle},
        )
        items = data.get("items", [])
        return self._flatten_channel(items[0]) if items else None

    @staticmethod
    def _flatten_channel(c: dict[str, Any]) -> dict[str, Any]:
        snippet = c.get("snippet", {})
        stats = c.get("statistics", {})
        content = c.get("contentDetails", {})
        subs = int(stats.get("subscriberCount", 0)) if not stats.get("hiddenSubscriberCount") else None
        views = int(stats.get("viewCount", 0))
        video_count = int(stats.get("videoCount", 0))
        return {
            "channel_id": c.get("id"),
            "title": snippet.get("title"),
            "description": (snippet.get("description") or "")[:300],
            "published_at": snippet.get("publishedAt"),
            "country": snippet.get("country"),
            "subscribers": subs,
            "total_views": views,
            "video_count": video_count,
            "avg_views_per_video": round(views / video_count, 1) if video_count else 0,
            "uploads_playlist_id": content.get("relatedPlaylists", {}).get("uploads"),
            "url": f"https://www.youtube.com/channel/{c.get('id')}",
        }

    def get_channel_recent_videos(self, uploads_playlist_id: str, max_results: int = 20) -> list[dict[str, Any]]:
        video_ids: list[str] = []
        page_token = None
        while len(video_ids) < max_results:
            params = {
                "part": "contentDetails",
                "playlistId": uploads_playlist_id,
                "maxResults": min(50, max_results - len(video_ids)),
            }
            if page_token:
                params["pageToken"] = page_token
            data = self._get("playlistItems", params)
            video_ids.extend(
                item["contentDetails"]["videoId"] for item in data.get("items", [])
            )
            page_token = data.get("nextPageToken")
            if not page_token:
                break
        return self.get_videos(video_ids[:max_results])

    # ---------- Trending ----------

    def get_trending(
        self, region_code: str = "ID", category_id: str | None = None, max_results: int = 25
    ) -> list[dict[str, Any]]:
        params = {
            "part": "snippet,statistics,contentDetails",
            "chart": "mostPopular",
            "regionCode": region_code,
            "maxResults": min(max_results, 50),
        }
        if category_id:
            params["videoCategoryId"] = category_id
        data = self._get("videos", params)
        return [self._flatten_video(v) for v in data.get("items", [])]


def _parse_duration(iso_duration: str) -> int:
    """Parse ISO8601 duration (e.g. PT1H2M3S) into total seconds."""
    match = re.match(
        r"P(?:(?P<days>\d+)D)?T?(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?",
        iso_duration or "",
    )
    if not match:
        return 0
    parts = match.groupdict()
    days = int(parts["days"] or 0)
    hours = int(parts["hours"] or 0)
    minutes = int(parts["minutes"] or 0)
    seconds = int(parts["seconds"] or 0)
    return days * 86400 + hours * 3600 + minutes * 60 + seconds
