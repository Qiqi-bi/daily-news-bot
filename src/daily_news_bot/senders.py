from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests

from .feishu_receipts import API_BASE, resolve_chat_id, tenant_access_token


CARD_TOTAL_LIMIT = 18000
CARD_ELEMENT_LIMIT = 1800
CARD_MAX_ELEMENTS = 8
POST_TOTAL_LIMIT = 24000


def _trim_content(content: str, limit: int) -> str:
    if len(content) <= limit:
        return content
    return content[: limit - 80].rstrip() + "\n\n内容较长，已截断；完整内容请打开网页。"


def _chunk_text(content: str, chunk_size: int = CARD_ELEMENT_LIMIT) -> list[str]:
    chunks: list[str] = []
    remaining = content.strip()
    while remaining and len(chunks) < CARD_MAX_ELEMENTS:
        if len(remaining) <= chunk_size:
            chunks.append(remaining)
            break

        split_at = remaining.rfind("\n\n", 0, chunk_size)
        if split_at <= 0:
            split_at = remaining.rfind("\n", 0, chunk_size)
        if split_at <= 0:
            split_at = chunk_size

        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()

    if remaining and chunks:
        chunks[-1] = _trim_content(chunks[-1] + "\n\n后续内容较长，已截断；完整内容请打开网页。", chunk_size)
    return [chunk for chunk in chunks if chunk]


def _raise_for_feishu_error(response: requests.Response) -> None:
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError:
        return
    code = payload.get("code")
    if code not in (None, 0):
        message = payload.get("msg") or payload.get("message") or "Feishu webhook returned an error"
        raise RuntimeError(f"Feishu webhook error {code}: {message}")


def _raise_for_feishu_api_error(response: requests.Response) -> dict[str, Any]:
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError:
        return {}
    code = payload.get("code")
    if code not in (None, 0):
        message = payload.get("msg") or payload.get("message") or "Feishu API returned an error"
        raise RuntimeError(f"Feishu API error {code}: {message}")
    return payload


def _prefixed_url(content: str, prefixes: tuple[str, ...]) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefixes):
            value = stripped.split("：", 1)[1].strip()
            if value.startswith(("https://", "http://")):
                return value
    return ""


def _button_urls(content: str) -> dict[str, str]:
    web_url = _prefixed_url(content, ("Dashboard：", "网页："))
    receipt_url = _prefixed_url(content, ("回执页：",))
    if not web_url:
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("https://") or stripped.startswith("http://"):
                web_url = stripped
                break
    return {"web": web_url, "receipt": receipt_url}


def _url_with_action(url: str, action: str) -> str:
    if not url:
        return ""
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["action"] = action
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _card_overview_fields(content: str) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    wanted_prefixes = ("年度目标：", "纪律：", "回执：", "最新 ")
    for line in content.splitlines():
        cleaned = line.strip().lstrip("- ").strip()
        if not cleaned:
            continue
        if cleaned.startswith(wanted_prefixes):
            fields.append(
                {
                    "is_short": False,
                    "text": {"tag": "lark_md", "content": cleaned[:240]},
                }
            )
        if len(fields) >= 3:
            break
    return fields


def _build_card_payload(title: str, content: str) -> dict[str, Any]:
    trimmed = _trim_content(content, CARD_TOTAL_LIMIT)
    chunks = _chunk_text(trimmed)
    elements: list[dict[str, Any]] = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "**读法**：飞书只展示中文简报、市场涨跌、关注方向和纪律级建议；不放英文原文、完整持仓、成本价和仓位金额。本卡不是交易指令，不保证收益。",
            },
        },
    ]
    overview_fields = _card_overview_fields(trimmed)
    if overview_fields:
        elements.append({"tag": "div", "fields": overview_fields})
    elements.append({"tag": "hr"})
    for index, chunk in enumerate(chunks, start=1):
        if index > 1:
            elements.append({"tag": "hr"})
        elements.append({"tag": "div", "text": {"tag": "lark_md", "content": chunk}})

    button_urls = _button_urls(trimmed)
    actions = []
    if button_urls["web"]:
        actions.append(
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "打开网页"},
                "url": button_urls["web"],
                "type": "primary",
            }
        )
    if button_urls["receipt"]:
        for label, action, button_type in (
            ("今天没操作", "noop", "default"),
            ("买入/加仓", "buy", "default"),
            ("卖出/减仓", "sell", "danger"),
        ):
            actions.append(
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": label},
                    "url": _url_with_action(button_urls["receipt"], action),
                    "type": button_type,
                }
            )
    if actions:
        elements.append(
            {
                "tag": "action",
                "actions": actions,
            }
        )

    return {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": "turquoise",
                "title": {"tag": "plain_text", "content": title},
            },
            "elements": elements,
        },
    }


def _build_app_card_payload(title: str, content: str) -> dict[str, Any]:
    webhook_payload = _build_card_payload(title, content)
    return webhook_payload["card"]


def _build_post_payload(title: str, content: str) -> dict[str, Any]:
    return {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": title,
                    "content": [[{"tag": "text", "text": _trim_content(content, POST_TOTAL_LIMIT)}]],
                }
            }
        },
    }


def send_feishu_webhook(webhook_url: str, title: str, content: str) -> None:
    if not webhook_url:
        return

    card_payload = _build_card_payload(title, content)
    try:
        response = requests.post(webhook_url, json=card_payload, timeout=20)
        _raise_for_feishu_error(response)
        return
    except Exception:
        fallback_payload = _build_post_payload(title, content)
        response = requests.post(webhook_url, json=fallback_payload, timeout=20)
        _raise_for_feishu_error(response)


def send_feishu_app_message(
    *,
    app_id: str,
    app_secret: str,
    chat_id: str = "",
    chat_name: str = "",
    title: str,
    content: str,
    timeout: float = 20,
) -> None:
    if not app_id or not app_secret:
        raise RuntimeError("FEISHU_APP_ID or FEISHU_APP_SECRET is missing")
    if not chat_id and not chat_name:
        raise RuntimeError("FEISHU_SEND_CHAT_ID or FEISHU_RECEIPT_CHAT_ID is missing")

    token = tenant_access_token(app_id, app_secret, timeout=timeout)
    resolved_chat_id = resolve_chat_id(token, chat_id, chat_name, timeout=timeout)
    if not resolved_chat_id:
        raise RuntimeError(f"Could not find Feishu chat: {chat_name or chat_id}")

    card = _build_app_card_payload(title, content)
    response = requests.post(
        f"{API_BASE}/im/v1/messages",
        params={"receive_id_type": "chat_id"},
        headers={
            "authorization": f"Bearer {token}",
            "content-type": "application/json; charset=utf-8",
        },
        json={
            "receive_id": resolved_chat_id,
            "msg_type": "interactive",
            "content": json.dumps(card, ensure_ascii=False),
        },
        timeout=timeout,
    )
    _raise_for_feishu_api_error(response)


def send_feishu_message(
    *,
    webhook_url: str = "",
    app_id: str = "",
    app_secret: str = "",
    chat_id: str = "",
    chat_name: str = "",
    title: str,
    content: str,
    allow_webhook_fallback: bool = False,
) -> str:
    app_error: Exception | None = None
    if app_id and app_secret and not (chat_id or chat_name):
        app_error = RuntimeError("Feishu app sender is configured but no target chat is configured")
    elif app_id and app_secret and (chat_id or chat_name):
        try:
            send_feishu_app_message(
                app_id=app_id,
                app_secret=app_secret,
                chat_id=chat_id,
                chat_name=chat_name,
                title=title,
                content=content,
            )
            return "app"
        except Exception as exc:
            app_error = exc

    if webhook_url:
        if app_error:
            if not allow_webhook_fallback:
                raise RuntimeError(f"Feishu app sender failed and webhook fallback is disabled: {app_error}") from app_error
            print(f"Feishu app sender failed; falling back to webhook: {app_error}")
        send_feishu_webhook(webhook_url, title, content)
        return "webhook_fallback" if app_error else "webhook"

    if app_error:
        raise app_error
    raise RuntimeError("No Feishu sender configured")
