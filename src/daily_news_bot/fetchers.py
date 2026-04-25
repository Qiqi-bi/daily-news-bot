from __future__ import annotations

import html
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from time import struct_time
from typing import Any

import feedparser

from .models import Article, SourceDef


TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    text = html.unescape(value)
    text = TAG_RE.sub(" ", text)
    text = WHITESPACE_RE.sub(" ", text)
    return text.strip()


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value.replace(tzinfo=None)


def _datetime_from_struct_time(value: Any) -> datetime | None:
    if not isinstance(value, struct_time):
        return None
    return datetime(*value[:6])


def parse_datetime(entry: dict) -> datetime | None:
    for field in ("published_parsed", "updated_parsed", "created_parsed"):
        parsed = _datetime_from_struct_time(entry.get(field))
        if parsed:
            return _normalize_datetime(parsed)

    for field in ("published", "updated", "created"):
        raw = entry.get(field)
        if raw:
            try:
                return _normalize_datetime(parsedate_to_datetime(raw))
            except (TypeError, ValueError, IndexError, OverflowError):
                continue
    return None


def extract_summary(entry: dict) -> str:
    summary = clean_text(entry.get("summary", ""))
    if summary:
        return summary

    for content_item in entry.get("content", []):
        content = clean_text(content_item.get("value", ""))
        if content:
            return content

    return ""


def _new_status(source: SourceDef) -> dict[str, Any]:
    return {
        "name": source.name,
        "url": source.url,
        "source_type": "rss",
        "category": source.category,
        "region": source.region,
        "official": source.official,
        "enabled": True,
        "key_configured": None,
        "raw_entries": 0,
        "returned_articles": 0,
        "skipped_old": 0,
        "skipped_undated": 0,
        "skipped_invalid": 0,
        "latest_published_at": None,
        "oldest_published_at": None,
        "ok": True,
        "error": "",
    }


def fetch_source_articles(
    source: SourceDef,
    hours_back: int,
    per_source_limit: int,
    now: datetime | None = None,
) -> tuple[list[Article], dict[str, Any]]:
    current = (now or datetime.utcnow()).replace(tzinfo=None)
    cutoff = current - timedelta(hours=hours_back)
    status = _new_status(source)

    feed = feedparser.parse(source.url)
    if getattr(feed, "bozo", 0):
        bozo_exception = getattr(feed, "bozo_exception", "")
        if bozo_exception:
            status["error"] = str(bozo_exception)[:300]

    entries = list(getattr(feed, "entries", []) or [])[:per_source_limit]
    status["raw_entries"] = len(entries)

    articles: list[Article] = []
    for entry in entries:
        published_at = parse_datetime(entry)
        if published_at is None:
            status["skipped_undated"] += 1
            continue
        if published_at < cutoff:
            status["skipped_old"] += 1
            continue

        title = clean_text(entry.get("title", ""))
        link = entry.get("link", "").strip()
        if not title or not link:
            status["skipped_invalid"] += 1
            continue

        summary = extract_summary(entry)
        article = Article(
            title=title,
            url=link,
            source=source.name,
            category=source.category,
            region=source.region,
            source_weight=source.weight,
            published_at=published_at,
            summary=summary,
            content=summary,
            official_source=source.official,
        )
        articles.append(article)

    status["returned_articles"] = len(articles)
    if articles:
        published_values = sorted(article.published_at for article in articles)
        status["oldest_published_at"] = published_values[0].isoformat()
        status["latest_published_at"] = published_values[-1].isoformat()
    return articles, status


def collect_articles_with_status(
    sources: list[SourceDef],
    hours_back: int,
    per_source_limit: int,
    now: datetime | None = None,
) -> tuple[list[Article], list[dict[str, Any]]]:
    current = (now or datetime.utcnow()).replace(tzinfo=None)
    articles: list[Article] = []
    statuses: list[dict[str, Any]] = []

    for source in sources:
        try:
            source_articles, status = fetch_source_articles(source, hours_back, per_source_limit, current)
            articles.extend(source_articles)
            statuses.append(status)
        except Exception as exc:
            status = _new_status(source)
            status["ok"] = False
            status["error"] = f"{type(exc).__name__}: {exc}"[:300]
            statuses.append(status)

    deduped: dict[str, Article] = {}
    for article in articles:
        deduped.setdefault(article.url, article)

    return sorted(deduped.values(), key=lambda item: item.published_at, reverse=True), statuses


def collect_articles(
    sources: list[SourceDef],
    hours_back: int,
    per_source_limit: int,
) -> list[Article]:
    articles, _ = collect_articles_with_status(sources, hours_back, per_source_limit)
    return articles