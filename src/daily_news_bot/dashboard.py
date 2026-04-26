from __future__ import annotations

import re
from html import escape
from typing import Any


def _text(value: Any, default: str = "-") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _shorten(value: Any, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", _text(value, "")).strip()
    if len(text) <= limit:
        return text
    return text[: max(limit - 1, 0)].rstrip() + "…"


def _strip_markdown(value: Any) -> str:
    text = _text(value, "")
    text = re.sub(r"^[-*>#\s]+", "", text).strip()
    text = text.replace("**", "").replace("__", "").replace("`", "")
    return text


def _fmt_num(value: Any) -> str:
    try:
        if value is None:
            return "未知"
        number = float(value)
    except (TypeError, ValueError):
        return "未知"
    if number.is_integer():
        return f"{int(number):,}"
    return f"{number:,.2f}"


def _fmt_pct(value: Any) -> str:
    try:
        if value is None:
            return "未知"
        return f"{float(value):+.2f}%"
    except (TypeError, ValueError):
        return "未知"


def _fmt_price(value: Any, currency: Any = "") -> str:
    try:
        if value is None:
            return "未知"
        price = float(value)
    except (TypeError, ValueError):
        return "未知"
    suffix = f" {currency}" if currency else ""
    if abs(price) >= 100:
        return f"{price:,.2f}{suffix}"
    if abs(price) >= 10:
        return f"{price:,.3f}{suffix}"
    return f"{price:,.4f}{suffix}"


def _fmt_cny(value: Any) -> str:
    try:
        if value is None:
            return "未知"
        return f"¥{float(value):,.2f}"
    except (TypeError, ValueError):
        return "未知"


def _fmt_age(value: Any) -> str:
    try:
        if value is None:
            return "未知"
        number = float(value)
    except (TypeError, ValueError):
        return "未知"
    if number < 1:
        return f"{number * 60:.0f} 分钟"
    return f"{number:.1f} 小时"


def _safe_url(value: Any) -> str:
    url = _text(value, "")
    if url.startswith(("http://", "https://", "file://", "./", "../", "/")):
        return url
    return ""


def _link(label: Any, url: Any, class_name: str = "") -> str:
    href = _safe_url(url)
    text = escape(_text(label))
    class_attr = f' class="{escape(class_name)}"' if class_name else ""
    if not href:
        return text
    return f'<a{class_attr} href="{escape(href)}">{text}</a>'


def _trend_class(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "flat"
    if number > 0:
        return "up"
    if number < 0:
        return "down"
    return "flat"


def _normalize_title_key(value: Any) -> str:
    text = _text(value, "").strip()
    for prefix in ("跟踪：", "跟踪:", "新增跟踪｜", "新增跟踪|"):
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()
    return re.sub(r"\s+", " ", text).casefold()


def _pill(label: Any, kind: str = "neutral") -> str:
    return f'<span class="pill {escape(kind)}">{escape(_text(label))}</span>'


def _metric(title: str, value: str, note: str = "", tone: str = "") -> str:
    tone_class = f" {tone}" if tone else ""
    note_html = f'<div class="metric-note">{escape(note)}</div>' if note else ""
    return (
        f'<div class="metric{tone_class}">'
        f'<div class="metric-title">{escape(title)}</div>'
        f'<div class="metric-value">{escape(value)}</div>'
        f"{note_html}</div>"
    )


def _section(title: str, body: str, subtitle: str = "", class_name: str = "") -> str:
    subtitle_html = f'<div class="section-subtitle">{escape(subtitle)}</div>' if subtitle else ""
    class_attr = f"panel {class_name}".strip()
    return f'<section class="{escape(class_attr)}"><h2>{escape(title)}</h2>{subtitle_html}{body}</section>'


def _empty(message: str = "暂无数据") -> str:
    return f'<div class="empty">{escape(message)}</div>'


def _render_list(lines: list[Any] | None, limit: int | None = None) -> str:
    source = list(lines or [])
    if limit is not None:
        source = source[:limit]
    items = []
    for raw in source:
        line = _strip_markdown(raw)
        if not line or line.startswith("|"):
            continue
        items.append(f"<li>{escape(line)}</li>")
    if not items:
        return _empty()
    return "<ul>" + "".join(items) + "</ul>"


def _render_table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return _empty()
    thead = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body_rows = ["<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows]
    return (
        '<div class="table-wrap"><table>'
        f"<thead><tr>{thead}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table></div>"
    )


def _compact_time(value: Any) -> str:
    text = _text(value, "")
    if not text:
        return "-"
    return text.replace("T", " ").replace("+00:00", " UTC")


def _theme_label(value: Any) -> str:
    mapping = {
        "broad_core": "宽基底仓",
        "growth_core": "成长底仓",
        "ai_attack": "AI进攻",
        "gold_insurance": "黄金保险",
        "dividend_lowvol": "红利低波",
        "power": "电力",
        "semiconductor": "半导体",
        "ai": "AI/科技",
        "energy": "能源/地缘",
        "gold": "黄金/避险",
        "china_macro": "中国宏观",
        "new_energy": "新能源",
    }
    return mapping.get(_text(value, ""), _text(value))


def _tag_label(value: Any) -> str:
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
    raw = _text(value, "")
    return mapping.get(raw, raw or "综合")


def _cluster_rows(clusters: list[dict[str, Any]] | None, translations: dict[str, Any] | None = None) -> str:
    if not clusters:
        return _empty("本次没有筛出核心事件")

    rows = []
    translation_items = translations or {}
    for index, cluster in enumerate(clusters[:10], start=1):
        representative = cluster.get("representative") or {}
        original_title = _text(representative.get("title") or cluster.get("theme"), "未命名事件")
        translation = translation_items.get(_text(cluster.get("cluster_id"), "")) or {}
        title_zh = _text(translation.get("title_zh"), "")
        title = title_zh or original_title
        url = representative.get("url")
        original_summary = _shorten(representative.get("summary") or representative.get("content") or cluster.get("theme"), 260)
        summary_zh = _shorten(translation.get("summary_zh") or translation.get("why_it_matters_zh"), 260)
        summary = summary_zh or original_summary
        original_title_html = ""
        if title_zh and title_zh != original_title:
            original_title_html = f'<div class="event-original">原文：{escape(original_title)}</div>'
        original_summary_html = ""
        if summary_zh and original_summary:
            original_summary_html = f'<div class="event-original">原摘要：{escape(original_summary)}</div>'
        tags = cluster.get("tags") or []
        tag_html = "".join(_pill(_tag_label(tag), "tag") for tag in tags[:5]) or _pill("未分类")
        source = _text(representative.get("source"), "未知来源")
        published = _compact_time(representative.get("published_at"))
        direction = _text(cluster.get("direction"), "中性")
        certainty = _text(cluster.get("certainty"), "未知")
        credibility = _text(cluster.get("credibility_label"), "未知")
        confirmed = _text(cluster.get("confirmed_source_count"), "0")
        importance = _text(cluster.get("importance"), "")
        articles = cluster.get("articles") or []
        article_sources = []
        for article in articles[:4]:
            source_name = _text(article.get("source"), "")
            if source_name:
                article_sources.append(source_name)
        source_line = " / ".join(dict.fromkeys(article_sources)) or source
        notes = cluster.get("credibility_notes") or []
        note_text = "；".join(_text(item, "") for item in notes if _text(item, ""))
        note_html = f'<div class="event-note">{escape(note_text)}</div>' if note_text else ""

        rows.append(
            '<article class="event-row">'
            f'<div class="event-rank">{index}</div>'
            '<div class="event-main">'
            f'<div class="event-title">{_link(title, url)}</div>'
            f"{original_title_html}"
            f'<div class="event-meta">{escape(source)} · {escape(published)} · {escape(source_line)}</div>'
            f'<div class="event-summary">{escape(summary)}</div>'
            f"{original_summary_html}"
            '<div class="event-tags">'
            f'{_pill(direction, "direction")} {_pill("确定性 " + certainty, "neutral")} '
            f'{_pill("可信 " + credibility, "neutral")} {_pill("信源 " + confirmed, "neutral")} '
            f'{_pill(importance, "importance") if importance else ""}{tag_html}'
            "</div>"
            f"{note_html}"
            "</div>"
            "</article>"
        )
    return '<div class="event-list">' + "".join(rows) + "</div>"


def _market_rows(market_snapshot: dict[str, Any]) -> list[list[str]]:
    result = []
    for item in market_snapshot.get("items") or []:
        trend = _trend_class(item.get("change_pct"))
        result.append(
            [
                f'<div class="asset-name">{escape(_text(item.get("name")))}</div><div class="asset-symbol">{escape(_text(item.get("symbol")))}</div>',
                escape(_fmt_price(item.get("price"), item.get("currency"))),
                f'<span class="change {trend}">{escape(_fmt_pct(item.get("change_pct")))}</span>',
                escape(_text(item.get("movement"), "未知")),
                escape(_compact_time(item.get("market_time_utc"))),
            ]
        )
    return result


def _watchlist_item(item: dict[str, Any], label: str, title_translations: dict[str, str] | None = None) -> str:
    condition = item.get("condition_text")
    if not condition and item.get("metric"):
        condition = f"{item.get('symbol') or item.get('metric')} {item.get('operator', '')} {item.get('threshold', '')}"
    observed = item.get("observed") or item.get("last_observed") or ""
    action = item.get("action") or ""
    details = " · ".join(part for part in [_text(condition, ""), _text(observed, "")] if part)
    raw_title = _text(item.get("title"), "未命名提醒")
    translated_title = (title_translations or {}).get(_normalize_title_key(raw_title))
    title = raw_title
    original_html = ""
    if translated_title:
        title = "跟踪：" + translated_title if raw_title.startswith(("跟踪：", "跟踪:")) else translated_title
        original_html = f'<div class="watch-original">原文：{escape(raw_title)}</div>'
    return (
        '<div class="watch-row">'
        f'<div class="watch-label">{escape(label)}</div>'
        f'<div class="watch-title">{escape(title)}</div>'
        f"{original_html}"
        f'<div class="watch-detail">{escape(_shorten(details, 220))}</div>'
        f'<div class="watch-action">{escape(_shorten(action, 220))}</div>'
        "</div>"
    )


def _watchlist_rows(watchlist: dict[str, Any], title_translations: dict[str, str] | None = None) -> str:
    rows = []
    for item in watchlist.get("triggered_items") or []:
        rows.append(_watchlist_item(item, "已触发", title_translations))
    for item in watchlist.get("new_items") or []:
        rows.append(_watchlist_item(item, "新增", title_translations))
    if len(rows) < 8:
        for item in watchlist.get("active_items") or []:
            if len(rows) >= 8:
                break
            rows.append(_watchlist_item(item, "继续盯", title_translations))
    if not rows:
        return _empty("没有触发提醒；系统仍会保留有效提醒并在后续运行继续检查")
    return '<div class="watch-list">' + "".join(rows) + "</div>"


def _coverage_body(payload: dict[str, Any]) -> str:
    data_quality = payload.get("data_quality") or {}
    coverage = data_quality.get("source_coverage") or payload.get("source_coverage") or {}
    market_coverage = data_quality.get("market_coverage") or (payload.get("market_snapshot") or {}).get("coverage") or {}
    credibility = payload.get("credibility_summary") or {}
    filtered = data_quality.get("credibility_filtered_articles", credibility.get("filtered_articles", 0))
    rows = [
        ["生成时间", escape(_compact_time(data_quality.get("generated_at_utc") or payload.get("generated_at_utc")))],
        ["新闻窗口", escape(f'{_compact_time(data_quality.get("window_start_utc") or payload.get("window_start_utc"))} → {_compact_time(data_quality.get("generated_at_utc") or payload.get("generated_at_utc"))}')],
        ["实际新闻", escape(f'{_compact_time(data_quality.get("oldest_article_at_utc") or payload.get("oldest_article_at_utc"))} → {_compact_time(data_quality.get("latest_article_at_utc") or payload.get("latest_article_at_utc"))}')],
        ["RSS 覆盖", escape(f'{coverage.get("rss_sources_with_articles", 0)}/{coverage.get("rss_sources_configured", 0)}')],
        ["API 覆盖", escape(f'{coverage.get("api_sources_with_articles", 0)}/{coverage.get("api_sources_enabled", 0)}')],
        ["官方源", escape(f'{coverage.get("official_sources_with_articles", 0)}/{coverage.get("configured_official_sources", 0)}；官方网页 {data_quality.get("official_page_articles_count", payload.get("official_page_articles_count", 0))} 条')],
        ["市场价格", escape(f'{market_coverage.get("returned_assets", 0)}/{market_coverage.get("configured_assets", 0)}')],
        ["低可信过滤", escape(f"{filtered} 条")],
    ]
    body = _render_table(["项目", "状态"], rows)
    empty_sample = data_quality.get("empty_sources_sample") or []
    if empty_sample:
        body += f'<div class="muted-block">本窗口无新内容的来源样例：{escape("、".join(_text(item) for item in empty_sample[:8]))}</div>'
    boundary = data_quality.get("boundary_note")
    if boundary:
        body += f'<div class="muted-block">{escape(_text(boundary))}</div>'
    return body


def _tag_distribution(tags: dict[str, Any] | None) -> str:
    if not tags:
        return ""
    items = []
    for tag, count in sorted(tags.items(), key=lambda item: (-int(item[1]), item[0]))[:8]:
        items.append(f'{_pill(f"{_tag_label(tag)} {count}", "tag")}')
    return '<div class="tag-strip">' + "".join(items) + "</div>"


def _title_translation_map(clusters: list[dict[str, Any]] | None, translations: dict[str, Any] | None) -> dict[str, str]:
    result: dict[str, str] = {}
    translation_items = translations or {}
    for cluster in clusters or []:
        representative = cluster.get("representative") or {}
        original_title = _text(representative.get("title") or cluster.get("theme"), "")
        title_zh = _text((translation_items.get(_text(cluster.get("cluster_id"), "")) or {}).get("title_zh"), "")
        if original_title and title_zh:
            result[_normalize_title_key(original_title)] = title_zh
            result[_normalize_title_key("跟踪：" + original_title)] = title_zh
    return result


def _cluster_display_title(cluster: dict[str, Any], translations: dict[str, Any]) -> str:
    representative = cluster.get("representative") or {}
    translation = translations.get(_text(cluster.get("cluster_id"), "")) or {}
    return _text(translation.get("title_zh") or representative.get("title") or cluster.get("theme"), "未命名事件")


def _translated_overview(payload: dict[str, Any], translations: dict[str, Any]) -> str:
    clusters = payload.get("clusters") or []
    titles = [_shorten(_cluster_display_title(cluster, translations), 54) for cluster in clusters[:3]]
    titles = [title for title in titles if title and title != "未命名事件"]
    if not titles:
        return _strip_markdown(payload.get("global_30s_overview") or "本次日报已生成。")

    directions = []
    tags = []
    high_credibility_count = 0
    for cluster in clusters[:6]:
        direction = _text(cluster.get("direction"), "")
        if direction and direction not in directions:
            directions.append(direction)
        if cluster.get("credibility_label") == "高":
            high_credibility_count += 1
        for tag in cluster.get("tags") or []:
            label = _tag_label(tag)
            if label and label not in tags:
                tags.append(label)

    direction_text = "、".join(directions[:3]) or "中性"
    tag_text = "、".join(tags[:4]) or "综合"
    return (
        f"今天先看：{'；'.join(titles)}。"
        f"主线集中在 {tag_text}，方向以 {direction_text} 为主；"
        f"高可信事件 {high_credibility_count} 个。先看市场快照是否确认，再决定要不要动手。"
    )


def _action_guidance_items(payload: dict[str, Any]) -> list[tuple[str, str, str]]:
    portfolio = payload.get("portfolio") or {}
    if portfolio.get("private_mode"):
        return [
            ("当前动作", "已生成私密版", "具体组合建议看飞书；公开网页不展示持仓和交易流水。"),
            ("继续持有", "看飞书", "需要持仓、成本和纪律线，已从私密配置计算。"),
            ("补仓/买别的", "看触发条件", "公开页只显示新闻与价格，不给个人化买卖判断。"),
            ("隐私保护", "不公开", "组合估值、AI 暴露、黄金仓位和历史缓存不发布到 Pages。"),
        ]
    if portfolio.get("enabled"):
        rows = []
        for raw in portfolio.get("action_slot_lines") or []:
            line = _strip_markdown(raw)
            if line:
                rows.append(("组合动作", _shorten(line, 92), "按配置生成；仍需复核实时价格、流动性和仓位纪律。"))
            if len(rows) >= 4:
                break
        if rows:
            return rows
        return [("当前动作", "观察", "组合配置已接入，但今天没有明确触发动作。")]

    return [
        ("当前动作", "观察", "缺少线上持仓配置，不生成买卖判断。"),
        ("继续持有", "待组合接入", "需要知道持仓、成本、目标比例和纪律线。"),
        ("补仓/买别的", "先不自动给", "需要现金、候选池、风险预算和买入规则。"),
        ("组合接入", "建议走私密", "默认只推飞书或 Actions 产物，不放公开网页。"),
    ]


def _action_guidance_section(payload: dict[str, Any]) -> str:
    cards = []
    for label, value, note in _action_guidance_items(payload):
        cards.append(
            '<div class="action-card">'
            f'<div class="action-label">{escape(label)}</div>'
            f'<div class="action-value">{escape(value)}</div>'
            f'<div class="action-note">{escape(note)}</div>'
            "</div>"
        )
    note = (
        "这不是交易指令；接入组合后也会输出“复核/观察/候选/纪律提醒”，"
        "动手前仍要确认价格、流动性和个人仓位约束。"
    )
    body = '<div class="action-grid">' + "".join(cards) + f'</div><div class="muted-block">{escape(note)}</div>'
    return _section("今天怎么处理", body, "先把能做和不能做说清楚，避免把新闻摘要误当交易建议。", "wide")


def _public_sibling(output_paths: dict[str, Any], filename: str) -> str:
    for key in ("report_json_url", "report_md_url", "dashboard_html_url"):
        url = _text(output_paths.get(key), "")
        if url.startswith(("http://", "https://")) and "/" in url:
            return url.rsplit("/", 1)[0].rstrip("/") + "/" + filename
    return ""


def _path_links(output_paths: dict[str, Any], dashboard: dict[str, Any]) -> str:
    pairs = [
        ("最新 Dashboard", output_paths.get("dashboard_html_url") or dashboard.get("public_url"), "页面根目录"),
        ("历史归档", output_paths.get("archive_index_url") or dashboard.get("archive_index_url"), "archive.html"),
        ("本次归档", output_paths.get("archive_url") or dashboard.get("archive_url"), "本次运行快照"),
        ("完整日报 Markdown", output_paths.get("report_md_url") or output_paths.get("report_md_uri"), output_paths.get("report_md_path")),
        ("结构化 JSON", output_paths.get("report_json_url") or output_paths.get("report_json_uri"), output_paths.get("report_json_path")),
        ("提醒状态 JSON", _public_sibling(output_paths, "watchlist.json"), "watchlist.json"),
    ]
    if output_paths.get("portfolio_md_generated"):
        pairs.append(("组合简报", output_paths.get("portfolio_md_url") or output_paths.get("portfolio_md_uri"), output_paths.get("portfolio_md_path")))
    if output_paths.get("weekly_md_generated"):
        pairs.append(("周复盘", output_paths.get("weekly_md_url") or output_paths.get("weekly_md_uri"), output_paths.get("weekly_md_path")))

    items = []
    for label, url, note in pairs:
        if not url:
            continue
        items.append(
            "<li>"
            f'{_link(label, url)}'
            f'<span class="path">{escape(_text(note, ""))}</span>'
            "</li>"
        )
    if not items:
        return _empty("暂无可打开的报告入口")
    return '<ul class="link-list">' + "".join(items) + "</ul>"


def _fixed_pool_rows(rows: list[dict[str, Any]] | None) -> list[list[str]]:
    result = []
    for row in rows or []:
        result.append(
            [
                escape(f"{_text(row.get('name'), '')} ({_text(row.get('code'), '')})"),
                escape(_text(row.get("state"), "观察")),
                escape(_text(row.get("amount_band"))),
                escape(_fmt_pct(row.get("day_change_pct"))),
                escape(_text(row.get("role"))),
                escape(_shorten(row.get("reason"), 160)),
            ]
        )
    return result


def _backfill_rows(rows: list[dict[str, Any]] | None) -> list[list[str]]:
    result = []
    for row in rows or []:
        latest_close = row.get("latest_close")
        latest_text = "未知" if latest_close is None else f"{float(latest_close):.4f}"
        result.append(
            [
                escape(f"{_text(row.get('name'), '')} ({_text(row.get('code'), '')})"),
                escape(_theme_label(row.get("theme_key"))),
                escape(_text(row.get("days"), "0")),
                escape(_fmt_pct(row.get("change_20d_pct"))),
                escape(_fmt_pct(row.get("change_60d_pct"))),
                escape(_fmt_pct(row.get("change_120d_pct"))),
                escape(_fmt_pct(row.get("change_250d_pct"))),
                escape(latest_text),
            ]
        )
    return result


def _win_leader_text(leader: dict[str, Any] | None) -> str:
    if not leader:
        return "-"
    return (
        f"{_text(leader.get('name'), '')} ({_text(leader.get('code'), '')}) / "
        f"胜率 {_fmt_pct(leader.get('win_rate_pct'))} / 均值 {_fmt_pct(leader.get('avg_return_pct'))} / "
        f"样本 {_text(leader.get('samples'), '0')}"
    )


def _win_rows(rows: list[dict[str, Any]] | None) -> list[list[str]]:
    result = []
    for row in rows or []:
        sample_days = row.get("sample_days") or {}
        sample_text = "/".join(str(sample_days.get(f"d{window}", 0)) for window in (60, 120, 250))
        selected_window = row.get("selected_window")
        selected_window_text = f"近{selected_window}天" if selected_window else "继续积累"
        leaders = row.get("selected_leaders") or {}
        result.append(
            [
                escape(_theme_label(row.get("theme_key"))),
                escape(sample_text),
                escape(selected_window_text),
                escape(_win_leader_text(leaders.get("t1"))),
                escape(_win_leader_text(leaders.get("t3"))),
                escape(_win_leader_text(leaders.get("t5"))),
            ]
        )
    return result


def _event_route_rows(rows: list[dict[str, Any]] | None) -> list[list[str]]:
    result = []
    for row in rows or []:
        result.append(
            [
                escape(_text(row.get("priority"), "观察")),
                escape(_shorten(row.get("title"), 180)),
                escape(_shorten(row.get("chain"), 220)),
                escape(_shorten(row.get("buy_text"), 160)),
                escape(_shorten(row.get("action_text"), 160)),
            ]
        )
    return result


def _portfolio_sections(portfolio: dict[str, Any], weekly: dict[str, Any]) -> list[str]:
    sections = []
    if portfolio.get("private_mode"):
        sections.append(
            _section(
                "组合配置（私密）",
                '<div class="muted-block">组合配置已接入本次运行，但公开网页不会展示持仓、成本、交易流水、组合估值、AI 暴露、黄金仓位和历史缓存。具体动作提示请看飞书推送。</div>',
                "默认保护你的个人仓位；如需公开展示，需要单独开启 PORTFOLIO_PUBLIC_OUTPUTS。",
                "wide",
            )
        )
        return sections
    if not portfolio.get("enabled"):
        sections.append(
            _section(
                "组合配置",
                '<div class="muted-block">线上没有发布私人持仓配置，所以这里不会展示组合估值、AI 暴露和黄金仓位。当前页面先按公开新闻、市场价格和提醒状态运行。</div>',
                "有本地 config/portfolio.yaml 时，组合区块会自动补上。",
                "wide",
            )
        )
        return sections

    sections.extend(
        [
            _section("今日动作", _render_list(portfolio.get("action_slot_lines"), 5), "只展示需要复核的动作，不替代交易指令。"),
            _section("A 股阶段", _render_list(portfolio.get("local_market_lines"), 8)),
            _section(
                "固定可买池",
                _render_table(
                    ["标的", "状态", "金额档位", "当日变化", "角色", "原因"],
                    _fixed_pool_rows(portfolio.get("fixed_buy_pool_rows")),
                ),
                class_name="wide",
            ),
            _section(
                "固定可买池回填",
                _render_table(
                    ["标的", "主题", "覆盖天数", "20日", "60日", "120日", "250日", "最新"],
                    _backfill_rows(portfolio.get("fixed_pool_backfill_rows")),
                ),
                class_name="wide",
            ),
            _section(
                "T+1/T+3/T+5 胜率",
                _render_table(
                    ["主题", "60/120/250样本", "参考窗口", "T+1", "T+3", "T+5"],
                    _win_rows(portfolio.get("fixed_pool_win_rows")),
                ),
                class_name="wide",
            ),
            _section("写死减仓规则", _render_list(portfolio.get("hard_reduce_rule_lines"), 8)),
            _section(
                "事件到标的映射",
                _render_table(
                    ["优先级", "事件", "传导链", "先看谁", "当前动作"],
                    _event_route_rows(portfolio.get("event_route_rows")),
                ),
                class_name="wide",
            ),
            _section("操作手册", _render_list(portfolio.get("playbook_rule_lines"), 12), class_name="wide"),
        ]
    )

    if weekly.get("enabled"):
        weekly_signals = [f"{index + 1}. {item}" for index, item in enumerate(weekly.get("signals") or [])]
        sections.append(_section("周复盘信号", _render_list(weekly_signals, 8), class_name="wide"))
    return sections


def _metric_cards(payload: dict[str, Any]) -> str:
    portfolio = payload.get("portfolio") or {}
    data_quality = payload.get("data_quality") or {}
    coverage = data_quality.get("source_coverage") or payload.get("source_coverage") or {}
    market_coverage = data_quality.get("market_coverage") or (payload.get("market_snapshot") or {}).get("coverage") or {}
    watchlist = payload.get("watchlist") or {}
    translations = payload.get("translations") or {}
    cards = [
        _metric("核心事件", f"{payload.get('selected_count', 0)} 个", f"从 {payload.get('articles_count', 0)} 条新闻里筛出", "accent"),
        _metric("最新时效", _fmt_age(data_quality.get("latest_article_age_hours")), data_quality.get("freshness_status") or "未知"),
        _metric("市场快照", f'{market_coverage.get("returned_assets", 0)}/{market_coverage.get("configured_assets", 0)}', "能源、黄金、美元、利率、美股期货"),
        _metric("提醒", f'{watchlist.get("triggered_count", 0)} 触发', f'新增 {watchlist.get("new_count", 0)} · 有效 {watchlist.get("active_count", 0)}'),
        _metric("RSS/API", f'{coverage.get("rss_sources_with_articles", 0)}/{coverage.get("rss_sources_configured", 0)} · {coverage.get("api_sources_with_articles", 0)}/{coverage.get("api_sources_enabled", 0)}', "前者 RSS，后者 API"),
        _metric("低可信过滤", f'{data_quality.get("credibility_filtered_articles", (payload.get("credibility_summary") or {}).get("filtered_articles", 0))} 条', "先过滤再聚类"),
    ]
    if translations.get("enabled"):
        cards.append(
            _metric(
                "外文速译",
                f'{translations.get("translated_count", len(translations.get("items") or {}))} 条',
                "核心外文标题自动转中文",
            )
        )
    elif translations.get("error"):
        cards.append(_metric("外文速译", "未完成", "翻译失败时保留原文"))
    if portfolio.get("private_mode"):
        cards.append(_metric("组合配置", "已接入", "私密模式：公开页不显示仓位明细"))
    elif portfolio.get("enabled"):
        summary = portfolio.get("summary") or {}
        quotes = portfolio.get("portfolio_quotes") or {}
        cards.extend(
            [
                _metric("组合估值", _fmt_cny(summary.get("total_value_cny")), "含场内价格/场外估值近似"),
                _metric("组合近一周", _fmt_pct(quotes.get("portfolio_week_change_pct")), "方向参考，不当精确收益"),
                _metric("直接 AI 暴露", _fmt_pct(summary.get("direct_ai_pct")), "纪律线默认 35%"),
                _metric("黄金仓位", _fmt_pct(summary.get("gold_pct")), "保险仓默认 10%-15%"),
            ]
        )
    return '<div class="metrics">' + "".join(cards) + "</div>"


_CSS = """
:root {
  color-scheme: light;
  --bg: #f4f6f8;
  --panel: #ffffff;
  --text: #172033;
  --muted: #647083;
  --line: #dfe5ec;
  --line-soft: #edf1f5;
  --blue: #1f6feb;
  --green: #17803d;
  --red: #bd2c2c;
  --amber: #936100;
  --teal: #0f766e;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans SC", system-ui, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.55;
}
.wrap {
  max-width: 1360px;
  margin: 0 auto;
  padding: 24px 28px 36px;
}
.topbar {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 20px;
  align-items: end;
  margin-bottom: 18px;
}
h1 {
  margin: 0;
  font-size: 30px;
  line-height: 1.2;
  letter-spacing: 0;
}
.subtitle {
  margin-top: 7px;
  color: var(--muted);
  font-size: 14px;
}
.top-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.button-link {
  border: 1px solid var(--line);
  background: #fff;
  color: var(--blue);
  padding: 7px 11px;
  border-radius: 6px;
  font-size: 13px;
}
.lead {
  background: #fff;
  border: 1px solid var(--line);
  border-left: 4px solid var(--blue);
  border-radius: 8px;
  padding: 16px 18px;
  margin-bottom: 14px;
}
.lead-title {
  font-weight: 700;
  margin-bottom: 6px;
}
.lead-text {
  color: #243247;
  font-size: 15px;
}
.tag-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  margin-top: 12px;
}
.metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(176px, 1fr));
  gap: 10px;
  margin: 14px 0 18px;
}
.metric {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 13px 14px;
}
.metric.accent {
  border-top: 3px solid var(--blue);
}
.metric-title {
  color: var(--muted);
  font-size: 12px;
  margin-bottom: 5px;
}
.metric-value {
  font-size: 24px;
  font-weight: 760;
  line-height: 1.2;
}
.metric-note {
  color: var(--muted);
  font-size: 12px;
  margin-top: 6px;
}
.action-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(220px, 100%), 1fr));
  gap: 10px;
}
.action-card {
  border: 1px solid var(--line-soft);
  background: #f8fafc;
  border-radius: 8px;
  padding: 12px;
  min-height: 98px;
}
.action-label {
  color: var(--muted);
  font-size: 12px;
  margin-bottom: 4px;
}
.action-value {
  font-size: 18px;
  font-weight: 760;
  line-height: 1.35;
  overflow-wrap: anywhere;
}
.action-note {
  color: var(--muted);
  font-size: 12px;
  margin-top: 7px;
}
.grid {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(360px, .65fr);
  gap: 14px;
  align-items: start;
}
.panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 16px;
  overflow: hidden;
}
.panel.wide {
  grid-column: 1 / -1;
}
.panel h2 {
  margin: 0 0 4px;
  font-size: 18px;
  line-height: 1.3;
}
.section-subtitle {
  color: var(--muted);
  font-size: 13px;
  margin-bottom: 12px;
}
.event-list {
  display: grid;
  gap: 0;
}
.event-row {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: 12px;
  padding: 14px 0;
  border-top: 1px solid var(--line-soft);
}
.event-row:first-child {
  border-top: 0;
  padding-top: 4px;
}
.event-rank {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 6px;
  background: #e8f1ff;
  color: #164a9f;
  font-weight: 700;
  font-size: 13px;
}
.event-title {
  font-weight: 700;
  font-size: 15px;
  line-height: 1.4;
}
.event-meta,
.event-note,
.event-original,
.asset-symbol,
.path,
.watch-detail,
.watch-action,
.watch-original,
.muted-block {
  color: var(--muted);
  font-size: 12px;
}
.event-summary {
  color: #27364b;
  margin-top: 6px;
  font-size: 13px;
}
.event-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 9px;
}
.event-note {
  margin-top: 7px;
}
.event-original {
  margin-top: 4px;
}
.pill {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 2px 7px;
  border-radius: 999px;
  border: 1px solid var(--line);
  color: #334155;
  background: #f8fafc;
  font-size: 12px;
  white-space: nowrap;
}
.pill.direction {
  color: var(--teal);
  border-color: #badbd7;
  background: #effaf8;
}
.pill.tag {
  color: #4d3b00;
  border-color: #f1d68a;
  background: #fff9e8;
}
.pill.importance {
  color: #7c2d12;
  border-color: #fdba74;
  background: #fff7ed;
}
.table-wrap {
  overflow: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
th,
td {
  border-bottom: 1px solid var(--line-soft);
  padding: 9px 8px;
  text-align: left;
  vertical-align: top;
}
th {
  color: var(--muted);
  font-weight: 650;
  background: #fafbfc;
}
.asset-name {
  font-weight: 650;
}
.change.up {
  color: var(--green);
  font-weight: 700;
}
.change.down {
  color: var(--red);
  font-weight: 700;
}
.change.flat {
  color: var(--muted);
  font-weight: 700;
}
.watch-list {
  display: grid;
  gap: 10px;
}
.watch-row {
  border-top: 1px solid var(--line-soft);
  padding-top: 10px;
}
.watch-row:first-child {
  border-top: 0;
  padding-top: 0;
}
.watch-label {
  display: inline-block;
  color: var(--amber);
  background: #fff8e1;
  border: 1px solid #ecd58a;
  border-radius: 6px;
  padding: 1px 6px;
  font-size: 12px;
  margin-bottom: 5px;
}
.watch-title {
  font-weight: 700;
}
.watch-action {
  margin-top: 3px;
}
.watch-original {
  margin-top: 2px;
}
ul {
  margin: 0;
  padding-left: 18px;
}
li {
  margin: 7px 0;
}
.link-list li {
  margin: 9px 0;
}
.path {
  display: block;
  margin-top: 2px;
  word-break: break-all;
}
.empty {
  color: var(--muted);
  padding: 8px 0;
}
.muted-block {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--line-soft);
}
a {
  color: var(--blue);
  text-decoration: none;
}
a:hover {
  text-decoration: underline;
}
.footer {
  color: var(--muted);
  font-size: 12px;
  margin-top: 16px;
}
@media (max-width: 900px) {
  .wrap {
    padding: 18px 14px 28px;
  }
  .topbar {
    grid-template-columns: 1fr;
  }
  .top-actions {
    justify-content: flex-start;
  }
  .grid {
    grid-template-columns: 1fr;
  }
  h1 {
    font-size: 25px;
  }
}
"""


def render_dashboard_html(payload: dict[str, Any]) -> str:
    portfolio = payload.get("portfolio") or {}
    weekly = payload.get("weekly_review") or {}
    data_quality = payload.get("data_quality") or {}
    output_paths = payload.get("output_paths") or {}
    dashboard = payload.get("dashboard") or {}
    watchlist = payload.get("watchlist") or {}
    market_snapshot = payload.get("market_snapshot") or {}
    translations = ((payload.get("translations") or {}).get("items") or {})
    title_translations = _title_translation_map(payload.get("clusters"), translations)
    generated = data_quality.get("generated_at_bjt") or payload.get("generated_at_utc") or "未知"
    global_overview = _translated_overview(payload, translations)
    archive_url = output_paths.get("archive_index_url") or dashboard.get("archive_index_url")
    report_url = output_paths.get("report_md_url") or output_paths.get("report_md_uri")

    lead = (
        '<div class="lead">'
        '<div class="lead-title">30 秒总览</div>'
        f'<div class="lead-text">{escape(global_overview)}</div>'
        f'{_tag_distribution(payload.get("tag_distribution"))}'
        "</div>"
    )

    actions = []
    if report_url:
        actions.append(_link("打开完整日报", report_url, "button-link"))
    if archive_url:
        actions.append(_link("历史归档", archive_url, "button-link"))
    top_actions = '<div class="top-actions">' + "".join(actions) + "</div>" if actions else ""

    sections = [
        _action_guidance_section(payload),
        _section("今日核心事件", _cluster_rows(payload.get("clusters"), translations), "按重要性、可信度和来源交叉验证排序；外文标题会自动加中文速译。", "wide"),
        _section(
            "市场快照",
            _render_table(["资产", "价格", "涨跌", "状态", "行情时间"], _market_rows(market_snapshot)),
            f'{_text(market_snapshot.get("provider"), "价格源未知")}；用于看新闻是否已被价格确认。',
        ),
        _section(
            "提醒与记忆",
            _watchlist_rows(watchlist, title_translations),
            f'触发 {watchlist.get("triggered_count", 0)} · 新增 {watchlist.get("new_count", 0)} · 有效 {watchlist.get("active_count", 0)}',
        ),
        _section("数据质量", _coverage_body(payload), "看覆盖、时效和过滤情况，避免把缺数据误当判断。"),
        _section("报告入口", _path_links(output_paths, dashboard)),
    ]
    sections.extend(_portfolio_sections(portfolio, weekly))

    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>每日投资雷达</title>
  <style>{_CSS}</style>
</head>
<body>
  <div class="wrap">
    <header class="topbar">
      <div>
        <h1>每日投资雷达</h1>
        <div class="subtitle">生成时间：{escape(_text(generated))} · 模式：{escape(_text(payload.get("mode"), "未知"))} · 不是交易终端，动手前仍需复核价格、流动性和仓位纪律。</div>
      </div>
      {top_actions}
    </header>
    {lead}
    {_metric_cards(payload)}
    <main class="grid">{''.join(sections)}</main>
    <div class="footer">公开 RSS/API/官方网页抓取有覆盖边界；重大交易前请二次确认官方源、实时行情和个人组合约束。</div>
  </div>
</body>
</html>
"""
    return html
