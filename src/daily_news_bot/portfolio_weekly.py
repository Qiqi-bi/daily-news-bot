from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .decision_journal import build_decision_snapshot, build_event_etf_history, build_weekly_decision_review
from .fixed_pool_history import build_fixed_pool_60d_panel
from .models import EventCluster
from .portfolio import (
    _action_board_lines,
    _action_slot_lines,
    _as_float,
    _annual_objective_lines,
    _china_view,
    _evaluate_fixed_buy_pool,
    _event_impacts,
    _event_route_lines,
    _fixed_buy_pool_lines,
    _fmt_cny,
    _fmt_pct,
    _hard_reduce_candidates,
    _hard_reduce_rule_lines,
    _local_market_panel_lines,
    _build_monthly_deployment_plan,
    _ai_overlap_lines,
    _candidate_pool_lines,
    _candidate_score_lines,
    _contribution_execution_lines,
    _drawdown_trigger_lines,
    _execution_check_lines,
    _fund_lookthrough_lines,
    _monthly_scenario_lines,
    _only_reduce_watch_lines,
    _profit_lock_watch_lines,
    _portfolio_with_quote_weights,
    _range_status,
    _score_candidate_pool,
    _single_attack_cap_lines,
    _sleeve_label,
    _stock_policy_lines,
    _summary_with_quotes,
    _trade_ledger_lines,
    _trade_checklist_lines,
    _playbook_rule_lines,
    _watchlist_lines,
    summarize_portfolio,
)


def _fmt_pct_or_unknown(value: float | None) -> str:
    if value is None:
        return "未知"
    return _fmt_pct(value)


def _quote_map(portfolio_quotes: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not portfolio_quotes:
        return {}
    return {
        item.get("holding_name", ""): item
        for item in portfolio_quotes.get("items") or []
        if item.get("holding_name")
    }


def _build_week_signals(portfolio: dict[str, Any], event_impacts: list[dict[str, Any]]) -> list[str]:
    signals: list[str] = []
    for impact in event_impacts[:3]:
        themes = "、".join(impact.get("themes") or []) or "综合变量"
        signals.append(f"{impact.get('title')}：继续观察 {themes} 是否从新闻走向价格确认。")

    for item in portfolio.get("watchlist") or []:
        joined = "、".join(item.get("confirmation_signals") or [])
        if joined:
            signals.append(f"{item.get('theme', '未命名主题')}：重点看 {joined}。")
        if len(signals) >= 6:
            break
    return signals[:6]


def build_weekly_portfolio_review(
    portfolio: dict[str, Any],
    clusters: list[EventCluster],
    portfolio_quotes: dict[str, Any] | None = None,
    fund_holdings: dict[str, Any] | None = None,
    execution_checks: dict[str, Any] | None = None,
    trade_ledger: dict[str, Any] | None = None,
    tracking_summary: dict[str, Any] | None = None,
    market_snapshot: dict[str, Any] | None = None,
    fixed_pool_history: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    del market_snapshot
    portfolio_for_weights = _portfolio_with_quote_weights(portfolio, portfolio_quotes)
    summary = _summary_with_quotes(summarize_portfolio(portfolio_for_weights), portfolio_quotes)
    event_impacts = _event_impacts(clusters, portfolio_for_weights)
    quote_map = _quote_map(portfolio_quotes)
    day_change = (portfolio_quotes or {}).get("portfolio_estimated_day_change_pct")
    week_change = (portfolio_quotes or {}).get("portfolio_week_change_pct")
    total_pnl_cny = summary.get("actual_total_pnl_cny")
    total_pnl_pct = summary.get("actual_total_pnl_pct")
    risk_controls = portfolio.get("risk_controls") or {}
    allocation = portfolio.get("allocation_framework") or {}
    profile = portfolio.get("profile") or {}
    drawdown_limit = _as_float(risk_controls.get("weekly_drawdown_limit_pct"), 8.0)
    monthly_contribution = _as_float(profile.get("monthly_contribution_cny"), 0.0)
    candidate_scores = _score_candidate_pool(portfolio, event_impacts, summary)
    action_board_lines = _action_board_lines(summary, portfolio, portfolio_quotes, candidate_scores, event_impacts)
    monthly_plan_lines = _build_monthly_deployment_plan(summary, portfolio, portfolio_quotes)
    monthly_scenario_lines = _monthly_scenario_lines(summary, portfolio, portfolio_quotes)
    contribution_execution_lines = _contribution_execution_lines(portfolio)
    trade_checklist_lines = _trade_checklist_lines(portfolio, portfolio_quotes, candidate_scores, execution_checks)
    fund_lookthrough_lines = _fund_lookthrough_lines(fund_holdings)
    execution_check_lines = _execution_check_lines(execution_checks)
    trade_ledger_lines = _trade_ledger_lines(trade_ledger)
    drawdown_lines = _drawdown_trigger_lines(portfolio, portfolio_quotes)
    ai_overlap_lines = _ai_overlap_lines(portfolio, portfolio_quotes, summary)
    single_attack_cap_lines = _single_attack_cap_lines(portfolio, portfolio_quotes)
    only_reduce_lines = _only_reduce_watch_lines(portfolio, portfolio_quotes)
    profit_lock_lines = _profit_lock_watch_lines(portfolio, portfolio_quotes)
    stock_policy_lines = _stock_policy_lines(portfolio)
    candidate_lines = _candidate_pool_lines(portfolio)
    event_route_lines, event_route_rows = _event_route_lines(
        event_impacts,
        portfolio,
        candidate_scores,
        summary,
        portfolio_quotes=portfolio_quotes,
        tracking_summary=tracking_summary,
    )
    event_history_stats = build_event_etf_history(event_route_rows)
    event_history_lines = event_history_stats.get("lines") or []
    local_market_lines, local_market_payload = _local_market_panel_lines(portfolio, portfolio_quotes, execution_checks)
    reduce_candidates = _hard_reduce_candidates(portfolio, summary, portfolio_quotes)
    hard_reduce_rule_lines = _hard_reduce_rule_lines(portfolio, reduce_candidates)
    fixed_buy_pool_rows = _evaluate_fixed_buy_pool(
        portfolio,
        summary,
        portfolio_quotes,
        execution_checks,
        candidate_scores,
        event_route_rows,
        local_market_payload=local_market_payload,
    )
    fixed_buy_pool_lines = _fixed_buy_pool_lines(fixed_buy_pool_rows)
    fixed_pool_history_panel = build_fixed_pool_60d_panel(portfolio, event_route_rows, fixed_pool_history)
    fixed_pool_backfill_lines = fixed_pool_history_panel.get("backfill_lines") or ["- 固定候选池历史回填暂不可用。"]
    fixed_pool_win_lines = fixed_pool_history_panel.get("win_lines") or ["- T+1/T+3/T+5 先手胜率暂不可用。"]
    action_slot_lines = _action_slot_lines(portfolio, fixed_buy_pool_rows, reduce_candidates, portfolio_quotes)
    annual_objective_lines = _annual_objective_lines(portfolio)
    playbook_rule_lines = _playbook_rule_lines(portfolio, summary)
    current_snapshot = build_decision_snapshot(
        generated_at=datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0),
        summary=summary,
        event_impacts=event_impacts,
        candidate_scores=candidate_scores,
        action_board_lines=action_board_lines,
        execution_checks=execution_checks,
        action_slot_lines=action_slot_lines,
    )
    decision_review = build_weekly_decision_review(current_snapshot, execution_checks=execution_checks)

    lines: list[str] = [
        "# 周日组合复盘",
        "",
        "## 30秒结论",
        "",
        f"- 你的组合本质上是“稳底仓 + 成长底仓 + AI进攻 + 黄金保险”，其中进攻仓 {_fmt_pct(summary['attack_pct'])}、成长底仓 {_fmt_pct(summary['growth_core_pct'])}，波动来源很清楚。",
        f"- 当前真实浮盈亏约 {_fmt_cny(total_pnl_cny or 0.0)}（{_fmt_pct_or_unknown(total_pnl_pct)}），每月新增资金约 {_fmt_cny(monthly_contribution)}，单周回撤警戒线 {_fmt_pct(drawdown_limit)}。" if total_pnl_cny is not None else f"- 每月新增资金约 {_fmt_cny(monthly_contribution)}，单周回撤警戒线 {_fmt_pct(drawdown_limit)}。",
        f"- 按当前权重估算，组合日内变化约 {_fmt_pct_or_unknown(day_change)}，近一周约 {_fmt_pct_or_unknown(week_change)}；这个数字更适合看方向，不适合作为精确盈亏。",
        "- 下周真正要盯的不是新闻数量，而是：AI是否继续拥挤、能源链是否形成持续共振、中国宏观变量是否开始主导宽基表现。",
        "",
        "## 本周组合结构回看",
        "",
        "| 维度 | 当前比例 | 复盘结论 |",
        "|---|---:|---|",
        f"| 稳底仓 | {_fmt_pct(summary['stable_core_pct'])} | {_range_status(summary['stable_core_pct'], allocation.get('stable_core_target_pct') or [35,45])}；沪深300 + 上证指数，是低吸时优先补的部分 |",
        f"| 成长底仓 | {_fmt_pct(summary['growth_core_pct'])} | {_range_status(summary['growth_core_pct'], allocation.get('growth_core_target_pct') or [15,20])}；创业板是核心仓，但不是防守仓 |",
        f"| 进攻仓 | {_fmt_pct(summary['attack_pct'])} | {_range_status(summary['attack_pct'], allocation.get('attack_target_pct') or [20,30])}；AI已经偏高，下周不宜继续无脑加同类 |",
        f"| 保险仓 | {_fmt_pct(summary['insurance_pct'])} | {_range_status(summary['insurance_pct'], allocation.get('insurance_target_pct') or [10,15])}；黄金负责对冲，不负责冲锋 |",
        "",
        "## 本周净值/价格跟踪",
        "",
        "| 持仓 | 分类 | 代码 | 成本 | 最新 | 权重 | 浮盈亏 | 近一周 | 下周定位 |",
        "|---|---|---|---:|---:|---:|---:|---:|---|",
    ]

    for holding in portfolio.get("holdings") or []:
        quote = quote_map.get(holding.get("name", ""), {})
        latest_text = "未知"
        if quote.get("estimate_nav") is not None:
            latest_text = f"{quote.get('estimate_nav'):.4f}"
        elif quote.get("official_nav") is not None:
            latest_text = f"{quote.get('official_nav'):.4f}"
        cost_text = "未知" if quote.get("cost_nav") is None else f"{quote.get('cost_nav'):.4f}"
        weight_text = "未知" if quote.get("actual_weight_pct") is None else _fmt_pct(quote.get("actual_weight_pct") or 0.0)
        pnl_text = "未知"
        if quote.get("unrealized_pnl_cny") is not None:
            pnl_text = f"{_fmt_cny(quote.get('unrealized_pnl_cny') or 0.0)} / {_fmt_pct_or_unknown(quote.get('unrealized_pnl_pct'))}"

        if holding.get("sleeve") == "insurance":
            positioning = "保险/对冲"
        elif holding.get("sleeve") == "attack":
            positioning = "高弹性主题仓"
        elif holding.get("sleeve") == "growth_core":
            positioning = "成长底仓/风格放大器"
        elif holding.get("sleeve") == "stable_core":
            positioning = "稳底仓"
        else:
            positioning = "待分类"

        week_text = "未知" if quote.get("week_change_pct") is None else _fmt_pct(quote.get("week_change_pct") or 0.0)
        lines.append(
            f"| {holding.get('name')} | {_sleeve_label(holding.get('sleeve'))} | {holding.get('code') or '未填'} | {cost_text} | {latest_text} | {weight_text} | {pnl_text} | {week_text} | {positioning} |"
        )

    lines.extend(["", "## 下周最该盯的事", ""])
    if event_impacts:
        for index, impact in enumerate(event_impacts[:4], start=1):
            lines.append(
                f"{index}. **{impact.get('priority')}**｜{impact.get('title')}｜映射：{'、'.join(impact.get('themes') or [])}｜影响仓位约 {_fmt_pct(impact.get('exposed_weight_pct') or 0.0)}。"
            )
    else:
        lines.append("- 本周没有识别到明显直连你组合主线的核心事件，优先观察A股本身的风格切换。")

    lines.extend(["", "## 上周建议后来怎么样", ""])
    lines.extend(decision_review.get("lines") or ["- 暂无复盘结论。"])

    lines.extend(["", "## A股本土风格面板", ""])
    lines.extend(["", "## A股风格阶段面板", ""])
    lines.extend(local_market_lines)

    lines.extend(["", "## 固定候选池", ""])
    lines.extend(fixed_buy_pool_lines)

    lines.extend(["", "## 固定候选池120/250日回填", ""])
    lines.extend(fixed_pool_backfill_lines)

    lines.extend(["", "## T+1/T+3/T+5先手胜率面板", ""])
    lines.extend(fixed_pool_win_lines)

    lines.extend(["", "## 写死减仓规则", ""])
    lines.extend(hard_reduce_rule_lines)

    lines.extend(["", "## 下周纪律档位", ""])
    lines.extend(action_slot_lines)

    lines.extend(["", "## 下周3大事件→A股/ETF映射", ""])
    lines.extend(event_route_lines)

    lines.extend(["", "## 这类消息历史上先动谁", ""])
    lines.extend(event_history_lines)

    lines.extend(["", "## 年度目标框架", ""])
    lines.extend(annual_objective_lines)

    lines.extend(["", "## 下周按哪几条规则执行", ""])
    lines.extend(playbook_rule_lines)

    lines.extend(["", "## 下周最该盯的6个信号", ""])
    for index, signal in enumerate(_build_week_signals(portfolio, event_impacts), start=1):
        lines.append(f"{index}. {signal}")

    lines.extend(
        [
            "",
            "## 下周纪律框架",
            "",
            "- **先做纪律，不先做交易**：先看直接AI≤35%、广义成长/科技≤55%、单个进攻仓≤15% 这三条线是否还成立。",
            f"- **新增资金先看补短板**：每月约 {_fmt_cny(monthly_contribution)} 的新增资金不要机械平均；如果没有新的中级别催化，不建议继续往同类AI主题堆仓。",
            f"- **回撤纪律先定好**：如果组合单周回撤接近 {_fmt_pct(drawdown_limit)}，先暂停新增进攻仓，检查AI、科创、创业板是否同向下跌。",
            "- **能源链只做观察，不做条件反射**：油价上涨先想到的是油气/航运/煤电链，不是立刻去追新能源。",
            "- **宽基是稳定器，不是拖油瓶**：如果未来想把组合做得更稳，宽基和防御仓的重要性会继续上升。",
            "",
            "## 下月新增资金手动分配框架",
            "",
        ]
    )
    lines.extend(monthly_plan_lines)
    lines.extend(["", "## 月中三档资金方案", ""])
    lines.extend(monthly_scenario_lines)
    lines.extend(["", "## 新增资金分批执行", ""])
    lines.extend(contribution_execution_lines)
    lines.extend(["", "## 交易前确认清单", ""])
    lines.extend(trade_checklist_lines)
    lines.extend(["", "## 低吸触发规则", ""])
    lines.extend(drawdown_lines)
    lines.extend(["", "## AI重叠度报告", ""])
    lines.extend(ai_overlap_lines)
    lines.extend(["", "## 基金前十大持仓穿透", ""])
    lines.extend(fund_lookthrough_lines)
    lines.extend(["", "## ETF执行检查", ""])
    lines.extend(execution_check_lines)
    lines.extend(["", "## 交易记录汇总", ""])
    lines.extend(trade_ledger_lines)
    lines.extend(["", "## 单个进攻仓上限", ""])
    lines.extend(single_attack_cap_lines)
    lines.extend(["", "## 只减不加观察线", ""])
    lines.extend(only_reduce_lines)
    lines.extend(["", "## 分批锁盈提醒", ""])
    lines.extend(profit_lock_lines)
    lines.extend(["", "## 候选池评分", ""])
    lines.extend(_candidate_score_lines(candidate_scores))
    lines.extend(
        [
            "",
            "## 下周不要做什么",
            "",
            "- 不要因为单日海外科技股大涨，就继续加同类AI基金。",
            "- 不要因为单日油价异动，就把新能源当成第一反应。",
            "- 不要把黄金当主攻仓；它的任务是保险，不是冲锋。",
            "",
            "## 候选ETF池",
            "",
        ]
    )
    lines.extend(candidate_lines if candidate_lines else ["- 暂未配置候选ETF池。"])
    lines.extend(["", "## 股票规则", ""])
    lines.extend(stock_policy_lines)
    lines.extend(["", "## 宏观主题观察池", ""])
    lines.extend(_watchlist_lines(portfolio, event_impacts))
    lines.extend(["", "## 中国视角", ""])
    lines.extend(_china_view(clusters))
    lines.extend(
        [
            "",
            "> 风险提示：本复盘用于下周跟踪框架和仓位纪律，不是自动买卖建议。若你后续补充成本价、份额和每月新增资金，复盘会明显更准确。",
        ]
    )

    payload = {
        "summary": summary,
        "event_impacts": event_impacts,
        "signals": _build_week_signals(portfolio, event_impacts),
        "candidate_scores": candidate_scores,
        "action_board_lines": action_board_lines,
        "local_market_lines": local_market_lines,
        "local_market_payload": local_market_payload,
        "reduce_candidates": reduce_candidates,
        "hard_reduce_rule_lines": hard_reduce_rule_lines,
        "fixed_buy_pool_rows": fixed_buy_pool_rows,
        "fixed_buy_pool_lines": fixed_buy_pool_lines,
        "fixed_pool_history": fixed_pool_history or {},
        "fixed_pool_backfill_lines": fixed_pool_backfill_lines,
        "fixed_pool_backfill_rows": fixed_pool_history_panel.get("backfill_rows") or [],
        "fixed_pool_win_lines": fixed_pool_win_lines,
        "fixed_pool_win_rows": fixed_pool_history_panel.get("win_rows") or [],
        "action_slot_lines": action_slot_lines,
        "event_route_lines": event_route_lines,
        "event_route_rows": event_route_rows,
        "event_history_lines": event_history_lines,
        "event_history_rows": event_history_stats.get("rows") or [],
        "annual_objective_lines": annual_objective_lines,
        "playbook_rule_lines": playbook_rule_lines,
        "decision_review": decision_review,
        "portfolio_quotes": portfolio_quotes or {},
    }
    return "\n".join(lines).strip() + "\n", payload
