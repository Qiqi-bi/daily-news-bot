from __future__ import annotations

import re
from collections import Counter

from .models import Article, EventCluster


STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "into",
    "after",
    "amid",
    "over",
    "will",
    "says",
    "news",
    "more",
    "than",
    "about",
    "have",
    "has",
    "are",
    "its",
    "their",
    "here",
    "what",
    "expect",
    "despite",
    "expected",
    "today",
    "week",
    "year",
    "market",
    "markets",
    "stock",
    "stocks",
    "prices",
    "price",
    "little",
    "changed",
    "higher",
    "high",
    "due",
}

BROAD_TOPIC_WORDS = {
    "iran",
    "war",
    "conflict",
    "china",
    "trump",
    "oil",
    "gas",
    "trade",
    "energy",
    "global",
    "world",
    "middle",
    "east",
    "profit",
    "earnings",
    "summer",
}

SPECIFIC_ANCHORS = {
    "warsh",
    "fed",
    "treasury",
    "hearing",
    "peace",
    "talks",
    "deal",
    "ceasefire",
    "hormuz",
    "pakistan",
    "vance",
    "halliburton",
    "apple",
    "cook",
    "ternus",
    "panama",
    "gasoline",
    "reserves",
    "winter",
    "europe",
    "electricity",
    "retail",
    "sales",
    "aerospace",
    "opec",
}

WORD_RE = re.compile(r"[a-zA-Z0-9]{3,}")



def normalize_tokens(text: str) -> list[str]:
    raw = WORD_RE.findall(text.lower())
    return [token for token in raw if token not in STOPWORDS]



def article_tokens(article: Article) -> set[str]:
    title_tokens = normalize_tokens(article.title)
    summary_tokens = normalize_tokens(article.summary)
    merged = set(title_tokens)
    merged.update(summary_tokens[:10])
    return merged



def similarity(left: Article, right: Article) -> float:
    left_tokens = article_tokens(left)
    right_tokens = article_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0

    intersection = left_tokens & right_tokens
    if not intersection:
        return 0.0

    significant_intersection = intersection - BROAD_TOPIC_WORDS
    anchor_overlap = intersection & SPECIFIC_ANCHORS
    if not anchor_overlap and len(significant_intersection) < 2:
        return 0.0

    union = left_tokens | right_tokens
    jaccard = len(intersection) / max(len(union), 1)
    overlap = len(intersection) / max(min(len(left_tokens), len(right_tokens)), 1)

    anchor_bonus = 0.0
    if anchor_overlap:
        anchor_bonus = 0.06
    elif len(significant_intersection) >= 3:
        anchor_bonus = 0.03

    score = max(jaccard, overlap * 0.9) + anchor_bonus

    if left.category != right.category and not anchor_overlap:
        score *= 0.88
    if (not left.summary or not right.summary) and not anchor_overlap:
        score *= 0.85

    return score



def build_theme(articles: list[Article]) -> str:
    if not articles:
        return "未命名事件"

    representative = sorted(
        articles,
        key=lambda item: (item.source_weight, item.published_at.timestamp()),
        reverse=True,
    )[0]

    counter = Counter()
    for article in articles:
        counter.update(article_tokens(article))

    keywords = [token for token, _ in counter.most_common(4)]
    if keywords:
        return f"{representative.title} ｜ 关键词：{' / '.join(keywords)}"
    return representative.title



def cluster_articles(articles: list[Article], threshold: float = 0.33) -> list[EventCluster]:
    clusters: list[EventCluster] = []

    for article in articles:
        matched_cluster: EventCluster | None = None
        best_score = 0.0
        for cluster in clusters:
            score = similarity(article, cluster.representative)
            if score >= threshold and score > best_score:
                matched_cluster = cluster
                best_score = score

        if matched_cluster is None:
            cluster_id = re.sub(r"[^a-z0-9]", "", representative_id(article.title))[:12]
            matched_cluster = EventCluster(cluster_id=cluster_id or "event", theme=article.title)
            clusters.append(matched_cluster)

        matched_cluster.articles.append(article)
        matched_cluster.theme = build_theme(matched_cluster.articles)

    return clusters



def representative_id(title: str) -> str:
    return title.lower().replace(" ", "-")
