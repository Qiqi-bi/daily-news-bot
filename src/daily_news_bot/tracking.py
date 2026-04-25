from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .models import EventCluster


WORD_RE = re.compile(r"[a-zA-Z0-9\u4e00-\u9fff]{2,}")
STOPWORDS = {
    "the", "and", "for", "with", "this", "that", "from", "amid", "will", "after", "news", "markets", "market",
    "today", "world", "business", "stock", "stocks", "prices", "price", "global", "update",
}
HISTORY_PATH = Path(__file__).resolve().parents[2] / "outputs" / "event_history.json"



def _tokenize(text: str) -> set[str]:
    return {token.lower() for token in WORD_RE.findall(text) if token.lower() not in STOPWORDS}



def _cluster_text(cluster: EventCluster) -> str:
    rep = cluster.representative
    return " ".join(part for part in [cluster.theme, rep.title, rep.summary] if part)



def _history_record(cluster: EventCluster, generated_at: datetime) -> dict[str, Any]:
    rep = cluster.representative
    return {
        "generated_at_utc": generated_at.isoformat(),
        "cluster_id": cluster.cluster_id,
        "theme": cluster.theme,
        "title": rep.title,
        "summary": rep.summary,
        "tags": cluster.tags,
        "direction": cluster.direction,
        "importance": cluster.importance,
        "score": cluster.score,
        "tokens": sorted(_tokenize(_cluster_text(cluster))),
    }



def load_event_history(path: Path = HISTORY_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []



def save_event_history(records: list[dict[str, Any]], path: Path = HISTORY_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")



def _similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    inter = len(left & right)
    if inter == 0:
        return 0.0
    return inter / max(min(len(left), len(right)), 1)



def build_tracking_summary(
    clusters: list[EventCluster],
    generated_at: datetime,
    path: Path = HISTORY_PATH,
    lookback_days: int = 7,
) -> dict[str, Any]:
    history = load_event_history(path)
    cutoff = generated_at - timedelta(days=lookback_days)
    recent_history = []
    for item in history:
        try:
            item_time = datetime.fromisoformat(item.get("generated_at_utc", ""))
        except ValueError:
            continue
        if item_time >= cutoff and item_time < generated_at:
            recent_history.append(item)

    summaries: list[dict[str, Any]] = []
    for cluster in clusters:
        current_tokens = _tokenize(_cluster_text(cluster))
        matches: list[dict[str, Any]] = []
        for item in recent_history:
            score = _similarity(current_tokens, set(item.get("tokens") or []))
            if score >= 0.45:
                matches.append({**item, "match_score": round(score, 3)})
        matches.sort(key=lambda item: (item.get("generated_at_utc", ""), item.get("match_score", 0)), reverse=True)
        recent_titles = [item.get("title", "") for item in matches[:3] if item.get("title")]
        last_seen = matches[0].get("generated_at_utc") if matches else None
        direction_counter = Counter(item.get("direction", "") for item in matches if item.get("direction"))
        summaries.append(
            {
                "cluster_id": cluster.cluster_id,
                "theme": cluster.theme,
                "seen_recently": bool(matches),
                "match_count": len(matches),
                "last_seen_utc": last_seen,
                "recent_titles": recent_titles,
                "recent_direction_bias": direction_counter.most_common(1)[0][0] if direction_counter else None,
            }
        )

    return {
        "generated_at_utc": generated_at.isoformat(),
        "lookback_days": lookback_days,
        "tracked_events": summaries,
    }



def update_event_history(
    clusters: list[EventCluster],
    generated_at: datetime,
    path: Path = HISTORY_PATH,
    keep_days: int = 400,
) -> None:
    history = load_event_history(path)
    cutoff = generated_at - timedelta(days=keep_days)
    kept: list[dict[str, Any]] = []
    for item in history:
        try:
            item_time = datetime.fromisoformat(item.get("generated_at_utc", ""))
        except ValueError:
            continue
        if item_time >= cutoff:
            kept.append(item)

    for cluster in clusters:
        kept.append(_history_record(cluster, generated_at))

    save_event_history(kept, path)
