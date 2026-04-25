from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

from .config import ROOT_DIR
from .tracking import load_event_history


ETF_KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
FUND_HISTORY_URL = "https://api.fund.eastmoney.com/f10/lsjz"
DEFAULT_TIMEOUT = 12
HISTORY_PATH = ROOT_DIR / "outputs" / "fixed_buy_pool_history.json"
BACKFILL_WINDOWS = (20, 60, 120, 250)
WIN_LOOKBACK_WINDOWS = (60, 120, 250)
DEFAULT_HISTORY_LIMIT = 320

THEME_KEYWORDS: dict[str, tuple[str, ...]] = {
    "ai": ("ai", "artificial intelligence", "人工智能", "算力", "半导体", "芯片", "科技"),
    "energy": ("oil", "crude", "brent", "wti", "gas", "lng", "energy", "iran", "hormuz", "原油", "石油", "天然气", "能源", "伊朗", "霍尔木兹"),
    "gold": ("gold", "fed", "yield", "dollar", "war", "geopolitics", "黄金", "美联储", "收益率", "美元", "战争", "地缘"),
    "china_macro": ("china", "chinese", "pboc", "yuan", "cnh", "trade", "tariff", "stimulus", "中国", "人民币", "政策", "贸易", "关税", "刺激"),
    "new_energy": ("ev", "battery", "lithium", "solar", "renewable", "新能源", "锂电", "光伏"),
}

EVENT_THEME_TO_FIXED_POOL_THEME_KEYS: dict[str, tuple[str, ...]] = {
    "ai": ("ai_attack", "semiconductor", "growth_core"),
    "energy": ("power", "gold_insurance", "dividend_lowvol"),
    "gold": ("gold_insurance", "dividend_lowvol"),
    "china_macro": ("broad_core", "growth_core", "dividend_lowvol"),
    "new_energy": ("growth_core",),
}

THEME_LABELS: dict[str, str] = {
    "ai": "AI/科技",
    "energy": "能源/地缘",
    "gold": "黄金/避险",
    "china_macro": "中国宏观",
    "new_energy": "新能源",
}


def _safe_float(value: Any) -> float | None:
    try:
        if value in (None, "", "-"):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _secid(code: str) -> str:
    return ("1." if code.startswith(("5", "6", "9")) else "0.") + code


def _request(url: str, *, params: dict[str, Any] | None = None, timeout: int = DEFAULT_TIMEOUT) -> requests.Response:
    response = requests.get(
        url,
        params=params,
        timeout=timeout,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://fund.eastmoney.com/",
        },
    )
    response.raise_for_status()
    return response


def _parse_day(value: Any) -> date | None:
    if isinstance(value, date):
        return value

    raw = str(value or "").strip()
    if not raw:
        return None

    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            sample = raw[:10] if fmt == "%Y-%m-%d" else raw[:8]
            return datetime.strptime(sample, fmt).date()
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _first_valid_close(points: list[dict[str, Any]], index: int) -> float | None:
    if index < 0 or index >= len(points):
        return None
    return _safe_float(points[index].get("close"))


def _normalize_points(points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for point in points:
        point_day = _parse_day(point.get("date") or "")
        if point_day is None:
            continue
        row = dict(point)
        row["date"] = point_day.isoformat()
        normalized.append(row)
    normalized.sort(key=lambda item: item.get("date") or "")
    return normalized


def _pct_change(points: list[dict[str, Any]], offset: int) -> float | None:
    if len(points) <= offset:
        return None
    latest = _first_valid_close(points, len(points) - 1)
    base = _first_valid_close(points, len(points) - 1 - offset)
    if latest in (None, 0) or base in (None, 0):
        return None
    return round((latest - base) / base * 100, 3)


def _pct_change_for_window(points: list[dict[str, Any]], window_days: int) -> float | None:
    if window_days <= 1:
        return None
    return _pct_change(points, window_days - 1)


def _normalize_history_item(item: dict[str, Any]) -> dict[str, Any]:
    points = _normalize_points(list(item.get("history") or []))
    normalized = dict(item)
    normalized["history"] = points
    for window in BACKFILL_WINDOWS:
        normalized[f"change_{window}d_pct"] = _pct_change_for_window(points, window)
    return normalized


def _load_cache(path: Path = HISTORY_PATH) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _save_cache(payload: dict[str, Any], path: Path = HISTORY_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_etf_history(code: str, name: str, theme_key: str, timeout: int = DEFAULT_TIMEOUT, limit: int = DEFAULT_HISTORY_LIMIT) -> dict[str, Any]:
    response = _request(
        ETF_KLINE_URL,
        params={
            "secid": _secid(code),
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "klt": "101",
            "fqt": "1",
            "lmt": str(limit),
            "end": "20500101",
        },
        timeout=timeout,
    )
    payload = response.json()
    data = payload.get("data") or {}
    klines = data.get("klines") or []
    points: list[dict[str, Any]] = []
    for row in klines:
        parts = str(row).split(",")
        if len(parts) < 3:
            continue
        points.append({
            "date": parts[0],
            "open": _safe_float(parts[1]),
            "close": _safe_float(parts[2]),
            "high": _safe_float(parts[3]) if len(parts) > 3 else None,
            "low": _safe_float(parts[4]) if len(parts) > 4 else None,
            "volume": _safe_float(parts[5]) if len(parts) > 5 else None,
            "amount": _safe_float(parts[6]) if len(parts) > 6 else None,
        })
    points = _normalize_points(points)
    return {
        "code": code,
        "name": name,
        "type": "ETF",
        "theme_key": theme_key,
        "history": points,
        **{f"change_{window}d_pct": _pct_change_for_window(points, window) for window in BACKFILL_WINDOWS},
        "provider": "Eastmoney ETF kline",
    }


def fetch_fund_history_item(code: str, name: str, theme_key: str, timeout: int = DEFAULT_TIMEOUT, limit: int = DEFAULT_HISTORY_LIMIT) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    page_index = 1
    page_size = 50
    total_count = 0

    while len(rows) < limit:
        response = _request(
            FUND_HISTORY_URL,
            params={"fundCode": code, "pageIndex": page_index, "pageSize": page_size},
            timeout=timeout,
        )
        payload = response.json()
        data = payload.get("Data") or {}
        chunk = data.get("LSJZList") or []
        total_count = int(data.get("TotalCount") or total_count or 0)
        if not chunk:
            break
        rows.extend(chunk)
        if len(chunk) < page_size:
            break
        if total_count and len(rows) >= total_count:
            break
        page_index += 1
        if page_index > 8:
            break

    points = _normalize_points(
        list(
            reversed(
                [
                    {
                        "date": row.get("FSRQ") or "",
                        "close": _safe_float(row.get("DWJZ")),
                        "day_change_pct": _safe_float(row.get("JZZZL")),
                    }
                    for row in rows[:limit]
                    if row.get("FSRQ")
                ]
            )
        )
    )
    return {
        "code": code,
        "name": name,
        "type": "FUND",
        "theme_key": theme_key,
        "history": points,
        **{f"change_{window}d_pct": _pct_change_for_window(points, window) for window in BACKFILL_WINDOWS},
        "provider": "Eastmoney fund history",
    }


def fetch_fixed_pool_history(portfolio: dict[str, Any], timeout: int = DEFAULT_TIMEOUT) -> dict[str, Any]:
    cache = _load_cache()
    items: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    fixed_pool = list(((portfolio.get("decision_cockpit") or {}).get("fixed_buy_pool") or []))
    for item in fixed_pool:
        code = str(item.get("code") or "").strip()
        if not code:
            continue
        try:
            if str(item.get("type") or "").upper() == "FUND":
                history_item = fetch_fund_history_item(code, item.get("name") or code, item.get("theme_key") or "", timeout=timeout)
            else:
                history_item = fetch_etf_history(code, item.get("name") or code, item.get("theme_key") or "", timeout=timeout)
            history_item["role"] = item.get("role") or ""
            items.append(_normalize_history_item(history_item))
        except Exception as exc:
            cached = next((cached_item for cached_item in (cache.get("items") or []) if str(cached_item.get("code") or "") == code), None)
            if cached:
                items.append(_normalize_history_item(cached))
            else:
                failures.append({"code": code, "name": item.get("name") or code, "error": f"{type(exc).__name__}: {exc}"[:300]})

    payload = {
        "captured_at_utc": datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0).isoformat(),
        "provider": "Eastmoney fixed buy pool history",
        "items": items,
        "failures": failures,
        "coverage": {"configured_assets": len(fixed_pool), "returned_assets": len(items), "failed_assets": len(failures)},
    }
    _save_cache(payload)
    return payload


def _match_theme_keys(text: str) -> set[str]:
    lowered = text.lower()
    matched: set[str] = set()
    for theme_key, keywords in THEME_KEYWORDS.items():
        if any(keyword.lower() in lowered for keyword in keywords):
            matched.add(theme_key)
    return matched


def _history_points_by_code(fixed_pool_history: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    return {
        str(item.get("code") or ""): list(item.get("history") or [])
        for item in fixed_pool_history.get("items") or []
        if item.get("code")
    }


def _theme_to_codes(portfolio: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    pool = list(((portfolio.get("decision_cockpit") or {}).get("fixed_buy_pool") or []))
    by_theme_key = {
        str(item.get("theme_key") or ""): item
        for item in pool
        if item.get("theme_key") and item.get("code")
    }
    result: dict[str, list[dict[str, Any]]] = {}
    for event_theme, pool_theme_keys in EVENT_THEME_TO_FIXED_POOL_THEME_KEYS.items():
        refs: list[dict[str, Any]] = []
        for pool_theme_key in pool_theme_keys:
            item = by_theme_key.get(pool_theme_key)
            if item:
                refs.append(item)
        result[event_theme] = refs
    return result


def _find_start_index(points: list[dict[str, Any]], trigger_day: date) -> int | None:
    for index, point in enumerate(points):
        point_day = _parse_day(point.get("date") or "")
        if point_day and point_day >= trigger_day:
            return index
    return None


def _compute_forward_return(points: list[dict[str, Any]], start_index: int, horizon: int) -> float | None:
    end_index = start_index + horizon
    if start_index < 0 or end_index >= len(points):
        return None
    start_close = _safe_float(points[start_index].get("close"))
    end_close = _safe_float(points[end_index].get("close"))
    if start_close in (None, 0) or end_close in (None, 0):
        return None
    return round((end_close - start_close) / start_close * 100, 3)


def _leader_from_stats(stats: list[dict[str, Any]]) -> dict[str, Any] | None:
    ranked = sorted(
        stats,
        key=lambda item: (
            item.get("avg_return_pct") or -999,
            item.get("win_rate_pct") or -999,
            item.get("samples") or 0,
        ),
        reverse=True,
    )
    return ranked[0] if ranked else None


def _preferred_window(sample_counts: dict[int, int]) -> int | None:
    if sample_counts.get(250, 0) >= 6:
        return 250
    if sample_counts.get(120, 0) >= 4:
        return 120
    if sample_counts.get(60, 0) >= 2:
        return 60
    fallback = [window for window in WIN_LOOKBACK_WINDOWS if sample_counts.get(window, 0) > 0]
    return fallback[-1] if fallback else None


def build_fixed_pool_60d_panel(
    portfolio: dict[str, Any],
    event_route_rows: list[dict[str, Any]],
    fixed_pool_history: dict[str, Any] | None,
    lookback_days: int = 250,
) -> dict[str, Any]:
    fixed_pool_history = fixed_pool_history or _load_cache()
    history_items = [_normalize_history_item(item) for item in (fixed_pool_history.get("items") or [])]
    if not history_items:
        return {
            "backfill_lines": ["- 固定可买池历史回填暂不可用。"],
            "win_lines": ["- T+1/T+3/T+5 先手胜率暂不可用。"],
            "backfill_rows": [],
            "win_rows": [],
        }

    backfill_rows: list[dict[str, Any]] = []
    for item in history_items:
        points = list(item.get("history") or [])
        backfill_rows.append(
            {
                "code": item.get("code") or "",
                "name": item.get("name") or "",
                "type": item.get("type") or "",
                "theme_key": item.get("theme_key") or "",
                "days": len(points),
                "change_20d_pct": item.get("change_20d_pct"),
                "change_60d_pct": item.get("change_60d_pct"),
                "change_120d_pct": item.get("change_120d_pct"),
                "change_250d_pct": item.get("change_250d_pct"),
                "latest_close": _safe_float(points[-1].get("close")) if points else None,
                "history": points,
            }
        )

    backfill_lines = [
        "- 已为固定可买池回填最近约 120/250 个交易日价格/净值，用于看中期持续性和先手胜率，而不是只看当天涨跌。"
    ]
    day_spans = [row.get("days") or 0 for row in backfill_rows if row.get("days")]
    if day_spans:
        backfill_lines.append(
            f"- 当前覆盖跨度：最短 {min(day_spans)} 天，最长 {max(day_spans)} 天；新基金/联接基金若历史不足，120/250日列会留空。"
        )
    for window in (60, 120, 250):
        leaders = sorted(
            [row for row in backfill_rows if row.get(f"change_{window}d_pct") is not None],
            key=lambda row: row.get(f"change_{window}d_pct") or -999,
            reverse=True,
        )[:3]
        if leaders:
            backfill_lines.append(
                f"- 近{window}日强弱："
                + "；".join(
                    f"{row.get('name')}({row.get('code')}) {row.get(f'change_{window}d_pct', 0.0):+.2f}%"
                    for row in leaders
                )
                + "。"
            )

    event_records = load_event_history()
    event_days = [
        parsed
        for item in event_records
        if (parsed := _parse_day(item.get("generated_at_utc") or "")) is not None
    ]
    latest_day = max(event_days, default=None)
    latest_reference_day = latest_day or date.today()
    cutoff_day = latest_reference_day - timedelta(days=lookback_days)
    daily_themes: dict[date, set[str]] = {}
    for record in event_records:
        record_day = _parse_day(record.get("generated_at_utc") or "")
        if not record_day or record_day < cutoff_day:
            continue
        text = " ".join(
            str(record.get(key) or "")
            for key in ("theme", "title", "summary")
        ) + " " + " ".join(str(tag) for tag in (record.get("tags") or []))
        matched = _match_theme_keys(text)
        if not matched:
            continue
        daily_themes.setdefault(record_day, set()).update(matched)

    relevant_event_themes = list(dict.fromkeys(str(item.get("theme_key") or "") for item in event_route_rows if item.get("theme_key")))
    if not relevant_event_themes:
        relevant_event_themes = list(EVENT_THEME_TO_FIXED_POOL_THEME_KEYS.keys())

    points_by_code = {
        str(item.get("code") or ""): list(item.get("history") or [])
        for item in history_items
        if item.get("code")
    }
    refs_by_theme = _theme_to_codes(portfolio)
    win_rows: list[dict[str, Any]] = []
    win_lines: list[str] = []
    for event_theme in relevant_event_themes[:3]:
        theme_refs = refs_by_theme.get(event_theme) or []
        row = {
            "theme_key": event_theme,
            "sample_days": {},
            "leaders": {},
            "selected_window": None,
            "selected_leaders": {},
        }
        theme_label = THEME_LABELS.get(event_theme, event_theme)
        sample_counts: dict[int, int] = {}
        for window in WIN_LOOKBACK_WINDOWS:
            window_cutoff = latest_reference_day - timedelta(days=window)
            theme_days = sorted(
                day
                for day, themes in daily_themes.items()
                if event_theme in themes and day >= window_cutoff
            )
            sample_counts[window] = len(theme_days)
            row["sample_days"][f"d{window}"] = len(theme_days)

            horizon_stats: dict[int, list[dict[str, Any]]] = {1: [], 3: [], 5: []}
            for ref in theme_refs:
                code = str(ref.get("code") or "")
                points = points_by_code.get(code) or []
                if not points:
                    continue
                for horizon in (1, 3, 5):
                    returns: list[float] = []
                    for trigger_day in theme_days:
                        start_index = _find_start_index(points, trigger_day)
                        if start_index is None:
                            continue
                        result = _compute_forward_return(points, start_index, horizon)
                        if result is not None:
                            returns.append(result)
                    if not returns:
                        continue
                    positive = [item for item in returns if item > 0]
                    horizon_stats[horizon].append(
                        {
                            "code": code,
                            "name": ref.get("name") or code,
                            "samples": len(returns),
                            "avg_return_pct": round(sum(returns) / len(returns), 3),
                            "win_rate_pct": round(len(positive) / len(returns) * 100, 1),
                        }
                    )

            row["leaders"][f"d{window}"] = {
                f"t{horizon}": _leader_from_stats(horizon_stats[horizon])
                for horizon in (1, 3, 5)
            }

        preferred_window = _preferred_window(sample_counts)
        row["selected_window"] = preferred_window
        row["selected_leaders"] = row["leaders"].get(f"d{preferred_window}", {}) if preferred_window else {}

        if not preferred_window:
            win_lines.append(f"- {theme_label}：近 60/120/250 天主题样本日 0/0/0 个，先继续积累。")
            win_rows.append(row)
            continue

        line_parts: list[str] = []
        for horizon in (1, 3, 5):
            leader = (row["selected_leaders"] or {}).get(f"t{horizon}")
            if leader:
                line_parts.append(
                    f"T+{horizon} 先手更常见 {leader.get('name')}({leader.get('code')})，胜率 {leader.get('win_rate_pct', 0.0):.0f}%"
                )

        sample_text = "/".join(str(sample_counts[window]) for window in WIN_LOOKBACK_WINDOWS)
        if line_parts:
            sample_note = "样本仍偏少，仅供观察；" if sample_counts.get(preferred_window, 0) < 8 else ""
            win_lines.append(
                f"- {theme_label}：近 60/120/250 天主题样本日 {sample_text} 个；当前优先参考近 {preferred_window} 天；{sample_note}"
                + "；".join(line_parts)
                + "。"
            )
        else:
            win_lines.append(
                f"- {theme_label}：近 60/120/250 天主题样本日 {sample_text} 个，但对应固定可买池还没有足够的 T+1/T+3/T+5 样本。"
            )
        win_rows.append(row)

    win_lines.append("- 说明：这块面板基于‘固定可买池 + 最近可用事件日 + 120/250日价格回填’统计，当前更适合做先手排序，不适合当成机械回测。")
    return {
        "backfill_lines": backfill_lines,
        "win_lines": win_lines,
        "backfill_rows": backfill_rows,
        "win_rows": win_rows,
    }
