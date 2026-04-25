from __future__ import annotations

import re
from collections import Counter
from datetime import datetime

from .credibility import assess_cluster_credibility
from .models import EventCluster


KEYWORDS = {
    "macro": ["inflation", "cpi", "ppi", "rates", "fed", "ecb", "yield", "bond", "tariff", "stimulus", "treasury", "retail sales"],
    "geopolitics": ["missile", "sanctions", "military", "israel", "iran", "ukraine", "taiwan", "china", "election", "peace talks", "ceasefire", "hormuz", "blockade"],
    "energy": ["oil", "gas", "opec", "energy", "crude", "electricity", "lng", "hormuz", "fuel", "jet fuel"],
    "technology": ["ai", "chip", "semiconductor", "nvidia", "openai", "data center", "cloud", "apple", "iphone", "cyberattack", "cyberattacks", "cybersecurity"],
    "markets": ["stocks", "market", "earnings", "bitcoin", "gold", "dollar", "treasury yields", "wall street", "shares"],
}

RECOGNIZED_TAGS = set(KEYWORDS)
WORD_RE = re.compile(r"[a-zA-Z0-9]{2,}")
CORPORATE_TERMS = (
    "ceo",
    "chairman",
    "chair",
    "earnings",
    "profit",
    "revenue",
    "guidance",
    "quarter",
    "shares",
    "shares pop",
    "stock gains",
    "stock turns lower",
    "first-quarter earnings",
    "to hand over",
    "replace tim cook",
)
COMMENTARY_TERMS = (
    "names the",
    "keeping her up",
    "keeping him up",
    "cramer",
    "analysts said",
    "strategist",
    "opinion",
)
MACRO_SHOCK_TERMS = (
    "cuts 20,000 flights",
    "cut flights",
    "supply shock",
    "blockade",
    "ceasefire",
    "attacked",
    "prices have jumped",
    "prices surge",
    "war ceasefire",
    "gas reserves",
    "electricity bills",
)



def cluster_text(cluster: EventCluster) -> str:
    parts: list[str] = [cluster.theme]
    for article in cluster.articles[:5]:
        parts.extend([article.title, article.summary])
    return " ".join(part for part in parts if part).lower()



def token_set(text: str) -> set[str]:
    return {token for token in WORD_RE.findall(text.lower()) if len(token) >= 2}



def infer_tags(cluster: EventCluster) -> list[str]:
    text = cluster_text(cluster)
    tokens = token_set(text)
    found: list[str] = []

    for tag, phrases in KEYWORDS.items():
        for phrase in phrases:
            if " " in phrase:
                if phrase in text:
                    found.append(tag)
                    break
            else:
                if phrase in tokens:
                    found.append(tag)
                    break

    category = cluster.representative.category.strip().lower()
    if category in RECOGNIZED_TAGS and category not in found and category != "geopolitics":
        found.append(category)

    if "geopolitics" in found and "cyberattack" in text and "iran" not in text and "ukraine" not in text:
        found = [tag for tag in found if tag != "geopolitics"]
        if "technology" not in found:
            found.append("technology")

    deduped: list[str] = []
    for item in found:
        if item not in deduped:
            deduped.append(item)
    return deduped



def infer_direction(cluster: EventCluster, tags: list[str]) -> str:
    text = cluster_text(cluster)
    if "geopolitics" in tags and "peace talks" in text:
        return "偏利多"
    if "geopolitics" in tags and ("war" in text or "missile" in text or "sanctions" in text or "attacked" in text):
        return "分化"
    if "macro" in tags and ("inflation" in text or "yield" in text or "hawkish" in text):
        return "偏利空"
    if "macro" in tags and ("stimulus" in text or "rate cut" in text or "easing" in text):
        return "偏利多"
    if "technology" in tags and "ai" in text:
        return "偏利多"
    return "中性"



def infer_certainty(cluster: EventCluster) -> str:
    if cluster.official_confirmation and cluster.credibility_score >= 0.72:
        return "高"
    if cluster.confirmed_source_count >= 3 and cluster.credibility_score >= 0.72:
        return "高"
    if cluster.confirmed_source_count >= 2 and cluster.credibility_score >= 0.56:
        return "中"
    if len({item.source for item in cluster.articles}) >= 2 and cluster.credibility_score >= 0.50:
        return "中"
    return "低"



def infer_importance(score: float) -> str:
    if score >= 6.6:
        return "★★★★★"
    if score >= 5.3:
        return "★★★★"
    if score >= 4.0:
        return "★★★"
    if score >= 2.8:
        return "★★"
    return "★"



def is_macro_shock_story(cluster: EventCluster) -> bool:
    text = cluster_text(cluster)
    return any(term in text for term in MACRO_SHOCK_TERMS)



def is_side_signal_story(cluster: EventCluster, tags: list[str]) -> bool:
    text = cluster_text(cluster)
    source_count = len({item.source for item in cluster.articles})
    if is_macro_shock_story(cluster):
        return False
    if source_count == 1 and any(term in text for term in CORPORATE_TERMS):
        return True
    if source_count == 1 and any(term in text for term in COMMENTARY_TERMS):
        return True
    if "technology" in tags and "cyberattack" in text and source_count == 1:
        return True
    if "technology" in tags and ("apple" in text or "nvidia" in text or "microsoft" in text or "tesla" in text) and source_count == 1:
        return True
    return False



def score_cluster(cluster: EventCluster, now: datetime | None = None) -> float:
    current = now or datetime.utcnow()
    assess_cluster_credibility(cluster)
    rep = cluster.representative
    age_hours = max((current - rep.published_at).total_seconds() / 3600, 0.1)
    recency_score = max(0.0, 2.4 - min(age_hours, 24.0) / 8.0)
    source_score = rep.source_weight * 2.2
    spread_score = min(len({item.source for item in cluster.articles}), 5) * 0.45
    volume_score = min(len(cluster.articles), 5) * 0.25
    credibility_score = cluster.credibility_score * 1.2

    tags = infer_tags(cluster)
    keyword_score = 0.0
    if "geopolitics" in tags:
        keyword_score += 1.4
    if "macro" in tags:
        keyword_score += 1.3
    if "markets" in tags:
        keyword_score += 1.0
    if "energy" in tags:
        keyword_score += 1.0
    if "technology" in tags:
        keyword_score += 0.6

    penalty = 0.0
    if is_side_signal_story(cluster, tags):
        penalty += 1.55
        if len({item.source for item in cluster.articles}) == 1:
            penalty += 0.35
    if cluster.credibility_label == "低":
        penalty += 1.25
    if cluster.confirmed_source_count <= 1 and not cluster.official_confirmation:
        penalty += 0.35

    score = source_score + recency_score + spread_score + volume_score + keyword_score + credibility_score - penalty
    cluster.tags = tags
    cluster.direction = infer_direction(cluster, tags)
    cluster.certainty = infer_certainty(cluster)
    cluster.importance = infer_importance(score)
    cluster.score = round(score, 2)
    return cluster.score



def rank_clusters(clusters: list[EventCluster]) -> list[EventCluster]:
    now = datetime.utcnow()
    for cluster in clusters:
        score_cluster(cluster, now=now)

    return sorted(clusters, key=lambda item: item.score, reverse=True)



def summarize_tag_distribution(clusters: list[EventCluster]) -> dict[str, int]:
    counter = Counter()
    for cluster in clusters:
        counter.update(cluster.tags)
    return dict(counter)
