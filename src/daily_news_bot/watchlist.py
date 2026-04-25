from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

from .config import ROOT_DIR
from .models import EventCluster


STATE_PATH = ROOT_DIR / "outputs" / "watchlist.json"
CONFIG_PATH = ROOT_DIR / "config" / "watchlist.yaml"
WORD_RE = re.compile(r"[a-zA-Z0-9\u4e00-\u9fff]{2,}")
STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "news",
    "market",
    "markets",
    "stock",
    "stocks",
    "update",
    "today",
    "global",
}


def _safe_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _tokenize(text: str) -> set[str]:
    return {token.lower() for token in WORD_RE.findall(text or "") if token.lower() not in STOPWORDS}


def _hash_id(prefix: str, text: str) -> str:
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"items": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"items": []}
    if isinstance(payload, list):
        return {"items": payload}
    if isinstance(payload, dict):
        payload.setdefault("items", [])
        return payload
    return {"items": []}


def _load_config(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or yaml is None:
        return []
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        return [item for item in payload.get("watchlist") or [] if isinstance(item, dict)]
    return []


def _normalize_entry(raw: dict[str, Any], generated_at: datetime, source: str) -> dict[str, Any]:
    entry = dict(raw)
    title = str(entry.get("title") or entry.get("theme") or entry.get("name") or entry.get("symbol") or "watch").strip()
    entry["id"] = str(entry.get("id") or _hash_id(source, title)).strip()
    entry["title"] = title
    entry["type"] = str(entry.get("type") or "news_theme").strip()
    entry["source"] = str(entry.get("source") or source)
    entry["enabled"] = bool(entry.get("enabled", True))
    entry["status"] = str(entry.get("status") or "active")
    entry["created_at_utc"] = str(entry.get("created_at_utc") or generated_at.isoformat())
    entry["trigger_count"] = int(entry.get("trigger_count") or 0)
    entry["repeat"] = bool(entry.get("repeat", False))
    entry["action"] = str(entry.get("action") or entry.get("note") or "复核事件、价格和仓位纪律后再决定。")
    keywords = entry.get("keywords")
    if isinstance(keywords, str):
        entry["keywords"] = [keywords]
    elif isinstance(keywords, list):
        entry["keywords"] = [str(item) for item in keywords if str(item).strip()]
    else:
        entry["keywords"] = []
    definition_payload = {
        key: entry.get(key)
        for key in (
            "type",
            "symbol",
            "name",
            "asset",
            "group",
            "metric",
            "operator",
            "threshold",
            "upper_threshold",
            "lower_threshold",
            "keywords",
            "min_keyword_matches",
            "min_occurrences",
            "similarity_threshold",
            "action",
            "repeat",
            "enabled",
        )
    }
    entry["definition_hash"] = hashlib.sha1(
        json.dumps(definition_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:12]
    return entry


def _merge_config_items(
    state_items: dict[str, dict[str, Any]],
    config_items: list[dict[str, Any]],
    generated_at: datetime,
) -> None:
    for raw in config_items:
        if raw.get("enabled") is False:
            continue
        incoming = _normalize_entry(raw, generated_at, "config")
        existing = state_items.get(incoming["id"], {})
        preserved = {"created_at_utc": existing.get("created_at_utc")} if existing.get("created_at_utc") else {}
        if existing.get("definition_hash") == incoming.get("definition_hash"):
            preserved.update(
                {
                    key: existing.get(key)
                    for key in (
                        "last_checked_at_utc",
                        "last_triggered_at_utc",
                        "trigger_count",
                        "status",
                    )
                    if existing.get(key) is not None
                }
            )
        merged = {**incoming, **preserved}
        if merged.get("repeat") and merged.get("status") == "triggered":
            merged["status"] = "active"
        state_items[merged["id"]] = merged


def _cluster_text(cluster: EventCluster) -> str:
    rep = cluster.representative
    return " ".join(
        str(part)
        for part in [cluster.theme, rep.title, rep.summary, rep.source, " ".join(cluster.tags or [])]
        if part
    )


def _similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / max(min(len(left), len(right)), 1)


def _market_items(market_snapshot: dict[str, Any] | None, entry: dict[str, Any]) -> list[dict[str, Any]]:
    items = list((market_snapshot or {}).get("items") or [])
    symbol = str(entry.get("symbol") or "").lower()
    name = str(entry.get("name") or entry.get("asset") or "").lower()
    group = str(entry.get("group") or "").lower()
    if symbol:
        return [item for item in items if str(item.get("symbol") or "").lower() == symbol]
    if name:
        return [item for item in items if name in str(item.get("name") or "").lower()]
    if group:
        return [item for item in items if str(item.get("group") or "").lower() == group]
    return []


def _portfolio_metric_value(portfolio_payload: dict[str, Any] | None, metric: str) -> float | None:
    portfolio = portfolio_payload or {}
    summary = portfolio.get("summary") or {}
    quotes = portfolio.get("portfolio_quotes") or {}
    exposures = quotes.get("actual_exposures") or {}
    for source in (summary, quotes, exposures):
        if metric in source:
            return _safe_float(source.get(metric))
    return None


def _compare(value: float | None, entry: dict[str, Any]) -> bool:
    if value is None:
        return False
    operator = str(entry.get("operator") or entry.get("condition") or ">=").strip()
    threshold = _safe_float(entry.get("threshold"))
    upper = _safe_float(entry.get("upper_threshold"))
    lower = _safe_float(entry.get("lower_threshold"))
    if operator in {">", "gt"} and threshold is not None:
        return value > threshold
    if operator in {">=", "gte"} and threshold is not None:
        return value >= threshold
    if operator in {"<", "lt"} and threshold is not None:
        return value < threshold
    if operator in {"<=", "lte"} and threshold is not None:
        return value <= threshold
    if operator == "between" and lower is not None and upper is not None:
        return lower <= value <= upper
    if operator == "outside" and lower is not None and upper is not None:
        return value < lower or value > upper
    return False


def _condition_text(entry: dict[str, Any]) -> str:
    entry_type = entry.get("type")
    if entry_type == "price":
        metric = entry.get("metric") or "price"
        target = entry.get("symbol") or entry.get("name") or entry.get("group") or "asset"
        return f"{target} {metric} {entry.get('operator', '>=')} {entry.get('threshold', '')}".strip()
    if entry_type == "portfolio_metric":
        return f"{entry.get('metric')} {entry.get('operator', '>=')} {entry.get('threshold', '')}".strip()
    if entry_type in {"news_theme", "event_followup"}:
        keywords = " / ".join(entry.get("keywords") or []) or entry.get("title", "")
        return f"新闻再次出现或关键词命中：{keywords}"
    return str(entry.get("condition_text") or entry.get("condition") or "条件满足")


def _evaluate_price(entry: dict[str, Any], market_snapshot: dict[str, Any] | None) -> tuple[bool, str]:
    metric = str(entry.get("metric") or "price")
    candidates = _market_items(market_snapshot, entry)
    if not candidates:
        return False, "未找到对应市场价格"
    observed_parts: list[str] = []
    for item in candidates:
        value = _safe_float(item.get(metric))
        observed_parts.append(f"{item.get('name') or item.get('symbol')} {metric}={value if value is not None else '未知'}")
        if _compare(value, entry):
            return True, observed_parts[-1]
    return False, "；".join(observed_parts[:3])


def _evaluate_portfolio_metric(entry: dict[str, Any], portfolio_payload: dict[str, Any] | None) -> tuple[bool, str]:
    metric = str(entry.get("metric") or "")
    value = _portfolio_metric_value(portfolio_payload, metric)
    observed = f"{metric}={value if value is not None else '未知'}"
    return _compare(value, entry), observed


def _evaluate_news(entry: dict[str, Any], clusters: list[EventCluster]) -> tuple[bool, str]:
    keywords = [str(item).lower() for item in entry.get("keywords") or [] if str(item).strip()]
    entry_tokens = set(entry.get("tokens") or []) or _tokenize(" ".join(keywords + [str(entry.get("title") or "")]))
    min_keyword_matches = int(entry.get("min_keyword_matches") or 1)
    similarity_threshold = _safe_float(entry.get("similarity_threshold"))
    if similarity_threshold is None:
        similarity_threshold = 0.35 if entry.get("type") == "event_followup" else 0.2

    matches: list[str] = []
    for cluster in clusters:
        text = _cluster_text(cluster)
        lower_text = text.lower()
        keyword_hits = sum(1 for keyword in keywords if keyword and keyword in lower_text)
        score = _similarity(entry_tokens, _tokenize(text))
        if keyword_hits >= min_keyword_matches or score >= similarity_threshold:
            matches.append(cluster.representative.title)

    min_occurrences = int(entry.get("min_occurrences") or 1)
    return len(matches) >= min_occurrences, "；".join(matches[:3]) or "未命中"


def _evaluate_entry(
    entry: dict[str, Any],
    clusters: list[EventCluster],
    market_snapshot: dict[str, Any] | None,
    portfolio_payload: dict[str, Any] | None,
) -> tuple[bool, str]:
    entry_type = entry.get("type")
    if entry_type == "price":
        return _evaluate_price(entry, market_snapshot)
    if entry_type == "portfolio_metric":
        return _evaluate_portfolio_metric(entry, portfolio_payload)
    if entry_type in {"news_theme", "event_followup"}:
        return _evaluate_news(entry, clusters)
    return False, "未知提醒类型"


def _auto_event_entries(clusters: list[EventCluster], generated_at: datetime, days: int = 7) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    expires_at = (generated_at + timedelta(days=days)).isoformat()
    for cluster in clusters[:5]:
        rep = cluster.representative
        text = _cluster_text(cluster)
        tokens = sorted(_tokenize(text))
        if not tokens:
            continue
        entry_id = _hash_id("event", rep.title)
        keywords = list(cluster.tags or [])[:5]
        keywords.extend(token for token in tokens[:8] if token not in keywords)
        entries.append(
            {
                "id": entry_id,
                "type": "event_followup",
                "title": f"跟踪：{rep.title}",
                "keywords": keywords[:12],
                "tokens": tokens[:40],
                "action": "如果下次再次出现，检查是否已经从新闻走向价格确认；未确认则继续观察，不自动行动。",
                "created_at_utc": generated_at.isoformat(),
                "expires_at_utc": expires_at,
                "status": "active",
                "source": "auto_event",
                "repeat": False,
            }
        )
    return entries


def _is_old_inactive(entry: dict[str, Any], generated_at: datetime, keep_days: int) -> bool:
    if entry.get("status") == "active":
        return False
    timestamp = _parse_dt(entry.get("last_triggered_at_utc")) or _parse_dt(entry.get("expires_at_utc")) or _parse_dt(entry.get("created_at_utc"))
    if timestamp is None:
        return False
    return timestamp < generated_at - timedelta(days=keep_days)


def _line_for_item(prefix: str, item: dict[str, Any]) -> str:
    condition = item.get("condition_text") or _condition_text(item)
    observed = item.get("observed") or "未记录"
    action = item.get("action") or "复核后再决定"
    return f"- {prefix}｜{item.get('title')}｜条件：{condition}｜当前：{observed}｜动作：{action}"


def _summary_lines(summary: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for item in summary.get("triggered_items") or []:
        lines.append(_line_for_item("已触发", item))
    for item in summary.get("new_items") or []:
        lines.append(_line_for_item("新增跟踪", item))
    active_items = summary.get("active_items") or []
    if active_items:
        lines.append(f"- 继续盯：{len(active_items)} 条有效提醒；其中前 5 条：" + "；".join(str(item.get("title")) for item in active_items[:5]))
    if not lines:
        lines.append("- 当前没有触发中的提醒；系统会继续保留有效 watchlist，下一次运行自动复核。")
    if summary.get("expired_count"):
        lines.append(f"- 已过期归档：{summary.get('expired_count')} 条。")
    return lines


def evaluate_watchlist(
    *,
    generated_at: datetime,
    clusters: list[EventCluster],
    market_snapshot: dict[str, Any] | None,
    portfolio_payload: dict[str, Any] | None = None,
    state_path: Path = STATE_PATH,
    config_path: Path = CONFIG_PATH,
    keep_days: int = 180,
) -> dict[str, Any]:
    state = _load_json(state_path)
    items_by_id = {
        str(item.get("id")): _normalize_entry(item, generated_at, str(item.get("source") or "state"))
        for item in state.get("items") or []
        if isinstance(item, dict) and item.get("id")
    }
    _merge_config_items(items_by_id, _load_config(config_path), generated_at)

    triggered: list[dict[str, Any]] = []
    expired_count = 0
    for entry in list(items_by_id.values()):
        if not entry.get("enabled", True):
            continue
        if entry.get("status") != "active" and not entry.get("repeat"):
            continue
        expires_at = _parse_dt(entry.get("expires_at_utc"))
        if expires_at and generated_at > expires_at:
            entry["status"] = "expired"
            entry["last_checked_at_utc"] = generated_at.isoformat()
            expired_count += 1
            continue

        is_triggered, observed = _evaluate_entry(entry, clusters, market_snapshot, portfolio_payload)
        entry["last_checked_at_utc"] = generated_at.isoformat()
        entry["last_observed"] = observed
        if is_triggered:
            entry["trigger_count"] = int(entry.get("trigger_count") or 0) + 1
            entry["last_triggered_at_utc"] = generated_at.isoformat()
            if not entry.get("repeat"):
                entry["status"] = "triggered"
            triggered.append({**entry, "observed": observed, "condition_text": _condition_text(entry)})

    new_items: list[dict[str, Any]] = []
    for auto_entry in _auto_event_entries(clusters, generated_at):
        existing = items_by_id.get(auto_entry["id"])
        if existing is None:
            items_by_id[auto_entry["id"]] = auto_entry
            new_items.append({**auto_entry, "observed": "从本次日报新增", "condition_text": _condition_text(auto_entry)})
        elif existing.get("status") == "active":
            existing["expires_at_utc"] = auto_entry["expires_at_utc"]
            existing["keywords"] = auto_entry["keywords"]
            existing["tokens"] = auto_entry["tokens"]

    items = [
        item
        for item in items_by_id.values()
        if not _is_old_inactive(item, generated_at, keep_days)
    ]
    items.sort(key=lambda item: (item.get("status") != "active", str(item.get("expires_at_utc") or ""), str(item.get("title") or "")))
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps({"updated_at_utc": generated_at.isoformat(), "items": items}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    active_items = [item for item in items if item.get("status") == "active" and item.get("enabled", True)]
    summary = {
        "generated_at_utc": generated_at.isoformat(),
        "state_path": str(state_path),
        "config_path": str(config_path),
        "active_count": len(active_items),
        "triggered_count": len(triggered),
        "expired_count": expired_count,
        "new_count": len(new_items),
        "triggered_items": triggered,
        "new_items": new_items,
        "active_items": active_items[:20],
    }
    summary["lines"] = _summary_lines(summary)
    return summary


def render_watchlist_markdown(summary: dict[str, Any] | None) -> str:
    if not summary:
        return ""
    lines = ["## 待办与触发提醒", ""]
    lines.extend(summary.get("lines") or [])
    return "\n".join(lines).strip() + "\n"
