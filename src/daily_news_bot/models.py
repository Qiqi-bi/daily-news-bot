from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class SourceDef:
    name: str
    url: str
    category: str
    region: str
    weight: float = 1.0
    official: bool = False


@dataclass(slots=True)
class Article:
    title: str
    url: str
    source: str
    category: str
    region: str
    source_weight: float
    published_at: datetime
    summary: str = ""
    content: str = ""
    official_source: bool = False
    source_domain: str = ""
    credibility_score: float = 0.0
    credibility_label: str = "未知"
    credibility_flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["published_at"] = self.published_at.isoformat()
        return data


@dataclass(slots=True)
class EventCluster:
    cluster_id: str
    theme: str
    articles: list[Article] = field(default_factory=list)
    score: float = 0.0
    tags: list[str] = field(default_factory=list)
    direction: str = "中性"
    certainty: str = "中"
    importance: str = "★★★"
    credibility_score: float = 0.0
    credibility_label: str = "未知"
    confirmed_source_count: int = 0
    official_confirmation: bool = False
    credibility_notes: list[str] = field(default_factory=list)

    @property
    def representative(self) -> Article:
        return sorted(
            self.articles,
            key=lambda item: (item.source_weight, item.published_at.timestamp()),
            reverse=True,
        )[0]

    def to_dict(self) -> dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "theme": self.theme,
            "score": self.score,
            "tags": self.tags,
            "direction": self.direction,
            "certainty": self.certainty,
            "importance": self.importance,
            "credibility_score": self.credibility_score,
            "credibility_label": self.credibility_label,
            "confirmed_source_count": self.confirmed_source_count,
            "official_confirmation": self.official_confirmation,
            "credibility_notes": list(self.credibility_notes),
            "representative": self.representative.to_dict(),
            "articles": [article.to_dict() for article in self.articles],
        }
