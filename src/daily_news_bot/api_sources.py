from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from .config import Settings
from .fetchers import clean_text
from .models import Article


DEFAULT_TIMEOUT = 20
NEWSAPI_URL = "https://newsapi.org/v2/everything"
FINNHUB_URL = "https://finnhub.io/api/v1/news"
ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"
POLYGON_URL = "https://api.polygon.io/v2/reference/news"
MARKETAUX_URL = "https://api.marketaux.com/v1/news/all"

API_KEY_PATTERNS = [
    re.compile(r"([?&](?:apiKey|apikey|api_token|token)=)[^&\s]+", re.IGNORECASE),
    re.compile(r"(Bearer\s+)[^\s]+", re.IGNORECASE),
]

PROVIDER_WEIGHTS = {
    "NewsAPI": 1.12,
    "Finnhub": 1.18,
    "Alpha Vantage": 1.10,
    "Polygon": 1.22,
    "Marketaux": 1.15,
}

CATEGORY_KEYWORDS = {
    "energy": ("oil", "gas", "lng", "opec", "crude", "fuel", "electricity", "power"),
    "technology": ("ai", "chip", "semiconductor", "nvidia", "apple", "microsoft", "openai", "data center"),
    "macro": ("fed", "ecb", "inflation", "cpi", "ppi", "rates", "yield", "treasury", "central bank", "jobs"),
    "geopolitics": ("war", "missile", "sanctions", "iran", "ukraine", "taiwan", "china", "ceasefire", "military"),
    "markets": ("stocks", "market", "shares", "wall street", "futures", "vix", "dollar", "gold"),
}


def _safe_error(message: str) -> str:
    sanitized = message
    for pattern in API_KEY_PATTERNS:
        sanitized = pattern.sub(r"\1***", sanitized)
    return sanitized[:300]


def _request_json(url: str, params: dict[str, Any], timeout: int = DEFAULT_TIMEOUT) -> tuple[dict[str, Any] | list[Any] | None, str, int | None]:
    try:
        response = requests.get(url, params=params, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    except requests.RequestException as exc:
        return None, _safe_error(f"{type(exc).__name__}: {exc}"), None

    status_code = response.status_code
    if status_code >= 400:
        body = _safe_error(response.text[:240])
        return None, f"HTTP {status_code}: {body}", status_code

    try:
        return response.json(), "", status_code
    except ValueError:
        return None, "Invalid JSON response", status_code


def _new_status(name: str, url: str, key_configured: bool) -> dict[str, Any]:
    return {
        "name": name,
        "url": url,
        "source_type": "api",
        "category": "api",
        "region": "global",
        "official": False,
        "enabled": key_configured,
        "key_configured": key_configured,
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


def _update_status_dates(status: dict[str, Any], articles: list[Article]) -> None:
    status["returned_articles"] = len(articles)
    if articles:
        published_values = sorted(article.published_at for article in articles)
        status["oldest_published_at"] = published_values[0].isoformat()
        status["latest_published_at"] = published_values[-1].isoformat()


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    candidates = [value]
    if value.endswith("Z"):
        candidates.append(value[:-1] + "+00:00")
    for candidate in candidates:
        try:
            parsed = datetime.fromisoformat(candidate)
            if parsed.tzinfo:
                return parsed.astimezone(timezone.utc).replace(tzinfo=None)
            return parsed.replace(tzinfo=None)
        except ValueError:
            continue
    return None


def _parse_alpha_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.strptime(value, "%Y%m%dT%H%M%S")
        return parsed.replace(tzinfo=None)
    except ValueError:
        return None


def _parse_unix_datetime(value: Any) -> datetime | None:
    try:
        if value is None:
            return None
        return datetime.fromtimestamp(int(value), tz=timezone.utc).replace(tzinfo=None)
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def _infer_category(title: str, summary: str, fallback: str = "markets") -> str:
    text = f"{title} {summary}".lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return category
    return fallback


def _build_article(
    provider_name: str,
    source_name: str,
    title: str,
    url: str,
    summary: str,
    published_at: datetime | None,
    fallback_category: str,
) -> Article | None:
    clean_title = clean_text(title)
    clean_url = (url or "").strip()
    clean_summary = clean_text(summary)
    if not clean_title or not clean_url or not published_at:
        return None

    source_label = source_name.strip() if source_name else provider_name
    return Article(
        title=clean_title,
        url=clean_url,
        source=f"{provider_name}/{source_label}",
        category=_infer_category(clean_title, clean_summary, fallback=fallback_category),
        region="global",
        source_weight=PROVIDER_WEIGHTS.get(provider_name, 1.0),
        published_at=published_at,
        summary=clean_summary,
        content=clean_summary,
        official_source=False,
    )


def _filter_recent(articles: list[Article], cutoff: datetime, limit: int) -> list[Article]:
    recent = [article for article in articles if article.published_at >= cutoff]
    recent.sort(key=lambda item: item.published_at, reverse=True)
    return recent[:limit]


def _collect_newsapi(settings: Settings, cutoff: datetime, limit: int, timeout: int) -> tuple[list[Article], dict[str, Any]]:
    status = _new_status("NewsAPI", NEWSAPI_URL, bool(settings.newsapi_key))
    if not settings.newsapi_key:
        return [], status

    payload, error, _ = _request_json(
        NEWSAPI_URL,
        {
            "q": 'markets OR economy OR inflation OR fed OR rates OR sanctions OR oil OR war OR ai OR chip',
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": limit,
            "from": cutoff.replace(microsecond=0).isoformat() + "Z",
            "apiKey": settings.newsapi_key,
        },
        timeout=timeout,
    )
    if error:
        status["ok"] = False
        status["error"] = error
        return [], status

    articles_raw = (payload or {}).get("articles") or []
    status["raw_entries"] = len(articles_raw)
    articles: list[Article] = []
    for item in articles_raw:
        article = _build_article(
            "NewsAPI",
            ((item.get("source") or {}).get("name") or "Unknown"),
            item.get("title") or "",
            item.get("url") or "",
            item.get("description") or item.get("content") or "",
            _parse_iso_datetime(item.get("publishedAt")),
            "markets",
        )
        if article is None:
            status["skipped_invalid"] += 1
            continue
        articles.append(article)
    articles = _filter_recent(articles, cutoff, limit)
    _update_status_dates(status, articles)
    return articles, status


def _collect_finnhub(settings: Settings, cutoff: datetime, limit: int, timeout: int) -> tuple[list[Article], dict[str, Any]]:
    status = _new_status("Finnhub", FINNHUB_URL, bool(settings.finnhub_api_key))
    if not settings.finnhub_api_key:
        return [], status

    articles: list[Article] = []
    raw_count = 0
    for category in settings.finnhub_news_categories or ("general",):
        payload, error, _ = _request_json(
            FINNHUB_URL,
            {
                "category": category,
                "token": settings.finnhub_api_key,
            },
            timeout=timeout,
        )
        if error:
            status["ok"] = False
            status["error"] = error
            return [], status

        items = payload or []
        raw_count += len(items)
        for item in items:
            article = _build_article(
                "Finnhub",
                item.get("source") or category,
                item.get("headline") or item.get("title") or "",
                item.get("url") or "",
                item.get("summary") or "",
                _parse_unix_datetime(item.get("datetime")),
                "markets",
            )
            if article is None:
                status["skipped_invalid"] += 1
                continue
            articles.append(article)

    status["raw_entries"] = raw_count
    articles = _filter_recent(articles, cutoff, limit)
    _update_status_dates(status, articles)
    return articles, status


def _collect_alpha_vantage(settings: Settings, cutoff: datetime, limit: int, timeout: int) -> tuple[list[Article], dict[str, Any]]:
    status = _new_status("Alpha Vantage", ALPHA_VANTAGE_URL, bool(settings.alpha_vantage_api_key))
    if not settings.alpha_vantage_api_key:
        return [], status

    payload, error, _ = _request_json(
        ALPHA_VANTAGE_URL,
        {
            "function": "NEWS_SENTIMENT",
            "sort": "LATEST",
            "limit": limit,
            "time_from": cutoff.strftime("%Y%m%dT%H%M"),
            "apikey": settings.alpha_vantage_api_key,
        },
        timeout=timeout,
    )
    if error:
        status["ok"] = False
        status["error"] = error
        return [], status

    if isinstance(payload, dict) and payload.get("Note"):
        status["ok"] = False
        status["error"] = str(payload.get("Note"))[:300]
        return [], status
    if isinstance(payload, dict) and payload.get("Information"):
        status["ok"] = False
        status["error"] = str(payload.get("Information"))[:300]
        return [], status

    feed = (payload or {}).get("feed") or []
    status["raw_entries"] = len(feed)
    articles: list[Article] = []
    for item in feed:
        article = _build_article(
            "Alpha Vantage",
            item.get("source") or "News Sentiment",
            item.get("title") or "",
            item.get("url") or "",
            item.get("summary") or "",
            _parse_alpha_datetime(item.get("time_published")),
            "markets",
        )
        if article is None:
            status["skipped_invalid"] += 1
            continue
        articles.append(article)

    articles = _filter_recent(articles, cutoff, limit)
    _update_status_dates(status, articles)
    return articles, status


def _collect_polygon(settings: Settings, cutoff: datetime, limit: int, timeout: int) -> tuple[list[Article], dict[str, Any]]:
    status = _new_status("Polygon", POLYGON_URL, bool(settings.polygon_api_key))
    if not settings.polygon_api_key:
        return [], status

    payload, error, _ = _request_json(
        POLYGON_URL,
        {
            "limit": limit,
            "order": "desc",
            "sort": "published_utc",
            "published_utc.gte": cutoff.replace(microsecond=0).isoformat() + "Z",
            "apiKey": settings.polygon_api_key,
        },
        timeout=timeout,
    )
    if error:
        status["ok"] = False
        status["error"] = error
        return [], status

    results = (payload or {}).get("results") or []
    status["raw_entries"] = len(results)
    articles: list[Article] = []
    for item in results:
        publisher = (item.get("publisher") or {}).get("name") or "News"
        article = _build_article(
            "Polygon",
            publisher,
            item.get("title") or "",
            item.get("article_url") or item.get("amp_url") or "",
            item.get("description") or "",
            _parse_iso_datetime(item.get("published_utc")),
            "markets",
        )
        if article is None:
            status["skipped_invalid"] += 1
            continue
        articles.append(article)

    articles = _filter_recent(articles, cutoff, limit)
    _update_status_dates(status, articles)
    return articles, status


def _collect_marketaux(settings: Settings, cutoff: datetime, limit: int, timeout: int) -> tuple[list[Article], dict[str, Any]]:
    status = _new_status("Marketaux", MARKETAUX_URL, bool(settings.marketaux_api_key))
    if not settings.marketaux_api_key:
        return [], status

    payload, error, _ = _request_json(
        MARKETAUX_URL,
        {
            "api_token": settings.marketaux_api_key,
            "language": "en",
            "sort": "published_desc",
            "published_after": cutoff.strftime("%Y-%m-%dT%H:%M"),
            "group_similar": "true",
            "filter_entities": "true",
            "limit": limit,
        },
        timeout=timeout,
    )
    if error:
        status["ok"] = False
        status["error"] = error
        return [], status

    data = (payload or {}).get("data") or []
    status["raw_entries"] = len(data)
    articles: list[Article] = []
    for item in data:
        article = _build_article(
            "Marketaux",
            item.get("source") or "News",
            item.get("title") or "",
            item.get("url") or "",
            item.get("description") or item.get("snippet") or "",
            _parse_iso_datetime(item.get("published_at")),
            "markets",
        )
        if article is None:
            status["skipped_invalid"] += 1
            continue
        articles.append(article)

    articles = _filter_recent(articles, cutoff, limit)
    _update_status_dates(status, articles)
    return articles, status


def collect_api_articles_with_status(
    settings: Settings,
    hours_back: int,
    per_source_limit: int,
    now: datetime | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[list[Article], list[dict[str, Any]]]:
    current = (now or datetime.utcnow()).replace(tzinfo=None)
    cutoff = current - timedelta(hours=hours_back)

    collectors = (
        _collect_newsapi,
        _collect_finnhub,
        _collect_alpha_vantage,
        _collect_polygon,
        _collect_marketaux,
    )

    articles: list[Article] = []
    statuses: list[dict[str, Any]] = []
    for collector in collectors:
        provider_articles, status = collector(settings, cutoff, per_source_limit, timeout)
        articles.extend(provider_articles)
        statuses.append(status)

    deduped: dict[str, Article] = {}
    for article in articles:
        existing = deduped.get(article.url)
        if existing is None or article.source_weight > existing.source_weight:
            deduped[article.url] = article

    final_articles = sorted(deduped.values(), key=lambda item: item.published_at, reverse=True)
    return final_articles, statuses
