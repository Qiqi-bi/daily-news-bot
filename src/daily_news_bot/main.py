from __future__ import annotations

import argparse
import copy
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .api_sources import collect_api_articles_with_status
from .clustering import cluster_articles
from .config import load_settings, load_sources
from .credibility import annotate_and_filter_articles, credibility_summary_to_dict
from .dashboard import render_dashboard_html
from .decision_journal import build_advice_tracking, build_decision_snapshot, update_decision_journal
from .execution_checks import fetch_execution_checks
from .fixed_pool_history import fetch_fixed_pool_history
from .fetchers import collect_articles_with_status
from .fund_holdings import fetch_portfolio_fund_holdings
from .logic_playbook import build_logic_playbook, render_logic_playbook_markdown
from .market_data import fetch_market_snapshot
from .official_pages import collect_official_page_articles_with_status
from .portfolio import build_portfolio_brief, load_portfolio
from .portfolio_quotes import fetch_portfolio_quotes, update_portfolio_history
from .portfolio_weekly import build_weekly_portfolio_review
from .prediction_lens import build_prediction_lens, render_prediction_lens_markdown
from .ranking import rank_clusters, summarize_tag_distribution
from .report import render_report, save_json, save_text
from .senders import send_feishu_message
from .signal_validation import build_signal_validation, render_signal_validation_markdown
from .strategic_lens import build_strategic_lens, render_strategic_lens_markdown
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


def _normalize_public_url(value: Any) -> str:
    url = str(value or "").strip()
    match = re.match(r"^(https?://)([^/]+)(.*)$", url)
    if not match:
        return url
    return match.group(1).lower() + match.group(2).lower() + match.group(3)


def _public_output_url(dashboard_public_url: str, filename: str) -> str:
    dashboard_public_url = _normalize_public_url(dashboard_public_url)
    if not dashboard_public_url:
        return ""
    if dashboard_public_url.endswith("/"):
        base_url = dashboard_public_url
    elif dashboard_public_url.endswith((".html", ".htm")):
        base_url = dashboard_public_url.rsplit("/", 1)[0] + "/"
    else:
        base_url = dashboard_public_url + "/"
    return base_url + filename.lstrip("/")


def _load_feishu_receipt_status(path: str | Path = "outputs/feishu_receipts.json") -> dict[str, Any]:
    target = Path(path)
    if not target.exists():
        return {"configured": False, "status": "not_run", "appended_count": 0}
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "configured": True,
            "ok": False,
            "status": "read_error",
            "error": f"{type(exc).__name__}: {exc}"[:300],
            "appended_count": 0,
        }
    if not isinstance(payload, dict):
        return {"configured": True, "ok": False, "status": "invalid_payload", "appended_count": 0}
    payload.setdefault("configured", not bool(payload.get("skipped")))
    payload.setdefault("appended_count", 0)
    payload.setdefault("status", "ok" if payload.get("ok") else "error")
    return payload


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
    action_lines = _pick_lines(portfolio.get("action_slot_lines"), 3) or ["- 暂无纪律触发；默认继续持有，不因单日新闻操作。"]

    lines = [
        "## 今日入口",
        "",
        f"- 组合：约 {_fmt_cny(summary.get('total_value_cny'))}；日内 {_fmt_pct(quotes.get('portfolio_estimated_day_change_pct'))}；近一周 {_fmt_pct(quotes.get('portfolio_week_change_pct'))}。",
        f"- 本土节奏：{local_line}",
        f"- 事件翻译：{route_line}",
        f"- 全球30秒：{global_line}",
        watchlist_line,
        "",
        "## 中长期纪律",
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


def _feishu_cjk_count(text: str) -> int:
    return sum(1 for char in text if "\u4e00" <= char <= "\u9fff")


def _feishu_latin_count(text: str) -> int:
    return sum(1 for char in text if "a" <= char.lower() <= "z")


def _feishu_too_much_english(text: str) -> bool:
    latin = _feishu_latin_count(text)
    cjk = _feishu_cjk_count(text)
    return latin >= 18 and latin > max(cjk * 2, 18)


def _feishu_cluster_fallback_title(cluster: dict[str, Any]) -> str:
    tags = [_feishu_tag_label(tag) for tag in (cluster.get("tags") or [])]
    tag_text = "、".join(list(dict.fromkeys(tag for tag in tags if tag))[:3]) or "综合"
    direction = str(cluster.get("direction") or "待确认")
    credibility = str(cluster.get("credibility_label") or "待确认")
    sources = int(cluster.get("confirmed_source_count") or 0)
    source_text = f"{sources} 个信源" if sources else "信源待确认"
    return f"{tag_text}事件：方向{direction}，可信度{credibility}，{source_text}"


def _feishu_title(cluster: dict[str, Any], translations: dict[str, Any]) -> str:
    representative = cluster.get("representative") or {}
    cluster_id = str(cluster.get("cluster_id") or "")
    translated = translations.get(cluster_id) or {}
    title = str(translated.get("title_zh") or "").strip()
    if title and not _feishu_too_much_english(title):
        return title
    raw_title = str(representative.get("title") or cluster.get("theme") or "").strip()
    if raw_title and _feishu_cjk_count(raw_title) >= 4 and not _feishu_too_much_english(raw_title):
        return raw_title
    return _feishu_cluster_fallback_title(cluster)


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


def _build_feishu_news_lines(clusters: list[dict[str, Any]], translations: dict[str, Any]) -> list[str]:
    if not clusters:
        return ["本次没有筛出核心新闻；先看市场快照和提醒状态。"]

    result: list[str] = []
    for index, cluster in enumerate(clusters[:3], start=1):
        translated = translations.get(str(cluster.get("cluster_id") or "")) or {}
        title = _feishu_short(_feishu_title(cluster, translations), 58)
        summary = str(translated.get("why_it_matters_zh") or translated.get("summary_zh") or "").strip()
        if _feishu_too_much_english(summary):
            summary = ""
        tags = [_feishu_tag_label(tag) for tag in cluster.get("tags") or []]
        tag_text = "、".join(list(dict.fromkeys(tag for tag in tags if tag))[:3]) or "综合"
        direction = str(cluster.get("direction") or "待确认")
        credibility = str(cluster.get("credibility_label") or "待确认")
        source_count = int(cluster.get("confirmed_source_count") or 0)
        verify = f"{source_count} 源确认" if source_count else "先二次确认"
        detail = _feishu_short(summary, 72) if summary else f"影响 {tag_text}，方向 {direction}，{verify}"
        result.append(f"{index}. {title}；{detail}；可信度 {credibility}。")
    return result


def _feishu_fmt_market_change(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "未知"
    return f"{number:+.2f}%"


def _build_feishu_market_lines(payload: dict[str, Any]) -> list[str]:
    items = (payload.get("market_snapshot") or {}).get("items") or []
    if not items:
        return ["本次没有拿到市场快照；动手前先查实时价格。"]

    preferred = ["WTI原油", "布伦特原油", "黄金", "美元指数", "美国10Y国债收益率", "VIX", "标普500期货", "纳斯达克100期货", "离岸人民币"]
    by_name = {str(item.get("name") or ""): item for item in items}
    ordered = [by_name[name] for name in preferred if name in by_name]
    ordered.extend(item for item in items if item not in ordered)

    result: list[str] = []
    display_names = {
        "WTI原油": "美国原油",
        "VIX": "波动率指数",
        "美国10Y国债收益率": "美国十年期收益率",
    }
    for item in ordered[:7]:
        raw_name = str(item.get("name") or "未知资产")
        name = display_names.get(raw_name, raw_name)
        change = _feishu_fmt_market_change(item.get("change_pct"))
        movement = str(item.get("movement") or "待确认")
        result.append(f"{name}：{change}，{movement}")
    return result


def _build_feishu_market_summary(payload: dict[str, Any]) -> str:
    lines = _build_feishu_market_lines(payload)
    if not lines:
        return "市场快照暂不可用，动手前先查实时价格。"
    return "市场：" + "；".join(lines[:5]) + "。"


def _feishu_action_visible_line(raw: Any) -> str:
    cleaned = _feishu_clean_line(raw)
    cleaned = re.sub(r"^\d+\.\s*", "", cleaned)
    cleaned = re.sub(r"\([0-9A-Za-z.=^_-]{3,}\)", "", cleaned)
    cleaned = re.sub(r"参考金额\s*¥?[0-9,.\s~￥¥]+", "参考金额按纪律表", cleaned)
    cleaned = re.sub(r"单只参考\s*¥?[0-9,.\s~￥¥]+", "单只金额按纪律表", cleaned)
    cleaned = re.sub(r"¥[0-9,]+(?:\.\d+)?\s*(?:~|-|至)\s*¥?[0-9,]+(?:\.\d+)?", "纪律区间", cleaned)
    cleaned = re.sub(r"¥[0-9,]+(?:\.\d+)?", "纪律金额", cleaned)
    return _feishu_short(cleaned, 118)


def _build_feishu_action_tendency(payload: dict[str, Any]) -> str:
    tracking = ((payload.get("portfolio") or {}).get("advice_tracking") or {})
    today_items = tracking.get("today_items") or []
    if today_items:
        item = today_items[0]
        action = str(item.get("action") or "继续持有")
        subject = _feishu_action_visible_line(item.get("subject") or "")
        verify_date = str(item.get("verify_at_utc") or "")[:10]
        suffix = f"；{verify_date} 回看" if verify_date else "；30天后回看"
        return _feishu_short(f"{action}｜{subject}{suffix}", 135)

    lines = _build_feishu_action_lines(payload)
    return _feishu_short(lines[0] if lines else "继续持有｜今天没有明确纪律触发，等待价格和事件继续确认。", 135)


def _build_feishu_action_lines(payload: dict[str, Any]) -> list[str]:
    portfolio = payload.get("portfolio") or {}
    if portfolio.get("enabled"):
        lines = []
        for raw in portfolio.get("action_slot_lines") or []:
            cleaned = _feishu_action_visible_line(raw)
            if cleaned:
                lines.append(_feishu_short(cleaned, 120))
        if lines:
            return lines[:3]
        return ["组合配置已接入；今天没有明确纪律触发，默认继续持有，动手前复核价格和仓位。"]

    return [
        "当前只能给新闻和价格提示：线上没有你的持仓、成本、现金和目标比例，所以不能判断仓位纪律。",
        "今天默认：观察，不追单；先看原油、黄金、美元、VIX 是否继续确认新闻方向。",
        "要生成持有/补仓/减仓复核，需要接入组合配置；建议默认只发飞书或私密产物，不放公开网页。",
    ]


def _build_feishu_focus_lines(payload: dict[str, Any]) -> list[str]:
    radar = ((payload.get("portfolio") or {}).get("industry_radar") or {})
    rows = radar.get("rows") or []
    focused = [
        row
        for row in rows
        if row.get("status") in {"今日关注", "每日必看", "降权观察"} and row.get("layer") != "avoid"
    ]
    if not focused:
        focused = [row for row in rows if row.get("layer") == "core"]

    result: list[str] = []
    for row in focused[:3]:
        score = str(row.get("score_card_text") or row.get("status") or "观察")
        watch = _feishu_short(row.get("watch") or row.get("why") or "", 58)
        result.append(f"{row.get('name') or '未命名行业'}｜{score}｜{watch}")
    if not result:
        result = ["今天没有新增行业信号；继续看核心资产价格是否确认。"]
    fillers = [
        "市场确认｜看黄金、原油、美元、美债是否支持新闻方向",
        "组合纪律｜看仓位是否偏离目标区间，不因单日新闻硬交易",
        "周报复盘｜只把连续确认的建议升级，不追一次性热点",
    ]
    for filler in fillers:
        if len(result) >= 3:
            break
        result.append(filler)
    return result[:3]


def _feishu_pct_range(values: Any) -> str:
    if isinstance(values, (list, tuple)) and values:
        items = list(values)
        low = float(items[0] or 0)
        high = float(items[1] if len(items) > 1 else items[0] or 0)
        if abs(low - high) < 0.001:
            return _fmt_pct(low)
        return f"{_fmt_pct(low)}~{_fmt_pct(high)}"
    return "未设置"


def _build_feishu_objective_lines(payload: dict[str, Any]) -> list[str]:
    objective = (payload.get("portfolio") or {}).get("annual_objective") or {}
    if not objective:
        return []
    base = _feishu_pct_range(objective.get("base_return_pct_range"))
    stretch = _feishu_pct_range(objective.get("stretch_return_pct_range"))
    drawdown = _fmt_pct(float(objective.get("max_annual_drawdown_pct") or 15.0))
    discipline = _feishu_short(objective.get("discipline") or "目标收益不触发单笔交易。", 88)
    return [
        f"年度目标：基础 {base}；冲刺 {stretch}；回撤红线 {drawdown}。",
        f"纪律：{discipline}",
    ]


def _build_feishu_strategic_lines(payload: dict[str, Any]) -> list[str]:
    lens = payload.get("strategic_lens") or {}
    rows = lens.get("rows") or []
    if not rows:
        return []

    result: list[str] = []
    for row in rows[:2]:
        title = _feishu_short(row.get("title") or "未命名事件", 42)
        game_read = _feishu_short(row.get("game_read") or row.get("question") or "", 74)
        result.append(f"{row.get('theme_label') or '资源约束'}：{title}｜{game_read}")
    result.append("纪律：先升级观察和确认条件，不把叙事直接变成买卖。")
    return result


def _build_feishu_prediction_lines(payload: dict[str, Any]) -> list[str]:
    lens = payload.get("prediction_lens") or {}
    cards = lens.get("cards") or []
    if not cards:
        return []

    result: list[str] = []
    for card in cards[:2]:
        result.append(
            f"{card.get('label') or '预警'}｜{card.get('window') or '待定'}｜"
            f"置信 {card.get('confidence') or '未知'}：{_feishu_short(card.get('prediction'), 82)}"
        )
    result.append("验证：至少等政策/订单/价格/相对强弱中两项确认；没确认不追。")
    return result


def _build_feishu_industry_radar_lines(payload: dict[str, Any]) -> list[str]:
    radar = (payload.get("portfolio") or {}).get("industry_radar") or {}
    rows = radar.get("rows") or []
    if not rows:
        return []

    focused = [
        row
        for row in rows
        if row.get("status") in {"今日关注", "每日必看"} and row.get("layer") != "avoid"
    ]
    if not focused:
        focused = [row for row in rows if row.get("layer") == "core"]

    result: list[str] = []
    for row in focused[:4]:
        name = row.get("name") or "未命名行业"
        status = row.get("status") or "观察"
        watch = _feishu_short(row.get("watch") or row.get("why") or "", 78)
        result.append(f"{name}｜{status}：{watch}")
    result.append("规则：行业雷达只决定看什么，不自动扩可买池，不直接生成买卖。")
    return result


def _build_feishu_validation_lines(payload: dict[str, Any]) -> list[str]:
    validation = payload.get("signal_validation") or {}
    rows = validation.get("rows") or []
    if not rows:
        return _pick_lines(validation.get("lines"), 2)

    result: list[str] = []
    for row in rows[:2]:
        t5 = row.get("t5") or {}
        samples = int(t5.get("samples") or 0)
        if samples:
            result.append(
                f"{row.get('theme') or '未命名'}：T+5 样本 {samples}，胜率 {float(t5.get('win_rate_pct') or 0):.0f}%，均值 {float(t5.get('avg_return_pct') or 0):+.2f}%，{row.get('verdict') or '继续观察'}。"
            )
        else:
            result.append(f"{row.get('theme') or '未命名'}：样本继续积累，先不把胜率当结论。")
    result.append("用途：验算只校准系统权重，不直接触发买卖。")
    return result


def _build_feishu_receipt_lines() -> list[str]:
    return [
        "有交易：复制一行回给我，我来入账；没操作不用回复，系统按原仓位继续。",
        "买入/加仓：买入 代码 金额 价格 原因；例：买入 518880 3000 5.12 黄金回落补保险仓。",
        "卖出/减仓：卖出 代码 份额/比例 价格 原因；例：卖出 513100 20% 1.35 AI仓位超线。",
    ]


def _build_feishu_receipt_status_line(payload: dict[str, Any]) -> str:
    status = payload.get("feishu_receipts") or {}
    if not status or status.get("status") == "not_run":
        return "回执状态：本次未读取；下次日报运行前会读取飞书群。"
    if status.get("skipped"):
        return f"回执状态：未启用；{_feishu_short(status.get('reason') or '缺少飞书群配置', 80)}"
    if not status.get("ok", False):
        return f"回执状态：读取失败；{_feishu_short(status.get('error') or '请看 Actions 日志', 100)}"
    return (
        f"回执状态：扫描 {status.get('message_count', 0)} 条，"
        f"新增入账 {status.get('appended_count', 0)} 条，"
        f"重复 {status.get('duplicate_count', 0)} 条，"
        f"解析失败 {status.get('error_count', 0)} 条。"
    )


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


def _build_feishu_digest(payload: dict[str, Any], receipt_form_url: str = "") -> str:
    watchlist = payload.get("watchlist") or {}
    dashboard = payload.get("dashboard") or {}
    dashboard_url = dashboard.get("archive_url") or dashboard.get("public_url") or "https://qiqi-bi.github.io/daily-news-bot/"
    receipt_line = _build_feishu_receipt_status_line(payload).replace("回执状态：", "")
    validation = payload.get("signal_validation") or {}
    clusters = list(payload.get("clusters") or [])
    translations = _feishu_translation_items(payload)
    overview = _build_feishu_overview(payload, clusters, translations)
    news_lines = _build_feishu_news_lines(clusters, translations)
    market_summary = _build_feishu_market_summary(payload)
    action_tendency = _build_feishu_action_tendency(payload)
    focus_lines = _build_feishu_focus_lines(payload)

    lines: list[str] = [
        "**总判断**",
        _feishu_short(f"{overview} {market_summary}", 260),
        "- 本卡不是交易指令，不保证收益；完整依据打开网页。",
        "",
        "**3条新闻**",
    ]
    lines.extend(news_lines[:3])
    lines.extend(
        [
            "",
            "**3个关注**",
        ]
    )
    lines.extend(f"{index}. {line}" for index, line in enumerate(focus_lines[:3], start=1))
    lines.extend(
        [
            "",
            "**调仓倾向**",
            f"- {action_tendency}",
            "",
            "**回执/周报**",
            f"- {receipt_line}；有交易才回一行中文，没操作不用回。",
            "- 周报只看系统建议有没有连续确认；不要每天为了新闻硬交易。",
        ]
    )
    if receipt_form_url:
        lines.append("- 也可以点卡片按钮填写回执。")
    lines.extend(
        [
            "",
            "**状态**",
            f"- 提醒触发 {watchlist.get('triggered_count', 0)} 条；事后验算累计 {validation.get('signal_count', 0)} 条信号。",
            "- 飞书不放英文原文、完整持仓、成本价、仓位金额；只给纪律级方向。",
            "",
            f"网页：{dashboard_url}",
        ]
    )
    if receipt_form_url:
        lines.append(f"回执页：{receipt_form_url}")
    return "\n".join(lines)


def _downgraded_priority(priority: str, score_delta: int) -> str:
    if score_delta >= 0:
        return priority
    if priority == "高":
        return "中"
    if priority == "中":
        return "低"
    return priority


def _apply_signal_validation_adjustments(portfolio_payload: dict[str, Any], validation: dict[str, Any]) -> None:
    adjustments = validation.get("adjustments") or {}
    if not adjustments:
        return

    for row in portfolio_payload.get("candidate_scores") or []:
        theme_key = str(row.get("theme_key") or "")
        adjustment = adjustments.get(theme_key)
        if not adjustment:
            continue
        score_delta = int(adjustment.get("score_delta") or 0)
        original_score = float(row.get("score") or 0)
        original_priority = str(row.get("priority") or "低")
        row["validation_adjustment"] = adjustment
        row["score_before_validation"] = original_score
        row["score"] = max(0, round(original_score + score_delta, 2))
        row["priority_before_validation"] = original_priority
        row["priority"] = _downgraded_priority(original_priority, score_delta)
        row["comment"] = f"{row.get('comment') or ''}；事后验算：{adjustment.get('adjustment')}。".strip("；")

    radar = portfolio_payload.get("industry_radar") or {}
    for row in radar.get("rows") or []:
        theme_key = str(row.get("id") or row.get("theme_key") or row.get("name") or "")
        adjustment = adjustments.get(theme_key)
        if not adjustment:
            continue
        row["validation_adjustment"] = adjustment
        score_card = row.get("score_card") or {}
        score_delta = int(adjustment.get("score_delta") or 0)
        if score_card:
            original_hit_rate = int(score_card.get("hit_rate") or 0)
            score_card["hit_rate"] = max(0, min(5, original_hit_rate + score_delta))
            score_card["hit_rate_note"] = str(adjustment.get("adjustment") or "事后验算更新")
            score_card["total"] = sum(
                int(score_card.get(key) or 0)
                for key in ("policy", "supply", "price", "news", "hit_rate")
            )
            score_card["label"] = "强观察" if score_card["total"] >= 18 else "观察" if score_card["total"] >= 12 else "积累"
            row["score_card"] = score_card
            row["score_card_text"] = (
                f"{score_card.get('total', 0)}分/{score_card.get('label', '积累')}；"
                f"政{score_card.get('policy', 0)} 供{score_card.get('supply', 0)} "
                f"价{score_card.get('price', 0)} 闻{score_card.get('news', 0)} 命{score_card.get('hit_rate', 0)}"
            )
        if int(adjustment.get("score_delta") or 0) < 0:
            row["status_before_validation"] = row.get("status")
            row["status"] = "降权观察"
            row["action"] = "先降权复核，不把该行业故事直接升级成买卖。"


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
            "annual_objective": portfolio.get("annual_objective") or {},
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


def _sanitize_public_feishu_receipts(payload: dict[str, Any]) -> dict[str, Any]:
    public_payload = copy.deepcopy(payload)
    receipt_status = public_payload.get("feishu_receipts") or {}
    if receipt_status:
        public_payload["feishu_receipts"] = {
            "configured": bool(receipt_status.get("configured")),
            "ok": bool(receipt_status.get("ok")),
            "skipped": bool(receipt_status.get("skipped")),
            "status": receipt_status.get("status"),
            "message_count": int(receipt_status.get("message_count") or 0),
            "ignored_count": int(receipt_status.get("ignored_count") or 0),
            "duplicate_count": int(receipt_status.get("duplicate_count") or 0),
            "error_count": int(receipt_status.get("error_count") or 0),
            "appended_count": int(receipt_status.get("appended_count") or 0),
        }
    return public_payload


def _strip_internal_path_values(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _strip_internal_path_values(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_strip_internal_path_values(item) for item in value]
    if not isinstance(value, str):
        return value

    normalized = value.replace("\\", "/")
    public_url = _normalize_public_url(value)
    if public_url != value:
        return public_url
    if normalized.startswith("file://"):
        return ""
    if "/home/runner/" in normalized or re.match(r"^[A-Za-z]:/", normalized):
        return normalized.rstrip("/").rsplit("/", 1)[-1]
    return value


def _sanitize_public_output_references(payload: dict[str, Any]) -> dict[str, Any]:
    public_payload = copy.deepcopy(payload)
    output_paths = dict(public_payload.get("output_paths") or {})
    public_labels = {
        "report_md_path": "report.md",
        "report_json_path": "report.json",
        "portfolio_md_path": "portfolio_brief.md",
        "weekly_md_path": "portfolio_weekly.md",
        "dashboard_html_path": "dashboard.html",
    }
    for key, label in public_labels.items():
        if key in output_paths:
            output_paths[key] = label
    for key in list(output_paths):
        if key.endswith("_uri"):
            output_paths[key] = ""
    public_payload["output_paths"] = output_paths

    dashboard = dict(public_payload.get("dashboard") or {})
    if "output_path" in dashboard:
        dashboard["output_path"] = "dashboard.html"
    public_payload["dashboard"] = dashboard
    public_payload = _strip_internal_path_values(public_payload)

    watchlist = dict(public_payload.get("watchlist") or {})
    for key in ("state_path", "config_path"):
        watchlist.pop(key, None)
    if watchlist:
        public_payload["watchlist"] = watchlist
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
    strategic_lens = build_strategic_lens(top_clusters, market_snapshot)
    prediction_lens = build_prediction_lens(top_clusters, market_snapshot)
    logic_playbook = build_logic_playbook()

    portfolio_brief = ""
    portfolio_payload: dict[str, Any] = {"enabled": False}
    weekly_review_markdown = ""
    weekly_review_payload: dict[str, Any] = {"enabled": False}
    signal_validation: dict[str, Any] = {"enabled": False, "lines": []}
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
                    action_slot_lines=portfolio_payload.get("action_slot_lines") or [],
                )
                update_decision_journal(decision_snapshot)
                advice_tracking = build_advice_tracking(decision_snapshot)
                portfolio_payload["decision_snapshot"] = decision_snapshot
                portfolio_payload["advice_tracking"] = advice_tracking
                if advice_tracking.get("lines"):
                    portfolio_brief = portfolio_brief.rstrip() + "\n\n## 建议追踪\n\n" + "\n".join(advice_tracking["lines"]) + "\n"
                    if weekly_review_markdown:
                        weekly_review_markdown = weekly_review_markdown.rstrip() + "\n\n## 建议追踪\n\n" + "\n".join(advice_tracking["lines"]) + "\n"
                    if weekly_review_payload.get("enabled"):
                        weekly_review_payload["advice_tracking"] = advice_tracking
            except Exception as exc:
                portfolio_payload["decision_snapshot_error"] = f"{type(exc).__name__}: {exc}"[:300]
            try:
                signal_validation = build_signal_validation(
                    generated_at=generated_at,
                    portfolio_payload=portfolio_payload,
                    execution_checks=execution_checks,
                )
                signal_validation["enabled"] = True
                _apply_signal_validation_adjustments(portfolio_payload, signal_validation)
                portfolio_payload["signal_validation"] = signal_validation
            except Exception as exc:
                signal_validation = {
                    "enabled": False,
                    "error": f"{type(exc).__name__}: {exc}"[:300],
                    "lines": [f"- 事后验算暂不可用：{type(exc).__name__}: {exc}"[:500]],
                }
                portfolio_payload["signal_validation"] = signal_validation

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
    strategic_lens_markdown = render_strategic_lens_markdown(strategic_lens)
    if strategic_lens_markdown:
        global_report = global_report.rstrip() + "\n\n" + strategic_lens_markdown + "\n"
    prediction_lens_markdown = render_prediction_lens_markdown(prediction_lens)
    if prediction_lens_markdown:
        global_report = global_report.rstrip() + "\n\n" + prediction_lens_markdown + "\n"
    logic_playbook_markdown = render_logic_playbook_markdown(logic_playbook)
    if logic_playbook_markdown:
        global_report = global_report.rstrip() + "\n\n" + logic_playbook_markdown + "\n"
    signal_validation_markdown = render_signal_validation_markdown(signal_validation) if signal_validation.get("enabled") else ""
    if signal_validation_markdown:
        global_report = global_report.rstrip() + "\n\n" + signal_validation_markdown + "\n"
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
        "strategic_lens": strategic_lens,
        "prediction_lens": prediction_lens,
        "logic_playbook": logic_playbook,
        "signal_validation": signal_validation,
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
    payload["feishu_receipts"] = _load_feishu_receipt_status()
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
    dashboard_public_url = _normalize_public_url(os.getenv("DASHBOARD_PUBLIC_URL", "").strip())
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
        "archive_url": _normalize_public_url(os.getenv("DASHBOARD_ARCHIVE_URL", "").strip()),
        "archive_index_url": _normalize_public_url(os.getenv("DASHBOARD_ARCHIVE_INDEX_URL", "").strip()),
    }

    payload["dashboard"] = {
        "enabled": True,
        "output_path": str(dashboard_path),
        "public_url": dashboard_public_url,
        "archive_url": payload["output_paths"]["archive_url"],
        "archive_index_url": payload["output_paths"]["archive_index_url"],
    }

    output_payload = _public_payload_without_private_portfolio(payload) if redact_portfolio_outputs else copy.deepcopy(payload)
    if dashboard_public_url:
        output_payload = _sanitize_public_output_references(output_payload)
    output_payload = _sanitize_public_feishu_receipts(output_payload)
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
    if args.send_feishu and (
        settings.feishu_webhook_url
        or (
            settings.feishu_app_id
            and settings.feishu_app_secret
            and (settings.feishu_send_chat_id or settings.feishu_send_chat_name)
        )
    ):
        feishu_content = _build_feishu_digest(payload, settings.feishu_receipt_form_url)
        sender = send_feishu_message(
            webhook_url=settings.feishu_webhook_url,
            app_id=settings.feishu_app_id,
            app_secret=settings.feishu_app_secret,
            chat_id=settings.feishu_send_chat_id,
            chat_name=settings.feishu_send_chat_name,
            title="每日投资雷达",
            content=feishu_content,
            allow_webhook_fallback=settings.feishu_allow_webhook_fallback,
        )
        print(f"Feishu message sent via {sender}.")

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
