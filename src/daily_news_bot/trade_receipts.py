from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

from .trade_ledger import aggregate_trade_ledger, load_trade_ledger


def _safe_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _current_shares(ledger: dict[str, Any], code: str) -> float:
    summary = aggregate_trade_ledger(ledger)
    for item in summary.get("positions") or []:
        if str(item.get("code") or "") == code:
            return float(item.get("shares") or 0)
    return 0.0


def parse_trade_receipt(text: str, ledger: dict[str, Any] | None = None) -> dict[str, Any]:
    parts = text.strip().split()
    if len(parts) < 4:
        raise ValueError("回执格式不完整，请用：BUY 代码 金额 价格 原因，或 SELL 代码 份额/比例 价格 原因")

    side = parts[0].lower()
    if side not in {"buy", "sell"}:
        raise ValueError("回执必须以 BUY 或 SELL 开头")

    code = parts[1].strip()
    size_text = parts[2].strip()
    price = _safe_float(parts[3])
    if not code:
        raise ValueError("缺少代码")
    if price is None or price <= 0:
        raise ValueError("价格必须是大于 0 的数字")

    reason = " ".join(parts[4:]).strip()
    trade: dict[str, Any] = {
        "date": datetime.now(timezone(timedelta(hours=8))).date().isoformat(),
        "code": code,
        "side": side,
        "price": price,
        "source": "feishu_receipt",
    }
    if reason:
        trade["reason"] = reason

    if side == "buy":
        amount = _safe_float(size_text.replace("元", ""))
        if amount is None or amount <= 0:
            raise ValueError("BUY 后面的金额必须是大于 0 的数字")
        trade["amount_cny"] = round(amount, 2)
        return trade

    if size_text.endswith("%"):
        pct = _safe_float(size_text[:-1])
        if pct is None or pct <= 0 or pct > 100:
            raise ValueError("SELL 百分比必须在 0-100 之间")
        shares = _current_shares(ledger or {"trades": []}, code) * pct / 100
        if shares <= 0:
            raise ValueError(f"没有找到 {code} 的可卖份额，无法按百分比减仓")
        trade["shares"] = round(shares, 4)
        trade["sell_pct"] = round(pct, 4)
    else:
        shares = _safe_float(size_text)
        if shares is None or shares <= 0:
            raise ValueError("SELL 后面的份额必须是大于 0 的数字，或写成 20%")
        trade["shares"] = round(shares, 4)
    return trade


def append_trade_receipt(path: str | Path, receipt_text: str, sender_id: str = "", message_id: str = "") -> dict[str, Any]:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    ledger = load_trade_ledger(target)
    ledger.setdefault("trades", [])
    trade = parse_trade_receipt(receipt_text, ledger)
    if sender_id:
        trade["sender_id"] = sender_id
    if message_id:
        trade["message_id"] = message_id
    ledger["trades"].append(trade)

    serializable = {key: value for key, value in ledger.items() if key not in {"enabled", "path"}}
    target.write_text(yaml.safe_dump(serializable, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return trade


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Append a Feishu trade receipt to trade_ledger.yaml")
    parser.add_argument("--ledger", default="config/trade_ledger.yaml")
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--sender-id", default="")
    parser.add_argument("--message-id", default="")
    args = parser.parse_args(argv)

    trade = append_trade_receipt(args.ledger, args.receipt, args.sender_id, args.message_id)
    print(yaml.safe_dump({"appended_trade": trade}, allow_unicode=True, sort_keys=False).strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
