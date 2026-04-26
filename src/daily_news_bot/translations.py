from __future__ import annotations

import json
import re
from typing import Any

from .config import Settings
from .llm import generate_report
from .models import EventCluster


TRANSLATION_SYSTEM_PROMPT = """你是财经新闻标题翻译助手。
任务：把英文或其它外文财经新闻标题、摘要翻译成简体中文。
要求：
- 只翻译，不添加原文没有的事实。
- 保留人名、公司名、国家、指数、ETF、商品、股票代码等关键信息。
- 标题要短、清楚，适合投资 dashboard 阅读。
- 输出严格 JSON，不要 Markdown，不要解释。
"""


def _contains_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def _needs_translation(text: str) -> bool:
    if not text or _contains_cjk(text):
        return False
    latin_chars = sum(1 for char in text if "a" <= char.lower() <= "z")
    return latin_chars >= 8


def _extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.IGNORECASE | re.DOTALL)
    if fenced:
        cleaned = fenced.group(1).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise
        data = json.loads(cleaned[start : end + 1])

    if not isinstance(data, dict):
        raise ValueError("Translation response must be a JSON object")
    return data


def translate_cluster_highlights(
    settings: Settings,
    clusters: list[EventCluster],
    *,
    limit: int = 10,
) -> dict[str, Any]:
    """Translate foreign-language cluster titles/summaries for dashboard display."""
    request_items: list[dict[str, Any]] = []
    for cluster in clusters[:limit]:
        representative = cluster.representative
        title = representative.title or cluster.theme
        summary = representative.summary or representative.content or ""
        if not _needs_translation(f"{title}\n{summary}"):
            continue
        request_items.append(
            {
                "cluster_id": cluster.cluster_id,
                "title": title,
                "summary": summary[:500],
                "tags": cluster.tags,
                "direction": cluster.direction,
            }
        )

    if not request_items:
        return {
            "enabled": False,
            "items": {},
            "reason": "no_foreign_cluster_titles",
        }

    user_prompt = (
        "请把下面的外文新闻标题和摘要翻译成简体中文。\n"
        "返回 JSON，格式必须是：\n"
        '{"items":[{"cluster_id":"...","title_zh":"...","summary_zh":"...","why_it_matters_zh":"..."}]}\n'
        "字段说明：title_zh 是中文标题；summary_zh 是中文摘要；why_it_matters_zh 用一句话说明它对市场为什么重要。\n\n"
        f"{json.dumps({'items': request_items}, ensure_ascii=False, indent=2)}"
    )

    output = generate_report(settings, TRANSLATION_SYSTEM_PROMPT, user_prompt)
    if not output:
        return {
            "enabled": False,
            "items": {},
            "error": "translation_llm_unavailable",
        }

    try:
        data = _extract_json_object(output)
    except Exception as exc:
        return {
            "enabled": False,
            "items": {},
            "error": f"translation_parse_failed: {type(exc).__name__}: {exc}",
        }

    translations: dict[str, dict[str, str]] = {}
    for item in data.get("items") or []:
        if not isinstance(item, dict):
            continue
        cluster_id = str(item.get("cluster_id") or "").strip()
        title_zh = str(item.get("title_zh") or "").strip()
        if not cluster_id or not title_zh:
            continue
        translations[cluster_id] = {
            "title_zh": title_zh,
            "summary_zh": str(item.get("summary_zh") or "").strip(),
            "why_it_matters_zh": str(item.get("why_it_matters_zh") or "").strip(),
        }

    return {
        "enabled": bool(translations),
        "items": translations,
        "requested_count": len(request_items),
        "translated_count": len(translations),
    }
