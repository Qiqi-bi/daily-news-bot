from __future__ import annotations

import argparse
import copy
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .api_sources import collect_api_articles_with_status
from .clustering import cluster_articles
from .config import load_settings, load_sources
from .credibility import annotate_and_filter_articles, credibility_summary_to_dict
from .dashboard import render_dashboard_html
from .decision_journal import build_decision_snapshot, update_decision_journal
from .execution_checks import fetch_execution_checks
from .fixed_pool_history import fetch_fixed_pool_history
from .fetchers import collect_articles_with_status
from .fund_holdings import fetch_portfolio_fund_holdings
from .market_data import fetch_market_snapshot
from .official_pages import collect_official_page_articles_with_status
from .portfolio import build_portfolio_brief, load_portfolio
from .portfolio_quotes import fetch_portfolio_quotes, update_portfolio_history
from .portfolio_weekly import build_weekly_portfolio_review
from .ranking import rank_clusters, summarize_tag_distribution
from .report import render_report, save_json, save_text
from .senders import send_feishu_webhook
from .trade_ledger import aggregate_trade_ledger, apply_trade_ledger_to_portfolio, load_trade_ledger
from .tracking import build_tracking_summary, update_event_history
from .translations import translate_cluster_highlights
from .watchlist import evaluate_watchlist, render_watchlist_markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="全球重大事件与市场影响日报机器人")
    parser.add_argument("--mode", default="comprehensive", choices=["comprehensive", "morning", "noon", "evening"])
    parser.add_argument("--hours", type=int, default=None)
    parser.add_argument("--top", type=int, default=None)
    parser.add_argument("--per-source-limit", type=int, default=None)
    parser.add_argument("--sources", default=None, help="sources.yaml 路径")
    parser.add_argument("--output", default="outputs/report.md")
    parser.add_argument("--json-output", default="outputs/report.json")
    parser.add_argument("--portfolio", default="config/portfolio.yaml", help="个人组合配置 YAML 路径")
    parser.add_argument("--portfolio-output", default="outputs/portfolio_brief.md")
    parser.add_argument("--no-portfolio", action="store_true", help="不生成个人组合影响速览")
    parser.add_argument("--weekly-review", action="store_true", help="额外生成周日组合复盘")
    parser.add_argument("--weekly-review-output", default="outputs/portfolio_weekly.md")
    parser.add_argument("--dashboard-output", default="outputs/dashboard.html")
    parser.add_argument("--send-feishu", action="store_true")
    return parser


def _iso_or_none(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _dedupe_articles(articles: list) -> list:
    deduped = {}
    for article in articles:
        existing = deduped.get(article.url)
        if existing is None:
            deduped[article.url] = article
            continue
        if article.official_source and not existing.official_source:
            deduped[article.url] = article
            continue
        if article.source_weight > existing.source_weight:
            deduped[article.url] = article
            continue
        if article.published_at > existing.published_at:
            deduped[article.url] = article
    return sorted(deduped.values(), key=lambda item: item.published_at, reverse=True)


def _build_source_coverage(statuses: list[dict[str, Any]]) -> dict[str, int]:
    configured = len(statuses)
    enabled = sum(1 for item in statuses if item.get("enabled", True))
    with_articles = sum(1 for item in statuses if item.get("returned_articles", 0) > 0)
    failed = sum(1 for item in statuses if item.get("enabled", True) and not item.get("ok", True))
    empty = sum(
        1 for item in statuses if item.get("enabled", True) and item.get("ok", True) and item.get("returned_articles", 0) == 0
    )
    skipped_undated = sum(int(item.get("skipped_undated", 0)) for item in statuses)
    skipped_old = sum(int(item.get("skipped_old", 0)) for item in statuses)
    configured_official = sum(1 for item in statuses if item.get("official"))
    official_with_articles = sum(
        1 for item in statuses if item.get("official") and item.get("returned_articles", 0) > 0
    )

    rss_statuses = [item for item in statuses if item.get("source_type") == "rss"]
    api_statuses = [item for item in statuses if item.get("source_type") == "api"]
    api_key_configured = sum(1 for item in api_statuses if item.get("key_configured"))
    api_enabled = sum(1 for item in api_statuses if item.get("enabled"))
    api_with_articles = sum(1 for item in api_statuses if item.get("returned_articles", 0) > 0)

    return {
        "configured_sources": configured,
        "enabled_sources": enabled,
        "sources_with_articles": with_articles,
        "sources_empty_in_window": empty,
        "sources_failed": failed,
        "skipped_undated_entries": skipped_undated,
        "skipped_old_entries": skipped_old,
        "configured_official_sources": configured_official,
        "official_sources_with_articles": official_with_articles,
        "rss_sources_configured": len(rss_statuses),
        "rss_sources_with_articles": sum(1 for item in rss_statuses if item.get("returned_articles", 0) > 0),
        "api_sources_configured": len(api_statuses),
        "api_keys_configured": api_key_configured,
        "api_sources_enabled": api_enabled,
        "api_sources_with_articles": api_with_articles,
    }



def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo:
        return value.astimezone(timezone.utc)
    return value.replace(tzinfo=timezone.utc)


def _format_time_utc_bjt(value: datetime | None) -> str:
    utc_value = _as_utc(value)
    if utc_value is None:
        return "未知"
    bjt_value = utc_value.astimezone(timezone(timedelta(hours=8)))
    return f"{utc_value.strftime('%Y-%m-%d %H:%M')} UTC / {bjt_value.strftime('%Y-%m-%d %H:%M')} BJT"


def _iso_bjt(value: datetime | None) -> str | None:
    utc_value = _as_utc(value)
    if utc_value is None:
        return None
    return utc_value.astimezone(timezone(timedelta(hours=8))).replace(tzinfo=None).isoformat()


def _build_data_quality_payload(
    *,
    generated_at: datetime,
    window_start: datetime,
    articles: list[Any],
    source_status: list[dict[str, Any]],
    source_coverage: dict[str, int],
    market_snapshot: dict[str, Any] | None,
    official_page_articles_count: int,
    credibility_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    published_values = [article.published_at for article in articles]
    latest_article_at = max(published_values) if published_values else None
    oldest_article_at = min(published_values) if published_values else None
    latest_age_hours = None
    if latest_article_at is not None:
        latest_age_hours = round(max((generated_at - latest_article_at).total_seconds() / 3600, 0), 2)

    if latest_age_hours is None:
        freshness_status = "无可用新闻"
    elif latest_age_hours <= 4:
        freshness_status = "新鲜"
    elif latest_age_hours <= 12:
        freshness_status = "可用"
    else:
        freshness_status = "偏旧，需手动复核是否漏了突发消息"

    failed_sources = [
        {
            "name": item.get("name"),
            "source_type": item.get("source_type"),
            "error": item.get("error", ""),
        }
        for item in source_status
        if item.get("enabled", True) and not item.get("ok", True)
    ]
    empty_sources = [
        item.get("name")
        for item in source_status
        if item.get("enabled", True) and item.get("ok", True) and item.get("returned_articles", 0) == 0
    ]
    market_coverage = (market_snapshot or {}).get("coverage") or {}
    credibility = credibility_summary or {}

    return {
        "generated_at_utc": generated_at.isoformat(),
        "generated_at_bjt": _iso_bjt(generated_at),
        "window_start_utc": window_start.isoformat(),
        "window_start_bjt": _iso_bjt(window_start),
        "latest_article_at_utc": _iso_or_none(latest_article_at),
        "latest_article_at_bjt": _iso_bjt(latest_article_at),
        "oldest_article_at_utc": _iso_or_none(oldest_article_at),
        "oldest_article_at_bjt": _iso_bjt(oldest_article_at),
        "latest_article_age_hours": latest_age_hours,
        "freshness_status": freshness_status,
        "articles_count": len(articles),
        "official_articles_count": sum(1 for article in articles if getattr(article, "official_source", False)),
        "official_page_articles_count": official_page_articles_count,
        "source_coverage": source_coverage,
        "failed_sources_sample": failed_sources[:8],
        "empty_sources_count": len(empty_sources),
        "empty_sources_sample": empty_sources[:8],
        "market_coverage": market_coverage,
        "credibility_filtered_articles": int(credibility.get("filtered_articles", 0)),
        "credibility_high_articles": int(credibility.get("high_credibility_articles", 0)),
        "credibility_medium_articles": int(credibility.get("medium_credibility_articles", 0)),
        "credibility_low_articles": int(credibility.get("low_credibility_articles", 0)),
        "credibility_filtered_samples": list(credibility.get("filtered_samples") or [])[:5],
        "boundary_note": "公开RSS/API/官方网页抓取，不保证100%全网、付费终端专有快讯或全球第一时间；重大交易前仍需二次确认。",
    }


def _render_data_quality_section(data_quality: dict[str, Any]) -> str:
    coverage = data_quality.get("source_coverage") or {}
    market_coverage = data_quality.get("market_coverage") or {}
    latest_age = data_quality.get("latest_article_age_hours")
    latest_age_text = "未知" if latest_age is None else f"{latest_age:.2f}小时"
    lines = [
        "## 数据覆盖与时效",
        "",
        f"- 生成时间：{data_quality.get('generated_at_utc', '未知')} UTC / {data_quality.get('generated_at_bjt', '未知')} BJT。",
        f"- 抓取窗口：{data_quality.get('window_start_utc', '未知')} UTC → {data_quality.get('generated_at_utc', '未知')} UTC。",
        f"- 实际新闻：共 {data_quality.get('articles_count', 0)} 条；最早 {data_quality.get('oldest_article_at_utc') or '未知'}，最新 {data_quality.get('latest_article_at_utc') or '未知'}；最新距生成约 {latest_age_text}，状态：{data_quality.get('freshness_status', '未知')}。",
        f"- 来源覆盖：RSS {coverage.get('rss_sources_with_articles', 0)}/{coverage.get('rss_sources_configured', 0)}；API {coverage.get('api_sources_with_articles', 0)}/{coverage.get('api_sources_enabled', 0)}；官方源 {coverage.get('official_sources_with_articles', 0)}/{coverage.get('configured_official_sources', 0)}；官方网页 {data_quality.get('official_page_articles_count', 0)} 条。",
        f"- 市场价格：{market_coverage.get('returned_assets', 0)}/{market_coverage.get('configured_assets', 0)} 个资产返回；用于验证新闻是否被价格确认，不等同于实时交易终端。",
    ]
    failed = data_quality.get("failed_sources_sample") or []
    if failed:
        failed_text = "、".join(str(item.get("name")) for item in failed[:5])
        lines.append(f"- 抓取失败样例：{failed_text}；失败不会中断报告，但会降低覆盖度。")
    if data_quality.get("empty_sources_count"):
        lines.append(f"- 时间窗内无新内容的来源：{data_quality.get('empty_sources_count')} 个；这通常不代表源失效，只代表窗口内没有新稿或发布时间不可识别。")
    filtered_count = int(data_quality.get("credibility_filtered_articles", 0))
    if filtered_count:
        lines.append(f"- 真实性过滤：已在聚类前拦截 {filtered_count} 条低可信/疑似传闻/疑似伪造内容。")
    high_count = int(data_quality.get("credibility_high_articles", 0))
    medium_count = int(data_quality.get("credibility_medium_articles", 0))
    low_count = int(data_quality.get("credibility_low_articles", 0))
    if high_count or medium_count or low_count:
        lines.append(f"- 剩余文章可信度分布：高 {high_count}｜中 {medium_count}｜低 {low_count}。低可信文章默认会被降权，即使未被拦截也不会优先进入核心事件。")
    lines.append(f"> 边界：{data_quality.get('boundary_note')}")
    return "\n".join(lines).strip()


def _empty_market_snapshot(generated_at: datetime, error: str) -> dict[str, Any]:
    return {
        "provider": "Yahoo Finance chart API",
        "captured_at_utc": generated_at.isoformat(),
        "items": [],
        "failures": [],
        "coverage": {
            "configured_assets": 0,
            "returned_assets": 0,
            "failed_assets": 0,
        },
        "error": error,
    }


def _empty_tracking_summary(generated_at: datetime, error: str) -> dict[str, Any]:
    return {
        "generated_at_utc": generated_at.isoformat(),
        "lookback_days": 7,
        "tracked_events": [],
        "error": error,
    }


def _continued_event_count(tracking_summary: dict[str, Any]) -> int:
    return sum(1 for item in tracking_summary.get("tracked_events", []) if item.get("seen_recently"))


def _public_output_url(dashboard_public_url: str, filename: str) -> str:
    if not dashboard_public_url:
        return ""
    if dashboard_public_url.endswith("/"):
        base_url = dashboard_public_url
    elif dashboard_public_url.endswith((".html", ".htm")):
        base_url = dashboard_public_url.rsplit("/", 1)[0] + "/"
    else:
        base_url = dashboard_public_url + "/"
    return base_url + filename.lstrip("/")


def _extract_30s_overview(content: str) -> str:
    markers = ("## 30秒总览", "## 30 秒总览")
    start = -1
    marker = ""
    for candidate in markers:
        start = content.find(candidate)
        if start >= 0:
            marker = candidate
            break
    if start < 0:
        return "完整全球雷达已生成，请查看 outputs/report.md。"
    section_start = start + len(marker)
    next_heading = content.find("\n## ", section_start)
    section = content[section_start: next_heading if next_heading >= 0 else len(content)].strip()
    return section[:1200].strip() or "完整全球雷达已生成，请查看 outputs/report.md。"


def _fmt_cny(value: float | None) -> str:
    if value is None:
        return "未知"
    return f"¥{value:,.0f}"


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "未知"
    return f"{value:.2f}%"


def _compact_text(content: str, limit: int = 220) -> str:
    compact = " ".join(line.strip("- ").strip() for line in content.splitlines() if line.strip())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


def _pick_lines(lines: list[str] | None, limit: int) -> list[str]:
    result: list[str] = []
    for line in lines or []:
        stripped = line.strip()
        if not stripped:
            continue
        result.append(stripped)
        if len(result) >= limit:
            break
    return result


def _build_feishu_content(report: str, payload: dict[str, Any]) -> str:
    portfolio = payload.get("portfolio") or {}
    data_quality = payload.get("data_quality") or {}
    coverage = data_quality.get("source_coverage") or {}
    latest_age = data_quality.get("latest_article_age_hours")
    latest_age_text = "未知" if latest_age is None else f"{latest_age:.1f}小时"
    quality_line = (
        f"- 最新新闻距生成约 {latest_age_text}；状态：{data_quality.get('freshness_status', '未知')}；"
        f"RSS {coverage.get('rss_sources_with_articles', 0)}/{coverage.get('rss_sources_configured', 0)}，"
        f"API {coverage.get('api_sources_with_articles', 0)}/{coverage.get('api_sources_enabled', 0)}，"
        f"官方 {coverage.get('official_sources_with_articles', 0)}/{coverage.get('configured_official_sources', 0)}；"
        f"已拦截低可信内容 {data_quality.get('credibility_filtered_articles', 0)} 条。"
    )
    dashboard = payload.get("dashboard") or {}
    dashboard_entry = dashboard.get("archive_url") or dashboard.get("public_url") or dashboard.get("output_path") or "outputs/dashboard.html"
    global_line = _compact_text(payload.get("global_30s_overview") or _extract_30s_overview(report), 180)
    watchlist = payload.get("watchlist") or {}
    watchlist_lines = watchlist.get("lines") or []
    watchlist_line = (
        f"- 待办提醒：触发 {watchlist.get('triggered_count', 0)} 条；"
        f"新增 {watchlist.get('new_count', 0)} 条；"
        f"有效 {watchlist.get('active_count', 0)} 条。"
    )
    if watchlist_lines:
        watchlist_line += " " + _compact_text(str(watchlist_lines[0]), 160)

    if not portfolio.get("enabled"):
        return chr(10).join([
            "## 今日入口",
            "",
            f"- 全球30秒：{global_line}",
            watchlist_line,
            quality_line,
            "",
            f"> 驾驶舱：{dashboard_entry}",
            "> 完整全球报告：outputs/report.md",
        ])

    summary = portfolio.get("summary") or {}
    quotes = portfolio.get("portfolio_quotes") or {}
    local_line = _compact_text(" ".join(_pick_lines(portfolio.get("local_market_lines"), 1)), 120) or "A股本土节奏暂不可用。"
    route_line = _compact_text(" ".join(_pick_lines(portfolio.get("event_route_lines"), 1)), 120) or "今天暂无强直连事件。"
    action_lines = _pick_lines(portfolio.get("action_slot_lines"), 3) or ["- 暂无动作建议。"]

    lines = [
        "## 今日入口",
        "",
        f"- 组合：约 {_fmt_cny(summary.get('total_value_cny'))}；日内 {_fmt_pct(quotes.get('portfolio_estimated_day_change_pct'))}；近一周 {_fmt_pct(quotes.get('portfolio_week_change_pct'))}。",
        f"- 本土节奏：{local_line}",
        f"- 事件翻译：{route_line}",
        f"- 全球30秒：{global_line}",
        watchlist_line,
        "",
        "## 今日3个动作",
        "",
    ]
    lines.extend(action_lines)
    lines.extend([
        "",
        "## 数据质量",
        "",
        quality_line,
        "- 覆盖度不是 100% 保证；重大交易前仍要二次确认官方源、价格和仓位纪律。",
        "",
        f"> 驾驶舱：{dashboard_entry}",
        "> 完整组合报告：outputs/portfolio_brief.md",
        "> 完整全球报告：outputs/report.md",
    ])
    return chr(10).join(lines)


def _feishu_short(text: Any, limit: int = 90) -> str:
    compact = " ".join(str(text or "").split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


def _feishu_translation_items(payload: dict[str, Any]) -> dict[str, Any]:
    return (payload.get("translations") or {}).get("items") or {}


def _feishu_title(cluster: dict[str, Any], translations: dict[str, Any]) -> str:
    representative = cluster.get("representative") or {}
    cluster_id = str(cluster.get("cluster_id") or "")
    translated = translations.get(cluster_id) or {}
    return str(translated.get("title_zh") or representative.get("title") or cluster.get("theme") or "未命名事件")


def _feishu_tag_label(tag: Any) -> str:
    mapping = {
        "geopolitics": "地缘",
        "energy": "能源",
        "macro": "宏观",
        "markets": "市场",
        "technology": "科技",
        "ai": "AI",
        "semiconductor": "半导体",
        "rates": "利率",
        "fx": "汇率",
        "gold": "黄金",
        "commodities": "商品",
        "supply_chain": "供应链",
        "policy": "政策",
        "earnings": "财报",
        "crypto": "加密",
    }
    raw = str(tag or "").strip()
    return mapping.get(raw, raw or "综合")


def _feishu_clean_line(text: Any) -> str:
    line = str(text or "").strip()
    while line.startswith(("-", "*", ">", "#")):
        line = line[1:].strip()
    return line.replace("**", "").replace("__", "").replace("`", "")


def _build_feishu_overview(payload: dict[str, Any], clusters: list[dict[str, Any]], translations: dict[str, Any]) -> str:
    titles = [_feishu_short(_feishu_title(cluster, translations), 42) for cluster in clusters[:3]]
    titles = [title for title in titles if title]
    if not titles:
        return "日报已生成。今天先看市场快照、核心事件和提醒状态，动手前再复核实时价格。"

    directions = []
    tags = []
    high_credibility_count = 0
    for cluster in clusters[:6]:
        direction = str(cluster.get("direction") or "").strip()
        if direction and direction not in directions:
            directions.append(direction)
        if cluster.get("credibility_label") == "高":
            high_credibility_count += 1
        for tag in cluster.get("tags") or []:
            label = _feishu_tag_label(tag)
            if label and label not in tags:
                tags.append(label)

    direction_text = "、".join(directions[:3]) or "中性"
    tag_text = "、".join(tags[:4]) or "综合"
    return (
        f"今天先看：{'；'.join(titles)}。"
        f"主线集中在 {tag_text}，方向以 {direction_text} 为主；"
        f"高可信事件 {high_credibility_count} 个。先看价格是否确认，不追单。"
    )


def _build_feishu_action_lines(payload: dict[str, Any]) -> list[str]:
    portfolio = payload.get("portfolio") or {}
    if portfolio.get("enabled"):
        lines = []
        for raw in portfolio.get("action_slot_lines") or []:
            cleaned = _feishu_clean_line(raw)
            if cleaned:
                lines.append(_feishu_short(cleaned, 120))
        if lines:
            return lines[:3]
        return ["组合配置已接入，但今天没有明确触发动作；按原计划观察，动手前复核价格和仓位。"]

    return [
        "当前只能给新闻和价格提示：线上没有你的持仓、成本、现金和目标比例，所以不能判断继续持有、补仓或换仓。",
        "今天默认动作：观察，不追单；先看原油、黄金、美元、VIX 是否继续确认新闻方向。",
        "要生成持有/补仓/减仓/候选标的，需要接入组合配置；建议默认只发飞书或私密产物，不放公开网页。",
    ]


def _build_feishu_receipt_lines() -> list[str]:
    return [
        "有交易：复制一行回给我，我来入账；没操作不用回复，系统按原仓位继续。",
        "买入/加仓：买入 代码 金额 价格 原因；例：买入 518880 3000 5.12 黄金回落补保险仓。",
        "卖出/减仓：卖出 代码 份额/比例 价格 原因；例：卖出 513100 20% 1.35 AI仓位超线。",
    ]


def _feishu_watch_title(item: dict[str, Any], clusters: list[dict[str, Any]], translations: dict[str, Any]) -> str:
    raw_title = str(item.get("title") or "未命名提醒")
    normalized = raw_title.replace("跟踪：", "", 1).replace("跟踪:", "", 1).strip().casefold()
    for cluster in clusters:
        representative = cluster.get("representative") or {}
        original_title = str(representative.get("title") or cluster.get("theme") or "").strip()
        if original_title and original_title.casefold() == normalized:
            title = _feishu_title(cluster, translations)
            return f"跟踪：{title}" if raw_title.startswith(("跟踪：", "跟踪:")) else title
    return raw_title


def _build_feishu_digest(payload: dict[str, Any]) -> str:
    data_quality = payload.get("data_quality") or {}
    coverage = data_quality.get("source_coverage") or {}
    watchlist = payload.get("watchlist") or {}
    clusters = payload.get("clusters") or []
    translations = _feishu_translation_items(payload)
    dashboard = payload.get("dashboard") or {}
    dashboard_url = dashboard.get("archive_url") or dashboard.get("public_url") or "https://qiqi-bi.github.io/daily-news-bot/"

    latest_age = data_quality.get("latest_article_age_hours")
    latest_age_text = "未知" if latest_age is None else f"{float(latest_age):.1f} 小时"
    global_line = _feishu_short(_build_feishu_overview(payload, clusters, translations), 260)

    lines: list[str] = [
        "**今日结论**",
        global_line,
        "",
        "**操作提示**",
        *[f"- {line}" for line in _build_feishu_action_lines(payload)],
        "",
        "**核心事件**",
    ]
    if clusters:
        for index, cluster in enumerate(clusters[:5], start=1):
            tags = "、".join(_feishu_tag_label(tag) for tag in (cluster.get("tags") or [])[:3]) or "综合"
            title = _feishu_short(_feishu_title(cluster, translations), 100)
            lines.append(
                f"{index}. {title}\n"
                f"   方向：{cluster.get('direction') or '未知'}；可信：{cluster.get('credibility_label') or '未知'}；"
                f"信源：{cluster.get('confirmed_source_count', 0)}；标签：{tags}"
            )
    else:
        lines.append("暂无核心事件。")

    market_items = (payload.get("market_snapshot") or {}).get("items") or []
    if market_items:
        lines.extend(["", "**市场快照**"])
        for item in market_items[:6]:
            pct = item.get("change_pct")
            pct_text = "未知" if pct is None else f"{float(pct):+.2f}%"
            lines.append(f"- {item.get('name') or item.get('symbol')}：{item.get('price')}，{pct_text}，{item.get('movement') or '未知'}")

    lines.extend(
        [
            "",
            "**提醒**",
            f"- 触发 {watchlist.get('triggered_count', 0)} 条；新增 {watchlist.get('new_count', 0)} 条；有效 {watchlist.get('active_count', 0)} 条。",
        ]
    )
    watch_items = list(watchlist.get("triggered_items") or []) + list(watchlist.get("new_items") or [])
    for item in watch_items[:3]:
        title = _feishu_short(_feishu_watch_title(item, clusters, translations), 90)
        action = _feishu_short(item.get("action") or "", 90)
        lines.append(f"- {title}" + (f"：{action}" if action else ""))

    lines.extend(
        [
            "",
            "**数据质量**",
            f"- 最新新闻距生成约 {latest_age_text}；状态：{data_quality.get('freshness_status') or '未知'}。",
            f"- RSS {coverage.get('rss_sources_with_articles', 0)}/{coverage.get('rss_sources_configured', 0)}；"
            f"API {coverage.get('api_sources_with_articles', 0)}/{coverage.get('api_sources_enabled', 0)}；"
            f"官方 {coverage.get('official_sources_with_articles', 0)}/{coverage.get('configured_official_sources', 0)}；"
            f"已过滤低可信内容 {data_quality.get('credibility_filtered_articles', 0)} 条。",
            "",
            "**操作回执（有交易才填）**",
            *[f"- {line}" for line in _build_feishu_receipt_lines()],
            "",
            f"Dashboard：{dashboard_url}",
        ]
    )
    return "\n".join(lines)


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _public_payload_without_private_portfolio(payload: dict[str, Any]) -> dict[str, Any]:
    public_payload = copy.deepcopy(payload)
    portfolio = public_payload.get("portfolio") or {}
    if portfolio.get("enabled"):
        public_payload["portfolio"] = {
            "enabled": True,
            "private_mode": True,
            "public_note": "组合配置已接入，但持仓、成本、现金、交易流水和组合估值不发布到公开网页；具体动作看飞书推送。",
        }
        public_payload["portfolio_brief_markdown"] = ""

    weekly = public_payload.get("weekly_review") or {}
    if weekly.get("enabled"):
        public_payload["weekly_review"] = {
            "enabled": True,
            "private_mode": True,
            "public_note": "周复盘已按私密组合生成，但不发布到公开网页。",
        }
        public_payload["weekly_review_markdown"] = ""

    output_paths = public_payload.get("output_paths") or {}
    output_paths.update(
        {
            "portfolio_md_generated": False,
            "portfolio_md_url": "",
            "portfolio_md_uri": "",
            "weekly_md_generated": False,
            "weekly_md_url": "",
            "weekly_md_uri": "",
        }
    )
    public_payload["output_paths"] = output_paths
    return public_payload


def run_pipeline(args: argparse.Namespace) -> tuple[str, dict[str, Any]]:
    settings = load_settings()
    generated_at = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)
    hours_back = args.hours if args.hours is not None else settings.hours_back
    top_events = args.top if args.top is not None else settings.top_events
    if args.weekly_review and args.hours is None:
        hours_back = max(hours_back, 24 * 7)
    if args.weekly_review and args.top is None:
        top_events = max(top_events, 8)
    per_source_limit = args.per_source_limit if args.per_source_limit is not None else settings.per_source_limit
    api_source_limit = settings.api_source_limit
    window_start = generated_at - timedelta(hours=hours_back)

    sources = load_sources(args.sources)
    rss_articles, rss_source_status = collect_articles_with_status(
        sources,
        hours_back=hours_back,
        per_source_limit=per_source_limit,
        now=generated_at,
    )
    official_page_articles, official_page_status = collect_official_page_articles_with_status(
        hours_back=hours_back,
        per_source_limit=min(per_source_limit, 6),
        now=generated_at,
        timeout=min(settings.timeout, 15),
    )
    api_articles, api_source_status = collect_api_articles_with_status(
        settings,
        hours_back=hours_back,
        per_source_limit=api_source_limit,
        now=generated_at,
        timeout=min(settings.timeout, 20),
    )

    articles = _dedupe_articles(rss_articles + official_page_articles + api_articles)
    source_status = rss_source_status + official_page_status + api_source_status
    articles, credibility_summary = annotate_and_filter_articles(articles)

    clusters = cluster_articles(articles)
    ranked = rank_clusters(clusters)
    preferred_clusters = [
        cluster
        for cluster in ranked
        if not (cluster.credibility_label == "低" and cluster.confirmed_source_count == 0 and not cluster.official_confirmation)
    ]
    fallback_clusters = [
        cluster
        for cluster in ranked
        if cluster.credibility_label == "低" and cluster.confirmed_source_count == 0 and not cluster.official_confirmation
    ]
    top_clusters = (preferred_clusters + fallback_clusters)[:top_events]

    try:
        market_snapshot = fetch_market_snapshot(timeout=min(settings.timeout, 10))
    except Exception as exc:
        market_snapshot = _empty_market_snapshot(generated_at, f"{type(exc).__name__}: {exc}")

    try:
        tracking_summary = build_tracking_summary(top_clusters, generated_at)
    except Exception as exc:
        tracking_summary = _empty_tracking_summary(generated_at, f"{type(exc).__name__}: {exc}")

    published_values = [article.published_at for article in articles]
    latest_article_at = max(published_values) if published_values else None
    oldest_article_at = min(published_values) if published_values else None
    source_coverage = _build_source_coverage(source_status)
    data_quality = _build_data_quality_payload(
        generated_at=generated_at,
        window_start=window_start,
        articles=articles,
        source_status=source_status,
        source_coverage=source_coverage,
        market_snapshot=market_snapshot,
        official_page_articles_count=len(official_page_articles),
        credibility_summary=credibility_summary,
    )

    portfolio_brief = ""
    portfolio_payload: dict[str, Any] = {"enabled": False}
    weekly_review_markdown = ""
    weekly_review_payload: dict[str, Any] = {"enabled": False}
    if not args.no_portfolio:
        portfolio = load_portfolio(args.portfolio)
        if portfolio:
            trade_ledger = aggregate_trade_ledger(load_trade_ledger())
            portfolio = apply_trade_ledger_to_portfolio(portfolio, trade_ledger)
            try:
                portfolio_quotes = fetch_portfolio_quotes(portfolio, timeout=min(settings.timeout, 12))
                update_portfolio_history(portfolio_quotes)
            except Exception as exc:
                portfolio_quotes = {
                    "provider": "Eastmoney fundgz + Eastmoney fund history",
                    "captured_at_utc": generated_at.isoformat(),
                    "items": [],
                    "failures": [{"holding_name": "portfolio", "code": "", "error": f"{type(exc).__name__}: {exc}"[:300]}],
                    "coverage": {"configured_holdings": len(portfolio.get("holdings") or []), "returned_holdings": 0, "failed_holdings": len(portfolio.get("holdings") or [])},
                    "portfolio_estimated_day_change_pct": None,
                    "portfolio_week_change_pct": None,
                    "leaders": {"top_positive": [], "top_negative": []},
                }
            try:
                fund_holdings = fetch_portfolio_fund_holdings(portfolio, timeout=min(settings.timeout, 12), top_n=10, portfolio_quotes=portfolio_quotes)
            except Exception as exc:
                fund_holdings = {
                    "provider": "Eastmoney fund quarterly top holdings",
                    "items": [],
                    "overlaps": [],
                    "failures": [{"holding_name": "portfolio", "code": "", "error": f"{type(exc).__name__}: {exc}"[:300]}],
                    "coverage": {"configured_holdings": len(portfolio.get("holdings") or []), "returned_holdings": 0, "failed_holdings": len(portfolio.get("holdings") or [])},
                }
            try:
                execution_checks = fetch_execution_checks(portfolio, timeout=min(settings.timeout, 10))
            except Exception as exc:
                execution_checks = {
                    "provider": "Eastmoney ETF execution checks",
                    "items": [],
                    "failures": [{"code": "portfolio", "name": "portfolio", "error": f"{type(exc).__name__}: {exc}"[:300]}],
                    "coverage": {"configured_assets": 0, "returned_assets": 0, "failed_assets": 1},
                }
            fixed_pool_size = len(((portfolio.get("decision_cockpit") or {}).get("fixed_buy_pool") or []))
            try:
                fixed_pool_history = fetch_fixed_pool_history(portfolio, timeout=min(settings.timeout, 15))
            except Exception as exc:
                fixed_pool_history = {
                    "provider": "Eastmoney fixed buy pool history",
                    "items": [],
                    "failures": [{"code": "fixed_buy_pool", "name": "fixed_buy_pool", "error": f"{type(exc).__name__}: {exc}"[:300]}],
                    "coverage": {"configured_assets": fixed_pool_size, "returned_assets": 0, "failed_assets": fixed_pool_size},
                }
            portfolio_brief, portfolio_payload = build_portfolio_brief(
                portfolio,
                top_clusters,
                market_snapshot=market_snapshot,
                tracking_summary=tracking_summary,
                portfolio_quotes=portfolio_quotes,
                fund_holdings=fund_holdings,
                execution_checks=execution_checks,
                trade_ledger=trade_ledger,
                fixed_pool_history=fixed_pool_history,
            )
            portfolio_payload["enabled"] = True
            portfolio_payload["quotes"] = portfolio_quotes
            portfolio_payload["fund_holdings"] = fund_holdings
            portfolio_payload["execution_checks"] = execution_checks
            portfolio_payload["trade_ledger"] = trade_ledger
            portfolio_payload["fixed_pool_history"] = fixed_pool_history
            if args.weekly_review:
                weekly_review_markdown, weekly_review_payload = build_weekly_portfolio_review(
                    portfolio,
                    top_clusters,
                    portfolio_quotes=portfolio_quotes,
                    fund_holdings=fund_holdings,
                    execution_checks=execution_checks,
                    trade_ledger=trade_ledger,
                    tracking_summary=tracking_summary,
                    market_snapshot=market_snapshot,
                    fixed_pool_history=fixed_pool_history,
                )
                weekly_review_payload["enabled"] = True
            try:
                decision_snapshot = build_decision_snapshot(
                    generated_at=generated_at,
                    summary=portfolio_payload.get("summary") or {},
                    event_impacts=portfolio_payload.get("event_impacts") or [],
                    candidate_scores=portfolio_payload.get("candidate_scores") or [],
                    action_board_lines=portfolio_payload.get("action_board_lines") or [],
                    execution_checks=execution_checks,
                )
                update_decision_journal(decision_snapshot)
                portfolio_payload["decision_snapshot"] = decision_snapshot
            except Exception as exc:
                portfolio_payload["decision_snapshot_error"] = f"{type(exc).__name__}: {exc}"[:300]

    try:
        translations = translate_cluster_highlights(settings, top_clusters)
    except Exception as exc:
        translations = {
            "enabled": False,
            "items": {},
            "error": f"{type(exc).__name__}: {exc}"[:300],
        }
    global_report, llm_used = render_report(
        settings,
        top_clusters,
        args.mode,
        market_snapshot=market_snapshot,
        tracking_summary=tracking_summary,
    )
    global_report = global_report.rstrip() + "\n\n" + _render_data_quality_section(data_quality) + "\n"
    report = f"{portfolio_brief}\n\n---\n\n{global_report}" if portfolio_brief else global_report

    history_update_error = ""
    try:
        history_clusters = ranked[: max(top_events, 8)]
        update_event_history(history_clusters, generated_at)
    except Exception as exc:
        history_update_error = f"{type(exc).__name__}: {exc}"

    payload = {
        "mode": args.mode,
        "generated_at_utc": generated_at.isoformat(),
        "window_start_utc": window_start.isoformat(),
        "hours_back": hours_back,
        "per_source_limit": per_source_limit,
        "api_source_limit": api_source_limit,
        "llm_used": llm_used,
        "articles_count": len(articles),
        "rss_articles_count": len(rss_articles),
        "official_page_articles_count": len(official_page_articles),
        "api_articles_count": len(api_articles),
        "clusters_count": len(clusters),
        "selected_count": len(top_clusters),
        "latest_article_at_utc": _iso_or_none(latest_article_at),
        "oldest_article_at_utc": _iso_or_none(oldest_article_at),
        "source_coverage": source_coverage,
        "credibility_summary": credibility_summary_to_dict(credibility_summary),
        "data_quality": data_quality,
        "source_status": source_status,
        "rss_source_status": rss_source_status,
        "api_source_status": api_source_status,
        "market_snapshot": market_snapshot,
        "tracking_summary": tracking_summary,
        "tracking_history_update_error": history_update_error,
        "portfolio": portfolio_payload,
        "portfolio_brief_markdown": portfolio_brief,
        "weekly_review": weekly_review_payload,
        "weekly_review_markdown": weekly_review_markdown,
        "_global_report_markdown": global_report,
        "global_30s_overview": _extract_30s_overview(global_report),
        "tag_distribution": summarize_tag_distribution(top_clusters),
        "translations": translations,
        "clusters": [cluster.to_dict() for cluster in top_clusters],
    }
    try:
        watchlist_summary = evaluate_watchlist(
            generated_at=generated_at,
            clusters=top_clusters,
            market_snapshot=market_snapshot,
            portfolio_payload=portfolio_payload,
        )
    except Exception as exc:
        watchlist_summary = {
            "generated_at_utc": generated_at.isoformat(),
            "active_count": 0,
            "triggered_count": 0,
            "expired_count": 0,
            "new_count": 0,
            "triggered_items": [],
            "new_items": [],
            "active_items": [],
            "error": f"{type(exc).__name__}: {exc}"[:300],
            "lines": [f"- watchlist 检查失败：{type(exc).__name__}: {exc}"[:500]],
        }
    payload["watchlist"] = watchlist_summary
    watchlist_section = render_watchlist_markdown(watchlist_summary)
    if watchlist_section:
        report = report.rstrip() + "\n\n" + watchlist_section
        if portfolio_brief:
            portfolio_brief = portfolio_brief.rstrip() + "\n\n" + watchlist_section
            payload["portfolio_brief_markdown"] = portfolio_brief
            payload["portfolio"]["watchlist_lines"] = watchlist_summary.get("lines") or []
            payload["portfolio"]["watchlist"] = watchlist_summary
    return report, payload


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    report, payload = run_pipeline(args)
    global_report = str(payload.pop("_global_report_markdown", "") or "")

    report_path = Path(args.output).resolve()
    json_path = Path(args.json_output).resolve()
    portfolio_path = Path(args.portfolio_output).resolve()
    weekly_path = Path(args.weekly_review_output).resolve()
    dashboard_path = Path(args.dashboard_output).resolve()
    dashboard_public_url = os.getenv("DASHBOARD_PUBLIC_URL", "").strip()
    portfolio_public_outputs = _env_flag("PORTFOLIO_PUBLIC_OUTPUTS", False)
    redact_portfolio_outputs = (
        bool(dashboard_public_url)
        and bool((payload.get("portfolio") or {}).get("enabled"))
        and not portfolio_public_outputs
    )

    payload["output_paths"] = {
        "report_md_path": str(report_path),
        "report_md_uri": report_path.as_uri(),
        "report_md_url": _public_output_url(dashboard_public_url, "report.md"),
        "report_json_path": str(json_path),
        "report_json_uri": json_path.as_uri(),
        "report_json_url": _public_output_url(dashboard_public_url, "report.json"),
        "portfolio_md_path": str(portfolio_path),
        "portfolio_md_uri": portfolio_path.as_uri(),
        "portfolio_md_url": _public_output_url(dashboard_public_url, "portfolio_brief.md"),
        "portfolio_md_generated": bool(payload.get("portfolio_brief_markdown")),
        "weekly_md_path": str(weekly_path),
        "weekly_md_uri": weekly_path.as_uri(),
        "weekly_md_url": _public_output_url(dashboard_public_url, "portfolio_weekly.md"),
        "weekly_md_generated": bool(payload.get("weekly_review_markdown")),
        "dashboard_html_path": str(dashboard_path),
        "dashboard_html_uri": dashboard_path.as_uri(),
        "dashboard_html_url": dashboard_public_url,
        "archive_url": os.getenv("DASHBOARD_ARCHIVE_URL", "").strip(),
        "archive_index_url": os.getenv("DASHBOARD_ARCHIVE_INDEX_URL", "").strip(),
    }

    payload["dashboard"] = {
        "enabled": True,
        "output_path": str(dashboard_path),
        "public_url": dashboard_public_url,
        "archive_url": payload["output_paths"]["archive_url"],
        "archive_index_url": payload["output_paths"]["archive_index_url"],
    }

    output_payload = _public_payload_without_private_portfolio(payload) if redact_portfolio_outputs else payload
    output_report = global_report if redact_portfolio_outputs and global_report else report

    save_text(args.output, output_report)
    if not redact_portfolio_outputs and payload.get("portfolio_brief_markdown"):
        save_text(args.portfolio_output, payload["portfolio_brief_markdown"])
    if not redact_portfolio_outputs and payload.get("weekly_review_markdown"):
        save_text(args.weekly_review_output, payload["weekly_review_markdown"])

    dashboard_error = ""
    try:
        dashboard_html = render_dashboard_html(output_payload)
        save_text(args.dashboard_output, dashboard_html)
    except Exception as exc:
        dashboard_error = f"{type(exc).__name__}: {exc}"
        output_payload["dashboard"]["enabled"] = False
        output_payload["dashboard"]["error"] = dashboard_error

    save_json(args.json_output, output_payload)

    settings = load_settings()
    if args.send_feishu and settings.feishu_webhook_url:
        feishu_content = _build_feishu_digest(payload)
        send_feishu_webhook(settings.feishu_webhook_url, "每日投资雷达", feishu_content)

    print(f"Markdown report saved to: {report_path}")
    print(f"JSON metadata saved to: {json_path}")
    if redact_portfolio_outputs:
        print("Portfolio outputs redacted from public dashboard/report; private action lines sent to Feishu.")
    elif payload.get("portfolio", {}).get("enabled"):
        print(f"Portfolio brief saved to: {portfolio_path}")
    if not redact_portfolio_outputs and payload.get("weekly_review", {}).get("enabled"):
        print(f"Weekly review saved to: {weekly_path}")
    if payload.get("dashboard", {}).get("enabled"):
        print(f"Dashboard saved to: {dashboard_path}")
    elif dashboard_error:
        print(f"Dashboard skipped: {dashboard_error}")
    print(f"LLM used: {payload['llm_used']}")
    print(
        "RSS sources with articles: "
        f"{payload['source_coverage']['rss_sources_with_articles']}/"
        f"{payload['source_coverage']['rss_sources_configured']}"
    )
    print(
        "API providers with articles: "
        f"{payload['source_coverage']['api_sources_with_articles']}/"
        f"{payload['source_coverage']['api_sources_enabled']}"
        f" (keys configured: {payload['source_coverage']['api_keys_configured']}/"
        f"{payload['source_coverage']['api_sources_configured']})"
    )
    print(
        "Official sources with articles: "
        f"{payload['source_coverage']['official_sources_with_articles']}/"
        f"{payload['source_coverage']['configured_official_sources']}"
    )
    print(f"Official page articles: {payload.get('official_page_articles_count', 0)}")
    print(
        "Market snapshot assets: "
        f"{payload['market_snapshot']['coverage']['returned_assets']}/"
        f"{payload['market_snapshot']['coverage']['configured_assets']}"
    )
    print(
        "Tracked continuing events: "
        f"{_continued_event_count(payload['tracking_summary'])}/"
        f"{payload['selected_count']}"
    )
    print(
        f"Article window UTC: {payload['window_start_utc']} -> {payload['generated_at_utc']} | "
        f"actual articles: {payload['oldest_article_at_utc']} -> {payload['latest_article_at_utc']}"
    )
    print(f"Credibility-filtered articles: {payload.get('credibility_summary', {}).get('filtered_articles', 0)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
