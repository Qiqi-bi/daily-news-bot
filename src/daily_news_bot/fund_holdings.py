from __future__ import annotations

import html
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from .config import ROOT_DIR


FUND_HOLDINGS_URL = "https://fundf10.eastmoney.com/FundArchivesDatas.aspx"
CACHE_PATH = ROOT_DIR / "outputs" / "fund_holdings_cache.json"
DEFAULT_TIMEOUT = 12
CONTENT_RE = re.compile(r"content:\s*\"(.*)\"\s*,\s*arryear", re.DOTALL)
REPORT_DATE_RE = re.compile(r"<font[^>]*>((?:19|20)\d{2}[-年/.]\d{1,2}[-月/.]\d{1,2}[^<]*)</font>")
ROW_RE = re.compile(r"<tr>(.*?)</tr>", re.DOTALL)
CELL_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")


def _clean_html(value: str) -> str:
    value = value.replace("\\\"", '"').replace("\\/", "/")
    value = value.replace("\\r", "").replace("\\n", "").replace("\\t", "")
    value = TAG_RE.sub("", value)
    return html.unescape(value).strip()


def _safe_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(str(value).replace("%", "").replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _extract_content(raw_text: str) -> str:
    match = CONTENT_RE.search(raw_text)
    if match:
        return match.group(1)
    fallback = re.search(r"content:\s*\"(.*)\"\s*}\s*;?", raw_text, re.DOTALL)
    return fallback.group(1) if fallback else raw_text


def _quote_context_by_code(portfolio_quotes: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    context: dict[str, dict[str, Any]] = {}
    for item in (portfolio_quotes or {}).get("items") or []:
        code = str(item.get("code") or "").strip()
        if not code:
            continue
        weight = _safe_float(item.get("actual_weight_pct"))
        if weight is None:
            weight = _safe_float(item.get("weight_pct"))
        context[code] = {
            "portfolio_weight_pct": weight,
            "estimated_position_value_cny": _safe_float(item.get("estimated_position_value_cny")),
            "unrealized_pnl_pct": _safe_float(item.get("unrealized_pnl_pct")),
        }
    return context


def _attach_portfolio_context(
    item: dict[str, Any],
    holding: dict[str, Any],
    quote_context: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    code = str(item.get("fund_code") or holding.get("code") or "").strip()
    context = quote_context.get(code, {})
    portfolio_weight_pct = context.get("portfolio_weight_pct")
    if portfolio_weight_pct is None:
        portfolio_weight_pct = _safe_float(holding.get("weight_pct"))
    item["holding_name"] = holding.get("name") or code
    item["holding_bucket"] = holding.get("bucket") or ""
    item["holding_sleeve"] = holding.get("sleeve") or ""
    item["portfolio_weight_pct"] = portfolio_weight_pct
    item["estimated_position_value_cny"] = context.get("estimated_position_value_cny")
    item["unrealized_pnl_pct"] = context.get("unrealized_pnl_pct")
    return item


def fetch_fund_top_holdings(code: str, timeout: int = DEFAULT_TIMEOUT, top_n: int = 10) -> dict[str, Any]:
    response = requests.get(
        FUND_HOLDINGS_URL,
        params={"type": "jjcc", "code": code, "topline": str(top_n), "year": "", "month": ""},
        headers={"User-Agent": "Mozilla/5.0", "Referer": "https://fundf10.eastmoney.com/"},
        timeout=timeout,
    )
    response.raise_for_status()
    content = _extract_content(response.text)
    date_match = REPORT_DATE_RE.search(content)
    report_date = _clean_html(date_match.group(1)) if date_match else ""

    holdings: list[dict[str, Any]] = []
    for row_html in ROW_RE.findall(content):
        cells = [_clean_html(cell) for cell in CELL_RE.findall(row_html)]
        if len(cells) < 9:
            continue
        rank = _safe_float(cells[0])
        stock_code = cells[1].strip()
        stock_name = cells[2].strip()
        nav_pct = _safe_float(cells[6])
        shares_10k = _safe_float(cells[7])
        market_value_10k = _safe_float(cells[8])
        if not stock_code or not stock_name or nav_pct is None:
            continue
        holdings.append(
            {
                "rank": int(rank or len(holdings) + 1),
                "stock_code": stock_code,
                "stock_name": stock_name,
                "nav_pct": nav_pct,
                "shares_10k": shares_10k,
                "market_value_10k_cny": market_value_10k,
            }
        )
        if len(holdings) >= top_n:
            break

    if not holdings:
        raise ValueError(f"No top holdings parsed for fund {code}")

    return {
        "fund_code": code,
        "report_date": report_date,
        "provider": "Eastmoney FundArchivesDatas jjcc",
        "captured_at_utc": datetime.utcnow().replace(microsecond=0).isoformat(),
        "holdings": holdings,
    }


def load_fund_holdings_cache(path: str | Path | None = None) -> dict[str, Any]:
    target = Path(path) if path else CACHE_PATH
    if not target.exists():
        return {}
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def save_fund_holdings_cache(payload: dict[str, Any], path: str | Path | None = None) -> None:
    target = Path(path) if path else CACHE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_portfolio_fund_holdings(
    portfolio: dict[str, Any],
    timeout: int = DEFAULT_TIMEOUT,
    top_n: int = 10,
    portfolio_quotes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cache = load_fund_holdings_cache()
    quote_context = _quote_context_by_code(portfolio_quotes)
    items: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    for holding in portfolio.get("holdings") or []:
        code = str(holding.get("code") or "").strip()
        if not code:
            continue
        try:
            item = fetch_fund_top_holdings(code, timeout=timeout, top_n=top_n)
            item = _attach_portfolio_context(item, holding, quote_context)
            cache[code] = item
        except Exception as exc:
            cached = cache.get(code)
            if cached:
                item = dict(cached)
                item = _attach_portfolio_context(item, holding, quote_context)
                item["from_cache"] = True
                item["cache_error"] = f"{type(exc).__name__}: {exc}"[:300]
            else:
                failures.append({"holding_name": holding.get("name") or code, "code": code, "error": f"{type(exc).__name__}: {exc}"[:300]})
                continue
        items.append(item)

    if items:
        save_fund_holdings_cache(cache)

    stock_map: dict[str, dict[str, Any]] = {}
    for item in items:
        fund_weight_pct = _safe_float(item.get("portfolio_weight_pct"))
        for stock in item.get("holdings") or []:
            code = stock.get("stock_code")
            if not code:
                continue
            nav_pct = float(stock.get("nav_pct") or 0.0)
            portfolio_exposure_pct = None
            if fund_weight_pct is not None:
                portfolio_exposure_pct = round(fund_weight_pct * nav_pct / 100, 4)
            row = stock_map.setdefault(
                code,
                {
                    "stock_code": code,
                    "stock_name": stock.get("stock_name"),
                    "funds": [],
                    "nav_pct_sum": 0.0,
                    "portfolio_exposure_pct_sum": 0.0,
                },
            )
            row["funds"].append(
                {
                    "fund_code": item.get("fund_code"),
                    "fund_name": item.get("holding_name"),
                    "nav_pct": nav_pct,
                    "portfolio_weight_pct": fund_weight_pct,
                    "portfolio_exposure_pct": portfolio_exposure_pct,
                }
            )
            row["nav_pct_sum"] = round(row["nav_pct_sum"] + nav_pct, 4)
            if portfolio_exposure_pct is not None:
                row["portfolio_exposure_pct_sum"] = round(row["portfolio_exposure_pct_sum"] + portfolio_exposure_pct, 4)

    stock_exposures = sorted(
        stock_map.values(),
        key=lambda row: (row.get("portfolio_exposure_pct_sum") or 0.0, len(row.get("funds") or []), row.get("nav_pct_sum") or 0.0),
        reverse=True,
    )
    overlaps = sorted(
        [row for row in stock_map.values() if len(row.get("funds") or []) >= 2],
        key=lambda row: (row.get("portfolio_exposure_pct_sum") or 0.0, len(row.get("funds") or []), row.get("nav_pct_sum") or 0.0),
        reverse=True,
    )

    return {
        "provider": "Eastmoney fund quarterly top holdings + portfolio weights",
        "captured_at_utc": datetime.utcnow().replace(microsecond=0).isoformat(),
        "items": items,
        "overlaps": overlaps,
        "stock_exposures": stock_exposures,
        "failures": failures,
        "coverage": {
            "configured_holdings": len(portfolio.get("holdings") or []),
            "returned_holdings": len(items),
            "weighted_holdings": sum(1 for item in items if item.get("portfolio_weight_pct") is not None),
            "failed_holdings": len(failures),
        },
    }
