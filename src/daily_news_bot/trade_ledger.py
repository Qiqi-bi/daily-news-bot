from __future__ import annotations

from datetime import datetime, timezone
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


def _trade_sort_value(trade: dict[str, Any]) -> float:
    raw_time = str(trade.get("feishu_create_time") or "").strip()
    if raw_time:
        try:
            timestamp = float(raw_time)
            return timestamp / 1000 if timestamp > 10_000_000_000 else timestamp
        except ValueError:
            pass
    raw_date = str(trade.get("date") or "").strip()
    if raw_date:
        try:
            return datetime.fromisoformat(raw_date).replace(tzinfo=timezone.utc).timestamp()
        except ValueError:
            return 0.0
    return 0.0


def _latest_trade(trades: list[dict[str, Any]]) -> dict[str, Any]:
    if not trades:
        return {}
    return max(trades, key=_trade_sort_value)


def _trade_side(value: Any) -> str:
    side = str(value or "").strip().lower()
    return "sell" if side == "sell" else "buy"


def aggregate_trade_ledger(ledger: dict[str, Any]) -> dict[str, Any]:
    positions: dict[str, dict[str, Any]] = {}
    accepted_trades: list[dict[str, Any]] = []
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

        accepted_trades.append(dict(trade))
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

    latest = _latest_trade(accepted_trades)
    latest_date = str(latest.get("date") or "").strip()
    return {
        "enabled": bool(ledger.get("enabled")),
        "path": ledger.get("path"),
        "positions": sorted(positions.values(), key=lambda item: item["code"]),
        "trade_count": sum(item.get("trade_count", 0) for item in positions.values()),
        "latest_trade_date": latest_date,
        "latest_trade_side": _trade_side(latest.get("side") or latest.get("type")) if latest else "",
        "latest_trade_code": str(latest.get("code") or "").strip(),
        "latest_trade_source": str(latest.get("source") or "").strip(),
    }


def build_trade_sync_status(
    trade_ledger: dict[str, Any] | None,
    receipt_status: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ledger = trade_ledger or {}
    receipt = receipt_status or {}
    trade_count = int(ledger.get("trade_count") or 0)
    positions_count = len(ledger.get("positions") or [])
    latest_date = str(ledger.get("latest_trade_date") or "").strip()
    latest_side = str(ledger.get("latest_trade_side") or "").strip()
    checked_at = str(receipt.get("checked_at_utc") or "").strip()
    receipt_state = str(receipt.get("status") or "").strip()

    base = {
        "label": "持仓同步",
        "trade_count": trade_count,
        "positions_count": positions_count,
        "last_trade_date": latest_date,
        "last_trade_side": latest_side,
        "checked_at_utc": checked_at,
    }
    latest_text = f"最近操作 {latest_date}" if latest_date else "还没有交易记录"

    if not ledger.get("enabled"):
        return {
            **base,
            "status": "disabled",
            "value": "未启用",
            "tone": "warn",
            "note": "系统还没有交易记录文件，仍按 portfolio.yaml 的原始持仓估算。",
        }
    if not receipt or receipt_state == "not_run":
        return {
            **base,
            "status": "ledger_loaded",
            "value": "按账本",
            "tone": "neutral",
            "note": f"本次未读取飞书回执；已读取 {trade_count} 条交易记录；{latest_text}。",
        }
    if receipt and not receipt.get("ok", False) and not receipt.get("skipped"):
        return {
            **base,
            "status": "receipt_error",
            "value": "需检查",
            "tone": "bad",
            "note": f"飞书回执读取失败；{latest_text}。动手前先确认是否漏记操作。",
        }
    if receipt.get("skipped"):
        reason = str(receipt.get("reason") or "本次未读取飞书回执").strip()
        return {
            **base,
            "status": "ledger_only",
            "value": "账本模式",
            "tone": "warn",
            "note": f"{reason}；{latest_text}。",
        }

    appended = int(receipt.get("appended_count") or 0)
    scanned = int(receipt.get("message_count") or 0)
    if appended > 0:
        return {
            **base,
            "status": "updated",
            "value": "刚更新",
            "tone": "good",
            "note": f"本次新增入账 {appended} 条；{latest_text}。系统已按最新账本重算组合。",
        }
    return {
        **base,
        "status": "synced",
        "value": "已同步",
        "tone": "good",
        "note": f"本次扫描 {scanned} 条，没有新增交易；{latest_text}。没回执就默认你没操作。",
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
