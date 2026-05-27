# backend/app/services/import_pipeline/adapters/youtube.py
"""YouTube Data API v3 adapter"""
import httpx
import structlog
from dataclasses import dataclass, field
from typing import Optional

logger = structlog.get_logger()
YT_BASE = "https://www.googleapis.com/youtube/v3"


@dataclass
class YouTubeVideo:
    video_id: str
    title: str
    description: str
    channel: str
    published_at: str
    url: str
    duration: Optional[str] = None
    tags: list[str] = field(default_factory=list)


async def yt_api_get(path: str, params: dict, api_key: str) -> dict:
    params["key"] = api_key
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{YT_BASE}{path}", params=params)
        resp.raise_for_status()
        return resp.json()


def youtube_item_to_video(item: dict) -> YouTubeVideo:
    snippet = item.get("snippet", {})
    video_id = item.get("id", {}).get("videoId", "") or item.get("snippet", {}).get("resourceId", {}).get("videoId", "")
    return YouTubeVideo(
        video_id=video_id,
        title=snippet.get("title", ""),
        description=snippet.get("description", "")[:1000],
        channel=snippet.get("channelTitle", ""),
        published_at=snippet.get("publishedAt", ""),
        url=f"https://www.youtube.com/watch?v={video_id}",
        tags=snippet.get("tags", []),
    )


async def import_liked_videos(api_key: str, max_results: int = 50) -> list[YouTubeVideo]:
    """高評価動画リストを取得（OAuth不要・APIキーのみ）"""
    if not api_key:
        raise ValueError("YOUTUBE_API_KEY is not set")

    results: list[YouTubeVideo] = []
    page_token: Optional[str] = None
    fetched = 0

    while fetched < max_results:
        params: dict = {
            "part": "snippet",
            "myRating": "like",
            "maxResults": min(50, max_results - fetched),
        }
        if page_token:
            params["pageToken"] = page_token

        data = await yt_api_get("/videos", params, api_key)

        for item in data.get("items", []):
            results.append(youtube_item_to_video(item))

        fetched += len(data.get("items", []))
        page_token = data.get("nextPageToken")

        if not page_token:
            break

    logger.info("youtube_liked_imported", count=len(results))
    return results


async def import_playlist(playlist_id: str, api_key: str, max_results: int = 50) -> list[YouTubeVideo]:
    results: list[YouTubeVideo] = []
    page_token: Optional[str] = None
    fetched = 0

    while fetched < max_results:
        params: dict = {
            "part": "snippet",
            "playlistId": playlist_id,
            "maxResults": min(50, max_results - fetched),
        }
        if page_token:
            params["pageToken"] = page_token

        data = await yt_api_get("/playlistItems", params, api_key)

        for item in data.get("items", []):
            results.append(youtube_item_to_video(item))

        fetched += len(data.get("items", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            break

    logger.info("youtube_playlist_imported", playlist_id=playlist_id, count=len(results))
    return results
