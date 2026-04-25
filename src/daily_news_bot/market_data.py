from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests


YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
DEFAULT_TIMEOUT = 10
ASSETS = (
    {"name": "WTI原油", "symbol": "CL=F", "group": "energy"},
    {"name": "布伦特原油", "symbol": "BZ=F", "group": "energy"},
    {"name": "黄金", "symbol": "GC=F", "group": "safe_haven"},
    {"name": "美元指数", "symbol": "DX-Y.NYB", "group": "fx"},
    {"name": "美国10Y国债收益率", "symbol": "^TNX", "group": "rates"},
    {"name": "VIX", "symbol": "^VIX", "group": "volatility"},
    {"name": "标普500期货", "symbol": "ES=F", "group": "equity"},
    {"name": "纳斯达克100期货", "symbol": "NQ=F", "group": "equity"},
    {"name": "离岸人民币", "symbol": "CNH=X", "group": "fx"},
)



def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None



def _latest_two(values: list[Any]) -> tuple[float | None, float | None]:
    clean = [_safe_float(item) for item in values if _safe_float(item) is not None]
    if not clean:
        return None, None
    if len(clean) == 1:
        return None, clean[-1]
    return clean[-2], clean[-1]



def _movement(change_pct: float | None) -> str:
    if change_pct is None:
        return "未知"
    if change_pct > 0.35:
        return "上涨"
    if change_pct < -0.35:
        return "下跌"
    return "震荡"



def fetch_quote(symbol: str, timeout: int = DEFAULT_TIMEOUT) -> dict[str, Any]:
    endpoint = YAHOO_CHART_URL.format(symbol=symbol)
    response = requests.get(
        endpoint,
        params={"interval": "1d", "range": "5d", "includePrePost": "false"},
        timeout=timeout,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    response.raise_for_status()
    payload = response.json()

    result = ((payload.get("chart") or {}).get("result") or [None])[0] or {}
    meta = result.get("meta") or {}
    indicators = result.get("indicators") or {}
    quotes = (indicators.get("quote") or [{}])[0]
    closes = quotes.get("close") or []
    previous_close, latest_close = _latest_two(closes)
    market_price = _safe_float(meta.get("regularMarketPrice")) or latest_close
    previous_close = previous_close or _safe_float(meta.get("chartPreviousClose")) or _safe_float(meta.get("previousClose"))

    change = None
    change_pct = None
    if market_price is not None and previous_close not in (None, 0):
        change = round(market_price - previous_close, 4)
        change_pct = round(change / previous_close * 100, 3)

    market_time = meta.get("regularMarketTime")
    market_time_iso = None
    if isinstance(market_time, int):
        market_time_iso = datetime.fromtimestamp(market_time, tz=timezone.utc).isoformat()

    return {
        "symbol": symbol,
        "price": market_price,
        "previous_close": previous_close,
        "change": change,
        "change_pct": change_pct,
        "movement": _movement(change_pct),
        "currency": meta.get("currency") or "",
        "exchange": meta.get("exchangeName") or meta.get("fullExchangeName") or "",
        "market_time_utc": market_time_iso,
        "provider": "Yahoo Finance chart API",
    }



def fetch_market_snapshot(timeout: int = DEFAULT_TIMEOUT) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for asset in ASSETS:
        try:
            quote = fetch_quote(asset["symbol"], timeout=timeout)
            quote["name"] = asset["name"]
            quote["group"] = asset["group"]
            items.append(quote)
        except Exception as exc:
            failures.append({
                "name": asset["name"],
                "symbol": asset["symbol"],
                "error": f"{type(exc).__name__}: {exc}"[:300],
            })

    return {
        "provider": "Yahoo Finance chart API",
        "captured_at_utc": datetime.utcnow().replace(microsecond=0).isoformat(),
        "items": items,
        "failures": failures,
        "coverage": {
            "configured_assets": len(ASSETS),
            "returned_assets": len(items),
            "failed_assets": len(failures),
        },
    }
