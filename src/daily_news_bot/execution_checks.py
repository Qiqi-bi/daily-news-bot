from __future__ import annotations

from datetime import datetime
import json
import re
from typing import Any

import requests


EASTMONEY_QUOTE_URL = "https://push2.eastmoney.com/api/qt/stock/get"
FUND_ESTIMATE_URL = "https://fundgz.1234567.com.cn/js/{code}.js"
DEFAULT_TIMEOUT = 10
JSONP_RE = re.compile(r"jsonpgz\((.*)\);?", re.DOTALL)
DEFAULT_BENCHMARK_ASSETS: dict[str, dict[str, str]] = {
    "510300": {"name": "沪深300ETF", "source": "benchmark"},
    "159915": {"name": "创业板ETF", "source": "benchmark"},
    "518880": {"name": "黄金ETF", "source": "benchmark"},
}


def _safe_float(value: Any, scale: float = 1.0) -> float | None:
    try:
        if value in (None, "", "-"):
            return None
        return round(float(value) / scale, 4)
    except (TypeError, ValueError):
        return None


def _secid(code: str) -> str:
    return ("1." if code.startswith(("5", "6", "9")) else "0.") + code


def fetch_intraday_nav_estimate(code: str, timeout: int = DEFAULT_TIMEOUT) -> dict[str, Any]:
    response = requests.get(
        FUND_ESTIMATE_URL.format(code=code),
        headers={"User-Agent": "Mozilla/5.0", "Referer": "https://fund.eastmoney.com/"},
        timeout=timeout,
    )
    response.raise_for_status()
    match = JSONP_RE.search(response.text.strip())
    if not match:
        raise ValueError(f"Unexpected fund estimate payload for {code}")
    payload = json.loads(match.group(1))
    estimate_nav = _safe_float(payload.get("gsz"), 1)
    official_nav = _safe_float(payload.get("dwjz"), 1)
    return {
        "estimate_nav": estimate_nav,
        "official_nav": official_nav,
        "nav_date": payload.get("jzrq") or "",
        "estimate_time": payload.get("gztime") or "",
    }


def fetch_etf_execution_quote(code: str, timeout: int = DEFAULT_TIMEOUT) -> dict[str, Any]:
    response = requests.get(
        EASTMONEY_QUOTE_URL,
        params={"secid": _secid(code), "fields": "f43,f44,f45,f46,f47,f48,f57,f58,f60,f116,f168,f169,f170,f171"},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    data = payload.get("data") or {}
    if not data:
        raise ValueError(f"No Eastmoney execution quote for {code}")

    latest = _safe_float(data.get("f43"), 1000)
    previous_close = _safe_float(data.get("f60"), 1000)
    change_pct = _safe_float(data.get("f170"), 100)
    turnover_cny = _safe_float(data.get("f48"), 1)
    amplitude_pct = _safe_float(data.get("f171"), 100)
    volume_lot = _safe_float(data.get("f47"), 1)
    market_value_cny = _safe_float(data.get("f116"), 1)
    nav_estimate: dict[str, Any] = {}
    premium_discount_pct = None
    premium_discount_basis = ""
    try:
        nav_estimate = fetch_intraday_nav_estimate(code, timeout=timeout)
        indicative_nav = nav_estimate.get("estimate_nav") or nav_estimate.get("official_nav")
        if latest not in (None, 0) and indicative_nav not in (None, 0):
            premium_discount_pct = round((latest - indicative_nav) / indicative_nav * 100, 4)
            premium_discount_basis = "估算净值/IOPV近似"
    except Exception as exc:
        nav_estimate = {"estimate_error": f"{type(exc).__name__}: {exc}"[:200]}

    liquidity_level = "未知"
    if turnover_cny is not None:
        if turnover_cny >= 100_000_000:
            liquidity_level = "好"
        elif turnover_cny >= 20_000_000:
            liquidity_level = "一般"
        else:
            liquidity_level = "偏弱"

    chase_risk = "未知"
    if change_pct is not None:
        if change_pct >= 2.5:
            chase_risk = "高"
        elif change_pct >= 1.0:
            chase_risk = "中"
        else:
            chase_risk = "低"

    premium_risk = "未知"
    if premium_discount_pct is not None:
        if abs(premium_discount_pct) >= 1.0:
            premium_risk = "高"
        elif abs(premium_discount_pct) >= 0.4:
            premium_risk = "中"
        else:
            premium_risk = "低"

    return {
        "code": code,
        "name": data.get("f58") or code,
        "latest_price": latest,
        "previous_close": previous_close,
        "change_pct": change_pct,
        "amplitude_pct": amplitude_pct,
        "volume_lot": volume_lot,
        "turnover_cny": turnover_cny,
        "market_value_cny": market_value_cny,
        "indicative_nav": nav_estimate.get("estimate_nav") or nav_estimate.get("official_nav"),
        "official_nav": nav_estimate.get("official_nav"),
        "nav_date": nav_estimate.get("nav_date") or "",
        "estimate_time": nav_estimate.get("estimate_time") or "",
        "premium_discount_pct": premium_discount_pct,
        "premium_discount_basis": premium_discount_basis,
        "premium_risk": premium_risk,
        "nav_estimate_error": nav_estimate.get("estimate_error", ""),
        "liquidity_level": liquidity_level,
        "chase_risk": chase_risk,
        "captured_at_utc": datetime.utcnow().replace(microsecond=0).isoformat(),
        "provider": "Eastmoney push2 stock quote",
    }


def _configured_execution_assets(portfolio: dict[str, Any]) -> dict[str, dict[str, Any]]:
    configured: dict[str, dict[str, Any]] = {}
    configured.update(DEFAULT_BENCHMARK_ASSETS)
    for holding in portfolio.get("holdings") or []:
        code = str(holding.get("code") or "").strip()
        if code and str(holding.get("type") or "").upper() == "ETF":
            configured[code] = {"name": holding.get("name") or code, "source": "holding"}
    for theme in portfolio.get("candidate_etf_pool") or []:
        for instrument in theme.get("instruments") or []:
            code = str(instrument.get("code") or "").strip()
            if code and str(instrument.get("type") or "").upper() == "ETF":
                configured.setdefault(code, {"name": instrument.get("name") or code, "source": "candidate", "theme": theme.get("theme")})
    return configured


def fetch_execution_checks(portfolio: dict[str, Any], timeout: int = DEFAULT_TIMEOUT) -> dict[str, Any]:
    configured = _configured_execution_assets(portfolio)
    items: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for code, meta in configured.items():
        try:
            quote = fetch_etf_execution_quote(code, timeout=timeout)
            quote.update(meta)
            items.append(quote)
        except Exception as exc:
            failures.append({"code": code, "name": meta.get("name", code), "error": f"{type(exc).__name__}: {exc}"[:300]})

    return {
        "provider": "Eastmoney ETF execution checks",
        "captured_at_utc": datetime.utcnow().replace(microsecond=0).isoformat(),
        "items": items,
        "failures": failures,
        "coverage": {"configured_assets": len(configured), "returned_assets": len(items), "failed_assets": len(failures)},
    }
