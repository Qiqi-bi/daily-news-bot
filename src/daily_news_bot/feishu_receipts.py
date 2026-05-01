from __future__ import annotations

import argparse
import json
import os
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import requests
import yaml

from .trade_ledger import load_trade_ledger
from .trade_receipts import is_trade_receipt_text, parse_trade_receipt


API_BASE = "https://open.feishu.cn/open-apis"


def _request_json(
    method: str,
    path: str,
    *,
    token: str = "",
    params: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
    timeout: float = 20,
) -> dict[str, Any]:
    headers = {"content-type": "application/json; charset=utf-8"}
    if token:
        headers["authorization"] = f"Bearer {token}"
    response = requests.request(
        method,
        f"{API_BASE}{path}",
        headers=headers,
        params=params,
        json=payload,
        timeout=timeout,
    )
    try:
        data = response.json()
    except ValueError:
        data = {}
    if not response.ok:
        detail = data.get("msg") or data.get("message") or response.text[:500]
        raise RuntimeError(f"Feishu HTTP {response.status_code}: {detail}")
    code = data.get("code")
    if code not in (None, 0):
        message = data.get("msg") or data.get("message") or "Feishu API returned an error"
        raise RuntimeError(f"Feishu API error {code}: {message}")
    return data


def tenant_access_token(app_id: str, app_secret: str, *, timeout: float = 20) -> str:
    data = _request_json(
        "POST",
        "/auth/v3/tenant_access_token/internal",
        payload={"app_id": app_id, "app_secret": app_secret},
        timeout=timeout,
    )
    token = str(data.get("tenant_access_token") or "")
    if not token:
        raise RuntimeError("Feishu tenant_access_token was empty")
    return token


def iter_chats(token: str, *, timeout: float = 20) -> list[dict[str, Any]]:
    chats: list[dict[str, Any]] = []
    page_token = ""
    while True:
        params: dict[str, Any] = {"page_size": 100}
        if page_token:
            params["page_token"] = page_token
        data = _request_json("GET", "/im/v1/chats", token=token, params=params, timeout=timeout)
        page = data.get("data") or {}
        chats.extend(list(page.get("items") or []))
        if not page.get("has_more"):
            break
        page_token = str(page.get("page_token") or "")
        if not page_token:
            break
    return chats


def resolve_chat_id(token: str, chat_id: str, chat_name: str, *, timeout: float = 20) -> str:
    if chat_id:
        return chat_id
    expected = chat_name.strip().casefold()
    if not expected:
        return ""

    partial_matches: list[dict[str, Any]] = []
    for chat in iter_chats(token, timeout=timeout):
        name = str(chat.get("name") or "").strip()
        item_chat_id = str(chat.get("chat_id") or "")
        if not name or not item_chat_id:
            continue
        normalized = name.casefold()
        if normalized == expected:
            return item_chat_id
        if expected in normalized:
            partial_matches.append(chat)

    if len(partial_matches) == 1:
        return str(partial_matches[0].get("chat_id") or "")
    return ""


def iter_messages(
    token: str,
    chat_id: str,
    *,
    start_time: int,
    end_time: int,
    timeout: float = 20,
) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    page_token = ""
    while True:
        params = {
            "container_id_type": "chat",
            "container_id": chat_id,
            "start_time": str(start_time),
            "end_time": str(end_time),
            "page_size": 50,
        }
        if page_token:
            params["page_token"] = page_token
        data = _request_json("GET", "/im/v1/messages", token=token, params=params, timeout=timeout)
        page = data.get("data") or {}
        messages.extend(list(page.get("items") or []))
        if not page.get("has_more"):
            break
        page_token = str(page.get("page_token") or "")
        if not page_token:
            break
    return sorted(messages, key=lambda item: str(item.get("create_time") or ""))


def _message_text(message: dict[str, Any]) -> str:
    body = message.get("body") or {}
    raw_content = body.get("content") or message.get("content") or ""
    if isinstance(raw_content, dict):
        content = raw_content
    else:
        try:
            content = json.loads(str(raw_content or "{}"))
        except json.JSONDecodeError:
            content = {"text": str(raw_content or "")}
    text = str(content.get("text") or "").strip()
    text = re.sub(r"@\S+\s*", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _message_id(message: dict[str, Any]) -> str:
    return str(message.get("message_id") or "")


def _sender_id(message: dict[str, Any]) -> str:
    sender = message.get("sender") or {}
    sender_id = sender.get("sender_id") or {}
    if isinstance(sender_id, dict):
        return str(sender_id.get("open_id") or sender_id.get("user_id") or "")
    return str(sender.get("id") or sender_id or "")


def _bjt_date_from_create_time(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        timestamp = float(raw)
    except ValueError:
        return ""
    if timestamp > 10_000_000_000:
        timestamp = timestamp / 1000
    bjt = datetime.fromtimestamp(timestamp, timezone.utc).astimezone(timezone(timedelta(hours=8)))
    return bjt.date().isoformat()


def _is_receipt(text: str) -> bool:
    return is_trade_receipt_text(text)


def poll_and_append_receipts(
    *,
    ledger_path: str | Path,
    app_id: str,
    app_secret: str,
    chat_id: str = "",
    chat_name: str = "",
    lookback_hours: float = 48,
    timeout: float = 20,
) -> dict[str, Any]:
    checked_at_utc = datetime.now(timezone.utc).isoformat()
    if not app_id or not app_secret:
        return {"ok": True, "skipped": True, "reason": "FEISHU_APP_ID or FEISHU_APP_SECRET is missing", "appended_count": 0, "checked_at_utc": checked_at_utc}
    if not chat_id and not chat_name:
        return {"ok": True, "skipped": True, "reason": "FEISHU_RECEIPT_CHAT_ID or FEISHU_RECEIPT_CHAT_NAME is missing", "appended_count": 0, "checked_at_utc": checked_at_utc}

    token = tenant_access_token(app_id, app_secret, timeout=timeout)
    resolved_chat_id = resolve_chat_id(token, chat_id, chat_name, timeout=timeout)
    if not resolved_chat_id:
        return {"ok": False, "error": f"Could not find Feishu chat: {chat_name or chat_id}", "appended_count": 0, "checked_at_utc": checked_at_utc}

    now = int(time.time())
    start = max(now - int(lookback_hours * 3600), 0)
    messages = iter_messages(token, resolved_chat_id, start_time=start, end_time=now, timeout=timeout)

    target = Path(ledger_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    ledger = load_trade_ledger(target)
    trades = ledger.setdefault("trades", [])
    existing_message_ids = {str(item.get("message_id") or "") for item in trades if item.get("message_id")}
    appended: list[dict[str, Any]] = []
    ignored = 0
    duplicate = 0
    errors: list[dict[str, str]] = []

    for message in messages:
        message_id = _message_id(message)
        if message_id and message_id in existing_message_ids:
            duplicate += 1
            continue

        text = _message_text(message)
        if not _is_receipt(text):
            ignored += 1
            continue

        try:
            trade = parse_trade_receipt(text, ledger)
        except Exception as exc:
            errors.append({"message_id": message_id, "error": f"{type(exc).__name__}: {exc}", "text": text[:200]})
            continue

        trade["source"] = "feishu_poll"
        trade["receipt_text"] = text
        trade_date = _bjt_date_from_create_time(message.get("create_time"))
        if trade_date:
            trade["date"] = trade_date
        if message_id:
            trade["message_id"] = message_id
            existing_message_ids.add(message_id)
        sender_id = _sender_id(message)
        if sender_id:
            trade["sender_id"] = sender_id
        if message.get("create_time"):
            trade["feishu_create_time"] = str(message.get("create_time"))
        trades.append(trade)
        appended.append(trade)

    if appended:
        serializable = {key: value for key, value in ledger.items() if key not in {"enabled", "path"}}
        target.write_text(yaml.safe_dump(serializable, allow_unicode=True, sort_keys=False), encoding="utf-8")

    return {
        "ok": True,
        "skipped": False,
        "chat_id": resolved_chat_id,
        "lookback_hours": lookback_hours,
        "message_count": len(messages),
        "ignored_count": ignored,
        "duplicate_count": duplicate,
        "error_count": len(errors),
        "errors": errors[:10],
        "appended_count": len(appended),
        "appended": appended,
        "checked_at_utc": checked_at_utc,
    }


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name, "").strip()
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def public_receipt_summary(summary: dict[str, Any]) -> dict[str, Any]:
    public = {
        "ok": bool(summary.get("ok")),
        "skipped": bool(summary.get("skipped")),
        "status": summary.get("status") or ("ok" if summary.get("ok") else "error"),
        "configured": not bool(summary.get("skipped")),
        "lookback_hours": summary.get("lookback_hours"),
        "message_count": int(summary.get("message_count") or 0),
        "ignored_count": int(summary.get("ignored_count") or 0),
        "duplicate_count": int(summary.get("duplicate_count") or 0),
        "error_count": int(summary.get("error_count") or 0),
        "appended_count": int(summary.get("appended_count") or 0),
    }
    if summary.get("reason"):
        public["reason"] = str(summary.get("reason"))[:300]
    if summary.get("error"):
        public["error"] = str(summary.get("error"))[:300]
    if summary.get("checked_at_utc"):
        public["checked_at_utc"] = str(summary.get("checked_at_utc"))[:40]
    return public


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Poll Feishu chat messages and append BUY/SELL receipts to the trade ledger.")
    parser.add_argument("--ledger", default="config/trade_ledger.yaml")
    parser.add_argument("--app-id", default=os.getenv("FEISHU_APP_ID", ""))
    parser.add_argument("--app-secret", default=os.getenv("FEISHU_APP_SECRET", ""))
    parser.add_argument("--chat-id", default=os.getenv("FEISHU_RECEIPT_CHAT_ID", ""))
    parser.add_argument("--chat-name", default=os.getenv("FEISHU_RECEIPT_CHAT_NAME", ""))
    parser.add_argument("--lookback-hours", type=float, default=_env_float("FEISHU_RECEIPT_LOOKBACK_HOURS", 48))
    parser.add_argument("--timeout", type=float, default=_env_float("FEISHU_API_TIMEOUT", 20))
    parser.add_argument("--summary-output", default="outputs/feishu_receipts.json")
    parser.add_argument("--soft-fail", action="store_true")
    args = parser.parse_args(argv)

    try:
        summary = poll_and_append_receipts(
            ledger_path=args.ledger,
            app_id=args.app_id,
            app_secret=args.app_secret,
            chat_id=args.chat_id,
            chat_name=args.chat_name,
            lookback_hours=args.lookback_hours,
            timeout=args.timeout,
        )
    except Exception as exc:
        summary = {"ok": False, "error": f"{type(exc).__name__}: {exc}", "appended_count": 0, "checked_at_utc": datetime.now(timezone.utc).isoformat()}
        if not args.soft_fail:
            print(json.dumps(public_receipt_summary(summary), ensure_ascii=False, indent=2))
            return 1

    public_summary = public_receipt_summary(summary)
    output_path = Path(args.summary_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(public_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(public_summary, ensure_ascii=False, indent=2))
    return 0 if summary.get("ok") or args.soft_fail else 1


if __name__ == "__main__":
    raise SystemExit(main())
