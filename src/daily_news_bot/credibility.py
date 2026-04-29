from __future__ import annotations

from dataclasses import asdict
from statistics import mean
from typing import Any
from urllib.parse import urlparse

from .models import Article, EventCluster


HIGH_TRUST_SOURCE_KEYWORDS = (
    "reuters",
    "reuters.com",
    "associated press",
    "ap news",
    "apnews.com",
    "bloomberg",
    "bloomberg.com",
    "wall street journal",
    "wsj",
    "wsj.com",
    "ft world",
    "financial times",
    "ft.com",
    "new york times",
    "nyt",
    "nytimes.com",
    "bbc",
    "bbc.com",
    "bbc.co.uk",
    "cnbc",
    "cnbc.com",
    "marketwatch",
    "marketwatch.com",
    "nikkei",
    "nikkei.com",
    "al jazeera",
    "aljazeera.com",
    "guardian",
    "theguardian.com",
    "federal reserve",
    "federalreserve.gov",
    "ecb",
    "ecb.europa.eu",
    "bank of england",
    "bankofengland.co.uk",
    "eia",
    "eia.gov",
    "opec",
    "opec.org",
    "iea",
    "iea.org",
    "treasury",
    "treasury.gov",
    "pboc",
    "people's bank of china",
    "gov.cn",
    "csrc",
    "sse",
    "szse",
    "mofcom",
    "ndrc",
    "stats.gov.cn",
    "mfa",
)

MEDIUM_TRUST_SOURCE_KEYWORDS = (
    "yahoo finance",
    "yahoo.com",
    "barron",
    "barrons.com",
    "forbes",
    "forbes.com",
    "fortune",
    "fortune.com",
    "business insider",
    "businessinsider.com",
    "axios",
    "axios.com",
    "semafor",
    "semafor.com",
    "cnn",
    "cnn.com",
    "fox business",
    "foxbusiness.com",
)

LOW_TRUST_SOURCE_KEYWORDS = (
    "globenewswire",
    "pr newswire",
    "accesswire",
    "business wire",
    "investorplace",
    "tipranks",
    "zacks",
    "seeking alpha",
    "motley fool",
    "benzinga",
)

HARD_BLOCK_TERMS = (
    "satire",
    "parody account",
    "fake screenshot",
    "fabricated",
    "hoax",
)

RUMOR_TERMS = (
    "rumor",
    "unconfirmed",
    "not verified",
    "unverified",
    "alleged",
    "allegedly",
    "speculation",
    "speculated",
    "circulating online",
    "viral post",
    "baseless",
    "without evidence",
    "no evidence",
    "conspiracy theory",
    "false flag",
    "inside job",
    "deep state",
    "plot behind",
    "幕后",
    "阴谋论",
    "自导自演",
    "无证据",
    "未证实",
)

SOCIAL_ONLY_TERMS = (
    "social media",
    "post on x",
    "posted on x",
    "telegram",
    "wechat screenshot",
    "whatsapp",
    "reddit post",
)

COMMENTARY_TERMS = (
    "opinion:",
    "analysis:",
    "watch:",
    "video:",
    "podcast",
    "live blog",
)

PRESS_RELEASE_TERMS = (
    "press release",
    "company announcement",
    "sponsored",
)


def _normalize(text: str | None) -> str:
    return (text or "").strip().lower()


def _source_domain(url: str) -> str:
    netloc = urlparse(url).netloc.lower().strip()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


def _matches_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def _rootish_domain(domain: str) -> str:
    if not domain:
        return ""
    parts = [part for part in domain.split(".") if part]
    if len(parts) <= 2:
        return domain
    if parts[-1] in {"cn", "uk", "jp", "au"} and len(parts) >= 3:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def _score_to_label(score: float) -> str:
    if score >= 0.78:
        return "高"
    if score >= 0.56:
        return "中"
    return "低"


def assess_article_credibility(article: Article) -> Article:
    source_text = _normalize(article.source)
    domain = _source_domain(article.url)
    title_text = _normalize(article.title)
    summary_text = _normalize(article.summary)
    joined_text = f"{title_text} {summary_text}"

    score = 0.52
    flags: list[str] = []

    if article.official_source:
        score += 0.34
        flags.append("官方源")

    trust_text = f"{source_text} {domain}"
    if _matches_any(trust_text, HIGH_TRUST_SOURCE_KEYWORDS):
        score += 0.24
        flags.append("高可信来源")
    elif _matches_any(trust_text, MEDIUM_TRUST_SOURCE_KEYWORDS):
        score += 0.10
        flags.append("主流媒体")

    if _matches_any(trust_text, LOW_TRUST_SOURCE_KEYWORDS):
        score -= 0.18
        flags.append("低可信来源")

    if _matches_any(joined_text, HARD_BLOCK_TERMS):
        score -= 0.35
        flags.append("疑似伪造/恶搞")
    if _matches_any(joined_text, RUMOR_TERMS):
        score -= 0.18
        flags.append("传闻/未证实措辞")
    if _matches_any(joined_text, SOCIAL_ONLY_TERMS):
        score -= 0.15
        flags.append("社交平台二手信号")
    if _matches_any(joined_text, COMMENTARY_TERMS):
        score -= 0.10
        flags.append("评论/观点内容")
    if _matches_any(joined_text, PRESS_RELEASE_TERMS) or _matches_any(trust_text, ("globenewswire", "pr newswire", "accesswire", "business wire")):
        score -= 0.14
        flags.append("公告/稿线分发")

    if not article.summary:
        score -= 0.05
        flags.append("摘要信息少")
    if len(article.title) < 18:
        score -= 0.03

    score = max(0.05, min(0.99, round(score, 3)))
    article.source_domain = domain
    article.credibility_score = score
    article.credibility_label = _score_to_label(score)
    article.credibility_flags = flags
    return article


def should_filter_article(article: Article) -> bool:
    flags = set(article.credibility_flags)
    if article.official_source:
        return False
    if article.credibility_score < 0.20:
        return True
    if "疑似伪造/恶搞" in flags:
        return True
    if article.credibility_score < 0.36 and ("传闻/未证实措辞" in flags or "社交平台二手信号" in flags):
        return True
    if article.credibility_score < 0.32 and "低可信来源" in flags:
        return True
    return False


def annotate_and_filter_articles(articles: list[Article]) -> tuple[list[Article], dict[str, Any]]:
    kept: list[Article] = []
    filtered: list[dict[str, Any]] = []
    for article in articles:
        assessed = assess_article_credibility(article)
        if should_filter_article(assessed):
            filtered.append(
                {
                    "title": assessed.title,
                    "source": assessed.source,
                    "url": assessed.url,
                    "credibility_score": assessed.credibility_score,
                    "credibility_label": assessed.credibility_label,
                    "credibility_flags": list(assessed.credibility_flags),
                }
            )
            continue
        kept.append(assessed)

    summary = {
        "kept_articles": len(kept),
        "filtered_articles": len(filtered),
        "filtered_samples": filtered[:8],
        "high_credibility_articles": sum(1 for article in kept if article.credibility_label == "高"),
        "medium_credibility_articles": sum(1 for article in kept if article.credibility_label == "中"),
        "low_credibility_articles": sum(1 for article in kept if article.credibility_label == "低"),
    }
    return kept, summary


def assess_cluster_credibility(cluster: EventCluster) -> EventCluster:
    articles = cluster.articles
    if not articles:
        cluster.credibility_score = 0.0
        cluster.credibility_label = "低"
        cluster.confirmed_source_count = 0
        cluster.official_confirmation = False
        cluster.credibility_notes = ["没有可用文章"]
        return cluster

    reliable_articles = [article for article in articles if article.credibility_score >= 0.56]
    high_articles = [article for article in articles if article.credibility_label == "高"]
    official_articles = [article for article in articles if article.official_source]
    domains = {_rootish_domain(article.source_domain) for article in reliable_articles if article.source_domain}
    scores = [article.credibility_score for article in articles[:6]]
    base_score = mean(scores) if scores else 0.0

    cluster_score = base_score
    if official_articles:
        cluster_score += 0.12
    if len(domains) >= 2:
        cluster_score += 0.10
    if len(domains) >= 3:
        cluster_score += 0.05
    if len(high_articles) >= 2:
        cluster_score += 0.04
    if sum(1 for article in articles if article.credibility_label == "低") >= max(2, len(articles) // 2 + 1):
        cluster_score -= 0.10

    cluster_score = max(0.05, min(0.99, round(cluster_score, 3)))

    notes: list[str] = []
    if official_articles:
        notes.append("有官方源确认")
    if len(domains) >= 3:
        notes.append("有3家及以上可靠来源交叉验证")
    elif len(domains) == 2:
        notes.append("有2家可靠来源交叉验证")
    elif len(domains) <= 1 and not official_articles:
        notes.append("主要依赖单一来源，需二次确认")
    if any("传闻/未证实措辞" in article.credibility_flags for article in articles):
        notes.append("含未证实/传闻措辞")

    cluster.credibility_score = cluster_score
    cluster.credibility_label = _score_to_label(cluster_score)
    cluster.confirmed_source_count = len(domains)
    cluster.official_confirmation = bool(official_articles)
    cluster.credibility_notes = notes
    return cluster


def credibility_summary_to_dict(summary: dict[str, Any]) -> dict[str, Any]:
    return dict(summary)
