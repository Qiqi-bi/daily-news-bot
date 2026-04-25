from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urljoin

import requests
from dateutil import parser as date_parser

from .models import Article


DEFAULT_TIMEOUT = 15
TAG_RE = re.compile(r"<[^>]+>")
LINK_RE = re.compile(r"<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", re.DOTALL | re.IGNORECASE)
DATE_RE = re.compile(r"(20\d{2})[-年/.](\d{1,2})[-月/.](\d{1,2})")
URL_DATE_RE = re.compile(r"/(20\d{2})(\d{2})(\d{2})|t(20\d{2})(\d{2})(\d{2})_")


@dataclass(slots=True)
class OfficialPageSource:
    name: str
    url: str
    category: str
    region: str
    weight: float = 1.25
    required_url_fragment: str = ""


OFFICIAL_PAGE_SOURCES: tuple[OfficialPageSource, ...] = (
    OfficialPageSource("PBOC Official Page", "https://www.pbc.gov.cn/goutongjiaoliu/113456/113469/index.html", "macro", "china", 1.45, "/goutongjiaoliu/113456/113469/"),
    OfficialPageSource("State Council China Page", "https://www.gov.cn/yaowen/", "macro", "china", 1.35, "/yaowen/"),
    OfficialPageSource("NDRC Official Page", "https://www.ndrc.gov.cn/xwdt/xwfb/", "macro", "china", 1.35, "/xwdt/xwfb/"),
    OfficialPageSource("MOFCOM Official Page", "https://www.mofcom.gov.cn/syxwfb/index.html", "macro", "china", 1.25, "/syxwfb/"),
    OfficialPageSource("NBS Data Releases Page", "https://www.stats.gov.cn/sj/zxfb/", "macro", "china", 1.25, "/sj/zxfb/"),
    OfficialPageSource("MFA Spokesperson Page", "https://www.mfa.gov.cn/web/wjdt_674879/fyrbt_674889/", "geopolitics", "china", 1.30, "/web/wjdt_674879/fyrbt_674889/"),
    OfficialPageSource("CSRC Official Page", "http://www.csrc.gov.cn/csrc/c100028/common_list.shtml", "markets", "china", 1.35, "/csrc/c100028/"),
    OfficialPageSource("SSE Official Page", "https://www.sse.com.cn/aboutus/mediacenter/hotandd/", "markets", "china", 1.25, "/aboutus/mediacenter/hotandd/c/"),
    OfficialPageSource("SZSE Official Page", "https://www.szse.cn/aboutus/trends/news/index.html", "markets", "china", 1.20, "/aboutus/trends/news/"),
    OfficialPageSource("MIIT Official Page", "https://www.miit.gov.cn/xwdt/gxdt/index.html", "technology", "china", 1.20, "/xwdt/gxdt/"),
)


def _clean(value: str) -> str:
    value = TAG_RE.sub("", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def _parse_date(raw: str) -> datetime | None:
    match = DATE_RE.search(raw)
    if match:
        year, month, day = [int(part) for part in match.groups()]
        return datetime(year, month, day, 23, 59)
    url_match = URL_DATE_RE.search(raw)
    if url_match:
        parts = [part for part in url_match.groups() if part]
        if len(parts) >= 3:
            return datetime(int(parts[0]), int(parts[1]), int(parts[2]), 23, 59)
    try:
        return date_parser.parse(raw, fuzzy=True).replace(tzinfo=None)
    except Exception:
        return None


def _status(source: OfficialPageSource) -> dict[str, Any]:
    return {
        "name": source.name,
        "url": source.url,
        "source_type": "official_page",
        "category": source.category,
        "region": source.region,
        "official": True,
        "enabled": True,
        "key_configured": None,
        "raw_entries": 0,
        "returned_articles": 0,
        "skipped_old": 0,
        "skipped_undated": 0,
        "skipped_invalid": 0,
        "skipped_future": 0,
        "latest_published_at": None,
        "oldest_published_at": None,
        "ok": True,
        "error": "",
    }


def fetch_official_page_articles(
    source: OfficialPageSource,
    hours_back: int,
    per_source_limit: int,
    now: datetime | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[list[Article], dict[str, Any]]:
    current = (now or datetime.utcnow()).replace(tzinfo=None)
    cutoff = current - timedelta(hours=hours_back)
    future_cutoff = current + timedelta(hours=18)
    status = _status(source)
    response = requests.get(source.url, headers={"User-Agent": "Mozilla/5.0"}, timeout=timeout)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding
    text = response.text

    links = LINK_RE.findall(text)
    status["raw_entries"] = len(links)
    articles: list[Article] = []
    seen: set[str] = set()
    for href, title_html in links:
        title = _clean(title_html)
        if not title or len(title) < 6:
            status["skipped_invalid"] += 1
            continue
        url = urljoin(source.url, href)
        if source.required_url_fragment and source.required_url_fragment not in url:
            status["skipped_invalid"] += 1
            continue
        if url in seen:
            continue
        seen.add(url)

        idx = text.find(href)
        context = text[max(0, idx - 260): idx + 520] if idx >= 0 else href + title
        published_at = _parse_date(title) or _parse_date(url) or _parse_date(context)
        if published_at is None:
            status["skipped_undated"] += 1
            continue
        if published_at > future_cutoff:
            status["skipped_future"] += 1
            continue
        if published_at > current:
            published_at = current
        if published_at < cutoff:
            status["skipped_old"] += 1
            continue
        articles.append(
            Article(
                title=title,
                url=url,
                source=source.name,
                category=source.category,
                region=source.region,
                source_weight=source.weight,
                published_at=published_at,
                summary="官方网页抓取：" + title,
                content="官方网页抓取：" + title,
                official_source=True,
            )
        )
        if len(articles) >= per_source_limit:
            break

    status["returned_articles"] = len(articles)
    if articles:
        published_values = sorted(article.published_at for article in articles)
        status["oldest_published_at"] = published_values[0].isoformat()
        status["latest_published_at"] = published_values[-1].isoformat()
    return articles, status


def collect_official_page_articles_with_status(
    hours_back: int,
    per_source_limit: int,
    now: datetime | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[list[Article], list[dict[str, Any]]]:
    current = (now or datetime.utcnow()).replace(tzinfo=None)
    articles: list[Article] = []
    statuses: list[dict[str, Any]] = []
    for source in OFFICIAL_PAGE_SOURCES:
        try:
            source_articles, status = fetch_official_page_articles(source, hours_back, per_source_limit, current, timeout=timeout)
            articles.extend(source_articles)
            statuses.append(status)
        except Exception as exc:
            status = _status(source)
            status["ok"] = False
            status["error"] = f"{type(exc).__name__}: {exc}"[:300]
            statuses.append(status)
    return sorted(articles, key=lambda item: item.published_at, reverse=True), statuses
