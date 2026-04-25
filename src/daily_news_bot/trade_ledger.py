from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .config import ROOT_DIR


DEFAULT_LEDGER_PATH = ROOT_DIR / "config" / "trade_ledger.yaml"


def load_trade_ledger(path: str | Path | None = None) -> dict[str, Any]:
    target = Path(path) if path else DEFAULT_LEDGER_PATH
    if not target.exists():
        return {"enabled": False, "path": str(target), "trades": []}
    payload = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        return {"enabled": False, "path": str(target), "trades": []}
    payload["enabled"] = True
    payload["path"] = str(target)
    payload.setdefault("trades", [])
    return payload


def _safe_float(value: Any) -> float:
    try:
        if value in (None, ""):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def aggregate_trade_ledger(ledger: dict[str, Any]) -> dict[str, Any]:
    positions: dict[str, dict[str, Any]] = {}
    for trade in ledger.get("trades") or []:
        code = str(trade.get("code") or "").strip()
        if not code:
            continue
        side = str(trade.get("side") or trade.get("type") or "buy").lower()
        shares = _safe_float(trade.get("shares"))
        price = _safe_float(trade.get("price") or trade.get("nav"))
        amount = _safe_float(trade.get("amount_cny"))
        fee = _safe_float(trade.get("fee_cny"))
        if shares <= 0 and price > 0 and amount > 0:
            shares = amount / price
        if amount <= 0 and shares > 0 and price > 0:
            amount = shares * price
        if shares <= 0 or amount <= 0:
            continue

        position = positions.setdefault(
            code,
            {"code": code, "name": trade.get("name") or code, "shares": 0.0, "cost_cny": 0.0, "buy_amount_cny": 0.0, "sell_amount_cny": 0.0, "trade_count": 0},
        )
        position["trade_count"] += 1
        if side == "sell":
            avg_cost = position["cost_cny"] / position["shares"] if position["shares"] > 0 else 0.0
            reduced_cost = min(position["cost_cny"], avg_cost * shares)
            position["shares"] = max(position["shares"] - shares, 0.0)
            position["cost_cny"] = max(position["cost_cny"] - reduced_cost, 0.0)
            position["sell_amount_cny"] += amount - fee
        else:
            position["shares"] += shares
            position["cost_cny"] += amount + fee
            position["buy_amount_cny"] += amount + fee

    for position in positions.values():
        shares = position["shares"]
        position["avg_cost"] = round(position["cost_cny"] / shares, 4) if shares > 0 else None
        position["shares"] = round(shares, 4)
        position["cost_cny"] = round(position["cost_cny"], 2)

    return {
        "enabled": bool(ledger.get("enabled")),
        "path": ledger.get("path"),
        "positions": sorted(positions.values(), key=lambda item: item["code"]),
        "trade_count": sum(item.get("trade_count", 0) for item in positions.values()),
    }


def apply_trade_ledger_to_portfolio(portfolio: dict[str, Any], trade_ledger: dict[str, Any]) -> dict[str, Any]:
    if not trade_ledger or not trade_ledger.get("enabled"):
        return portfolio
    positions = {
        str(item.get("code") or ""): item
        for item in trade_ledger.get("positions") or []
        if item.get("code")
    }
    if not positions:
        return portfolio

    updated = dict(portfolio)
    holdings: list[dict[str, Any]] = []
    for holding in portfolio.get("holdings") or []:
        code = str(holding.get("code") or "")
        item = dict(holding)
        position = positions.get(code)
        if position:
            item["shares"] = position.get("shares")
            if position.get("avg_cost") is not None:
                item["cost_nav"] = position.get("avg_cost")
            item["ledger_cost_cny"] = position.get("cost_cny")
            item["ledger_trade_count"] = position.get("trade_count")
            item["data_source"] = "trade_ledger"
        holdings.append(item)
    updated["holdings"] = holdings
    updated["trade_ledger_applied"] = True
    return updated
