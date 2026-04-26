from __future__ import annotations

import json
import re
from typing import Any

import requests

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


def _translate_with_google(text: str, *, timeout: int = 12) -> str:
    if not text.strip():
        return ""
    response = requests.get(
        "https://translate.googleapis.com/translate_a/single",
        params={
            "client": "gtx",
            "sl": "auto",
            "tl": "zh-CN",
            "dt": "t",
            "q": text,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    parts = data[0] if isinstance(data, list) and data else []
    translated = "".join(str(part[0]) for part in parts if isinstance(part, list) and part)
    return translated.strip()


def _topic_label(tags: list[Any]) -> str:
    mapping = {
        "geopolitics": "地缘政治",
        "energy": "能源",
        "macro": "宏观",
        "markets": "市场",
        "technology": "科技",
        "crypto": "加密资产",
        "rates": "利率",
        "fx": "汇率",
        "gold": "黄金",
    }
    labels = [mapping.get(str(tag), str(tag)) for tag in tags if str(tag).strip()]
    return "、".join(dict.fromkeys(labels) or ["相关资产"])


def _why_it_matters(tags: list[Any], direction: Any) -> str:
    topic = _topic_label(tags)
    direction_text = str(direction or "待确认")
    return f"该事件可能影响{topic}定价，当前方向判断为{direction_text}，仍需结合价格和更多信源复核。"


def _rough_translate_title(title: str, tags: list[Any]) -> str:
    replacements = [
        (r"\bU\.S\.\b|\bUS\b", "美国"),
        (r"\bIran\b", "伊朗"),
        (r"\bRussia\b", "俄罗斯"),
        (r"\bChina\b", "中国"),
        (r"\bTrump\b", "特朗普"),
        (r"\bWhite House\b", "白宫"),
        (r"\bFederal Reserve\b|\bFed\b", "美联储"),
        (r"\bsanctions?\b", "制裁"),
        (r"\bwar\b", "战争"),
        (r"\bshock\b", "冲击"),
        (r"\bprices?\b", "价格"),
        (r"\boil\b", "石油"),
        (r"\bgold\b", "黄金"),
        (r"\bmarkets?\b", "市场"),
        (r"\beconomic warfare\b", "经济战"),
        (r"\bdeveloping nations\b", "发展中国家"),
        (r"\bhigher\b", "更高"),
        (r"\bcould last\b", "可能持续"),
        (r"\bminister says\b", "部长表示"),
        (r"\bdrug cartel\b", "贩毒集团"),
        (r"\bgovernment\b", "政府"),
    ]
    translated = title
    for pattern, replacement in replacements:
        translated = re.sub(pattern, replacement, translated, flags=re.IGNORECASE)
    if translated == title:
        return f"{_topic_label(tags)}新闻：{title}"
    return translated


def _fallback_translate_items(request_items: list[dict[str, Any]]) -> tuple[dict[str, dict[str, str]], str]:
    translations: dict[str, dict[str, str]] = {}
    provider = "google_translate"
    for item in request_items:
        cluster_id = str(item.get("cluster_id") or "").strip()
        if not cluster_id:
            continue
        title = str(item.get("title") or "").strip()
        summary = str(item.get("summary") or "").strip()
        tags = list(item.get("tags") or [])
        direction = item.get("direction")

        try:
            title_zh = _translate_with_google(title)
            summary_zh = _translate_with_google(summary) if summary else ""
        except Exception:
            provider = "rule_based"
            title_zh = _rough_translate_title(title, tags)
            summary_zh = _rough_translate_title(summary, tags) if summary else ""

        if title_zh:
            translations[cluster_id] = {
                "title_zh": title_zh,
                "summary_zh": summary_zh,
                "why_it_matters_zh": _why_it_matters(tags, direction),
            }
    return translations, provider


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
        fallback_items, provider = _fallback_translate_items(request_items)
        if fallback_items:
            return {
                "enabled": True,
                "items": fallback_items,
                "requested_count": len(request_items),
                "translated_count": len(fallback_items),
                "provider": provider,
                "llm_error": "translation_llm_unavailable",
            }
        return {
            "enabled": False,
            "items": {},
            "error": "translation_llm_unavailable",
        }

    try:
        data = _extract_json_object(output)
    except Exception as exc:
        fallback_items, provider = _fallback_translate_items(request_items)
        if fallback_items:
            return {
                "enabled": True,
                "items": fallback_items,
                "requested_count": len(request_items),
                "translated_count": len(fallback_items),
                "provider": provider,
                "llm_error": f"translation_parse_failed: {type(exc).__name__}: {exc}",
            }
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
        "provider": "llm",
    }
