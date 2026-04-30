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


def _fmt_pct_plain(value: Any) -> str:
    try:
        if value is None:
            return "未知"
        return f"{float(value):.2f}%"
    except (TypeError, ValueError):
        return "未知"


def _objective_range_text(values: Any) -> str:
    if not isinstance(values, (list, tuple)) or not values:
        return "未设置"
    items = list(values)
    low = items[0]
    high = items[1] if len(items) > 1 else items[0]
    if _fmt_pct_plain(low) == _fmt_pct_plain(high):
        return _fmt_pct_plain(low)
    return f"{_fmt_pct_plain(low)}-{_fmt_pct_plain(high)}"


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


def _section(title: str, body: str, subtitle: str = "", class_name: str = "", section_id: str = "") -> str:
    subtitle_html = f'<div class="section-subtitle">{escape(subtitle)}</div>' if subtitle else ""
    class_attr = f"panel {class_name}".strip()
    id_attr = f' id="{escape(section_id)}"' if section_id else ""
    return f'<section{id_attr} class="{escape(class_attr)}"><h2>{escape(title)}</h2>{subtitle_html}{body}</section>'


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
        original_summary = _shorten(representative.get("summary") or representative.get("content") or cluster.get("theme"), 180)
        summary_zh = _shorten(translation.get("summary_zh") or translation.get("why_it_matters_zh"), 180)
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


def _market_signal_strip(market_snapshot: dict[str, Any]) -> str:
    items = market_snapshot.get("items") or []
    if not items:
        return ""
    chips = []
    for item in items[:6]:
        trend = _trend_class(item.get("change_pct"))
        pct = _fmt_pct(item.get("change_pct"))
        chips.append(
            f'<div class="signal-chip {escape(trend)}">'
            f'<span class="signal-name">{escape(_text(item.get("name") or item.get("symbol")))}</span>'
            f'<span class="signal-value">{escape(pct)}</span>'
            "</div>"
        )
    return '<div class="signal-strip" aria-label="市场信号">' + "".join(chips) + "</div>"


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
        objective = portfolio.get("annual_objective") or {}
        base_target = _objective_range_text(objective.get("base_return_pct_range"))
        stretch_target = _objective_range_text(objective.get("stretch_return_pct_range"))
        drawdown = _fmt_pct_plain(objective.get("max_annual_drawdown_pct"))
        return [
            ("年度目标", f"{base_target} / {stretch_target}", f"基础目标在前，冲刺目标只在行情和纪律同时配合时参考；回撤红线 {drawdown}。"),
            ("投资模式", "中长期纪律", "默认不因单日新闻交易；公开页只展示新闻、价格和风险状态。"),
            ("今日处理", "默认不动", "具体仓位纪律看飞书私密推送；没有触发就继续持有。"),
            ("何时动手", "只看触发", "回撤、仓位超线、折溢价/流动性异常或你主动回执后才复核。"),
            ("隐私保护", "不公开", "组合估值、AI 暴露、黄金仓位和历史缓存不发布到 Pages。"),
        ]
    if portfolio.get("enabled"):
        rows = []
        for raw in portfolio.get("action_slot_lines") or []:
            line = _strip_markdown(raw)
            if line:
                rows.append(("纪律提醒", _shorten(line, 92), "用于复核，不是每日买卖指令；仍需确认价格、流动性和仓位。"))
            if len(rows) >= 4:
                break
        if rows:
            return rows
        return [("今日处理", "默认不动", "组合配置已接入，但今天没有触发需要处理的纪律项。")]

    return [
        ("投资模式", "中长期纪律", "缺少线上持仓配置，不生成买卖判断。"),
        ("继续持有", "待组合接入", "需要知道持仓、成本、目标比例和纪律线。"),
        ("补仓/换仓", "先不自动给", "需要现金、候选池、风险预算和买入规则。"),
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
        "日报默认不催买卖；它只把新闻、价格和你的仓位纪律放到一起，"
        "出现触发项时提醒你复核，最终仍由你手动决定。"
    )
    body = '<div class="action-grid">' + "".join(cards) + f'</div><div class="muted-block">{escape(note)}</div>'
    return _section("中长期纪律", body, "默认不动；只有触发风险、回撤、仓位上限或你的操作回执时才需要处理。", "wide", "decision")


def _system_boundary_section(payload: dict[str, Any]) -> str:
    validation = payload.get("signal_validation") or {}
    watchlist = payload.get("watchlist") or {}
    signal_count = int(validation.get("signal_count") or 0)
    triggered_count = int(watchlist.get("triggered_count") or 0)
    items = [
        (
            "不能保证赚钱",
            "过滤 + 纪律",
            "它负责把新闻、价格、提醒和验证条件整理清楚；不承诺收益，也不把单日叙事直接变成交易。",
        ),
        (
            "持仓靠回执更新",
            "不自动猜测",
            "系统只认你在飞书回过的买入/卖出；没回执就按原仓位继续，避免把未发生的操作写进判断。",
        ),
        (
            "行业逻辑继续养",
            f"{signal_count} 条验算",
            "人工智能、黄金、半导体材料、能源电力、关键矿产等主线会继续记录样本，用命中率决定加权或降权。",
        ),
    ]
    cards = []
    for label, value, note in items:
        cards.append(
            '<div class="action-card boundary-card">'
            f'<div class="action-label">{escape(label)}</div>'
            f'<div class="action-value">{escape(value)}</div>'
            f'<div class="action-note">{escape(note)}</div>'
            "</div>"
        )
    note = (
        f"今天提醒触发 {triggered_count} 条。结论只给复核顺序：先确认价格和证据，再看仓位纪律，最后由你手动决定。"
    )
    body = '<div class="action-grid">' + "".join(cards) + f'</div><div class="muted-block">{escape(note)}</div>'
    return _section("系统边界", body, "这三条是使用前提：不稳赢、不猜持仓、不把行业故事直接当买卖。", "wide", "boundary")


def _strategic_lens_section(payload: dict[str, Any]) -> str:
    lens = payload.get("strategic_lens") or {}
    summary_lines = lens.get("summary_lines") or [
        "三问法：谁被卡、谁拿筹码、钱在让谁完成什么任务。",
        "没有价格、政策或订单确认时，只记录观察，不做动作。",
    ]
    framework_lines = lens.get("framework_lines") or []
    rows = lens.get("rows") or []

    summary_html = "".join(f"<li>{escape(_strip_markdown(line))}</li>" for line in summary_lines[:3])
    body = f'<div class="strategy-summary"><ul>{summary_html}</ul></div>'

    if rows:
        cards = []
        for row in rows[:5]:
            tags = (
                _pill(row.get("theme_label") or "资源约束", "tag")
                + _pill(f"可信 {row.get('credibility_label') or '未知'}", "neutral")
                + _pill(row.get("direction") or "中性", "neutral")
            )
            cards.append(
                '<article class="strategy-card">'
                f'<div class="strategy-card-head">{tags}</div>'
                f'<h3>{escape(_shorten(row.get("title"), 92))}</h3>'
                f'<div class="strategy-question">{escape(_text(row.get("question"), "先问约束在哪里"))}</div>'
                f'<p>{escape(_shorten(row.get("game_read"), 145))}</p>'
                f'<div class="strategy-check">{escape(_shorten(row.get("price_check"), 135))}</div>'
                f'<div class="strategy-note">{escape(_shorten(row.get("portfolio_note"), 135))}</div>'
                "</article>"
            )
        body += '<div class="strategy-grid">' + "".join(cards) + "</div>"
    else:
        body += _render_list(framework_lines, 5)

    disclaimer = lens.get("disclaimer")
    if disclaimer:
        body += f'<div class="muted-block">{escape(disclaimer)}</div>'
    return _section(
        "资源博弈视角",
        body,
        "把新闻拆成供给、技术、通道、结算和政策许可，先判断筹码变化，再看价格是否确认。",
        "wide",
        "strategy",
    )


def _prediction_lens_section(payload: dict[str, Any]) -> str:
    lens = payload.get("prediction_lens") or {}
    summary_lines = lens.get("summary_lines") or [
        "今天没有生成强发酵预警卡；继续按核心事件、资源博弈和纪律面板观察。",
        "如果只有单一叙事，没有政策、订单或价格确认，先不升级。",
    ]
    cards = lens.get("cards") or []
    framework_lines = lens.get("framework_lines") or []
    summary_html = "".join(f"<li>{escape(_strip_markdown(line))}</li>" for line in summary_lines[:3])
    body = f'<div class="prediction-summary"><ul>{summary_html}</ul></div>'

    if cards:
        card_html = []
        for card in cards[:5]:
            tags = (
                _pill(card.get("label") or "预警", "tag")
                + _pill(f"窗口 {card.get('window') or '待定'}", "neutral")
                + _pill(f"置信 {card.get('confidence') or '未知'}", "importance")
            )
            card_html.append(
                '<article class="prediction-card">'
                f'<div class="prediction-card-head">{tags}</div>'
                f'<h3>{escape(_shorten(card.get("prediction"), 100))}</h3>'
                f'<p>{escape(_shorten(card.get("why"), 150))}</p>'
                f'<div class="prediction-row"><b>验证</b><span>{escape(_shorten(card.get("verify"), 145))}</span></div>'
                f'<div class="prediction-row"><b>失效</b><span>{escape(_shorten(card.get("invalidate"), 145))}</span></div>'
                f'<div class="prediction-note">{escape(_shorten(card.get("discipline"), 135))}</div>'
                "</article>"
            )
        body += '<div class="prediction-grid">' + "".join(card_html) + "</div>"
    else:
        body += _render_list(framework_lines, 5)

    disclaimer = lens.get("disclaimer")
    if disclaimer:
        body += f'<div class="muted-block">{escape(disclaimer)}</div>'
    return _section(
        "发酵预警卡片",
        body,
        "提前找可能发酵的主线、验证条件和失效条件；不是买卖信号。",
        "wide",
        "predictions",
    )


def _logic_playbook_section(payload: dict[str, Any]) -> str:
    playbook = payload.get("logic_playbook") or {}
    summary_lines = playbook.get("summary_lines") or [
        "系统每天先用固定框架看新闻，再决定是否生成预警。",
        "没有验证条件的判断，只进入观察，不进入操作。",
    ]
    cards = playbook.get("cards") or []
    summary_html = "".join(f"<li>{escape(_strip_markdown(line))}</li>" for line in summary_lines[:3])
    body = f'<div class="playbook-summary"><ul>{summary_html}</ul></div>'

    if cards:
        items = []
        for card in cards[:9]:
            items.append(
                '<article class="playbook-card">'
                f'<h3>{escape(_text(card.get("name"), "框架"))}</h3>'
                f'<div class="playbook-question">{escape(_shorten(card.get("question"), 70))}</div>'
                f'<p>{escape(_shorten(card.get("use_when"), 120))}</p>'
                f'<div class="playbook-confirm">{escape(_shorten(card.get("confirm"), 125))}</div>'
                f'<div class="playbook-avoid">{escape(_shorten(card.get("avoid"), 115))}</div>'
                "</article>"
            )
        body += '<div class="playbook-grid">' + "".join(items) + "</div>"
    else:
        body += _empty("暂无思维框架")

    disclaimer = playbook.get("disclaimer")
    if disclaimer:
        body += f'<div class="muted-block">{escape(disclaimer)}</div>'
    return _section(
        "思维框架库",
        body,
        "这些是系统看新闻的固定问题，用来把小作文变成可验证的研究清单。",
        "wide",
        "playbook",
    )


def _receipt_status(payload: dict[str, Any]) -> tuple[str, str, str, str]:
    status = payload.get("feishu_receipts") or {}
    if not status or status.get("status") == "not_run":
        return ("操作回执", "本次未读取", "日报运行前会读取飞书群里的买入/卖出消息。", "neutral")
    if status.get("skipped"):
        return ("操作回执", "未配置", _shorten(status.get("reason") or "未配置飞书群读取。", 120), "warn")
    if not status.get("ok", False):
        return ("操作回执", "读取失败", _shorten(status.get("error") or "飞书消息读取失败。", 120), "bad")

    appended = int(status.get("appended_count") or 0)
    errors = int(status.get("error_count") or 0)
    messages = int(status.get("message_count") or 0)
    duplicates = int(status.get("duplicate_count") or 0)
    if appended:
        return ("操作回执", f"新增 {appended} 条", f"扫描 {messages} 条消息，重复 {duplicates} 条，解析失败 {errors} 条。", "good")
    return ("操作回执", "没有新操作", f"扫描 {messages} 条消息，重复 {duplicates} 条，解析失败 {errors} 条。", "neutral")


def _receipt_status_body(payload: dict[str, Any]) -> str:
    label, value, note, tone = _receipt_status(payload)
    status = payload.get("feishu_receipts") or {}
    rows = [
        ["状态", escape(value)],
        ["扫描消息", escape(_text(status.get("message_count"), "0"))],
        ["新增入账", escape(_text(status.get("appended_count"), "0"))],
        ["重复跳过", escape(_text(status.get("duplicate_count"), "0"))],
        ["解析失败", escape(_text(status.get("error_count"), "0"))],
    ]
    body = (
        f'<div class="receipt-banner {escape(tone)}">'
        f'<div class="receipt-title">{escape(label)}：{escape(value)}</div>'
        f'<div class="receipt-note">{escape(note)}</div>'
        "</div>"
        + _render_table(["项目", "结果"], rows)
    )
    if int(status.get("error_count") or 0):
        body += '<div class="muted-block">有解析失败的回执时，请到 GitHub Actions 运行日志里看原因；公开页面只展示统计，不展示飞书原文。</div>'
    return body


def _decision_strip(payload: dict[str, Any]) -> str:
    action_items = _action_guidance_items(payload)
    action_label, action_value, action_note = action_items[0] if action_items else ("当前动作", "观察", "先看价格确认。")
    receipt_label, receipt_value, receipt_note, receipt_tone = _receipt_status(payload)
    watchlist = payload.get("watchlist") or {}
    data_quality = payload.get("data_quality") or {}
    clusters = payload.get("clusters") or []
    translations = ((payload.get("translations") or {}).get("items") or {})
    top_event = _cluster_display_title(clusters[0], translations) if clusters else "暂无核心事件"
    quality_value = data_quality.get("freshness_status") or "未知"
    quality_note = f"最新新闻约 {_fmt_age(data_quality.get('latest_article_age_hours'))}；提醒触发 {watchlist.get('triggered_count', 0)} 条。"
    items = [
        ("今日纪律", action_value, action_note, "primary"),
        ("最先看", _shorten(top_event, 72), "先确认新闻是否已被油价、黄金、美元、VIX 等价格吸收。", "risk"),
        (receipt_label, receipt_value, receipt_note, receipt_tone),
        ("数据状态", quality_value, quality_note, "neutral"),
    ]
    cards = []
    for label, value, note, tone in items:
        cards.append(
            f'<div class="decision-card {escape(tone)}">'
            f'<div class="decision-label">{escape(label)}</div>'
            f'<div class="decision-value">{escape(_shorten(value, 88))}</div>'
            f'<div class="decision-note">{escape(_shorten(note, 120))}</div>'
            "</div>"
        )
    return '<section class="decision-strip">' + "".join(cards) + "</section>"


def _status_bar(payload: dict[str, Any], generated: Any) -> str:
    data_quality = payload.get("data_quality") or {}
    watchlist = payload.get("watchlist") or {}
    _, receipt_value, _, receipt_tone = _receipt_status(payload)
    chips = [
        ("生成", _compact_time(generated)),
        ("模式", _text(payload.get("mode"), "未知")),
        ("数据", _text(data_quality.get("freshness_status"), "未知")),
        ("提醒", f"{watchlist.get('triggered_count', 0)} 触发"),
        ("回执", receipt_value),
    ]
    items = []
    for label, value in chips:
        tone = receipt_tone if label == "回执" else ""
        tone_class = f" {escape(tone)}" if tone else ""
        items.append(
            f'<span class="status-chip{tone_class}"><span>{escape(label)}</span><b>{escape(_shorten(value, 42))}</b></span>'
        )
    return '<div class="status-bar">' + "".join(items) + "</div>"


def _hero_panel(payload: dict[str, Any], global_overview: str, market_snapshot: dict[str, Any]) -> str:
    data_quality = payload.get("data_quality") or {}
    market_coverage = data_quality.get("market_coverage") or market_snapshot.get("coverage") or {}
    _, receipt_value, receipt_note, receipt_tone = _receipt_status(payload)
    stats = [
        ("核心事件", f"{payload.get('selected_count', 0)} 个", f"从 {payload.get('articles_count', 0)} 条新闻筛出"),
        ("最新时效", _fmt_age(data_quality.get("latest_article_age_hours")), _text(data_quality.get("freshness_status"), "未知")),
        ("市场快照", f'{market_coverage.get("returned_assets", 0)}/{market_coverage.get("configured_assets", 0)}', "价格确认"),
        ("操作回执", receipt_value, _shorten(receipt_note, 56)),
    ]
    stat_html = []
    for label, value, note in stats:
        tone = receipt_tone if label == "操作回执" else ""
        tone_class = f" {escape(tone)}" if tone else ""
        stat_html.append(
            f'<div class="hero-stat{tone_class}">'
            f'<span>{escape(label)}</span>'
            f'<b>{escape(value)}</b>'
            f'<small>{escape(note)}</small>'
            "</div>"
        )
    return (
        '<section class="hero-panel">'
        '<div class="hero-copy">'
        '<div class="eyebrow">今日简报</div>'
        "<h2>先看风险，再决定是否需要处理</h2>"
        f'<p>{escape(_shorten(global_overview, 230))}</p>'
        f'{_tag_distribution(payload.get("tag_distribution"))}'
        f'{_market_signal_strip(market_snapshot)}'
        "</div>"
        '<div class="hero-stats">'
        + "".join(stat_html)
        + '<div class="hero-note">默认不操作；有交易才在飞书群发“买入/卖出”，没操作不用回复。</div>'
        "</div>"
        "</section>"
    )


def _quick_nav(archive_url: Any = "") -> str:
    links = [
        ("决策", "#decision"),
        ("边界", "#boundary"),
        ("事件", "#events"),
        ("博弈", "#strategy"),
        ("预警", "#predictions"),
        ("验算", "#validation"),
        ("框架", "#playbook"),
        ("市场", "#market"),
        ("提醒", "#watchlist"),
        ("回执", "#receipts"),
        ("质量", "#quality"),
    ]
    if _safe_url(archive_url):
        links.append(("归档", archive_url))
    return '<nav class="quick-nav" aria-label="快速导航">' + "".join(
        f'<a href="{escape(href)}">{escape(label)}</a>' for label, href in links
    ) + "</nav>"


def _public_sibling(output_paths: dict[str, Any], filename: str) -> str:
    for key in ("report_json_url", "report_md_url", "dashboard_html_url"):
        url = _text(output_paths.get(key), "")
        if url.startswith(("http://", "https://")) and "/" in url:
            return url.rsplit("/", 1)[0].rstrip("/") + "/" + filename
    return ""


def _path_links(output_paths: dict[str, Any], dashboard: dict[str, Any]) -> str:
    pairs = [
        ("最新网页", output_paths.get("dashboard_html_url") or dashboard.get("public_url"), "页面根目录"),
        ("历史归档", output_paths.get("archive_index_url") or dashboard.get("archive_index_url"), "archive.html"),
        ("本次归档", output_paths.get("archive_url") or dashboard.get("archive_url"), "本次运行快照"),
        ("完整日报 Markdown", output_paths.get("report_md_url") or output_paths.get("report_md_uri"), output_paths.get("report_md_path")),
        ("结构化 JSON", output_paths.get("report_json_url") or output_paths.get("report_json_uri"), output_paths.get("report_json_path")),
        ("提醒状态 JSON", _public_sibling(output_paths, "watchlist.json"), "watchlist.json"),
        ("信号验算 JSON", _public_sibling(output_paths, "signal_validation.json"), "signal_validation.json"),
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
    state_label = {"可买": "可复核", "减仓": "减仓复核"}
    for row in rows or []:
        result.append(
            [
                escape(f"{_text(row.get('name'), '')} ({_text(row.get('code'), '')})"),
                escape(state_label.get(_text(row.get("state"), "观察"), _text(row.get("state"), "观察"))),
                escape(_text(row.get("amount_band"))),
                escape(_fmt_pct(row.get("day_change_pct"))),
                escape(_text(row.get("role"))),
                escape(_shorten(row.get("reason"), 160)),
            ]
        )
    return result


def _industry_radar_rows(radar: dict[str, Any] | None) -> list[list[str]]:
    result = []
    for row in (radar or {}).get("rows") or []:
        instruments = "、".join(_text(item) for item in row.get("instruments") or [])
        action = _text(row.get("action"), "")
        if instruments:
            action = f"{action} 参考：{instruments}"
        result.append(
            [
                escape(_text(row.get("layer_label"))),
                escape(_text(row.get("name"))),
                escape(_text(row.get("status"))),
                escape(_shorten(row.get("watch"), 120)),
                escape(_shorten(row.get("verify"), 120)),
                escape(_shorten(action, 130)),
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


def _validation_bucket_text(bucket: dict[str, Any] | None) -> str:
    data = bucket or {}
    samples = int(data.get("samples") or 0)
    if samples <= 0:
        return "样本不足"
    return f"{samples}次 / 胜率 {_fmt_pct_plain(data.get('win_rate_pct'))} / 均值 {_fmt_pct(data.get('avg_return_pct'))}"


def _validation_rows(validation: dict[str, Any] | None) -> list[list[str]]:
    result = []
    for row in (validation or {}).get("rows") or []:
        result.append(
            [
                escape(_text(row.get("theme"))),
                escape(_text(row.get("signals"), "0")),
                escape(_validation_bucket_text(row.get("t1"))),
                escape(_validation_bucket_text(row.get("t5"))),
                escape(_validation_bucket_text(row.get("t20"))),
                escape(_text(row.get("verdict"), "继续积累")),
                escape(_text(row.get("adjustment"), "不调整")),
            ]
        )
    return result


def _signal_validation_section(payload: dict[str, Any]) -> str:
    validation = payload.get("signal_validation") or {}
    lines = validation.get("lines") or ["- 事后验算会在跑满几个交易日后逐步形成样本。"]
    body = (
        '<div class="validation-lead">'
        + "".join(f"<div>{escape(_strip_markdown(line))}</div>" for line in lines[:3])
        + "</div>"
        + _render_table(
            ["主题", "信号数", "T+1", "T+5", "T+20", "结论", "权重"],
            _validation_rows(validation),
        )
    )
    note = validation.get("note") or "只用于校准系统权重，不代表未来收益，也不会直接触发交易。"
    body += f'<div class="muted-block">{escape(note)}</div>'
    return _section("事后验算", body, "每天记录信号，后续自动回看表现；命中率用于校准，不用于保证收益。", "wide", "validation")


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
                '<div class="muted-block">组合配置已接入本次运行，但公开网页不会展示持仓、成本、交易流水、组合估值、AI 暴露、黄金仓位和历史缓存。具体纪律提示请看飞书推送。</div>',
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
            _section("纪律提醒", _render_list(portfolio.get("action_slot_lines"), 5), "只展示需要复核的事项，不替代交易指令。"),
            _section("A 股阶段", _render_list(portfolio.get("local_market_lines"), 8)),
            _section(
                "行业雷达",
                _render_table(
                    ["层级", "行业", "状态", "看什么", "验证条件", "动作"],
                    _industry_radar_rows(portfolio.get("industry_radar")),
                ),
                "雷达决定每天看什么；可买池不自动扩张，也不直接给买卖指令。",
                "wide",
            ),
            _section(
                "固定候选池",
                _render_table(
                    ["标的", "状态", "金额档位", "当日变化", "角色", "原因"],
                    _fixed_pool_rows(portfolio.get("fixed_buy_pool_rows")),
                ),
                class_name="wide",
            ),
            _section(
                "候选池回填",
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
    strategic_lens = payload.get("strategic_lens") or {}
    if strategic_lens.get("enabled"):
        cards.append(
            _metric(
                "资源博弈",
                f'{strategic_lens.get("match_count", 0)} 条',
                "供给、通道、技术、结算筹码",
            )
        )
    prediction_lens = payload.get("prediction_lens") or {}
    if prediction_lens.get("enabled"):
        cards.append(
            _metric(
                "发酵预警",
                f'{prediction_lens.get("card_count", 0)} 张',
                "主线、窗口、验证和失效条件",
            )
        )
    logic_playbook = payload.get("logic_playbook") or {}
    if logic_playbook.get("enabled"):
        cards.append(_metric("思维框架", f'{len(logic_playbook.get("cards") or [])} 条', "每天固定检查"))
    validation = payload.get("signal_validation") or {}
    if validation.get("enabled"):
        cards.append(
            _metric(
                "事后验算",
                f'{validation.get("signal_count", 0)} 条',
                "T+1/T+5/T+20 自动复盘",
                "accent",
            )
        )
    _, receipt_value, receipt_note, receipt_tone = _receipt_status(payload)
    cards.append(_metric("操作回执", receipt_value, receipt_note, "accent" if receipt_tone == "good" else ""))
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
html {
  scroll-behavior: smooth;
  scroll-padding-top: 76px;
}
body {
  margin: 0;
  font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans SC", system-ui, sans-serif;
  background:
    radial-gradient(circle at top left, rgba(31, 111, 235, 0.08), transparent 32rem),
    linear-gradient(180deg, #f8fafc 0%, var(--bg) 18rem);
  color: var(--text);
  line-height: 1.55;
}
.wrap {
  max-width: 1180px;
  margin: 0 auto;
  padding: 24px 24px 36px;
}
.topbar {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 20px;
  align-items: center;
  margin-bottom: 10px;
}
h1 {
  margin: 0;
  font-size: 30px;
  line-height: 1.2;
  letter-spacing: 0;
}
.subtitle {
  margin-top: 6px;
  color: var(--muted);
  font-size: 14px;
}
.eyebrow {
  color: var(--blue);
  font-size: 12px;
  font-weight: 760;
  margin-bottom: 5px;
  text-transform: uppercase;
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
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 650;
}
.status-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 10px 0 4px;
}
.status-chip {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.82);
  border-radius: 999px;
  padding: 5px 10px;
  font-size: 12px;
}
.status-chip span {
  color: var(--muted);
}
.status-chip b {
  color: #263244;
  font-weight: 720;
}
.status-chip.good {
  border-color: #bbf7d0;
  background: #f0fdf4;
}
.status-chip.bad {
  border-color: #fecaca;
  background: #fff5f5;
}
.status-chip.warn {
  border-color: #fde68a;
  background: #fffbeb;
}
.quick-nav {
  position: sticky;
  top: 0;
  z-index: 4;
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding: 8px 0 12px;
  margin: -4px 0 4px;
  background: linear-gradient(180deg, var(--bg) 72%, rgba(244, 246, 248, 0));
  scrollbar-width: none;
}
.quick-nav::-webkit-scrollbar {
  display: none;
}
.quick-nav a {
  flex: 0 0 auto;
  border: 1px solid var(--line);
  background: #fff;
  color: #334155;
  border-radius: 999px;
  padding: 6px 11px;
  font-size: 13px;
  font-weight: 640;
}
.quick-nav a:hover {
  color: var(--blue);
  text-decoration: none;
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
.hero-panel {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(250px, .55fr);
  gap: 18px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 20px;
  margin: 12px 0 14px;
  box-shadow: 0 14px 38px rgba(17, 24, 39, 0.07);
}
.hero-copy h2 {
  margin: 0;
  font-size: 24px;
  line-height: 1.22;
}
.hero-copy p {
  margin: 12px 0 0;
  color: #263244;
  font-size: 16px;
  line-height: 1.65;
  max-width: 780px;
}
.hero-stats {
  display: grid;
  gap: 10px;
}
.hero-stat {
  border: 1px solid var(--line-soft);
  border-radius: 10px;
  padding: 10px 12px;
  background: #f8fafc;
}
.hero-stat.good {
  background: #f0fdf4;
  border-color: #bbf7d0;
}
.hero-stat.bad {
  background: #fff5f5;
  border-color: #fecaca;
}
.hero-stat.warn {
  background: #fffbeb;
  border-color: #fde68a;
}
.hero-stat span,
.hero-stat small {
  display: block;
  color: var(--muted);
  font-size: 12px;
}
.hero-stat b {
  display: block;
  margin: 2px 0 1px;
  font-size: 19px;
  line-height: 1.25;
  overflow-wrap: anywhere;
}
.hero-note {
  color: var(--muted);
  font-size: 12px;
  padding: 2px 2px 0;
}
.tag-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  margin-top: 12px;
}
.signal-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(118px, 1fr));
  gap: 8px;
  margin-top: 13px;
}
.signal-chip {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  border: 1px solid var(--line-soft);
  background: #f8fafc;
  border-radius: 8px;
  padding: 7px 9px;
  min-width: 0;
}
.signal-name {
  color: #334155;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.signal-value {
  font-size: 12px;
  font-weight: 760;
  white-space: nowrap;
}
.signal-chip.up .signal-value {
  color: var(--green);
}
.signal-chip.down .signal-value {
  color: var(--red);
}
.signal-chip.flat .signal-value {
  color: var(--muted);
}
.decision-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin: 14px 0 18px;
}
.decision-card {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 13px 14px;
  min-height: 112px;
  border-top: 3px solid #94a3b8;
}
.decision-card.primary {
  border-top-color: var(--blue);
}
.decision-card.risk {
  border-top-color: var(--amber);
}
.decision-card.good {
  border-top-color: var(--green);
}
.decision-card.bad {
  border-top-color: var(--red);
}
.decision-card.warn {
  border-top-color: var(--amber);
}
.decision-label {
  color: var(--muted);
  font-size: 12px;
  margin-bottom: 6px;
}
.decision-value {
  font-size: 18px;
  font-weight: 780;
  line-height: 1.3;
  overflow-wrap: anywhere;
}
.decision-note {
  color: var(--muted);
  font-size: 12px;
  margin-top: 8px;
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
.boundary-card {
  background: #fff;
  border-top: 3px solid #94a3b8;
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
.strategy-summary {
  border: 1px solid #cfe2ff;
  background: #f6faff;
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 12px;
}
.strategy-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(280px, 100%), 1fr));
  gap: 10px;
}
.strategy-card {
  border: 1px solid var(--line-soft);
  border-radius: 8px;
  background: #fff;
  padding: 13px;
  min-height: 210px;
}
.strategy-card-head {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}
.strategy-card h3 {
  margin: 0 0 8px;
  font-size: 15px;
  line-height: 1.38;
}
.strategy-question {
  color: var(--blue);
  font-weight: 720;
  font-size: 13px;
  margin-bottom: 7px;
}
.strategy-card p,
.strategy-check,
.strategy-note {
  margin: 0;
  color: #27364b;
  font-size: 13px;
  line-height: 1.55;
}
.strategy-check {
  margin-top: 9px;
  color: #475569;
}
.strategy-note {
  margin-top: 8px;
  color: var(--muted);
  padding-top: 8px;
  border-top: 1px solid var(--line-soft);
}
.prediction-summary {
  border: 1px solid #d6eadf;
  background: #f4fbf7;
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 12px;
}
.prediction-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(290px, 100%), 1fr));
  gap: 10px;
}
.prediction-card {
  border: 1px solid var(--line-soft);
  border-radius: 8px;
  background: #fff;
  padding: 13px;
  min-height: 245px;
}
.prediction-card-head {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}
.prediction-card h3 {
  margin: 0 0 9px;
  font-size: 15px;
  line-height: 1.38;
}
.prediction-card p {
  margin: 0 0 10px;
  color: #27364b;
  font-size: 13px;
  line-height: 1.55;
}
.prediction-row {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  gap: 8px;
  padding: 7px 0;
  border-top: 1px solid var(--line-soft);
  font-size: 13px;
}
.prediction-row b {
  color: #334155;
}
.prediction-row span,
.prediction-note {
  color: var(--muted);
}
.prediction-note {
  border-top: 1px solid var(--line-soft);
  padding-top: 8px;
  margin-top: 2px;
  font-size: 13px;
  line-height: 1.5;
}
.validation-lead {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(260px, 100%), 1fr));
  gap: 10px;
  margin-bottom: 12px;
}
.validation-lead div {
  border: 1px solid #cfe2ff;
  background: #f6faff;
  border-radius: 8px;
  padding: 10px 12px;
  color: #263244;
  font-size: 13px;
  line-height: 1.55;
}
.playbook-summary {
  border: 1px solid #e7d7ff;
  background: #fbf7ff;
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 12px;
}
.playbook-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(245px, 100%), 1fr));
  gap: 10px;
}
.playbook-card {
  border: 1px solid var(--line-soft);
  border-radius: 8px;
  background: #fff;
  padding: 12px;
  min-height: 210px;
}
.playbook-card h3 {
  margin: 0 0 7px;
  font-size: 15px;
}
.playbook-question {
  color: var(--blue);
  font-size: 13px;
  font-weight: 720;
  line-height: 1.45;
  margin-bottom: 8px;
}
.playbook-card p,
.playbook-confirm,
.playbook-avoid {
  color: #27364b;
  font-size: 13px;
  line-height: 1.5;
  margin: 0;
}
.playbook-confirm {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--line-soft);
}
.playbook-avoid {
  margin-top: 7px;
  color: var(--muted);
}
.receipt-banner {
  border: 1px solid var(--line);
  border-left: 4px solid #94a3b8;
  background: #f8fafc;
  border-radius: 8px;
  padding: 11px 12px;
  margin-bottom: 12px;
}
.receipt-banner.good {
  border-left-color: var(--green);
  background: #f0fdf4;
}
.receipt-banner.bad {
  border-left-color: var(--red);
  background: #fff5f5;
}
.receipt-banner.warn {
  border-left-color: var(--amber);
  background: #fffbeb;
}
.receipt-title {
  font-weight: 760;
}
.receipt-note {
  color: var(--muted);
  font-size: 12px;
  margin-top: 4px;
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
  border-radius: 10px;
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
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
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
  .quick-nav {
    margin-left: -14px;
    margin-right: -14px;
    padding-left: 14px;
    padding-right: 14px;
  }
  .hero-panel {
    grid-template-columns: 1fr;
    padding: 16px;
  }
  .decision-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .decision-card {
    min-height: auto;
  }
  .metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .grid {
    grid-template-columns: 1fr;
  }
  h1 {
    font-size: 25px;
  }
}
@media (max-width: 520px) {
  .wrap {
    padding-top: 16px;
  }
  .subtitle {
    font-size: 12px;
  }
  .lead {
    padding: 13px;
  }
  .lead-text {
    font-size: 14px;
  }
  .hero-copy h2 {
    font-size: 21px;
  }
  .hero-copy p {
    font-size: 14px;
  }
  .status-bar {
    flex-wrap: nowrap;
    overflow-x: auto;
    padding-bottom: 2px;
    scrollbar-width: none;
  }
  .status-bar::-webkit-scrollbar {
    display: none;
  }
  .status-chip {
    flex: 0 0 auto;
  }
  .decision-strip {
    grid-template-columns: 1fr;
  }
  .metrics {
    grid-template-columns: 1fr;
  }
  .metric-value {
    font-size: 20px;
  }
  .event-row {
    grid-template-columns: 28px minmax(0, 1fr);
    gap: 9px;
  }
  .panel {
    padding: 13px;
  }
  .event-summary {
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .event-tags {
    gap: 5px;
  }
  .pill {
    font-size: 11px;
    min-height: 20px;
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

    hero = _hero_panel(payload, global_overview, market_snapshot)

    actions = []
    if report_url:
        actions.append(_link("打开完整日报", report_url, "button-link"))
    if archive_url:
        actions.append(_link("历史归档", archive_url, "button-link"))
    top_actions = '<div class="top-actions">' + "".join(actions) + "</div>" if actions else ""

    sections = [
        _system_boundary_section(payload),
        _section("今日核心事件", _cluster_rows(payload.get("clusters"), translations), "按重要性、可信度和来源交叉验证排序；外文标题会自动加中文速译。", "wide", "events"),
        _strategic_lens_section(payload),
        _prediction_lens_section(payload),
        _signal_validation_section(payload),
        _logic_playbook_section(payload),
        _action_guidance_section(payload),
        _section(
            "市场快照",
            _render_table(["资产", "价格", "涨跌", "状态", "行情时间"], _market_rows(market_snapshot)),
            f'{_text(market_snapshot.get("provider"), "价格源未知")}；用于看新闻是否已被价格确认。',
            section_id="market",
        ),
        _section(
            "提醒与记忆",
            _watchlist_rows(watchlist, title_translations),
            f'触发 {watchlist.get("triggered_count", 0)} · 新增 {watchlist.get("new_count", 0)} · 有效 {watchlist.get("active_count", 0)}',
            section_id="watchlist",
        ),
        _section("操作回执", _receipt_status_body(payload), "飞书群里有交易才填；没操作不用回复，系统按原仓位继续。", section_id="receipts"),
        _section("数据质量", _coverage_body(payload), "看覆盖、时效和过滤情况，避免把缺数据误当判断。", section_id="quality"),
        _section("报告入口", _path_links(output_paths, dashboard), section_id="links"),
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
        <div class="eyebrow">投资雷达</div>
        <h1>每日投资雷达</h1>
        <div class="subtitle">公开页看结论和证据；具体组合动作走飞书私密推送；本页不是交易指令，不保证收益。</div>
      </div>
      {top_actions}
    </header>
    {_status_bar(payload, generated)}
    {_quick_nav(archive_url)}
    {hero}
    {_decision_strip(payload)}
    <main class="grid">{''.join(sections)}</main>
    <div class="footer">本页不是交易指令，不保证收益；公开 RSS/API/官方网页抓取有覆盖边界，重大交易前请二次确认官方源、实时行情和个人组合约束。</div>
  </div>
</body>
</html>
"""
    return html
