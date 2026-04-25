from __future__ import annotations

from typing import Any

import requests


CARD_TOTAL_LIMIT = 24000
CARD_ELEMENT_LIMIT = 2800
CARD_MAX_ELEMENTS = 10
POST_TOTAL_LIMIT = 30000


def _trim_content(content: str, limit: int) -> str:
    if len(content) <= limit:
        return content
    return content[: limit - 80].rstrip() + "\n\n---\n内容较长，已截断；完整内容请查看 outputs/report.md。"


def _chunk_text(content: str, chunk_size: int = CARD_ELEMENT_LIMIT) -> list[str]:
    chunks: list[str] = []
    remaining = content.strip()
    while remaining and len(chunks) < CARD_MAX_ELEMENTS:
        if len(remaining) <= chunk_size:
            chunks.append(remaining)
            break

        split_at = remaining.rfind("\n## ", 0, chunk_size)
        if split_at <= 0:
            split_at = remaining.rfind("\n### ", 0, chunk_size)
        if split_at <= 0:
            split_at = remaining.rfind("\n", 0, chunk_size)
        if split_at <= 0:
            split_at = chunk_size

        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()

    if remaining and chunks:
        chunks[-1] = _trim_content(chunks[-1] + "\n\n---\n后续内容较长，已截断；完整内容请查看 outputs/report.md。", chunk_size)
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


def _build_card_payload(title: str, content: str) -> dict[str, Any]:
    trimmed = _trim_content(content, CARD_TOTAL_LIMIT)
    chunks = _chunk_text(trimmed)
    elements: list[dict[str, Any]] = [
        {
            "tag": "markdown",
            "content": "**快速阅读提示**：先看 30 秒总览，再看市场影响地图和明天 5 个信号。",
        },
        {"tag": "hr"},
    ]
    for index, chunk in enumerate(chunks, start=1):
        if index > 1:
            elements.append({"tag": "hr"})
        elements.append({"tag": "markdown", "content": chunk})

    return {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": "blue",
                "title": {"tag": "plain_text", "content": title},
            },
            "elements": elements,
        },
    }


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