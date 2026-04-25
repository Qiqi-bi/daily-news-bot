from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import Settings
from .llm import generate_report
from .models import EventCluster
from .prompts import SYSTEM_PROMPT, build_user_prompt


def _format_number(value: float | None) -> str:
    if value is None:
        return "未知"
    absolute_value = abs(value)
    if absolute_value >= 1000:
        return f"{value:,.2f}"
    if absolute_value >= 100:
        return f"{value:.2f}"
    if absolute_value >= 1:
        return f"{value:.3f}"
    return f"{value:.4f}"


def _market_lines(market_snapshot: dict[str, Any] | None) -> list[str]:
    if not market_snapshot:
        return ["- 本次未提供市场价格快照。"]

    items = market_snapshot.get("items") or []
    failures = market_snapshot.get("failures") or []
    if not items:
        error_text = market_snapshot.get("error") or "暂无可用价格数据。"
        return [f"- {error_text}", f"- 失败资产数：{len(failures)}"] if failures else [f"- {error_text}"]

    lines: list[str] = []
    for item in items[:8]:
        pct = item.get("change_pct")
        pct_text = "未知" if pct is None else f"{pct:+.3f}%"
        lines.append(
            f"- {item.get('name')}：{_format_number(item.get('price'))} {item.get('currency') or ''} | "
            f"日变动 {pct_text} | {item.get('movement', '未知')}"
        )
    if failures:
        lines.append(f"- 另有 {len(failures)} 个资产未返回价格。")
    return lines


def _tracking_map(tracking_summary: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not tracking_summary:
        return {}
    return {
        item.get("cluster_id", ""): item
        for item in tracking_summary.get("tracked_events") or []
        if item.get("cluster_id")
    }


def _build_watch_signals(
    clusters: list[EventCluster],
    market_snapshot: dict[str, Any] | None,
) -> list[str]:
    signals: list[str] = []
    for cluster in clusters[:3]:
        signals.append(f"{cluster.representative.title} 是否获得更多官方确认或实质性进展。")

    market_items = market_snapshot.get("items") if market_snapshot else []
    for item in market_items or []:
        if item.get("group") in {"energy", "rates", "volatility"}:
            signals.append(f"{item.get('name')} 是否延续当前 {item.get('movement', '波动')} 方向。")
        if len(signals) >= 5:
            break

    generic_signals = [
        "是否出现新的政策表态、制裁、停火或央行口径变化。",
        "是否有更多官方源与主流媒体形成交叉验证。",
    ]
    for signal in generic_signals:
        if len(signals) >= 5:
            break
        signals.append(signal)
    return signals[:5]


def build_fallback_report(
    clusters: list[EventCluster],
    mode: str,
    market_snapshot: dict[str, Any] | None = None,
    tracking_summary: dict[str, Any] | None = None,
) -> str:
    headline = {
        "morning": "# 全球市场早报",
        "noon": "# 全球市场午报",
        "evening": "# 全球市场晚报",
    }.get(mode, "# 全球重大事件与市场影响简报")

    tracked = _tracking_map(tracking_summary)
    lines: list[str] = [
        headline,
        "",
        "> 注意：模型分析未返回内容，本次为规则化 fallback 报告。建议检查 .env 的模型配置或接口兼容性。",
        "",
        "## 30 秒总览",
        "",
    ]

    for cluster in clusters[:5]:
        representative = cluster.representative
        lines.append(
            f"- {representative.title}；主要影响：{', '.join(cluster.tags) or '综合'}；方向：{cluster.direction}。"
        )

    lines.extend(["", "## 市场价格快照", ""])
    lines.extend(_market_lines(market_snapshot))

    lines.extend(["", "## 今日最重要的事件", ""])
    for index, cluster in enumerate(clusters, start=1):
        representative = cluster.representative
        tracking_item = tracked.get(cluster.cluster_id, {})
        continuity_text = "是" if tracking_item.get("seen_recently") else "否"
        recent_titles = " / ".join(tracking_item.get("recent_titles") or []) or "无"
        lines.extend(
            [
                f"### {index}. {representative.title}",
                f"**一句话结论：** 这是一个与 {', '.join(cluster.tags) or '综合'} 相关的重要事件，市场方向偏向 {cluster.direction}。",
                f"**真实性状态：** {cluster.credibility_label}；交叉验证来源 {cluster.confirmed_source_count} 家；官方确认：{'是' if cluster.official_confirmation else '否'}。",
                f"**发生了什么：** {representative.summary or representative.title}",
                f"**为什么重要：** 该事件被 {len(cluster.articles)} 条报道覆盖，重要性为 {cluster.importance}。",
                f"**影响链条：** 事件发生 → 预期变化 → {', '.join(cluster.tags) or '相关资产'} 重新定价。",
                "**受益方：** 素材未提供足够细节时，以直接受主题推动的资产与行业为主。",
                "**受损方：** 素材未提供足够细节时，以直接受主题冲击的资产与行业为主。",
                f"**对市场的含义：** 当前确定性为 {cluster.certainty}，需要结合价格、交叉验证和后续官方确认一起看。",
                f"**连续事件追踪：** 近 7 天连续出现：{continuity_text}；近期相似标题：{recent_titles}。",
                "**接下来 24～72 小时盯什么：** 后续政策表态、关键价格变化，以及是否出现更多官方源或主流媒体交叉确认。",
                "",
            ]
        )

    lines.extend(["## 连续事件追踪", ""])
    tracked_events = (tracking_summary or {}).get("tracked_events") or []
    if tracked_events:
        for item in tracked_events:
            recent_titles = " / ".join(item.get("recent_titles") or []) or "无"
            lines.append(
                f"- {item.get('theme')} | 近 7 天出现 {item.get('match_count', 0)} 次 | "
                f"上次出现：{item.get('last_seen_utc') or '无'} | 近期标题：{recent_titles}"
            )
    else:
        lines.append("- 本次没有可追踪的连续事件。")

    lines.extend(["", "## 明天最该盯的 5 个信号", ""])
    for index, signal in enumerate(_build_watch_signals(clusters, market_snapshot), start=1):
        lines.append(f"{index}. {signal}")

    lines.extend(
        [
            "",
            "## 哪些消息不要过度解读",
            "",
            "- 单一来源、低确定性的事件，先等更多媒体或官方源确认。",
            "- 谈判、听证、停火、调查等仍在推进中的消息，不要当成已经落地。",
            "- 单日价格大涨大跌，往往先反映情绪，不一定代表趋势已经确认。",
            "",
            "## 一句话总结",
            "",
            "今天更重要的不是单条新闻本身，而是这些事件如何共同改变了市场对增长、通胀、利率和风险偏好的定价。",
        ]
    )
    return "\n".join(lines).strip() + "\n"



def sanitize_report_output(content: str) -> str:
    """Remove model overreach such as support/resistance levels or direct trading instructions."""
    blocked_terms = ("支撑", "阻力", "目标位", "止损")
    direct_advice_terms = ("建议买入", "建议卖出", "可以加仓", "可以减仓", "直接买入", "直接卖出")
    kept_lines: list[str] = []
    removed = 0
    for line in content.splitlines():
        if any(term in line for term in blocked_terms) or any(term in line for term in direct_advice_terms):
            removed += 1
            continue
        kept_lines.append(line)

    cleaned = "\n".join(kept_lines).strip()
    if removed:
        cleaned += "\n\n> 风险提示：已自动移除模型生成的支撑位、阻力位、目标位或直接交易指令；本报告只作为信息整理与研究参考。"
    elif "风险提示" not in cleaned:
        cleaned += "\n\n> 风险提示：本报告只作为信息整理与研究参考，不构成投资建议。"
    return cleaned.strip() + "\n"
def render_report(
    settings: Settings,
    clusters: list[EventCluster],
    mode: str,
    market_snapshot: dict[str, Any] | None = None,
    tracking_summary: dict[str, Any] | None = None,
) -> tuple[str, bool]:
    user_prompt = build_user_prompt(
        mode,
        clusters,
        market_snapshot=market_snapshot,
        tracking_summary=tracking_summary,
    )
    llm_output = generate_report(settings, SYSTEM_PROMPT, user_prompt)
    if llm_output:
        return sanitize_report_output(llm_output), True
    return sanitize_report_output(build_fallback_report(
        clusters,
        mode,
        market_snapshot=market_snapshot,
        tracking_summary=tracking_summary,
    )), False


def save_text(path: str | Path, content: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def save_json(path: str | Path, payload: dict) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
