from __future__ import annotations

from html import escape
from typing import Any


def _fmt_pct(value: Any) -> str:
    try:
        if value is None:
            return "未知"
        return f"{float(value):+.2f}%"
    except (TypeError, ValueError):
        return "未知"


def _fmt_cny(value: Any) -> str:
    try:
        if value is None:
            return "未知"
        return f"¥{float(value):,.2f}"
    except (TypeError, ValueError):
        return "未知"


def _clean_line(line: str) -> str:
    text = str(line or "").strip()
    if not text:
        return ""
    if text.startswith("- "):
        return text[2:].strip()
    if text.startswith("> "):
        return text[2:].strip()
    return text


def _render_list(lines: list[str] | None, limit: int | None = None) -> str:
    source = lines or []
    if limit is not None:
        source = source[:limit]
    items = []
    for raw in source:
        line = _clean_line(raw)
        if not line or line.startswith("|"):
            continue
        items.append(f"<li>{escape(line)}</li>")
    if not items:
        return '<div class="empty">暂无数据</div>'
    return "<ul>" + "".join(items) + "</ul>"


def _render_table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return '<div class="empty">暂无数据</div>'
    thead = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body_rows = []
    for row in rows:
        body_rows.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>")
    return (
        '<div class="table-wrap"><table>'
        f"<thead><tr>{thead}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        '</table></div>'
    )


def _fixed_pool_rows(rows: list[dict[str, Any]] | None) -> list[list[str]]:
    result = []
    for row in rows or []:
        result.append([
            escape(f"{row.get('name', '')} ({row.get('code', '')})"),
            escape(str(row.get('state') or '观察')),
            escape(str(row.get('amount_band') or '-')),
            escape(_fmt_pct(row.get('day_change_pct'))),
            escape(str(row.get('role') or '-')),
            escape(str(row.get('reason') or '-')),
        ])
    return result


def _theme_label(value: str | None) -> str:
    mapping = {
        'broad_core': '宽基底仓',
        'growth_core': '成长底仓',
        'ai_attack': 'AI进攻',
        'gold_insurance': '黄金保险',
        'dividend_lowvol': '红利低波',
        'power': '电力',
        'semiconductor': '半导体',
        'ai': 'AI/科技',
        'energy': '能源/地缘',
        'gold': '黄金/避险',
        'china_macro': '中国宏观',
        'new_energy': '新能源',
    }
    return mapping.get(str(value or ''), str(value or '-'))



def _backfill_rows(rows: list[dict[str, Any]] | None) -> list[list[str]]:
    result = []
    for row in rows or []:
        latest_close = row.get('latest_close')
        latest_text = '未知' if latest_close is None else f"{float(latest_close):.4f}"
        result.append([
            escape(f"{row.get('name', '')} ({row.get('code', '')})"),
            escape(_theme_label(row.get('theme_key'))),
            escape(str(row.get('days') or 0)),
            escape(_fmt_pct(row.get('change_20d_pct'))),
            escape(_fmt_pct(row.get('change_60d_pct'))),
            escape(_fmt_pct(row.get('change_120d_pct'))),
            escape(_fmt_pct(row.get('change_250d_pct'))),
            escape(latest_text),
        ])
    return result

def _win_leader_text(leader: dict[str, Any] | None) -> str:
    if not leader:
        return '-'
    return (
        f"{leader.get('name', '')} ({leader.get('code', '')}) / "
        f"胜率 {leader.get('win_rate_pct', 0):.0f}% / 均值 {leader.get('avg_return_pct', 0):+.2f}% / 样本 {leader.get('samples', 0)}"
    )



def _win_rows(rows: list[dict[str, Any]] | None) -> list[list[str]]:
    result = []
    for row in rows or []:
        sample_days = row.get('sample_days') or {}
        sample_text = '/'.join(str(sample_days.get(f'd{window}', 0)) for window in (60, 120, 250))
        selected_window = row.get('selected_window')
        selected_window_text = f"近{selected_window}天" if selected_window else '继续积累'
        leaders = row.get('selected_leaders') or {}
        result.append([
            escape(_theme_label(row.get('theme_key'))),
            escape(sample_text),
            escape(selected_window_text),
            escape(_win_leader_text(leaders.get('t1'))),
            escape(_win_leader_text(leaders.get('t3'))),
            escape(_win_leader_text(leaders.get('t5'))),
        ])
    return result

def _event_route_rows(rows: list[dict[str, Any]] | None) -> list[list[str]]:
    result = []
    for row in rows or []:
        result.append([
            escape(str(row.get('priority') or '观察')),
            escape(str(row.get('title') or '-')),
            escape(str(row.get('chain') or '-')),
            escape(str(row.get('buy_text') or '-')),
            escape(str(row.get('action_text') or '-')),
        ])
    return result


def _render_href_or_text(value: str) -> str:
    text = str(value or "")
    escaped = escape(text)
    if text.startswith(("http://", "https://", "file://")):
        return f'<a href="{escaped}">{escaped}</a>'
    return escaped


def _path_links(output_paths: dict[str, Any]) -> str:
    pairs = [
        ('全球日报', output_paths.get('report_md_uri'), output_paths.get('report_md_path')),
        ('组合日报', output_paths.get('portfolio_md_uri'), output_paths.get('portfolio_md_path')),
        ('周日复盘', output_paths.get('weekly_md_uri'), output_paths.get('weekly_md_path')),
    ]
    pairs[0] = (
        pairs[0][0],
        output_paths.get('report_md_url') or pairs[0][1],
        output_paths.get('report_md_url') or pairs[0][2],
    )
    pairs[1] = (
        pairs[1][0],
        output_paths.get('portfolio_md_url') or pairs[1][1],
        output_paths.get('portfolio_md_url') or pairs[1][2],
    )
    pairs[2] = (
        pairs[2][0],
        output_paths.get('weekly_md_url') or pairs[2][1],
        output_paths.get('weekly_md_url') or pairs[2][2],
    )
    if output_paths.get('portfolio_md_generated') is False:
        pairs[1] = (pairs[1][0], "", "")
    if output_paths.get('weekly_md_generated') is False:
        pairs[2] = (pairs[2][0], "", "")
    pairs.insert(1, (
        'JSON metadata',
        output_paths.get('report_json_url') or output_paths.get('report_json_uri'),
        output_paths.get('report_json_url') or output_paths.get('report_json_path'),
    ))
    if output_paths.get('archive_url'):
        pairs.insert(0, ('This run archive', output_paths.get('archive_url'), output_paths.get('archive_url')))
    if output_paths.get('archive_index_url'):
        pairs.insert(0, ('Archive index', output_paths.get('archive_index_url'), output_paths.get('archive_index_url')))
    items = []
    for label, uri, path in pairs:
        if uri and path:
            items.append(f'<li><a href="{escape(str(uri))}">{escape(label)}</a><span class="path">{escape(str(path))}</span></li>')
    if not items:
        return '<div class="empty">暂无附加文件</div>'
    return '<ul class="link-list">' + ''.join(items) + '</ul>'


def _card(title: str, value: str, note: str = "") -> str:
    note_html = f'<div class="note">{escape(note)}</div>' if note else ''
    return f'<div class="metric"><div class="metric-title">{escape(title)}</div><div class="metric-value">{escape(value)}</div>{note_html}</div>'


def _section(title: str, body: str) -> str:
    return f'<section class="panel"><h2>{escape(title)}</h2>{body}</section>'


def render_dashboard_html(payload: dict[str, Any]) -> str:
    portfolio = payload.get('portfolio') or {}
    weekly = payload.get('weekly_review') or {}
    data_quality = payload.get('data_quality') or {}
    output_paths = payload.get('output_paths') or {}
    watchlist = payload.get('watchlist') or {}
    summary = portfolio.get('summary') or {}
    quotes = portfolio.get('portfolio_quotes') or {}
    local_market_payload = portfolio.get('local_market_payload') or {}
    generated = payload.get('generated_at_utc') or '未知'
    global_overview = payload.get('global_30s_overview') or '暂无全局总览。'
    dashboard = payload.get('dashboard') or {}
    dashboard_link = dashboard.get('public_url') or dashboard.get('output_path') or ''

    metrics = [
        _card("组合估值", _fmt_cny(summary.get("total_value_cny")), "含场内价格/场外估值近似"),
        _card("组合近一周", _fmt_pct(quotes.get("portfolio_week_change_pct")), "只看方向，不当精确收益"),
        _card("A股阶段", str(local_market_payload.get("phase") or "未知"), str(local_market_payload.get("style") or "本土风格框架")),
        _card("直接AI暴露", _fmt_pct(summary.get("direct_ai_pct")), "纪律线默认 35%"),
        _card("黄金仓位", _fmt_pct(summary.get("gold_pct")), "保险仓默认 10%-15%"),
        _card("新闻覆盖", f"{data_quality.get('articles_count', 0)} 条", "含 RSS / API / 官方源"),
        _card("最新时效", f"{data_quality.get('latest_article_age_hours', '未知')} 小时", data_quality.get("freshness_status") or "未知"),
        _card("待办提醒", f"{watchlist.get('triggered_count', 0)} 触发", f"{watchlist.get('active_count', 0)} 条继续盯"),
    ]

    sections = [
        _section('30秒总览', f'<div class="hero">{escape(str(global_overview))}</div>'),
    ]
    sections.append(_section('待办与触发提醒', _render_list(watchlist.get('lines'), 8)))
    if portfolio.get('enabled'):
        sections.extend([
            _section("今日3个动作", _render_list(portfolio.get("action_slot_lines"), 3)),
            _section("A股风格阶段", _render_list(portfolio.get("local_market_lines"), 6)),
            _section("固定可买池", _render_table(
                ["标的", "状态", "金额档位", "当日变化", "角色", "原因"],
                _fixed_pool_rows(portfolio.get("fixed_buy_pool_rows")),
            )),
            _section("固定可买池120/250日回填", _render_table(
                ["标的", "主题", "覆盖", "20日", "60日", "120日", "250日", "最新"],
                _backfill_rows(portfolio.get("fixed_pool_backfill_rows")),
            )),
            _section("T+1/T+3/T+5先手胜率面板", _render_table(
                ["主题", "60/120/250样本日", "当前参考窗", "T+1", "T+3", "T+5"],
                _win_rows(portfolio.get("fixed_pool_win_rows")),
            )),
            _section("写死减仓规则", _render_list(portfolio.get("hard_reduce_rule_lines"), 6)),
            _section("事件→A股/ETF映射", _render_table(
                ["优先级", "事件", "传导链", "A股/ETF先看谁", "当前动作"],
                _event_route_rows(portfolio.get("event_route_rows")),
            )),
            _section("操作手册", _render_list(portfolio.get("playbook_rule_lines"), 10)),
        ])


    if weekly.get('enabled'):
        weekly_signals = [f'{index + 1}. {item}' for index, item in enumerate(weekly.get('signals') or [])]
        sections.append(_section('周日复盘信号', _render_list(weekly_signals, 6)))

    quality_lines = [
        f"生成时间：{generated}",
        f"新闻窗口：{payload.get('window_start_utc') or '未知'} → {generated}",
        f"实际新闻：{payload.get('oldest_article_at_utc') or '未知'} → {payload.get('latest_article_at_utc') or '未知'}",
        f"可信度拦截：{(payload.get('credibility_summary') or {}).get('filtered_articles', 0)} 条",
    ]
    sections.append(_section('数据质量', _render_list(quality_lines)))
    sections.append(_section('报告入口', _path_links(output_paths)))
    if dashboard_link:
        sections.append(_section('当前驾驶舱', f'<div class="hero small">{_render_href_or_text(str(dashboard_link))}</div>'))

    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>投资决策驾驶舱</title>
  <style>
    :root {{ color-scheme: light; --bg:#f6f8fb; --panel:#ffffff; --text:#152033; --muted:#6b7280; --line:#e5e7eb; --accent:#2563eb; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:"Microsoft YaHei","PingFang SC",system-ui,sans-serif; background:var(--bg); color:var(--text); }}
    .wrap {{ max-width:1280px; margin:0 auto; padding:24px; }}
    .header {{ display:flex; justify-content:space-between; gap:16px; align-items:flex-end; flex-wrap:wrap; margin-bottom:20px; }}
    h1 {{ margin:0; font-size:30px; }}
    .sub {{ color:var(--muted); margin-top:6px; }}
    .metrics {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; margin:18px 0 22px; }}
    .metric,.panel {{ background:var(--panel); border:1px solid var(--line); border-radius:16px; box-shadow:0 4px 14px rgba(15,23,42,.04); }}
    .metric {{ padding:16px; }}
    .metric-title {{ color:var(--muted); font-size:13px; margin-bottom:8px; }}
    .metric-value {{ font-size:24px; font-weight:700; }}
    .note {{ color:var(--muted); font-size:12px; margin-top:6px; }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(360px,1fr)); gap:16px; align-items:start; }}
    .panel {{ padding:18px; }}
    .panel h2 {{ margin:0 0 12px; font-size:18px; }}
    .hero {{ background:#eff6ff; border:1px solid #bfdbfe; color:#1d4ed8; padding:14px 16px; border-radius:12px; line-height:1.65; }}
    .hero.small {{ font-size:13px; color:#334155; background:#f8fafc; border-color:#e2e8f0; }}
    ul {{ margin:0; padding-left:18px; }}
    li {{ margin:8px 0; line-height:1.6; }}
    .table-wrap {{ overflow:auto; }}
    table {{ width:100%; border-collapse:collapse; font-size:13px; }}
    th,td {{ border-bottom:1px solid var(--line); padding:10px 8px; text-align:left; vertical-align:top; }}
    th {{ color:var(--muted); font-weight:600; background:#fafafa; position:sticky; top:0; }}
    .empty {{ color:var(--muted); padding:4px 0; }}
    .footer {{ color:var(--muted); font-size:12px; margin-top:18px; }}
    .link-list {{ padding-left:18px; }}
    .path {{ display:block; color:var(--muted); font-size:12px; margin-top:4px; }}
    a {{ color:var(--accent); text-decoration:none; }}
    a:hover {{ text-decoration:underline; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="header">
      <div>
        <h1>投资决策驾驶舱</h1>
        <div class="sub">生成时间：{escape(str(generated))} UTC</div>
      </div>
      <div class="sub">先看最重要的事，再看传导链，再决定是否动手</div>
    </div>
    <div class="metrics">{''.join(metrics)}</div>
    <div class="grid">{''.join(sections)}</div>
    <div class="footer">说明：这是你的静态决策面板，不替代交易终端与人工复核；任何实际买卖前仍需二次确认价格、流动性、折溢价与仓位纪律。</div>
  </div>
</body>
</html>
"""
    return html
