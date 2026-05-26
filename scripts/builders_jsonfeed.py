#!/usr/bin/env python3
"""Convert follow-builders JSON snapshots into a JSON Feed for TrendRadar."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


SOURCES = {
    "x": "https://raw.githubusercontent.com/zarazhangrui/follow-builders/main/feed-x.json",
    "podcasts": "https://raw.githubusercontent.com/zarazhangrui/follow-builders/main/feed-podcasts.json",
    "blogs": "https://raw.githubusercontent.com/zarazhangrui/follow-builders/main/feed-blogs.json",
}


def fetch_json(url: str, timeout: int = 30) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": "dailyinput-builders-feed/1.0"})
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def compact(value: str | None, limit: int) -> str:
    text = " ".join((value or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def is_recent(value: str | None, cutoff: datetime) -> bool:
    published = parse_datetime(value)
    return published is None or published >= cutoff


def add_x_items(data: dict[str, Any], items: list[dict[str, Any]], cutoff: datetime) -> None:
    for builder in data.get("x", []):
        name = builder.get("name") or builder.get("handle") or "Builder"
        handle = builder.get("handle") or ""
        bio = builder.get("bio") or ""
        for tweet in builder.get("tweets", []):
            created_at = tweet.get("createdAt")
            if not is_recent(created_at, cutoff):
                continue
            text = tweet.get("text") or ""
            url = tweet.get("url") or ""
            if not text or not url:
                continue
            metrics = (
                f"likes={tweet.get('likes', 0)}, "
                f"retweets={tweet.get('retweets', 0)}, "
                f"replies={tweet.get('replies', 0)}"
            )
            items.append(
                {
                    "id": url,
                    "url": url,
                    "title": f"[X] {name}: {compact(text, 110)}",
                    "content_text": f"{text}\n\n{metrics}\n\nProfile: {bio}",
                    "date_published": created_at,
                    "authors": [{"name": f"{name} (@{handle})" if handle else name}],
                    "tags": ["builders", "x"],
                }
            )


def add_podcast_items(data: dict[str, Any], items: list[dict[str, Any]], cutoff: datetime) -> None:
    for episode in data.get("podcasts", []):
        published_at = episode.get("publishedAt")
        if not is_recent(published_at, cutoff):
            continue
        title = episode.get("title") or ""
        url = episode.get("url") or ""
        if not title or not url:
            continue
        show_name = episode.get("name") or "Podcast"
        transcript = compact(episode.get("transcript"), 1800)
        items.append(
            {
                "id": episode.get("guid") or url,
                "url": url,
                "title": f"[Podcast] {show_name}: {title}",
                "content_text": transcript,
                "date_published": published_at,
                "authors": [{"name": show_name}],
                "tags": ["builders", "podcast"],
            }
        )


def add_blog_items(data: dict[str, Any], items: list[dict[str, Any]], cutoff: datetime) -> None:
    for post in data.get("blogs", []):
        published_at = (
            post.get("publishedAt")
            or post.get("published_at")
            or post.get("date")
            or post.get("createdAt")
        )
        if not is_recent(published_at, cutoff):
            continue
        title = post.get("title") or ""
        url = post.get("url") or post.get("link") or ""
        if not title or not url:
            continue
        author = post.get("name") or post.get("author") or post.get("source") or "Builder Blog"
        body = post.get("summary") or post.get("content") or post.get("text") or post.get("description") or ""
        items.append(
            {
                "id": post.get("id") or url,
                "url": url,
                "title": f"[Blog] {author}: {title}",
                "content_text": compact(body, 1800),
                "date_published": published_at,
                "authors": [{"name": author}],
                "tags": ["builders", "blog"],
            }
        )


def item_sort_key(item: dict[str, Any]) -> datetime:
    return parse_datetime(item.get("date_published")) or datetime.min.replace(tzinfo=timezone.utc)


def build_feed(max_age_days: int, max_items: int) -> dict[str, Any]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    items: list[dict[str, Any]] = []

    for name, url in SOURCES.items():
        try:
            data = fetch_json(url)
        except (OSError, URLError, json.JSONDecodeError) as exc:
            print(f"[builders] skipped {name}: {exc}", file=sys.stderr)
            continue
        if name == "x":
            add_x_items(data, items, cutoff)
        elif name == "podcasts":
            add_podcast_items(data, items, cutoff)
        elif name == "blogs":
            add_blog_items(data, items, cutoff)

    deduped: dict[str, dict[str, Any]] = {}
    for item in items:
        deduped[item["id"]] = item

    sorted_items = sorted(deduped.values(), key=item_sort_key, reverse=True)[:max_items]
    return {
        "version": "https://jsonfeed.org/version/1.1",
        "title": "AI Builders",
        "home_page_url": "https://github.com/zarazhangrui/follow-builders",
        "feed_url": "http://127.0.0.1:8765/builders.json",
        "description": "Recent builder posts, podcasts, and notes from follow-builders.",
        "items": sorted_items,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-age-days", type=int, default=3)
    parser.add_argument("--max-items", type=int, default=40)
    args = parser.parse_args()

    feed = build_feed(max_age_days=args.max_age_days, max_items=args.max_items)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(feed, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[builders] wrote {len(feed['items'])} items to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
