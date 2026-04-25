from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from .config import ROOT_DIR


FUND_ESTIMATE_URL = "https://fundgz.1234567.com.cn/js/{code}.js"
FUND_HISTORY_URL = "https://api.fund.eastmoney.com/f10/lsjz"
DEFAULT_TIMEOUT = 10
HISTORY_PATH = ROOT_DIR / "outputs" / "portfolio_history.json"
JSONP_RE = re.compile(r"jsonpgz\((.*)\);?", re.DOTALL)


def _safe_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _movement(change_pct: float | None) -> str:
    if change_pct is None:
        return "未知"
    if change_pct > 0.35:
        return "上涨"
    if change_pct < -0.35:
        return "下跌"
    return "震荡"


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


def fetch_fund_estimate(code: str, timeout: int = DEFAULT_TIMEOUT) -> dict[str, Any]:
    response = _request(FUND_ESTIMATE_URL.format(code=code), timeout=timeout)
    match = JSONP_RE.search(response.text.strip())
    if not match:
        raise ValueError(f"Unexpected estimate payload for {code}")
    payload = json.loads(match.group(1))

    official_nav = _safe_float(payload.get("dwjz"))
    estimate_nav = _safe_float(payload.get("gsz"))
    day_change_pct = _safe_float(payload.get("gszzl"))
    estimate_gap_pct = None
    if official_nav not in (None, 0) and estimate_nav is not None:
        estimate_gap_pct = round((estimate_nav - official_nav) / official_nav * 100, 3)

    return {
        "code": code,
        "name": payload.get("name") or code,
        "official_nav_date": payload.get("jzrq") or "",
        "official_nav": official_nav,
        "estimate_nav": estimate_nav,
        "day_change_pct": day_change_pct,
        "movement": _movement(day_change_pct),
        "estimate_gap_pct": estimate_gap_pct,
        "estimate_time": payload.get("gztime") or "",
        "provider": "Eastmoney fundgz",
    }


def fetch_fund_history(code: str, page_size: int = 10, timeout: int = DEFAULT_TIMEOUT) -> list[dict[str, Any]]:
    response = _request(
        FUND_HISTORY_URL,
        params={"fundCode": code, "pageIndex": 1, "pageSize": page_size},
        timeout=timeout,
    )
    payload = response.json()
    rows = ((payload.get("Data") or {}).get("LSJZList") or [])
    result: list[dict[str, Any]] = []
    for row in rows:
        result.append(
            {
                "date": row.get("FSRQ") or "",
                "nav": _safe_float(row.get("DWJZ")),
                "day_change_pct": _safe_float(row.get("JZZZL")),
            }
        )
    return result


def fetch_holding_quote(holding: dict[str, Any], total_value_cny: float, timeout: int = DEFAULT_TIMEOUT) -> dict[str, Any]:
    code = str(holding.get("code") or "").strip()
    if not code:
        raise ValueError(f"Holding {holding.get('name', '未知持仓')} missing code")

    estimate = fetch_fund_estimate(code, timeout=timeout)
    history = fetch_fund_history(code, page_size=10, timeout=timeout)
    week_base_nav = None
    week_change_pct = None
    if len(history) >= 6 and history[5].get("nav") not in (None, 0):
        week_base_nav = history[5]["nav"]
    elif len(history) >= 2 and history[-1].get("nav") not in (None, 0):
        week_base_nav = history[-1]["nav"]

    latest_official_nav = estimate.get("official_nav") or (history[0].get("nav") if history else None)
    if latest_official_nav not in (None, 0) and week_base_nav not in (None, 0):
        week_change_pct = round((latest_official_nav - week_base_nav) / week_base_nav * 100, 3)

    configured_weight_pct = _safe_float(holding.get("weight_pct"))
    shares = _safe_float(holding.get("shares"))
    cost_nav = _safe_float(holding.get("cost_nav"))
    latest_value_nav = estimate.get("estimate_nav") or latest_official_nav
    estimated_position_value = None
    invested_cost_cny = None
    unrealized_pnl_cny = None
    unrealized_pnl_pct = None
    if shares is not None and latest_value_nav is not None:
        estimated_position_value = round(shares * latest_value_nav, 2)
    elif configured_weight_pct is not None:
        estimated_position_value = round(total_value_cny * configured_weight_pct / 100, 2)

    if shares is not None and cost_nav is not None:
        invested_cost_cny = round(shares * cost_nav, 2)
    if estimated_position_value is not None and invested_cost_cny not in (None, 0):
        unrealized_pnl_cny = round(estimated_position_value - invested_cost_cny, 2)
        unrealized_pnl_pct = round(unrealized_pnl_cny / invested_cost_cny * 100, 3)

    weight_pct = configured_weight_pct or 0.0
    daily_contribution_pct = None
    if estimate.get("day_change_pct") is not None:
        daily_contribution_pct = round(weight_pct * estimate["day_change_pct"] / 100, 3)
    weekly_contribution_pct = None
    if week_change_pct is not None:
        weekly_contribution_pct = round(weight_pct * week_change_pct / 100, 3)

    return {
        "holding_name": holding.get("name") or code,
        "code": code,
        "type": holding.get("type") or "",
        "bucket": holding.get("bucket") or "",
        "sleeve": holding.get("sleeve") or "",
        "core": bool(holding.get("core", False)),
        "weight_pct": weight_pct,
        "configured_weight_pct": configured_weight_pct,
        "shares": shares,
        "cost_nav": cost_nav,
        "official_name": estimate.get("name") or holding.get("name") or code,
        "official_nav_date": estimate.get("official_nav_date") or "",
        "official_nav": latest_official_nav,
        "estimate_nav": estimate.get("estimate_nav"),
        "estimate_time": estimate.get("estimate_time") or "",
        "day_change_pct": estimate.get("day_change_pct"),
        "week_change_pct": week_change_pct,
        "estimate_gap_pct": estimate.get("estimate_gap_pct"),
        "movement": estimate.get("movement") or "未知",
        "estimated_position_value_cny": estimated_position_value,
        "invested_cost_cny": invested_cost_cny,
        "unrealized_pnl_cny": unrealized_pnl_cny,
        "unrealized_pnl_pct": unrealized_pnl_pct,
        "daily_contribution_pct": daily_contribution_pct,
        "weekly_contribution_pct": weekly_contribution_pct,
        "history": history,
        "provider": estimate.get("provider") or "Eastmoney fundgz",
    }


def fetch_portfolio_quotes(portfolio: dict[str, Any], timeout: int = DEFAULT_TIMEOUT) -> dict[str, Any]:
    profile = portfolio.get("profile") or {}
    total_value_cny = _safe_float(profile.get("total_value_cny")) or 0.0
    items: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for holding in portfolio.get("holdings") or []:
        try:
            items.append(fetch_holding_quote(holding, total_value_cny, timeout=timeout))
        except Exception as exc:
            failures.append(
                {
                    "holding_name": holding.get("name") or "未知持仓",
                    "code": str(holding.get("code") or ""),
                    "error": f"{type(exc).__name__}: {exc}"[:300],
                }
            )

    actual_total_value_cny = round(
        sum(item.get("estimated_position_value_cny") or 0.0 for item in items), 2
    ) if items else None
    actual_total_cost_cny = round(
        sum(item.get("invested_cost_cny") or 0.0 for item in items), 2
    ) if items else None
    actual_total_pnl_cny = None
    actual_total_pnl_pct = None
    if actual_total_value_cny is not None and actual_total_cost_cny not in (None, 0):
        actual_total_pnl_cny = round(actual_total_value_cny - actual_total_cost_cny, 2)
        actual_total_pnl_pct = round(actual_total_pnl_cny / actual_total_cost_cny * 100, 3)

    if actual_total_value_cny not in (None, 0):
        for item in items:
            value = item.get("estimated_position_value_cny")
            if value is not None:
                item["actual_weight_pct"] = round(value / actual_total_value_cny * 100, 3)
                item["weight_pct"] = item["actual_weight_pct"]

    core_weight_pct = round(
        sum(item.get("actual_weight_pct") or 0.0 for item in items if item.get("core")), 3
    ) if items else None
    direct_ai_weight_pct = round(
        sum(item.get("actual_weight_pct") or 0.0 for item in items if item.get("bucket") == "ai_direct"), 3
    ) if items else None
    growth_tech_weight_pct = round(
        sum(item.get("actual_weight_pct") or 0.0 for item in items if item.get("bucket") in {"ai_direct", "growth_broad"}), 3
    ) if items else None
    gold_weight_pct = round(
        sum(item.get("actual_weight_pct") or 0.0 for item in items if item.get("bucket") == "gold"), 3
    ) if items else None
    stable_core_weight_pct = round(
        sum(item.get("actual_weight_pct") or 0.0 for item in items if item.get("sleeve") == "stable_core"), 3
    ) if items else None
    growth_core_weight_pct = round(
        sum(item.get("actual_weight_pct") or 0.0 for item in items if item.get("sleeve") == "growth_core"), 3
    ) if items else None
    attack_weight_pct = round(
        sum(item.get("actual_weight_pct") or 0.0 for item in items if item.get("sleeve") == "attack"), 3
    ) if items else None
    insurance_weight_pct = round(
        sum(item.get("actual_weight_pct") or 0.0 for item in items if item.get("sleeve") == "insurance"), 3
    ) if items else None

    portfolio_day_change_pct = round(
        sum(
            ((item.get("actual_weight_pct") if item.get("actual_weight_pct") is not None else item.get("weight_pct")) or 0.0)
            * ((item.get("day_change_pct") or 0.0) / 100)
            for item in items
        ), 3
    ) if items else None
    portfolio_week_change_pct = round(
        sum(
            ((item.get("actual_weight_pct") if item.get("actual_weight_pct") is not None else item.get("weight_pct")) or 0.0)
            * ((item.get("week_change_pct") or 0.0) / 100)
            for item in items
        ), 3
    ) if items else None

    leaders = sorted(
        [item for item in items if item.get("day_change_pct") is not None],
        key=lambda item: item.get("day_change_pct") or 0.0,
        reverse=True,
    )

    return {
        "provider": "Eastmoney fundgz + Eastmoney fund history",
        "captured_at_utc": datetime.utcnow().replace(microsecond=0).isoformat(),
        "items": items,
        "failures": failures,
        "coverage": {
            "configured_holdings": len(portfolio.get("holdings") or []),
            "returned_holdings": len(items),
            "failed_holdings": len(failures),
        },
        "actual_total_value_cny": actual_total_value_cny,
        "actual_total_cost_cny": actual_total_cost_cny,
        "actual_total_pnl_cny": actual_total_pnl_cny,
        "actual_total_pnl_pct": actual_total_pnl_pct,
        "actual_exposures": {
            "core_weight_pct": core_weight_pct,
            "direct_ai_pct": direct_ai_weight_pct,
            "growth_tech_pct": growth_tech_weight_pct,
            "gold_pct": gold_weight_pct,
            "stable_core_pct": stable_core_weight_pct,
            "growth_core_pct": growth_core_weight_pct,
            "attack_pct": attack_weight_pct,
            "insurance_pct": insurance_weight_pct,
        },
        "portfolio_estimated_day_change_pct": portfolio_day_change_pct,
        "portfolio_week_change_pct": portfolio_week_change_pct,
        "leaders": {
            "top_positive": [item.get("holding_name") for item in leaders[:2]],
            "top_negative": [item.get("holding_name") for item in list(reversed(leaders[-2:]))],
        },
    }


def load_portfolio_history(path: str | Path | None = None) -> list[dict[str, Any]]:
    target = Path(path) if path else HISTORY_PATH
    if not target.exists():
        return []
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(payload, list):
        return payload
    return []


def update_portfolio_history(snapshot: dict[str, Any], path: str | Path | None = None, max_entries: int = 180) -> list[dict[str, Any]]:
    target = Path(path) if path else HISTORY_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    history = load_portfolio_history(target)

    captured = str(snapshot.get("captured_at_utc") or "")
    day_key = captured[:10]
    compact = {
        "captured_at_utc": captured,
        "portfolio_estimated_day_change_pct": snapshot.get("portfolio_estimated_day_change_pct"),
        "portfolio_week_change_pct": snapshot.get("portfolio_week_change_pct"),
        "items": [
            {
                "holding_name": item.get("holding_name"),
                "code": item.get("code"),
                "estimate_nav": item.get("estimate_nav"),
                "official_nav": item.get("official_nav"),
                "day_change_pct": item.get("day_change_pct"),
                "week_change_pct": item.get("week_change_pct"),
            }
            for item in snapshot.get("items") or []
        ],
    }

    replaced = False
    for index, item in enumerate(history):
        if str(item.get("captured_at_utc") or "")[:10] == day_key:
            history[index] = compact
            replaced = True
            break
    if not replaced:
        history.append(compact)

    history = sorted(history, key=lambda item: item.get("captured_at_utc") or "")[-max_entries:]
    target.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    return history
