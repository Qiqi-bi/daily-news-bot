from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any

import yaml

from .config import ROOT_DIR
from .decision_journal import build_event_etf_history
from .fixed_pool_history import build_fixed_pool_60d_panel
from .industry_radar import build_industry_radar, render_industry_radar_lines
from .models import EventCluster


THEME_RULES: dict[str, dict[str, Any]] = {
    "ai": {
        "label": "AI/科技成长",
        "keywords": (
            "ai",
            "artificial intelligence",
            "semiconductor",
            "chip",
            "nvidia",
            "apple",
            "openai",
            "人工智能",
            "算力",
            "半导体",
            "芯片",
            "科技",
            "苹果",
            "英伟达",
        ),
        "benefit": "AI主题、科创AI、创业板成长风格可能最敏感。",
        "risk": "估值和拥挤度较高，若海外科技股或半导体链回撤，组合波动会被放大。",
    },
    "ai_power_base": {
        "label": "AI电力底座/算电协同",
        "keywords": (
            "compute power and electricity",
            "green compute",
            "ai data center",
            "data center power",
            "800v hvdc",
            "liquid cooling",
            "power grid",
            "transformer",
            "算电协同",
            "绿色算力",
            "零碳算力",
            "算力电力",
            "数据中心用电",
            "绿电",
            "电网",
            "变压器",
            "特高压",
            "风电",
            "源网荷储",
            "储能",
            "虚拟电厂",
            "电力交易",
            "绿证",
            "液冷",
            "服务器电源",
            "AIDC",
        ),
        "benefit": "AI长期需求会扩散到绿电、电网设备、储能、液冷和数据中心电源，是独立于AI进攻仓的长期底座线。",
        "risk": "故事兑现周期长，收益可能被地方、电网、客户或重资产折旧分走；只能小底仓跟踪，不能替代价格和订单确认。",
    },
    "gold": {
        "label": "黄金/避险",
        "keywords": (
            "gold",
            "treasury",
            "yield",
            "dollar",
            "fed",
            "federal reserve",
            "inflation",
            "war",
            "geopolitics",
            "黄金",
            "美债",
            "收益率",
            "美元",
            "美联储",
            "通胀",
            "战争",
            "地缘",
            "避险",
        ),
        "benefit": "黄金仓位承担组合保险功能，适合用来对冲地缘和实际利率下行风险。",
        "risk": "若美元和美债实际利率同步走强，黄金可能对组合形成拖累。",
    },
    "energy": {
        "label": "能源/航运/大宗链",
        "keywords": (
            "oil",
            "crude",
            "brent",
            "wti",
            "opec",
            "gas",
            "lng",
            "energy",
            "fuel",
            "shipping",
            "hormuz",
            "iran",
            "middle east",
            "原油",
            "石油",
            "天然气",
            "能源",
            "燃油",
            "航运",
            "油运",
            "霍尔木兹",
            "伊朗",
            "中东",
            "煤炭",
        ),
        "benefit": "第一层通常不是新能源，而是油气、煤炭、电力、油运、航运、炼化和部分化工链。",
        "risk": "高油价会压制航空、消费、制造业利润，并可能推高通胀预期。",
    },
    "china_macro": {
        "label": "中国宏观/A股宽基",
        "keywords": (
            "china",
            "chinese",
            "pboc",
            "yuan",
            "cnh",
            "tariff",
            "trade",
            "stimulus",
            "pmi",
            "中国",
            "人民币",
            "央行",
            "政策",
            "刺激",
            "贸易",
            "关税",
            "出口",
            "消费",
            "a股",
            "沪深300",
        ),
        "benefit": "更容易影响沪深300、上证指数、创业板等宽基仓位。",
        "risk": "若外需、汇率或政策预期转弱，宽基仓位会同步受压。",
    },
    "new_energy": {
        "label": "新能源",
        "keywords": (
            "ev",
            "battery",
            "lithium",
            "solar",
            "renewable",
            "新能源",
            "电动车",
            "锂电",
            "锂价",
            "光伏",
            "储能",
        ),
        "benefit": "新能源更看产业周期、价格出清、政策和订单修复。",
        "risk": "油价上涨只能提供长期替代逻辑，不等于A股新能源会立刻上涨。",
    },
}


DEFAULT_LONG_TERM_CANDIDATE_ETF_POOL: list[dict[str, Any]] = [
    {
        "theme": "AI电力底座",
        "theme_key": "ai_power_base",
        "role": "算电协同/绿色算力长期底仓候选",
        "fit_for": "当算电协同、绿电、数据中心用电、电网设备、储能或液冷订单形成连续确认时",
        "caution": "这是1-5年主线，不是短线AI进攻仓；首次只允许2%-3%观察底仓，确认后再看5%-8%。",
        "instruments": [
            {
                "name": "电力ETF",
                "code": "561560",
                "type": "ETF",
                "market": "A股",
                "usage": "观察/候选，偏绿电运营和电力现金流",
            },
            {
                "name": "电网设备ETF易方达",
                "code": "560390",
                "type": "ETF",
                "market": "A股",
                "usage": "观察/候选，偏电网设备、变压器和特高压",
            },
        ],
    }
]


DEFAULT_LONG_TERM_FIXED_BUY_POOL: list[dict[str, Any]] = [
    {
        "code": "560390",
        "name": "电网设备ETF易方达",
        "type": "ETF",
        "role": "AI电力底座观察仓",
        "theme_key": "ai_power_base",
        "comment": "算电协同、电网设备、变压器和特高压方向；只做2%-3%试探底仓，不追高",
    }
]


@dataclass(slots=True)
class HoldingImpact:
    name: str
    weight_pct: float
    role: str
    matched_themes: list[str]
    impact_level: str
    note: str


def load_portfolio(path: str | None = None) -> dict[str, Any] | None:
    portfolio_path = Path(path) if path else ROOT_DIR / "config" / "portfolio.yaml"
    if not portfolio_path.is_absolute():
        portfolio_path = ROOT_DIR / portfolio_path
    if not portfolio_path.exists():
        return None
    payload = yaml.safe_load(portfolio_path.read_text(encoding="utf-8")) or {}
    payload["_path"] = str(portfolio_path)
    return payload


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _maybe_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _fmt_pct(value: float) -> str:
    return f"{value:.2f}%"


def _fmt_cny(value: float) -> str:
    return f"¥{value:,.2f}"


def _quote_map(portfolio_quotes: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not portfolio_quotes:
        return {}
    return {
        item.get("holding_name", ""): item
        for item in portfolio_quotes.get("items") or []
        if item.get("holding_name")
    }


def _quote_map_by_code(portfolio_quotes: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not portfolio_quotes:
        return {}
    return {
        str(item.get("code") or ""): item
        for item in portfolio_quotes.get("items") or []
        if item.get("code")
    }


def _execution_map_by_code(execution_checks: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not execution_checks:
        return {}
    return {
        str(item.get("code") or ""): item
        for item in execution_checks.get("items") or []
        if item.get("code")
    }


def _fmt_nav(value: float | None) -> str:
    if value is None:
        return "未知"
    return f"{value:.4f}"


def _fmt_pct_or_unknown(value: float | None) -> str:
    if value is None:
        return "未知"
    return _fmt_pct(value)


def _text_for_cluster(cluster: EventCluster) -> str:
    representative = cluster.representative
    return f"{representative.title} {representative.summary} {representative.source}".lower()


def _keyword_in_text(keyword: str, text: str) -> bool:
    lowered = keyword.lower().strip()
    if not lowered:
        return False
    if any("a" <= char <= "z" for char in lowered):
        return re.search(rf"\b{re.escape(lowered)}\b", text) is not None
    return lowered in text


def _match_event_themes(cluster: EventCluster) -> list[str]:
    text = _text_for_cluster(cluster)
    matched: list[str] = []
    for theme_key, rule in THEME_RULES.items():
        if any(_keyword_in_text(keyword, text) for keyword in rule["keywords"]):
            matched.append(theme_key)
    return matched


def _holding_themes(holding: dict[str, Any]) -> str:
    values = [holding.get("name", ""), holding.get("role", ""), holding.get("bucket", "")]
    values.extend(holding.get("themes") or [])
    return " ".join(str(value) for value in values).lower()


def summarize_portfolio(portfolio: dict[str, Any]) -> dict[str, Any]:
    holdings = portfolio.get("holdings") or []
    total_value = _as_float((portfolio.get("profile") or {}).get("total_value_cny"))
    total_weight = sum(_as_float(item.get("weight_pct")) for item in holdings)

    def sum_if(*needles: str) -> float:
        return sum(
            _as_float(item.get("weight_pct"))
            for item in holdings
            if any(needle.lower() in _holding_themes(item) for needle in needles)
        )

    direct_ai = sum(_as_float(item.get("weight_pct")) for item in holdings if item.get("bucket") == "ai_direct")
    growth_tech = sum(
        _as_float(item.get("weight_pct"))
        for item in holdings
        if item.get("bucket") in {"ai_direct", "growth_broad"}
    )
    gold = sum(_as_float(item.get("weight_pct")) for item in holdings if item.get("bucket") == "gold")
    core_broad = sum(_as_float(item.get("weight_pct")) for item in holdings if item.get("bucket") == "broad_core")
    stable_core = sum(_as_float(item.get("weight_pct")) for item in holdings if item.get("sleeve") == "stable_core")
    growth_core = sum(_as_float(item.get("weight_pct")) for item in holdings if item.get("sleeve") == "growth_core")
    attack = sum(_as_float(item.get("weight_pct")) for item in holdings if item.get("sleeve") == "attack")
    insurance = sum(_as_float(item.get("weight_pct")) for item in holdings if item.get("sleeve") == "insurance")
    china_equity = max(total_weight - gold, 0.0)

    return {
        "total_value_cny": total_value,
        "holdings_count": len(holdings),
        "total_weight_pct": total_weight,
        "direct_ai_pct": direct_ai,
        "growth_tech_pct": growth_tech,
        "gold_pct": gold,
        "core_broad_pct": core_broad,
        "stable_core_pct": stable_core,
        "growth_core_pct": growth_core,
        "attack_pct": attack,
        "insurance_pct": insurance,
        "china_equity_pct": china_equity,
    }


def _summary_with_quotes(summary: dict[str, Any], portfolio_quotes: dict[str, Any] | None) -> dict[str, Any]:
    if not portfolio_quotes:
        return summary
    actual_exposures = portfolio_quotes.get("actual_exposures") or {}
    updated = dict(summary)
    if portfolio_quotes.get("actual_total_value_cny") is not None:
        updated["total_value_cny"] = portfolio_quotes["actual_total_value_cny"]
    if actual_exposures.get("direct_ai_pct") is not None:
        updated["direct_ai_pct"] = actual_exposures["direct_ai_pct"]
    if actual_exposures.get("growth_tech_pct") is not None:
        updated["growth_tech_pct"] = actual_exposures["growth_tech_pct"]
    if actual_exposures.get("gold_pct") is not None:
        updated["gold_pct"] = actual_exposures["gold_pct"]
    if actual_exposures.get("core_weight_pct") is not None:
        updated["core_broad_pct"] = actual_exposures["core_weight_pct"]
    if actual_exposures.get("stable_core_pct") is not None:
        updated["stable_core_pct"] = actual_exposures["stable_core_pct"]
    if actual_exposures.get("growth_core_pct") is not None:
        updated["growth_core_pct"] = actual_exposures["growth_core_pct"]
    if actual_exposures.get("attack_pct") is not None:
        updated["attack_pct"] = actual_exposures["attack_pct"]
    if actual_exposures.get("insurance_pct") is not None:
        updated["insurance_pct"] = actual_exposures["insurance_pct"]
    updated["china_equity_pct"] = max(100 - updated.get("gold_pct", 0.0), 0.0)
    updated["actual_total_cost_cny"] = portfolio_quotes.get("actual_total_cost_cny")
    updated["actual_total_pnl_cny"] = portfolio_quotes.get("actual_total_pnl_cny")
    updated["actual_total_pnl_pct"] = portfolio_quotes.get("actual_total_pnl_pct")
    return updated


def _cap_status(value: float, cap: float) -> str:
    if cap <= 0:
        return "未设置"
    if value > cap:
        return "超出上限"
    if value >= cap * 0.92:
        return "接近上限"
    if value >= cap * 0.75:
        return "偏高"
    return "正常"


def _gold_status(gold_pct: float, target_range: list[Any]) -> str:
    if len(target_range) != 2:
        return "未设置区间"
    low = _as_float(target_range[0])
    high = _as_float(target_range[1])
    if gold_pct < low:
        return "低于保险仓区间"
    if gold_pct > high:
        return "高于保险仓区间"
    return "处于保险仓区间"


def _range_status(value: float, target_range: list[Any]) -> str:
    if len(target_range) != 2:
        return "未设置"
    low = _as_float(target_range[0])
    high = _as_float(target_range[1])
    if value < low:
        return "低配"
    if value > high:
        return "高配"
    return "区间内"


def _range_deviation(value: float, target_range: list[Any]) -> float:
    if len(target_range) != 2:
        return 0.0
    low = _as_float(target_range[0])
    high = _as_float(target_range[1], low)
    if value < low:
        return round(low - value, 2)
    if value > high:
        return round(high - value, 2)
    return 0.0


def _allocation_action(label: str, status: str, deviation: float) -> str:
    if status == "低配":
        return f"新增资金优先补 {label}，差约 {_fmt_pct(abs(deviation))} 到目标下沿。"
    if status == "高配":
        return f"暂停新增 {label}；若继续扩大，进入减仓/再平衡复核。"
    if status == "区间内":
        return "维持，不因单日新闻改变目标仓位。"
    return "目标区间未设置，先只观察。"


def _allocation_deviation_text(status: str, deviation: float) -> str:
    if status == "低配":
        return f"差 {_fmt_pct(abs(deviation))}"
    if status == "高配":
        return f"超 {_fmt_pct(abs(deviation))}"
    if status == "区间内":
        return "0.00%"
    return "-"


def _allocation_deviation_panel(summary: dict[str, Any], portfolio: dict[str, Any]) -> dict[str, Any]:
    allocation = portfolio.get("allocation_framework") or {}
    total_weight = _as_float(summary.get("total_weight_pct"), 100.0)
    reserve_pct = max(0.0, round(100.0 - total_weight, 2))
    definitions = [
        ("stable_core", "稳底仓", summary.get("stable_core_pct"), allocation.get("stable_core_target_pct") or [35, 45]),
        ("growth_core", "成长底仓", summary.get("growth_core_pct"), allocation.get("growth_core_target_pct") or [15, 20]),
        ("attack", "进攻仓", summary.get("attack_pct"), allocation.get("attack_target_pct") or [20, 30]),
        ("insurance", "保险仓", summary.get("insurance_pct"), allocation.get("insurance_target_pct") or [10, 15]),
        ("reserve", "现金/等待", reserve_pct, allocation.get("reserve_target_pct") or [0, 10]),
    ]

    rows: list[dict[str, Any]] = []
    for key, label, current_raw, target_range in definitions:
        current = _as_float(current_raw)
        status = _range_status(current, target_range)
        deviation = _range_deviation(current, target_range)
        rows.append(
            {
                "key": key,
                "label": label,
                "current_pct": current,
                "target_range_pct": [_as_float(target_range[0]), _as_float(target_range[1])] if len(target_range) == 2 else [],
                "status": status,
                "deviation_pct": deviation,
                "deviation_text": _allocation_deviation_text(status, deviation),
                "action": _allocation_action(label, status, deviation),
            }
        )

    high = [row for row in rows if row["status"] == "高配"]
    low = [row for row in rows if row["status"] == "低配"]
    if high:
        conclusion = "优先处理高配：" + "、".join(row["label"] for row in high[:2]) + "。"
    elif low:
        conclusion = "新增资金优先补低配：" + "、".join(row["label"] for row in low[:2]) + "。"
    else:
        conclusion = "主要仓位在目标区间内，默认继续持有。"
    return {"enabled": True, "rows": rows, "conclusion": conclusion}


def _allocation_deviation_lines(panel: dict[str, Any]) -> list[str]:
    lines = [
        f"- {panel.get('conclusion') or '按目标仓位做再平衡复核。'}",
        "| 模块 | 当前 | 目标 | 偏离 | 状态 | 处理 |",
        "|---|---:|---:|---:|---|---|",
    ]
    for row in panel.get("rows") or []:
        lines.append(
            f"| {row.get('label')} | {_fmt_pct(row.get('current_pct') or 0.0)} | {_fmt_pct_range(row.get('target_range_pct'))} | {row.get('deviation_text') or _fmt_pct(row.get('deviation_pct') or 0.0)} | {row.get('status')} | {row.get('action')} |"
        )
    return lines


def _merge_by_key(configured: list[dict[str, Any]], defaults: list[dict[str, Any]], key_name: str) -> list[dict[str, Any]]:
    rows = [dict(item) for item in configured if isinstance(item, dict)]
    existing = {str(item.get(key_name) or "") for item in rows}
    for item in defaults:
        key = str(item.get(key_name) or "")
        if key and key not in existing:
            rows.append(dict(item))
            existing.add(key)
    return rows


def _candidate_etf_pool(portfolio: dict[str, Any]) -> list[dict[str, Any]]:
    return _merge_by_key(
        list(portfolio.get("candidate_etf_pool") or []),
        DEFAULT_LONG_TERM_CANDIDATE_ETF_POOL,
        "theme_key",
    )


def _candidate_pool_lines(portfolio: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for item in _candidate_etf_pool(portfolio):
        lines.append(
            f"- {item.get('theme', '未命名')}：{item.get('role', '')}；适用场景：{item.get('fit_for', '')}；注意：{item.get('caution', '')}。"
        )
        instruments = item.get("instruments") or []
        if instruments:
            refs = "、".join(
                f"`{instrument.get('code')}` {instrument.get('name')}"
                for instrument in instruments
                if instrument.get("code") and instrument.get("name")
            )
            usage = instruments[0].get("usage") or "观察/候选"
            if refs:
                lines.append(f"- {item.get('theme', '未命名')}参考代码：{refs}；默认用途：{usage}。")
    return lines


def _iter_rule_holdings(
    portfolio: dict[str, Any],
    portfolio_quotes: dict[str, Any] | None,
    applies_to_sleeves: set[str] | None = None,
):
    quote_by_name = _quote_map(portfolio_quotes)
    for holding in portfolio.get("holdings") or []:
        if applies_to_sleeves and holding.get("sleeve") not in applies_to_sleeves:
            continue
        quote = quote_by_name.get(holding.get("name", ""), {})
        weight = quote.get("actual_weight_pct")
        if weight is None:
            weight = _as_float(holding.get("weight_pct"))
        pnl_pct = quote.get("unrealized_pnl_pct")
        yield holding, quote, weight, pnl_pct


def _single_attack_cap_lines(portfolio: dict[str, Any], portfolio_quotes: dict[str, Any] | None) -> list[str]:
    cap = _as_float((portfolio.get("risk_controls") or {}).get("single_attack_holding_cap_pct"), 0.0)
    if cap <= 0:
        return ["- 未启用单个进攻仓上限。"]

    lines: list[str] = []
    for holding, _, weight, _ in _iter_rule_holdings(portfolio, portfolio_quotes, {"attack"}):
        if weight is None or weight <= 0:
            continue
        if weight >= cap:
            lines.append(
                f"- {holding.get('name')}：当前仓位约 {_fmt_pct(weight)}，已达到/超过单个进攻仓上限 {_fmt_pct(cap)}；默认不再新增，优先处理重叠风险。"
            )
        elif weight >= cap * 0.9:
            lines.append(
                f"- {holding.get('name')}：当前仓位约 {_fmt_pct(weight)}，已接近单个进攻仓上限 {_fmt_pct(cap)}；除非出现强催化并二次确认，否则不建议继续加。"
            )
    if not lines:
        lines.append(f"- 当前没有单个进攻仓接近或超过 {_fmt_pct(cap)} 的上限。")
    return lines


def _only_reduce_watch_lines(portfolio: dict[str, Any], portfolio_quotes: dict[str, Any] | None) -> list[str]:
    controls = portfolio.get("risk_controls") or {}
    watchline = controls.get("only_reduce_watchline") or {}
    if not watchline.get("enabled"):
        return ["- 未启用只减不加观察线。"]
    threshold = _as_float(watchline.get("unrealized_profit_pct"), 30.0)
    applies = set(watchline.get("applies_to_sleeves") or [])
    lines: list[str] = []
    for holding, _, _, pnl_pct in _iter_rule_holdings(portfolio, portfolio_quotes, applies or None):
        if pnl_pct is None:
            continue
        if pnl_pct >= threshold:
            lines.append(
                f"- {holding.get('name')}：浮盈 {_fmt_pct(pnl_pct)}，已触发只减不加观察线；含义是先不新增同类进攻仓，不等于必须卖出。"
            )
    if not lines:
        lines.append(f"- 当前没有持仓触发 {_fmt_pct(threshold)} 的只减不加观察线。")
    return lines


def _profit_lock_watch_lines(portfolio: dict[str, Any], portfolio_quotes: dict[str, Any] | None) -> list[str]:
    controls = portfolio.get("risk_controls") or {}
    watchline = controls.get("profit_lock_watchline") or {}
    if not watchline.get("enabled"):
        return ["- 未启用分批锁盈提醒。"]
    threshold = _as_float(watchline.get("unrealized_profit_pct"), 50.0)
    applies = set(watchline.get("applies_to_sleeves") or [])
    action = watchline.get("action") or "达到后提醒考虑分批锁定部分收益，不自动卖出。"
    lines: list[str] = []
    for holding, _, _, pnl_pct in _iter_rule_holdings(portfolio, portfolio_quotes, applies or None):
        if pnl_pct is None:
            continue
        if pnl_pct >= threshold:
            lines.append(
                f"- {holding.get('name')}：浮盈 {_fmt_pct(pnl_pct)}，已触发 {_fmt_pct(threshold)} 分批锁盈提醒；{action}"
            )
    if not lines:
        lines.append(f"- 当前没有持仓触发 {_fmt_pct(threshold)} 的分批锁盈提醒。")
    return lines


def _drawdown_trigger_lines(portfolio: dict[str, Any], portfolio_quotes: dict[str, Any] | None) -> list[str]:
    week_change = (portfolio_quotes or {}).get("portfolio_week_change_pct")
    triggers = portfolio.get("drawdown_triggers") or []
    if week_change is None:
        return ["- 暂无近一周组合变化，不能判断低吸触发级别。"]
    drawdown = max(-week_change, 0.0)
    active = None
    for trigger in sorted(triggers, key=lambda item: _as_float(item.get("drawdown_pct"))):
        if drawdown >= _as_float(trigger.get("drawdown_pct")):
            active = trigger
    if active:
        return [
            f"- 当前近一周回撤约 {_fmt_pct(drawdown)}，触发级别：{active.get('level')}。",
            f"- 动作框架：{active.get('action')}。",
            f"- 你的偏好：{(portfolio.get('preferences') or {}).get('low_buy_preference', '优先低吸稳底仓')}。",
        ]
    return [
        f"- 当前近一周没有触发低吸规则（近一周变化 {_fmt_pct(week_change)}）。",
        "- 这种情况下不要为了把钱投出去而硬加进攻仓；按月度分配框架执行即可。",
    ]


def _attack_allocation_blockers(portfolio: dict[str, Any], portfolio_quotes: dict[str, Any] | None) -> list[str]:
    controls = portfolio.get("risk_controls") or {}
    cap = _as_float(controls.get("single_attack_holding_cap_pct"), 0.0)
    only_reduce = controls.get("only_reduce_watchline") or {}
    only_reduce_threshold = _as_float(only_reduce.get("unrealized_profit_pct"), 30.0)
    only_reduce_enabled = bool(only_reduce.get("enabled"))
    profit_lock = controls.get("profit_lock_watchline") or {}
    profit_lock_threshold = _as_float(profit_lock.get("unrealized_profit_pct"), 50.0)
    profit_lock_enabled = bool(profit_lock.get("enabled"))

    blockers: list[str] = []
    for holding, _, weight, pnl_pct in _iter_rule_holdings(portfolio, portfolio_quotes, {"attack"}):
        name = holding.get("name", "未知持仓")
        if cap > 0 and weight is not None and weight >= cap:
            blockers.append(f"{name} 单仓约 {_fmt_pct(weight)}，已到 {_fmt_pct(cap)} 上限")
        if only_reduce_enabled and pnl_pct is not None and pnl_pct >= only_reduce_threshold:
            blockers.append(f"{name} 浮盈 {_fmt_pct(pnl_pct)}，触发只减不加")
        if profit_lock_enabled and pnl_pct is not None and pnl_pct >= profit_lock_threshold:
            blockers.append(f"{name} 浮盈 {_fmt_pct(pnl_pct)}，触发分批锁盈提醒")
    return list(dict.fromkeys(blockers))


def _score_candidate_pool(
    portfolio: dict[str, Any],
    event_impacts: list[dict[str, Any]],
    summary: dict[str, Any],
) -> list[dict[str, Any]]:
    event_theme_keys = {key for impact in event_impacts for key in impact.get("theme_keys", [])}
    attack_pct = summary.get("attack_pct", 0.0)
    gold_pct = summary.get("insurance_pct", summary.get("gold_pct", 0.0))
    rows: list[dict[str, Any]] = []
    for item in _candidate_etf_pool(portfolio):
        theme = item.get("theme", "未命名")
        key = item.get("theme_key", "")
        catalyst = 1
        overlap_risk = 1
        fit = 2
        comment = item.get("caution", "")

        if key == "power":
            catalyst = 3 if "energy" in event_theme_keys else 2
            overlap_risk = 1
            fit = 4 if attack_pct > 30 else 3
        elif key == "semiconductor":
            catalyst = 4 if "ai" in event_theme_keys else 2
            overlap_risk = 5 if attack_pct > 30 else 4
            fit = 2 if attack_pct > 30 else 3
        elif key == "metals_gold":
            catalyst = 4 if any(theme_key in event_theme_keys for theme_key in ("gold", "energy")) else 2
            overlap_risk = 2 if gold_pct <= 15 else 3
            fit = 3 if gold_pct <= 15 else 2
        elif key == "dividend_lowvol":
            catalyst = 3 if any(theme_key in event_theme_keys for theme_key in ("energy", "gold", "china_macro")) else 2
            overlap_risk = 1
            fit = 4 if attack_pct > 25 else 3
        elif key == "hk_tech":
            catalyst = 3 if "ai" in event_theme_keys or "china_macro" in event_theme_keys else 2
            overlap_risk = 4 if attack_pct > 30 else 3
            fit = 2 if attack_pct > 30 else 3
        elif key == "ai_power_base":
            catalyst = 4 if "ai_power_base" in event_theme_keys else 3
            overlap_risk = 1
            fit = 5 if attack_pct > 30 else 4
            comment = comment or "长期底座线，只允许小底仓观察，不增加AI进攻仓重叠。"

        total = catalyst + fit - overlap_risk
        if total >= 5:
            priority = "高"
        elif total >= 3:
            priority = "中"
        else:
            priority = "低"
        rows.append(
            {
                "theme": theme,
                "theme_key": key,
                "priority": priority,
                "score": total,
                "catalyst_score": catalyst,
                "fit_score": fit,
                "overlap_risk": overlap_risk,
                "comment": comment,
                "role": item.get("role", ""),
                "instruments": list(item.get("instruments") or []),
                "instrument_refs": "、".join(
                    f"{instrument.get('name')}({instrument.get('code')})"
                    for instrument in (item.get("instruments") or [])
                    if instrument.get("name") and instrument.get("code")
                ),
            }
        )
    return sorted(rows, key=lambda row: row["score"], reverse=True)


def _candidate_score_lines(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["- 暂未配置候选池评分。"]
    lines = ["| 候选方向 | 优先级 | 分数 | 为什么 |", "|---|---|---:|---|"]
    for row in rows:
        refs = f"；参考：{row['instrument_refs']}" if row.get("instrument_refs") else ""
        lines.append(
            f"| {row['theme']} | {row['priority']} | {row['score']} | 催化 {row['catalyst_score']} / 适配 {row['fit_score']} / 重叠风险 {row['overlap_risk']}；{row['comment']}{refs} |"
        )
    return lines


def _candidate_score_index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("theme_key") or ""): item
        for item in rows
        if item.get("theme_key")
    }


def _instrument_text(instruments: list[dict[str, Any]] | None, limit: int = 3) -> str:
    refs = [
        f"{item.get('name')}({item.get('code')})"
        for item in (instruments or [])
        if item.get("name") and item.get("code")
    ]
    return "、".join(refs[:limit]) if refs else "暂无候选"


def _holding_refs(
    portfolio: dict[str, Any],
    *,
    sleeves: set[str] | None = None,
    buckets: set[str] | None = None,
    codes: set[str] | None = None,
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for holding in portfolio.get("holdings") or []:
        code = str(holding.get("code") or "")
        sleeve = str(holding.get("sleeve") or "")
        bucket = str(holding.get("bucket") or "")
        if sleeves and sleeve not in sleeves:
            continue
        if buckets and bucket not in buckets:
            continue
        if codes and code not in codes:
            continue
        refs.append({"name": holding.get("name") or code, "code": code})
    return refs


def _primary_theme_key(title: str, theme_keys: list[str]) -> str:
    text = title.lower()
    if "ai_power_base" in theme_keys and any(
        keyword in text
        for keyword in ("算电", "绿色算力", "数据中心用电", "绿电", "电网", "液冷", "800v", "hvdc", "源网荷储", "虚拟电厂")
    ):
        return "ai_power_base"
    if "ai" in theme_keys and any(keyword in text for keyword in ("ai", "artificial intelligence", "chip", "semiconductor", "算力", "人工智能", "半导体", "芯片")):
        return "ai"
    if "energy" in theme_keys and any(keyword in text for keyword in ("oil", "crude", "brent", "wti", "gas", "lng", "iran", "hormuz", "原油", "石油", "天然气", "伊朗", "霍尔木兹")):
        return "energy"
    if "gold" in theme_keys and any(keyword in text for keyword in ("gold", "fed", "yield", "dollar", "黄金", "美联储", "收益率", "美元")):
        return "gold"
    if "china_macro" in theme_keys and any(keyword in text for keyword in ("china", "chinese", "yuan", "pboc", "trade", "tariff", "中国", "人民币", "政策", "关税", "贸易")):
        return "china_macro"
    if "new_energy" in theme_keys and any(keyword in text for keyword in ("ev", "battery", "lithium", "solar", "新能源", "锂电", "光伏")):
        return "new_energy"

    ordered = ["ai_power_base", "energy", "gold", "ai", "china_macro", "new_energy"]
    for item in ordered:
        if item in theme_keys:
            return item
    return theme_keys[0] if theme_keys else ""


def _route_chain_text(theme_key: str) -> str:
    return {
        "energy": "地缘/航道风险 → 原油天然气/运价 → 通胀与成本预期 → A股先传到电力、有色、黄金、油运/航运链。",
        "gold": "美债实际利率/美元/避险情绪 → 黄金定价 → 组合保险仓与资源避险链重估。",
        "china_macro": "中国政策/汇率/风险偏好 → 宽基先修复 → 再传成长风格、港股科技和高弹性主题。",
        "ai": "海外AI龙头/半导体景气/国内算力政策 → 科创AI与半导体先动 → 再传AI主题和成长风格。",
        "ai_power_base": "AI算力需求 → 数据中心用电和绿电约束 → 电网设备/储能/液冷/电源订单 → 再看电力、电网和算力底座候选。",
        "new_energy": "产业价格/订单/政策变化 → 新能源链盈利预期修复 → 再决定是否从观察升级为交易。",
    }.get(theme_key, "新闻主线 → 风险偏好与价格确认 → 再决定是否映射到A股ETF。")


def _route_watch_text(theme_key: str) -> str:
    return {
        "energy": "观察 `能源链`、`航运链` 观察池是否出现连续2-3天新闻和价格共振。",
        "gold": "观察美元、实际利率和金价是否同向确认，而不是只看一篇避险标题。",
        "china_macro": "观察人民币、A股成交额、沪深300/上证是否同步放量确认。",
        "ai": "观察半导体指数、海外AI龙头、国内算力政策与成交量是否共振。",
        "ai_power_base": "观察算电协同政策、数据中心项目、绿电/PPA、电网设备、储能和液冷订单是否形成连续确认。",
        "new_energy": "观察锂价、光伏产业链价格、销量和政策，而不是只看油价联想。",
    }.get(theme_key, "观察价格是否和新闻主线共振。")


def _route_mistake_text(theme_key: str) -> str:
    return {
        "energy": "不要把“油价上涨”直接翻译成“立刻买新能源”；第一反应通常是电力/黄金/有色/航运。",
        "gold": "不要把黄金当主攻仓；它的任务是保险和对冲，不是替代AI去冲收益。",
        "china_macro": "不要只因一条政策标题就去追最拥挤的高弹性主题；宽基通常比主题先受益。",
        "ai": "不要因为单日纳指或海外科技股大涨，就继续叠加同类AI基金。",
        "ai_power_base": "不要把长期算电故事当成今天重仓买入理由；首次只能小底仓，必须等政策、订单和价格确认。",
        "new_energy": "不要把长期替代逻辑当成短期交易信号；新能源更看产业价格和订单周期。",
    }.get(theme_key, "不要把单条新闻直接当成买卖指令。")


def _route_buy_text(
    theme_key: str,
    portfolio: dict[str, Any],
    summary: dict[str, Any],
    candidate_index: dict[str, dict[str, Any]],
    portfolio_quotes: dict[str, Any] | None = None,
) -> str:
    stable_core = _instrument_text(_holding_refs(portfolio, sleeves={"stable_core"}))
    growth_core = _instrument_text(_holding_refs(portfolio, sleeves={"growth_core"}))
    attack_etf = _instrument_text(_holding_refs(portfolio, codes={"588930"}))
    attack_fund = _instrument_text(_holding_refs(portfolio, codes={"011840"}))
    insurance = _instrument_text(_holding_refs(portfolio, sleeves={"insurance"}))
    power = _instrument_text((candidate_index.get("power") or {}).get("instruments"))
    ai_power_base = _instrument_text((candidate_index.get("ai_power_base") or {}).get("instruments"))
    semi = _instrument_text((candidate_index.get("semiconductor") or {}).get("instruments"))
    metals_gold = _instrument_text((candidate_index.get("metals_gold") or {}).get("instruments"))
    dividend = _instrument_text((candidate_index.get("dividend_lowvol") or {}).get("instruments"))
    hk_tech = _instrument_text((candidate_index.get("hk_tech") or {}).get("instruments"))
    direct_ai_pct = _as_float(summary.get("direct_ai_pct"), 0.0)
    direct_ai_cap = _as_float((portfolio.get("risk_controls") or {}).get("direct_ai_cap_pct"), 35.0)
    gold_pct = _as_float(summary.get("gold_pct"), 0.0)
    gold_range = (portfolio.get("risk_controls") or {}).get("gold_target_range_pct") or [10, 15]
    gold_low = _as_float(gold_range[0], 10.0) if gold_range else 10.0
    attack_blockers = _attack_allocation_blockers(portfolio, portfolio_quotes)

    if theme_key == "energy":
        primary = [item for item in [power, metals_gold, dividend] if item and item != "暂无候选"]
        if gold_pct < gold_low and insurance and insurance != "暂无候选":
            primary.insert(1, insurance)
        return "优先看：" + "；其次：".join(primary[:3]) if primary else "优先看电力/黄金/有色方向，但先等价格确认。"
    if theme_key == "gold":
        if gold_pct < gold_low and insurance and insurance != "暂无候选":
            return f"优先补保险仓 {insurance}；场内替代可看 {metals_gold}。"
        return f"黄金仓已不低，更多是持有/观察；若要替代表达可看 {dividend}。"
    if theme_key == "china_macro":
        return f"优先补稳底仓 {stable_core}；风险偏好继续改善时再看 {growth_core}、{dividend}、{hk_tech}。"
    if theme_key == "ai":
        if attack_blockers:
            return f"当前先不新增AI进攻仓；优先处理现有 {attack_etf}、{attack_fund} 的重叠和上限问题，后续再看 {semi}、{hk_tech}。"
        if direct_ai_pct >= direct_ai_cap:
            return f"当前直接AI已接近/超过上限，先持有 {attack_etf}、{attack_fund}，不建议新增同类AI/半导体。"
        return f"若AI仓位仍有空间，优先ETF化表达 {attack_etf}；补充候选看 {semi}，再看 {hk_tech}。"
    if theme_key == "ai_power_base":
        refs = ai_power_base if ai_power_base and ai_power_base != "暂无候选" else power
        return f"优先看长期底座候选 {refs}；首次只允许2%-3%观察底仓，连续确认后才考虑5%-8%，不新增AI进攻仓重叠。"
    if theme_key == "new_energy":
        return "当前不给直接买入优先级；先把它留在观察池，等产业价格和政策一起确认。"
    return "先看现有底仓是否值得加，确认后再看候选ETF池。"


def _route_action_text(theme_key: str, priority: str, summary: dict[str, Any], portfolio: dict[str, Any]) -> str:
    if theme_key == "ai":
        direct_ai_pct = _as_float(summary.get("direct_ai_pct"), 0.0)
        direct_ai_cap = _as_float((portfolio.get("risk_controls") or {}).get("direct_ai_cap_pct"), 35.0)
        if direct_ai_pct >= direct_ai_cap:
            return "观察｜AI主线存在，但你自己的AI暴露已高，动作应从“找机会加”切换成“控制重叠和等更好赔率”。"
    if theme_key == "energy":
        return "观察｜先确认它是否从海外新闻传到A股价格，再决定是否把电力/黄金/有色升到买入候选。"
    if theme_key == "ai_power_base":
        return "观察底仓｜这是1-5年主线，先看绿电/电网/储能/液冷订单；若要动手也只做2%-3%试探仓。"
    if priority == "立即确认":
        return "立即确认｜这条主线已经足够重要，但依旧要等新闻、价格、纪律三项同时满足。"
    if priority == "忽略":
        return "忽略｜和你当前组合直连度低，不值得今天分散注意力。"
    return "观察｜先做跟踪，不急着下结论。"


def _event_route_lines(
    event_impacts: list[dict[str, Any]],
    portfolio: dict[str, Any],
    candidate_scores: list[dict[str, Any]],
    summary: dict[str, Any],
    portfolio_quotes: dict[str, Any] | None = None,
    tracking_summary: dict[str, Any] | None = None,
) -> tuple[list[str], list[dict[str, Any]]]:
    candidate_index = _candidate_score_index(candidate_scores)
    tracking_map = {
        str(item.get("cluster_id") or ""): item
        for item in (tracking_summary or {}).get("tracked_events") or []
        if item.get("cluster_id")
    }
    lines: list[str] = []
    rows: list[dict[str, Any]] = []
    for index, impact in enumerate(event_impacts[:3], start=1):
        theme_key = _primary_theme_key(str(impact.get("title") or ""), list(impact.get("theme_keys") or []))
        tracking = tracking_map.get(str(impact.get("cluster_id") or ""), {})
        continuity = "首次上榜"
        if tracking.get("seen_recently"):
            continuity = f"近7天持续跟踪，历史匹配 {tracking.get('match_count', 0)} 次"
        route = {
            "title": impact.get("title") or "未命名事件",
            "priority": impact.get("priority") or "观察",
            "theme_key": theme_key,
            "continuity": continuity,
            "chain": _route_chain_text(theme_key),
            "buy_text": _route_buy_text(theme_key, portfolio, summary, candidate_index, portfolio_quotes=portfolio_quotes),
            "watch_text": _route_watch_text(theme_key),
            "mistake_text": _route_mistake_text(theme_key),
            "action_text": _route_action_text(theme_key, impact.get("priority") or "观察", summary, portfolio),
        }
        rows.append(route)
        lines.extend(
            [
                f"{index}. **{route['priority']}**｜{route['title']}",
                f"- 连续性：{route['continuity']}。",
                f"- 传导链：{route['chain']}",
                f"- A股/ETF先看谁：{route['buy_text']}",
                f"- 观察信号：{route['watch_text']}",
                f"- 先别误买：{route['mistake_text']}",
                f"- 当前动作：{route['action_text']}",
            ]
        )
    if not lines:
        lines.append("- 今天没有足够强的事件→ETF映射，先按既有仓位纪律执行。")
    return lines, rows


def _annual_objective_lines(portfolio: dict[str, Any]) -> list[str]:
    objective = _annual_objective_payload(portfolio)
    base_text = _fmt_pct_range(objective["base_return_pct_range"])
    stretch_text = _fmt_pct_range(objective["stretch_return_pct_range"])
    max_drawdown = _as_float(objective.get("max_annual_drawdown_pct"), 15.0)
    mode = objective.get("mode") or "range"
    note = objective.get("note") or "年度目标是方向盘，不是单笔交易扳机。"
    priorities = objective.get("priority_order") or ["先控制回撤", "再提高胜率", "最后争取收益"]
    budget = objective.get("return_budget") or {}
    lines = [
        f"- 建议用**两层区间目标**而不是死目标：当前模式 `{mode}`，基础目标先看 {base_text}，行情和纪律都配合时再看冲刺目标 {stretch_text}。",
        f"- 年度最大回撤红线先定为 {_fmt_pct(max_drawdown)}；一旦逼近，优先降波动和降重叠，而不是硬扛。",
        f"- 优先级顺序：{' → '.join(str(item) for item in priorities[:4])}。",
        "- 操作含义：年度收益目标只决定组合节奏，不会因为“还差目标”就强行买入；如果为追收益破坏仓位纪律，说明目标过激。",
        f"- 解释：{note}",
    ]
    rows = budget.get("rows") or []
    if rows:
        lines.extend(
            [
                "",
                "| 模块 | 目标仓位 | 假设年收益 | 对组合贡献 | 角色 |",
                "|---|---:|---:|---:|---|",
            ]
        )
        for row in rows:
            lines.append(
                f"| {row.get('label')} | {_fmt_pct_range(row.get('target_range_pct'))} | "
                f"{_fmt_pct_range(row.get('expected_return_pct_range'))} | "
                f"{_fmt_pct_range(row.get('contribution_pct_range'))} | {row.get('role')} |"
            )
        lines.append(f"- 拆账结论：按目标仓位和默认假设，组合目标贡献约 {_fmt_pct_range(budget.get('estimated_return_contribution_pct_range'))}；{budget.get('note')}")
    return lines


def _range_pair(values: Any, fallback: list[float]) -> list[float]:
    if isinstance(values, (list, tuple)) and values:
        first = _as_float(values[0], fallback[0])
        second = _as_float(values[1], first) if len(values) >= 2 else first
        return [first, second]
    return fallback


def _fmt_pct_range(values: Any) -> str:
    low, high = _range_pair(values, [0.0, 0.0])
    if abs(low - high) < 0.001:
        return _fmt_pct(low)
    return f"{_fmt_pct(low)} ~ {_fmt_pct(high)}"


def _range_mid(values: Any, fallback: list[float]) -> float:
    low, high = _range_pair(values, fallback)
    return round((low + high) / 2, 2)


def _annual_return_budget_payload(portfolio: dict[str, Any]) -> dict[str, Any]:
    allocation = portfolio.get("allocation_framework") or {}
    objective = portfolio.get("annual_objective") or {}
    assumptions = objective.get("return_assumptions_pct") or {}
    rows: list[dict[str, Any]] = []
    configs = [
        ("stable_core", "稳底仓", "stable_core_target_pct", [35.0, 45.0], [5.0, 8.0], "宽基底仓负责长期收益底座，不追热点。"),
        ("growth_core", "成长底仓", "growth_core_target_pct", [15.0, 20.0], [8.0, 14.0], "成长底仓负责弹性，但要承认波动。"),
        ("attack", "进攻仓", "attack_target_pct", [20.0, 30.0], [12.0, 22.0], "进攻仓决定冲刺空间，必须受硬闸门约束。"),
        ("insurance", "保险仓", "insurance_target_pct", [10.0, 15.0], [-2.0, 8.0], "保险仓不追求跑赢，核心任务是降低组合断崖风险。"),
        ("reserve", "机动/缓冲", "reserve_target_pct", [0.0, 10.0], [0.0, 2.0], "机动仓负责等待确认，不为凑收益强行交易。"),
    ]
    low_total = 0.0
    high_total = 0.0
    for key, label, allocation_key, target_fallback, return_fallback, role in configs:
        target_range = _range_pair(allocation.get(allocation_key), target_fallback)
        return_range = _range_pair(assumptions.get(key), return_fallback)
        contribution_low = round(target_range[0] * return_range[0] / 100, 2)
        contribution_high = round(target_range[1] * return_range[1] / 100, 2)
        low_total += contribution_low
        high_total += contribution_high
        rows.append(
            {
                "key": key,
                "label": label,
                "target_range_pct": target_range,
                "target_mid_pct": _range_mid(target_range, target_fallback),
                "expected_return_pct_range": return_range,
                "expected_return_mid_pct": _range_mid(return_range, return_fallback),
                "contribution_pct_range": [contribution_low, contribution_high],
                "contribution_mid_pct": round(_range_mid(target_range, target_fallback) * _range_mid(return_range, return_fallback) / 100, 2),
                "role": role,
            }
        )

    return {
        "rows": rows,
        "estimated_return_contribution_pct_range": [round(low_total, 2), round(high_total, 2)],
        "note": "这是目标拆账，不是收益承诺；用来检查收益目标是否主要靠仓位结构和纪律，而不是靠每天预测。",
    }


def _annual_objective_payload(portfolio: dict[str, Any]) -> dict[str, Any]:
    objective = portfolio.get("annual_objective") or {}
    configured_target = _range_pair(objective.get("target_return_pct_range"), [12.0, 18.0])
    base_range = _range_pair(objective.get("base_return_pct_range"), [8.0, 12.0])
    stretch_range = _range_pair(objective.get("stretch_return_pct_range"), configured_target)
    if "base_return_pct_range" not in objective and configured_target[1] <= 14:
        base_range = configured_target
        stretch_range = _range_pair(objective.get("stretch_return_pct_range"), [12.0, 18.0])

    return {
        "mode": objective.get("mode") or "range",
        "base_return_pct_range": base_range,
        "stretch_return_pct_range": stretch_range,
        "configured_target_return_pct_range": configured_target,
        "max_annual_drawdown_pct": _as_float(objective.get("max_annual_drawdown_pct"), 15.0),
        "priority_order": objective.get("priority_order") or ["先控制回撤", "再提高胜率", "最后争取收益"],
        "note": objective.get("note") or "年度目标是方向盘，不是单笔交易扳机。",
        "discipline": "目标收益不触发单笔交易；只有仓位、价格、流动性和事件验证同时满足时才进入行动窗口。",
        "return_budget": _annual_return_budget_payload(portfolio),
    }


def _playbook_rule_lines(portfolio: dict[str, Any], summary: dict[str, Any]) -> list[str]:
    configured = portfolio.get("playbook_rules") or []
    if configured:
        lines: list[str] = []
        for index, item in enumerate(configured[:10], start=1):
            title = item.get("title") or f"规则{index}"
            trigger = item.get("trigger") or "无"
            action = item.get("action") or "无"
            lines.append(f"{index}. **{title}**：触发条件：{trigger}；动作：{action}。")
        return lines

    direct_ai_cap = _as_float((portfolio.get("risk_controls") or {}).get("direct_ai_cap_pct"), 35.0)
    growth_tech_cap = _as_float((portfolio.get("risk_controls") or {}).get("growth_tech_cap_pct"), 55.0)
    single_attack_cap = _as_float((portfolio.get("risk_controls") or {}).get("single_attack_holding_cap_pct"), 15.0)
    weekly_drawdown = _as_float((portfolio.get("risk_controls") or {}).get("weekly_drawdown_limit_pct"), 8.0)
    gold_range = (portfolio.get("risk_controls") or {}).get("gold_target_range_pct") or [10, 15]
    monthly = _as_float((portfolio.get("profile") or {}).get("monthly_contribution_cny"), 10000.0)
    return [
        "1. **先看主线再动仓**：单条新闻不直接下单，至少要看到“事件 + 价格 + 纪律”三项同时成立。",
        f"2. **直接AI设上限**：直接AI暴露超过 {_fmt_pct(direct_ai_cap)} 时，不再新增同类AI/半导体/港股科技。",
        f"3. **广义成长科技设上限**：成长/科技暴露超过 {_fmt_pct(growth_tech_cap)} 时，新增资金优先回流宽基、红利低波或保险仓。",
        f"4. **单个进攻仓不超上限**：任一进攻仓接近 {_fmt_pct(single_attack_cap)} 就不再加；若 011840 和 588930 同时涨很多，优先考虑先减 011840。",
        f"5. **周回撤先救节奏**：单周回撤到 5% 开始分批低吸底仓；接近 {_fmt_pct(weekly_drawdown)} 时暂停进攻仓，只补稳底仓。",
        f"6. **黄金只做保险**：黄金目标区间是 {_fmt_pct(_as_float(gold_range[0], 10.0))} ~ {_fmt_pct(_as_float(gold_range[1], 15.0))}，不把它当主攻仓。",
        "7. **能源冲击先想传导链**：先看电力/黄金/有色/航运，不把新能源当第一反应。",
        f"8. **月度资金分批投**：每月约 {_fmt_cny(monthly)} 默认分两到三笔，不在单日情绪高潮时一次性打满。",
        "9. **股票只观察不默认分配**：主题先用ETF/基金表达，股票只进观察池，不进入月度默认资金分配。",
        "10. **复盘优先修规则**：每周先复盘哪条规则有效，再决定是否调仓，而不是看完新闻立刻找票。",
    ]


def _hard_risk_gate_payload(portfolio: dict[str, Any]) -> dict[str, Any]:
    controls = portfolio.get("risk_controls") or {}
    gates = controls.get("hard_gates") or {}
    return {
        "max_single_action_pct_of_monthly": _as_float(gates.get("max_single_action_pct_of_monthly"), 40.0),
        "max_monthly_attack_add_pct_of_monthly": _as_float(gates.get("max_monthly_attack_add_pct_of_monthly"), 25.0),
        "max_monthly_action_count": int(_as_float(gates.get("max_monthly_action_count"), 2.0)),
        "confirmation_required_count": int(_as_float(gates.get("confirmation_required_count"), 2.0)),
        "confirmation_window_days": int(_as_float(gates.get("confirmation_window_days"), 7.0)),
        "max_chase_day_pct": _as_float(gates.get("max_chase_day_pct"), 2.5),
    }


def _trade_month_key(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        timestamp = float(raw)
        if timestamp > 10_000_000_000:
            timestamp = timestamp / 1000
        if timestamp > 946684800:
            return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m")
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(raw[:10]).strftime("%Y-%m")
    except ValueError:
        return ""


def _hard_risk_gate_status(
    portfolio: dict[str, Any],
    trade_ledger: dict[str, Any] | None,
    now: datetime | None = None,
) -> dict[str, Any]:
    gates = _hard_risk_gate_payload(portfolio)
    current = now or datetime.now(timezone.utc)
    month_key = current.strftime("%Y-%m")
    monthly = _as_float((portfolio.get("profile") or {}).get("monthly_contribution_cny"), 0.0)
    attack_cap = monthly * gates["max_monthly_attack_add_pct_of_monthly"] / 100 if monthly > 0 else 0.0
    attack_codes = {
        str(item.get("code") or "")
        for item in portfolio.get("holdings") or []
        if str(item.get("sleeve") or "") == "attack" and item.get("code")
    }
    trades = [
        trade
        for trade in (trade_ledger or {}).get("trades") or []
        if _trade_month_key(trade.get("date") or trade.get("created_at_utc") or trade.get("feishu_create_time")) == month_key
    ]
    buy_trades = [trade for trade in trades if str(trade.get("side") or trade.get("type") or "buy").lower() != "sell"]
    attack_buys = [trade for trade in buy_trades if str(trade.get("code") or "") in attack_codes]
    attack_used = sum(_as_float(trade.get("amount_cny")) for trade in attack_buys)
    action_count = len(trades)
    action_limit = int(gates["max_monthly_action_count"])
    return {
        "month": month_key,
        "ledger_enabled": bool((trade_ledger or {}).get("enabled")),
        "action_count": action_count,
        "action_limit": action_limit,
        "action_remaining": max(action_limit - action_count, 0),
        "attack_add_used_cny": round(attack_used, 2),
        "attack_add_limit_cny": round(attack_cap, 2),
        "attack_add_remaining_cny": round(max(attack_cap - attack_used, 0.0), 2),
        "blocks_new_action": action_limit > 0 and action_count >= action_limit,
        "blocks_attack_add": attack_cap > 0 and attack_used >= attack_cap,
    }


def _hard_risk_gate_lines(
    portfolio: dict[str, Any],
    summary: dict[str, Any],
    trade_ledger: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> list[str]:
    del summary
    gates = _hard_risk_gate_payload(portfolio)
    status = _hard_risk_gate_status(portfolio, trade_ledger, now=now)
    monthly = _as_float((portfolio.get("profile") or {}).get("monthly_contribution_cny"), 0.0)
    single_cap = monthly * gates["max_single_action_pct_of_monthly"] / 100 if monthly > 0 else 0.0
    attack_cap = monthly * gates["max_monthly_attack_add_pct_of_monthly"] / 100 if monthly > 0 else 0.0
    single_text = _fmt_cny(single_cap) if single_cap > 0 else f"月新增资金的 {_fmt_pct(gates['max_single_action_pct_of_monthly'])}"
    attack_text = _fmt_cny(attack_cap) if attack_cap > 0 else f"月新增资金的 {_fmt_pct(gates['max_monthly_attack_add_pct_of_monthly'])}"
    return [
        f"- **单次上限**：任何一次手动操作默认不超过 {single_text}；超过就拆到下次周报后再复核。",
        f"- **进攻仓月度上限**：AI/半导体/港股科技等进攻方向每月新增合计不超过 {attack_text}；仓位超线时新增为 0。",
        (
            f"- **本月状态**：{status['month']} 已记录主动调仓 {status['action_count']}/{status['action_limit']} 次；"
            f"进攻仓新增 {_fmt_cny(status['attack_add_used_cny'])}/{_fmt_cny(status['attack_add_limit_cny'])}，"
            f"剩余额度 {_fmt_cny(status['attack_add_remaining_cny'])}。"
            if status["ledger_enabled"]
            else "- **本月状态**：未启用交易账本，系统无法核对本月操作次数和已用额度；默认按硬闸门保守执行。"
        ),
        f"- **连续确认**：新主题至少需要 {gates['confirmation_window_days']} 天内 {gates['confirmation_required_count']} 次确认，确认项可来自新闻、价格、订单、政策或回执复盘。",
        f"- **追高闸门**：候选标的单日涨幅超过 {_fmt_pct(gates['max_chase_day_pct'])} 默认不追，只进入下次复核。",
        f"- **频率闸门**：每月最多 {gates['max_monthly_action_count']} 次主动调仓；没操作就不填回执，系统按未操作继续跟踪。",
    ]


def _decision_cockpit(portfolio: dict[str, Any]) -> dict[str, Any]:
    return portfolio.get("decision_cockpit") or {}


def _fixed_buy_pool(portfolio: dict[str, Any]) -> list[dict[str, Any]]:
    return _merge_by_key(
        list((_decision_cockpit(portfolio).get("fixed_buy_pool") or [])),
        DEFAULT_LONG_TERM_FIXED_BUY_POOL,
        "code",
    )


def _amount_band_text(portfolio: dict[str, Any], key: str) -> str:
    bands = (_decision_cockpit(portfolio).get("action_amount_bands") or {}).get(key) or []
    if len(bands) < 2:
        return "-"
    low = _as_float(bands[0], 0.0)
    high = _as_float(bands[1], 0.0)
    return f"{_fmt_cny(low)} ~ {_fmt_cny(high)}"


def _avg_non_null(values: list[float | None]) -> float | None:
    clean = [value for value in values if value is not None]
    if not clean:
        return None
    return round(sum(clean) / len(clean), 3)


def _instrument_snapshot(
    code: str,
    portfolio_quotes: dict[str, Any] | None,
    execution_checks: dict[str, Any] | None,
) -> dict[str, Any]:
    quote = _quote_map_by_code(portfolio_quotes).get(code, {})
    execution = _execution_map_by_code(execution_checks).get(code, {})
    latest_value = execution.get("latest_price")
    if latest_value is None:
        latest_value = quote.get("estimate_nav") if quote.get("estimate_nav") is not None else quote.get("official_nav")
    change_pct = execution.get("change_pct")
    if change_pct is None:
        change_pct = quote.get("day_change_pct")
    return {
        "code": code,
        "latest_value": latest_value,
        "change_pct": change_pct,
        "turnover_cny": execution.get("turnover_cny"),
        "chase_risk": execution.get("chase_risk") or "未知",
        "liquidity_level": execution.get("liquidity_level") or "未知",
        "premium_discount_pct": execution.get("premium_discount_pct"),
        "quote": quote,
        "execution": execution,
    }


def _benchmark_change_for_theme(theme_key: str, local_market_payload: dict[str, Any] | None) -> float | None:
    payload = local_market_payload or {}
    if theme_key in {"ai_attack", "semiconductor", "growth_core", "power", "ai_power_base"}:
        return _maybe_float(payload.get("broad_change_pct"))
    if theme_key in {"dividend_lowvol", "gold_insurance"}:
        return _maybe_float(payload.get("ai_change_pct"))
    return _maybe_float(payload.get("broad_change_pct"))


def _volume_confirmation(turnover_cny: Any) -> str:
    turnover = _as_float(turnover_cny)
    if turnover <= 0:
        return "未知"
    if turnover >= 100_000_000:
        return "放量"
    if turnover >= 20_000_000:
        return "正常"
    return "不足"


def _pullback_position(change_pct: float | None, chase_risk: str) -> str:
    if chase_risk == "高" or (change_pct is not None and change_pct >= 2.5):
        return "高位追涨"
    if change_pct is not None and change_pct <= -1.0:
        return "回撤观察"
    if change_pct is not None and -1.0 < change_pct < 1.0:
        return "正常区间"
    return "偏热"


def _crowding_level(chase_risk: str, local_market_payload: dict[str, Any] | None) -> str:
    payload = local_market_payload or {}
    phase = str(payload.get("phase") or "")
    risk_avg = _maybe_float(payload.get("risk_avg_pct"))
    high_chase_count = int(payload.get("high_chase_count") or 0)
    if chase_risk == "高" or phase == "主题过热" or high_chase_count >= 2 or (risk_avg is not None and risk_avg >= 1.5):
        return "高"
    if chase_risk == "中" or (risk_avg is not None and risk_avg >= 0.8):
        return "中"
    return "低"


def _market_confirmation(
    *,
    theme_key: str,
    snap: dict[str, Any],
    local_market_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    change_pct = _maybe_float(snap.get("change_pct"))
    benchmark_change = _benchmark_change_for_theme(theme_key, local_market_payload)
    relative_strength = None
    if change_pct is not None and benchmark_change is not None:
        relative_strength = round(change_pct - benchmark_change, 3)

    if relative_strength is None:
        relative_status = "未知"
    elif relative_strength >= 0.7:
        relative_status = "强"
    elif relative_strength <= -0.7:
        relative_status = "弱"
    else:
        relative_status = "中性"

    volume_status = _volume_confirmation(snap.get("turnover_cny"))
    chase_risk = str(snap.get("chase_risk") or "未知")
    pullback = _pullback_position(change_pct, chase_risk)
    crowding = _crowding_level(chase_risk, local_market_payload)

    score = 50
    if relative_status == "强":
        score += 15
    elif relative_status == "弱":
        score -= 15
    if volume_status == "放量":
        score += 12
    elif volume_status == "正常":
        score += 6
    elif volume_status == "不足":
        score -= 12
    if pullback == "回撤观察":
        score += 8
    elif pullback == "高位追涨":
        score -= 18
    if crowding == "高":
        score -= 18
    elif crowding == "中":
        score -= 7

    blockers: list[str] = []
    if pullback == "高位追涨":
        blockers.append("追高位置，不把强势当成马上买")
    if volume_status == "不足":
        blockers.append("成交额不足，价格确认不够硬")
    if crowding == "高":
        blockers.append("资金拥挤偏高，先降级观察")
    if relative_status == "弱":
        blockers.append("相对强弱落后，先等板块确认")

    score = max(0, min(100, score))
    blocks_action = bool(blockers) and score < 60
    text = (
        f"确认 {score}/100｜相对{relative_status}"
        f"｜成交{volume_status}｜{pullback}｜拥挤{crowding}"
    )
    return {
        "score": score,
        "relative_strength_pct": relative_strength,
        "relative_strength_status": relative_status,
        "volume_confirmation": volume_status,
        "pullback_position": pullback,
        "crowding_level": crowding,
        "blocks_action": blocks_action,
        "blockers": blockers,
        "text": text,
    }



def _local_market_panel_lines(
    portfolio: dict[str, Any],
    portfolio_quotes: dict[str, Any] | None,
    execution_checks: dict[str, Any] | None,
) -> tuple[list[str], dict[str, Any]]:
    panel = (_decision_cockpit(portfolio).get("local_market_panel") or {})
    broad = _avg_non_null([
        _instrument_snapshot(code, portfolio_quotes, execution_checks).get("change_pct")
        for code in panel.get("broad_core_codes") or []
    ])
    growth = _avg_non_null([
        _instrument_snapshot(code, portfolio_quotes, execution_checks).get("change_pct")
        for code in panel.get("growth_codes") or []
    ])
    ai = _avg_non_null([
        _instrument_snapshot(code, portfolio_quotes, execution_checks).get("change_pct")
        for code in panel.get("ai_codes") or []
    ])
    defense = _avg_non_null([
        _instrument_snapshot(code, portfolio_quotes, execution_checks).get("change_pct")
        for code in panel.get("defense_codes") or []
    ])
    hk_tech = _avg_non_null([
        _instrument_snapshot(code, portfolio_quotes, execution_checks).get("change_pct")
        for code in panel.get("hk_tech_codes") or []
    ])

    style = "均衡拉锯"
    if ai is not None and broad is not None and ai - broad >= 0.7 and growth is not None and growth < broad:
        style = "AI独强，成长分化"
    elif ai is not None and broad is not None and ai - broad >= 0.7:
        style = "成长/科技占优"
    elif growth is not None and broad is not None and growth - broad >= 0.6:
        style = "成长占优"
    elif defense is not None and ai is not None and defense - ai >= 0.5:
        style = "防御占优"
    elif defense is not None and broad is not None and defense - broad >= 0.4:
        style = "防御偏强"
    elif broad is not None and broad > 0 and (ai or 0) < 0.6 and (growth or 0) < 0.6:
        style = "宽基主导"

    risk_avg = _avg_non_null([growth, ai, hk_tech])
    panel_codes = []
    for key in ("broad_core_codes", "growth_codes", "ai_codes", "defense_codes", "hk_tech_codes"):
        panel_codes.extend(str(code) for code in panel.get(key) or [])
    seen: set[str] = set()
    panel_items: list[dict[str, Any]] = []
    execution_map = _execution_map_by_code(execution_checks)
    for code in panel_codes:
        if code in seen:
            continue
        seen.add(code)
        item = execution_map.get(code)
        if item and item.get("change_pct") is not None:
            panel_items.append(item)

    high_chase_count = sum(1 for item in panel_items if item.get("chase_risk") == "高")
    sentiment = "中性"
    if (risk_avg is not None and risk_avg >= 1.2) or high_chase_count >= 2:
        sentiment = "偏热，容易追高"
    elif (risk_avg is not None and risk_avg <= -0.8) and (defense or 0.0) >= -0.1:
        sentiment = "偏冷，防御相对占优"
    elif (risk_avg is not None and abs(risk_avg) < 0.5) and high_chase_count == 0:
        sentiment = "中性偏可控"

    top_positive = sorted(panel_items, key=lambda item: item.get("change_pct") or 0.0, reverse=True)[:2]
    top_negative = sorted(panel_items, key=lambda item: item.get("change_pct") or 0.0)[:2]
    broad_vs_growth = None if growth is None or broad is None else round(growth - broad, 3)
    defense_vs_ai = None if defense is None or ai is None else round(defense - ai, 3)

    phase = "轮动混沌"
    phase_reason = "宽基、成长、防御之间差距还不够大，先按纪律而不是按情绪追节奏。"
    if (risk_avg is not None and risk_avg >= 1.5) and high_chase_count >= 2:
        phase = "主题过热"
        phase_reason = f"高弹性方向均值 {_fmt_pct_or_unknown(risk_avg)}，追高风险标的 {high_chase_count} 个，比起加仓更需要先压纪律。"
    elif defense is not None and ((ai is not None and defense - ai >= 0.6) or (broad is not None and defense - broad >= 0.45)):
        phase = "防御强"
        phase_reason = f"防御相对AI {(_fmt_pct_or_unknown(defense_vs_ai) if defense_vs_ai is not None else '未知')}，资金更偏向低波动板块。"
    elif ai is not None and broad is not None and ai - broad >= 0.8:
        phase = "成长强"
        phase_reason = f"AI链相对宽基 { _fmt_pct_or_unknown(round(ai - broad, 3)) }，资金在拥挤高弹性方向。"
    elif growth is not None and broad is not None and growth - broad >= 0.5:
        phase = "成长强"
        phase_reason = f"成长相对宽基 { _fmt_pct_or_unknown(broad_vs_growth) }，市场更偏弹性风格。"
    elif broad is not None and growth is not None and broad - growth >= 0.4 and broad > -0.3:
        phase = "宽基强"
        phase_reason = f"宽基相对成长 { _fmt_pct_or_unknown(round(broad - growth, 3)) }，说明资金更像是先回核心资产。"

    lines = [
        f"- 风格阶段：{phase}；{phase_reason}",
        f"- 风格主线：{style}；宽基 {_fmt_pct_or_unknown(broad)} / 成长 {_fmt_pct_or_unknown(growth)} / AI链 {_fmt_pct_or_unknown(ai)} / 防御 {_fmt_pct_or_unknown(defense)}。",
        f"- 情绪温度：{sentiment}；成长相对宽基 { _fmt_pct_or_unknown(broad_vs_growth) if broad_vs_growth is not None else '未知'}，防御相对AI { _fmt_pct_or_unknown(defense_vs_ai) if defense_vs_ai is not None else '未知'}。",
        "- 板块轮动：最强 " + "、".join(f"{item.get('name')}({item.get('code')}) { _fmt_pct(item.get('change_pct') or 0.0) }" for item in top_positive) + "；最弱 " + "、".join(f"{item.get('name')}({item.get('code')}) { _fmt_pct(item.get('change_pct') or 0.0) }" for item in top_negative) + "。" if top_positive and top_negative else "- 板块轮动：样本不足。",
    ]

    if phase == "主题过热":
        lines.append("- 执行提醒：先看你自己的AI上限、只减不加线和单仓纪律，不要把‘最热’误读成‘最该追’。")
    elif phase == "成长强" or style in {"成长/科技占优", "成长占优"}:
        lines.append("- 执行提醒：即使成长在涨，也要先看你自己的AI/成长上限；你的系统重点是分辨‘能不能追’，不是只看‘涨没涨’。")
    elif phase == "防御强" or style in {"防御占优", "防御偏强"}:
        lines.append("- 执行提醒：更适合往稳底仓、红利低波、黄金或电力迁移，不适合继续堆高弹性主题。")
    elif phase == "宽基强":
        lines.append("- 执行提醒：更适合先补宽基底仓，不要把主题板块单日异动当成全市场主线。")
    else:
        lines.append("- 执行提醒：本土风格没有走出单边主线时，优先保留机动性，减少情绪化换仓。")

    payload = {
        "phase": phase,
        "phase_reason": phase_reason,
        "style": style,
        "sentiment": sentiment,
        "broad_change_pct": broad,
        "growth_change_pct": growth,
        "ai_change_pct": ai,
        "defense_change_pct": defense,
        "hk_tech_change_pct": hk_tech,
        "risk_avg_pct": risk_avg,
        "high_chase_count": high_chase_count,
        "broad_vs_growth_pct": broad_vs_growth,
        "defense_vs_ai_pct": defense_vs_ai,
        "top_positive": [{"name": item.get("name"), "code": item.get("code"), "change_pct": item.get("change_pct")} for item in top_positive],
        "top_negative": [{"name": item.get("name"), "code": item.get("code"), "change_pct": item.get("change_pct")} for item in top_negative],
    }
    return lines, payload

def _hard_reduce_candidates(
    portfolio: dict[str, Any],
    summary: dict[str, Any],
    portfolio_quotes: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    config = portfolio.get("hard_reduce_rules") or {}
    preferred_order = [str(code) for code in (config.get("preferred_reduce_order") or [])]
    risk_controls = portfolio.get("risk_controls") or {}
    single_attack_cap = _as_float(risk_controls.get("single_attack_holding_cap_pct"), 15.0)
    only_reduce_pct = _as_float(((risk_controls.get("only_reduce_watchline") or {}).get("unrealized_profit_pct")), 30.0)
    profit_lock_pct = _as_float(((risk_controls.get("profit_lock_watchline") or {}).get("unrealized_profit_pct")), 50.0)
    direct_ai_cap = _as_float(risk_controls.get("direct_ai_cap_pct"), 35.0)
    quote_map = _quote_map(portfolio_quotes)
    holding_profiles = {
        str(item.get("code") or ""): item
        for item in ((portfolio.get("fund_penetration") or {}).get("holding_profiles") or [])
        if item.get("code")
    }
    order_rank = {code: index for index, code in enumerate(preferred_order)}
    rows: list[dict[str, Any]] = []
    for holding in portfolio.get("holdings") or []:
        code = str(holding.get("code") or "")
        if not code or str(holding.get("sleeve") or "") != "attack":
            continue
        quote = quote_map.get(holding.get("name", ""), {})
        weight_pct = _as_float(quote.get("actual_weight_pct"), _as_float(holding.get("weight_pct"), 0.0))
        pnl_pct = quote.get("unrealized_pnl_pct")
        profile = holding_profiles.get(code, {})
        overlap_level = str(profile.get("overlap_level") or "")
        trigger = ""
        amount_key = ""
        reason = ""
        priority = 0
        if pnl_pct is not None and pnl_pct >= profit_lock_pct and overlap_level == "high":
            trigger = "锁盈线"
            amount_key = "reduce_medium_cny"
            reason = f"高重叠AI仓浮盈达到 {profit_lock_pct:.0f}% 以上，适合分批锁盈。"
            priority = 4
        elif weight_pct >= single_attack_cap:
            trigger = "单仓上限"
            amount_key = "reduce_small_cny"
            reason = f"单个进攻仓达到/超过 {single_attack_cap:.0f}% 上限，先减仓而不是再找理由持有。"
            priority = 3
        elif pnl_pct is not None and pnl_pct >= only_reduce_pct and overlap_level == "high":
            trigger = "只减不加线"
            amount_key = "reduce_small_cny"
            reason = f"高重叠AI仓浮盈达到 {only_reduce_pct:.0f}% 以上，原则上进入只减不加。"
            priority = 2
        elif summary.get("direct_ai_pct", 0.0) >= direct_ai_cap and (pnl_pct or 0.0) > 0 and overlap_level == "high":
            trigger = "AI总暴露超线"
            amount_key = "reduce_small_cny"
            reason = f"直接AI总暴露达到/超过 {direct_ai_cap:.0f}%，优先减高重叠盈利仓。"
            priority = 1
        if trigger:
            rows.append(
                {
                    "name": holding.get("name") or code,
                    "code": code,
                    "trigger": trigger,
                    "amount_band": _amount_band_text(portfolio, amount_key),
                    "reason": reason,
                    "priority": priority,
                    "order_rank": order_rank.get(code, 999),
                    "weight_pct": weight_pct,
                    "pnl_pct": pnl_pct,
                }
            )
    return sorted(rows, key=lambda row: (-row.get("priority", 0), row.get("order_rank", 999), -(row.get("pnl_pct") or 0.0)))


def _hard_reduce_rule_lines(portfolio: dict[str, Any], reduce_candidates: list[dict[str, Any]]) -> list[str]:
    config = portfolio.get("hard_reduce_rules") or {}
    note = config.get("note") or "减仓规则未配置。"
    lines = [f"- {note}"]
    rules = config.get("rules") or []
    for index, item in enumerate(rules[:4], start=1):
        lines.append(
            f"{index}. **{item.get('name', f'规则{index}')}**：触发条件：{item.get('trigger', '无')}；动作：{item.get('action', '无')}。"
        )
    if reduce_candidates:
        top = reduce_candidates[0]
        lines.append(
            f"- 当前若执行减仓，优先顺序第一位是 {top.get('name')}({top.get('code')})｜触发：{top.get('trigger')}｜参考金额 {top.get('amount_band')}。"
        )
    return lines


def _opportunity_scorecard(
    *,
    theme_key: str,
    state: str,
    score: int,
    chase_risk: str,
    liquidity_level: str,
    event_theme_keys: set[str],
    candidate_priority: dict[str, str],
    gate_status: dict[str, Any],
) -> dict[str, Any]:
    upside_ranges = {
        "broad_core": [3.0, 8.0],
        "growth_core": [5.0, 12.0],
        "ai_attack": [8.0, 18.0],
        "gold_insurance": [2.0, 8.0],
        "dividend_lowvol": [3.0, 7.0],
        "power": [4.0, 10.0],
        "ai_power_base": [5.0, 12.0],
        "semiconductor": [8.0, 18.0],
    }
    drawdown_map = {
        "broad_core": 6.0,
        "growth_core": 12.0,
        "ai_attack": 16.0,
        "gold_insurance": 7.0,
        "dividend_lowvol": 7.0,
        "power": 9.0,
        "ai_power_base": 10.0,
        "semiconductor": 16.0,
    }
    theme_to_event = {
        "broad_core": "china_macro",
        "growth_core": "china_macro",
        "ai_attack": "ai",
        "gold_insurance": "gold",
        "dividend_lowvol": "china_macro",
        "power": "energy",
        "ai_power_base": "ai_power_base",
        "semiconductor": "ai",
    }
    upside_range = upside_ranges.get(theme_key, [3.0, 8.0])
    max_drawdown = drawdown_map.get(theme_key, 10.0)
    if chase_risk == "高":
        max_drawdown += 2.0
    if liquidity_level == "偏弱":
        max_drawdown += 2.0

    confirmation_required = 2 if theme_key in {"broad_core", "gold_insurance", "dividend_lowvol"} else 3
    confirmation_count = 0
    if state in {"可买", "减仓"}:
        confirmation_count += 1
    if theme_to_event.get(theme_key) in event_theme_keys:
        confirmation_count += 1
    if candidate_priority.get(theme_key) in {"高", "中"}:
        confirmation_count += 1
    if chase_risk != "高":
        confirmation_count += 1
    if liquidity_level not in {"偏弱", "未知"}:
        confirmation_count += 1
    confirmation_count = min(confirmation_count, confirmation_required)

    upside_mid = _range_mid(upside_range, [3.0, 8.0])
    odds_ratio = round(upside_mid / max(max_drawdown, 0.1), 2)
    odds_score = int(round(score + confirmation_count * 6 + odds_ratio * 10 - max_drawdown))
    blockers: list[str] = []
    if chase_risk == "高":
        blockers.append("当天追高风险高")
    if liquidity_level == "偏弱":
        blockers.append("流动性偏弱")
    if gate_status.get("blocks_new_action"):
        blockers.append("本月操作次数已满")
    if theme_key in {"ai_attack", "semiconductor"} and gate_status.get("blocks_attack_add"):
        blockers.append("进攻仓本月新增额度已满")

    if state == "减仓":
        label = "减风险优先"
    elif state == "可买" and confirmation_count >= confirmation_required and not blockers and odds_score >= 65:
        label = "可复核"
    elif state == "可买":
        label = "等确认"
    else:
        label = "只观察"

    return {
        "label": label,
        "odds_score": max(min(odds_score, 100), 0),
        "expected_upside_pct_range": upside_range,
        "max_drawdown_pct": round(max_drawdown, 2),
        "odds_ratio": odds_ratio,
        "confirmation_count": confirmation_count,
        "confirmation_required": confirmation_required,
        "blockers": blockers,
        "text": f"{label}｜确认 {confirmation_count}/{confirmation_required}｜上行假设 {_fmt_pct_range(upside_range)}｜可承受回撤约 {_fmt_pct(max_drawdown)}",
    }


def _evaluate_fixed_buy_pool(
    portfolio: dict[str, Any],
    summary: dict[str, Any],
    portfolio_quotes: dict[str, Any] | None,
    execution_checks: dict[str, Any] | None,
    candidate_scores: list[dict[str, Any]],
    event_route_rows: list[dict[str, Any]],
    local_market_payload: dict[str, Any] | None = None,
    trade_ledger: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    allocation = portfolio.get("allocation_framework") or {}
    holdings_by_code = {str(item.get("code") or ""): item for item in portfolio.get("holdings") or [] if item.get("code")}
    event_theme_keys = {str(item.get("theme_key") or "") for item in event_route_rows if item.get("theme_key")}
    candidate_priority = {str(item.get("theme_key") or ""): str(item.get("priority") or "低") for item in candidate_scores if item.get("theme_key")}
    attack_blockers = _attack_allocation_blockers(portfolio, portfolio_quotes)
    week_change = (portfolio_quotes or {}).get("portfolio_week_change_pct")
    stable_target = allocation.get("stable_core_target_pct") or [35, 45]
    growth_target = allocation.get("growth_core_target_pct") or [15, 20]
    gold_range = (portfolio.get("risk_controls") or {}).get("gold_target_range_pct") or [10, 15]
    gold_low = _as_float(gold_range[0], 10.0)
    gold_high = _as_float(gold_range[1], 15.0)
    direct_ai_cap = _as_float((portfolio.get("risk_controls") or {}).get("direct_ai_cap_pct"), 35.0)
    growth_tech_cap = _as_float((portfolio.get("risk_controls") or {}).get("growth_tech_cap_pct"), 55.0)
    gate_status = _hard_risk_gate_status(portfolio, trade_ledger)
    results: list[dict[str, Any]] = []

    for item in _fixed_buy_pool(portfolio):
        code = str(item.get("code") or "")
        snap = _instrument_snapshot(code, portfolio_quotes, execution_checks)
        holding = holdings_by_code.get(code, {})
        weight, pnl_pct = _holding_weight_and_pnl(holding, portfolio_quotes) if holding else (0.0, None)
        state = "观察"
        amount_key = ""
        score = 40
        reason = item.get("comment") or ""
        action_hint = "等待新闻、价格和纪律共振"
        chase_risk = str(snap.get("chase_risk") or "未知")
        liquidity_level = str(snap.get("liquidity_level") or "未知")

        theme_key = str(item.get("theme_key") or "")
        market_confirmation = _market_confirmation(
            theme_key=theme_key,
            snap=snap,
            local_market_payload=local_market_payload,
        )
        if theme_key == "broad_core":
            if attack_blockers or (week_change is not None and week_change <= -3) or summary.get("stable_core_pct", 0.0) < _as_float(stable_target[0], 35.0):
                state = "可买"
                amount_key = "buy_core_large_cny"
                score = 92
                reason = "进攻仓受限或组合进入回撤档位时，底仓优先级最高。"
                action_hint = "优先低吸，不追涨"
            elif chase_risk == "高":
                state = "观察"
                score = 55
                reason = "底仓是好东西，但当天涨幅偏高时不需要硬追。"
            else:
                state = "观察"
                score = 60
                reason = "底仓始终可关注，但只有在回撤、补短板或进攻仓受限时才升为可复核候选。"
        elif theme_key == "growth_core":
            if summary.get("growth_tech_pct", 0.0) >= growth_tech_cap * 0.92 or chase_risk == "高":
                state = "观察"
                score = 45
                reason = "成长总暴露已不低，且它本身会放大组合波动。"
            elif ("china_macro" in event_theme_keys or "ai" in event_theme_keys) and summary.get("growth_core_pct", 0.0) < _as_float(growth_target[0], 15.0):
                state = "可买"
                amount_key = "buy_core_small_cny"
                score = 72
                reason = "有主线催化且成长底仓低于目标区间时，才进入小幅补仓复核。"
        elif theme_key == "ai_attack":
            if weight >= _as_float((portfolio.get("risk_controls") or {}).get("single_attack_holding_cap_pct"), 15.0) or (pnl_pct or 0.0) >= 30 or attack_blockers:
                state = "减仓"
                amount_key = "reduce_small_cny" if (pnl_pct or 0.0) < 50 else "reduce_medium_cny"
                score = 95
                reason = "你自己的AI仓位纪律已经先于新闻；这时先处理重叠和上限。"
                action_hint = "优先减重叠，不是看涨了再追"
            elif "ai" in event_theme_keys and chase_risk != "高":
                state = "可买"
                amount_key = "buy_probe_cny"
                score = 68
                reason = "只有AI仓位没超线且当天不拥挤时，才考虑小仓试探。"
        elif theme_key == "gold_insurance":
            if summary.get("gold_pct", 0.0) < gold_low:
                state = "可买"
                amount_key = "buy_defense_cny"
                score = 76
                reason = "黄金低于保险仓目标区间，可以补到位。"
            elif ("gold" in event_theme_keys or "energy" in event_theme_keys) and summary.get("gold_pct", 0.0) <= gold_high:
                state = "观察"
                score = 63
                reason = "有避险催化，但你当前黄金已在合理区间，更适合持有/观察。"
        elif theme_key == "dividend_lowvol":
            if summary.get("growth_tech_pct", 0.0) >= growth_tech_cap * 0.9 or candidate_priority.get("dividend_lowvol") == "高":
                state = "可买"
                amount_key = "buy_defense_cny"
                score = 80
                reason = "当成长/AI偏高时，红利低波是最自然的波动缓冲器。"
            else:
                state = "观察"
                score = 58
        elif theme_key == "power":
            if "energy" in event_theme_keys and chase_risk != "高":
                state = "可买"
                amount_key = "buy_probe_cny"
                score = 70
                reason = "能源冲击的第一层通常更先传到电力，而不是新能源。"
            else:
                state = "观察"
                score = 56
        elif theme_key == "ai_power_base":
            if ("ai_power_base" in event_theme_keys or candidate_priority.get("ai_power_base") == "高") and chase_risk != "高":
                state = "可买"
                amount_key = "buy_probe_cny"
                score = 74
                reason = "AI电力底座是1-5年主线，首次只允许2%-3%观察底仓，后续等政策、订单和价格确认再升级。"
                action_hint = "小底仓观察，不追高、不替代AI仓位上限"
            else:
                state = "观察"
                score = 35
                reason = "长期主线值得看，但还没到连续确认；先看绿电、电网、储能、液冷和数据中心电源订单。"
        elif theme_key == "semiconductor":
            if attack_blockers or summary.get("direct_ai_pct", 0.0) >= direct_ai_cap * 0.95:
                state = "观察"
                score = 35
                reason = "逻辑没错，但你当前仓位结构不允许继续往AI上游堆。"
            elif "ai" in event_theme_keys and chase_risk != "高":
                state = "可买"
                amount_key = "buy_probe_cny"
                score = 66
                reason = "AI主线强化时，半导体通常比主题基金更前排，但只作为小仓复核候选。"

        if state == "可买" and local_market_payload and str(local_market_payload.get("style") or "") in {"防御占优", "防御偏强"} and theme_key in {"growth_core", "ai_attack", "semiconductor"}:
            state = "观察"
            score -= 8
            reason = "本土市场当前偏防御，这类高弹性方向更适合先观察。"
        if state == "可买" and chase_risk == "高":
            state = "观察"
            score -= 10
            reason = "当天追高风险偏高，先别把‘候选’误读成‘现在就买’。"
        if state == "可买" and gate_status.get("blocks_new_action"):
            state = "观察"
            score -= 12
            reason = "本月主动调仓次数已到硬闸门，除减风险外不新增操作。"
        if state == "可买" and theme_key in {"ai_attack", "semiconductor"} and gate_status.get("blocks_attack_add"):
            state = "观察"
            score -= 12
            reason = "本月进攻仓新增额度已用完，AI/半导体方向只观察。"
        if state == "可买" and market_confirmation.get("blocks_action"):
            state = "观察"
            score -= 10
            reason = f"行情确认不足：{'；'.join((market_confirmation.get('blockers') or [])[:2])}。"

        opportunity_score = _opportunity_scorecard(
            theme_key=theme_key,
            state=state,
            score=score,
            chase_risk=chase_risk,
            liquidity_level=liquidity_level,
            event_theme_keys=event_theme_keys,
            candidate_priority=candidate_priority,
            gate_status=gate_status,
        )

        results.append(
            {
                "code": code,
                "name": item.get("name") or code,
                "type": item.get("type") or "",
                "role": item.get("role") or "",
                "theme_key": theme_key,
                "state": state,
                "amount_band": _amount_band_text(portfolio, amount_key) if amount_key else "-",
                "reason": reason,
                "action_hint": action_hint,
                "score": score,
                "opportunity_score": opportunity_score,
                "odds_label": opportunity_score.get("label"),
                "odds_score": opportunity_score.get("odds_score"),
                "day_change_pct": snap.get("change_pct"),
                "latest_value": snap.get("latest_value"),
                "premium_discount_pct": snap.get("premium_discount_pct"),
                "liquidity_level": liquidity_level,
                "chase_risk": chase_risk,
                "market_confirmation": market_confirmation,
            }
        )

    return sorted(results, key=lambda row: (row.get("state") == "减仓", row.get("state") == "可买", row.get("score") or 0), reverse=True)


def _fixed_buy_pool_lines(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["- 尚未配置固定候选池。"]
    state_label = {"可买": "可复核", "减仓": "减仓复核"}
    lines = ["| 标的 | 状态 | 行情确认 | 赔率 | 金额档位 | 当日变化 | 角色 | 原因 |", "|---|---|---|---|---|---:|---|---|"]
    for row in rows:
        day_text = _fmt_pct_or_unknown(row.get("day_change_pct"))
        state = str(row.get("state") or "")
        odds = row.get("opportunity_score") or {}
        odds_text = odds.get("text") or row.get("odds_label") or "-"
        confirmation = (row.get("market_confirmation") or {}).get("text") or "-"
        lines.append(
            f"| {row.get('name')}({row.get('code')}) | {state_label.get(state, state)} | {confirmation} | {odds_text} | {row.get('amount_band')} | {day_text} | {row.get('role')} | {row.get('reason')} |"
        )
    return lines


def _action_slot_lines(
    portfolio: dict[str, Any],
    fixed_pool_rows: list[dict[str, Any]],
    reduce_candidates: list[dict[str, Any]],
    portfolio_quotes: dict[str, Any] | None,
) -> list[str]:
    lines: list[str] = []
    broad_buy_rows = [row for row in fixed_pool_rows if row.get("state") == "可买" and row.get("theme_key") == "broad_core"]
    other_buy_rows = [row for row in fixed_pool_rows if row.get("state") == "可买" and row.get("theme_key") != "broad_core"]
    observe_rows = [row for row in fixed_pool_rows if row.get("state") == "观察"]

    if reduce_candidates:
        row = reduce_candidates[0]
        lines.append(f"1. **减仓复核**｜{row.get('name')}({row.get('code')})｜参考金额 {row.get('amount_band')}｜原因：{row.get('reason')}；不是自动卖出。")
    if broad_buy_rows:
        names = "、".join(f"{row.get('name')}({row.get('code')})" for row in broad_buy_rows[:2])
        amount = broad_buy_rows[0].get("amount_band")
        odds = (broad_buy_rows[0].get("opportunity_score") or {}).get("text") or "赔率待确认"
        lines.append(f"{len(lines)+1}. **低吸候选**｜{names}｜单只参考 {amount}｜{odds}｜条件：进攻仓受限或进入回撤档位时，才优先把新增资金给稳底仓。")
    if other_buy_rows:
        row = other_buy_rows[0]
        odds = (row.get("opportunity_score") or {}).get("text") or "赔率待确认"
        lines.append(f"{len(lines)+1}. **候选观察**｜{row.get('name')}({row.get('code')})｜参考金额 {row.get('amount_band')}｜{odds}｜条件：{row.get('reason')}；确认后再手动处理。")

    if len(lines) < 3 and observe_rows:
        row = observe_rows[0]
        odds = (row.get("opportunity_score") or {}).get("text") or "赔率不足"
        lines.append(f"{len(lines)+1}. **观察**｜{row.get('name')}({row.get('code')})｜{odds}｜先看：{row.get('action_hint')}；当前不急着动。")
    if len(lines) < 3:
        week_change = (portfolio_quotes or {}).get("portfolio_week_change_pct")
        lines.append(f"{len(lines)+1}. **默认不动**｜如果组合近一周约 {_fmt_pct_or_unknown(week_change)}，先按既有纪律跑，不因为单条新闻临时加动作。")
    return lines[:3]


def _build_monthly_deployment_plan(
    summary: dict[str, Any],
    portfolio: dict[str, Any],
    portfolio_quotes: dict[str, Any] | None = None,
) -> list[str]:
    allocation = portfolio.get("allocation_framework") or {}
    profile = portfolio.get("profile") or {}
    monthly = _as_float(profile.get("monthly_contribution_cny"), 0.0)
    if monthly <= 0:
        return ["- 未设置每月新增资金，暂不给出分配框架。"]

    stable_target = allocation.get("stable_core_target_pct") or [35, 45]
    growth_target = allocation.get("growth_core_target_pct") or [15, 20]
    attack_target = allocation.get("attack_target_pct") or [20, 30]
    insurance_target = allocation.get("insurance_target_pct") or [10, 15]

    stable = summary.get("stable_core_pct", 0.0)
    growth = summary.get("growth_core_pct", 0.0)
    attack = summary.get("attack_pct", 0.0)
    insurance = summary.get("insurance_pct", 0.0)

    stable_amt = 0.0
    growth_amt = 0.0
    attack_amt = 0.0
    insurance_amt = 0.0
    reserve_amt = 0.0

    max_cash_pct = _as_float((portfolio.get("risk_controls") or {}).get("max_cash_reserve_pct"), 0.0)
    attack_blockers = _attack_allocation_blockers(portfolio, portfolio_quotes)
    insurance_low = _as_float(insurance_target[0])

    if attack > _as_float(attack_target[1]):
        stable_amt = monthly * 0.55
        growth_amt = monthly * 0.20
        insurance_amt = monthly * 0.10 if insurance < insurance_low else monthly * 0.05
        reserve_amt = monthly - stable_amt - growth_amt - insurance_amt
    else:
        stable_amt = monthly * 0.45
        growth_amt = monthly * 0.20 if growth <= _as_float(growth_target[1]) else monthly * 0.10
        attack_amt = monthly * 0.15 if attack < _as_float(attack_target[0]) else monthly * 0.05
        insurance_amt = monthly * 0.10 if insurance < insurance_low else monthly * 0.05
        reserve_amt = monthly - stable_amt - growth_amt - attack_amt - insurance_amt

    if attack_blockers and attack_amt > 0:
        blocked_attack_amt = attack_amt
        attack_amt = 0.0
        insurance_extra = blocked_attack_amt * 0.10 if insurance < insurance_low else 0.0
        insurance_amt += insurance_extra
        stable_amt += (blocked_attack_amt - insurance_extra) * 0.70
        growth_amt += (blocked_attack_amt - insurance_extra) * 0.30

    if max_cash_pct <= 0 and reserve_amt > 0:
        stable_amt += reserve_amt * 0.65
        growth_amt += reserve_amt * 0.35
        reserve_amt = 0.0

    lines = [
        f"- 稳底仓：框架参考 {_fmt_cny(stable_amt)}，对应 `沪深300ETF易方达 + 上证指数ETF富国`；你现在更需要的是稳底仓，不是继续堆高弹性。",
        f"- 成长底仓：框架参考 {_fmt_cny(growth_amt)}，对应 `创业板ETF易方达`；它可以长期拿，但要承认它不是防守仓。",
        f"- 进攻仓：框架参考 {_fmt_cny(attack_amt)}，对应 `天弘AI + 科创AI`；如果AI拥挤度高，就宁可给 0 或很小。",
        f"- 保险仓：框架参考 {_fmt_cny(insurance_amt)}，对应 `华安黄金ETF联接A`；只有在保险仓低于目标区间或地缘风险抬升时才复核。",
        f"- 机动资金：框架参考 {_fmt_cny(max(reserve_amt, 0.0))}；你偏好不主动留现金，所以若没有强信号，机动部分默认回流稳底仓/成长底仓。",
        "- 折中规则：不是留钱等系统猜底，而是没有确认信号时，不强行把新增资金打进进攻仓，默认回流稳底仓/成长底仓。",
    ]
    if attack_blockers:
        lines.append(f"- 当前暂缓新增进攻仓的原因：{'；'.join(attack_blockers[:3])}。")
    return lines


def _stock_policy_lines(portfolio: dict[str, Any]) -> list[str]:
    policy = portfolio.get("stock_policy") or {}
    if not policy:
        return ["- 未配置股票观察规则。"]
    if policy.get("allowed") and not policy.get("monthly_allocation_allowed"):
        return [f"- {policy.get('note') or '股票只做观察，不进入月度资金默认分配。'}"]
    return ["- 股票可进入月度分配；若你后续改变规则，再调整配置。"]


def _holding_weight_and_pnl(
    holding: dict[str, Any],
    portfolio_quotes: dict[str, Any] | None,
) -> tuple[float, float | None]:
    quote = _quote_map(portfolio_quotes).get(holding.get("name", ""), {})
    weight = quote.get("actual_weight_pct")
    if weight is None:
        weight = _as_float(holding.get("weight_pct"))
    return _as_float(weight), quote.get("unrealized_pnl_pct")


def _ai_overlap_lines(
    portfolio: dict[str, Any],
    portfolio_quotes: dict[str, Any] | None,
    summary: dict[str, Any],
) -> list[str]:
    penetration = portfolio.get("fund_penetration") or {}
    profiles = {
        str(item.get("code") or ""): item
        for item in penetration.get("holding_profiles") or []
        if item.get("code")
    }
    reduce_order = penetration.get("preferred_reduce_order") or []
    direct_ai: list[tuple[dict[str, Any], float, float | None]] = []
    related_growth: list[tuple[dict[str, Any], float, float | None]] = []
    for holding in portfolio.get("holdings") or []:
        bucket = holding.get("bucket")
        weight, pnl_pct = _holding_weight_and_pnl(holding, portfolio_quotes)
        if bucket == "ai_direct":
            direct_ai.append((holding, weight, pnl_pct))
        elif bucket == "growth_broad":
            related_growth.append((holding, weight, pnl_pct))

    direct_ai_pct = summary.get("direct_ai_pct", 0.0)
    growth_tech_pct = summary.get("growth_tech_pct", 0.0)
    direct_ai_cap = _as_float((portfolio.get("risk_controls") or {}).get("direct_ai_cap_pct"), 35.0)
    single_cap = _as_float((portfolio.get("risk_controls") or {}).get("single_attack_holding_cap_pct"), 15.0)

    if not direct_ai:
        return ["- 当前没有直接AI进攻仓，暂不需要做AI重叠度判断。"]

    if direct_ai_pct >= direct_ai_cap or len(direct_ai) >= 2:
        level = "高"
        verdict = "两只AI主题已经构成明显重复暴露，新增资金默认不再进同类AI。"
    elif direct_ai_pct >= direct_ai_cap * 0.75:
        level = "中"
        verdict = "AI暴露偏高，新增前需要二次确认催化是否足够强。"
    else:
        level = "低"
        verdict = "AI重叠暂可接受，但仍不建议把半导体、港股科技都当成分散。"

    lines = [
        f"- AI重叠度：{level}；直接AI约 {_fmt_pct(direct_ai_pct)}，广义成长/科技约 {_fmt_pct(growth_tech_pct)}。",
        f"- 结论：{verdict}",
        "| 持仓 | 代码 | 当前权重 | 浮盈亏 | 重叠判断 |",
        "|---|---|---:|---:|---|",
    ]
    for holding, weight, pnl_pct in direct_ai:
        reason = "直接AI进攻仓"
        profile = profiles.get(str(holding.get("code") or ""))
        if profile:
            tags = "、".join(profile.get("look_through_tags") or [])
            if tags:
                reason += f"；穿透标签：{tags}"
        if weight >= single_cap:
            reason += f"；已超过单仓 {_fmt_pct(single_cap)} 纪律"
        elif weight >= single_cap * 0.9:
            reason += f"；接近单仓 {_fmt_pct(single_cap)} 纪律"
        lines.append(
            f"| {holding.get('name')} | {holding.get('code')} | {_fmt_pct(weight)} | {_fmt_pct_or_unknown(pnl_pct)} | {reason} |"
        )
    for holding, weight, pnl_pct in related_growth:
        profile = profiles.get(str(holding.get("code") or ""))
        tags = "、".join(profile.get("look_through_tags") or []) if profile else ""
        extra = f"；穿透标签：{tags}" if tags else ""
        lines.append(
            f"| {holding.get('name')} | {holding.get('code')} | {_fmt_pct(weight)} | {_fmt_pct_or_unknown(pnl_pct)} | 成长底仓，但会放大AI/科技同向波动{extra} |"
        )
    if reduce_order:
        first = reduce_order[0]
        lines.append(
            f"- 分批锁盈顺序：若 `011840` 和 `588930` 都涨很多，优先复核 `{first.get('code')}`；原因：{first.get('reason', '用户偏好和重叠风险更高')}。"
        )
    lines.extend(
        [
            "- 操作含义：如果未来AI继续涨，优先判断是否“锁一部分收益/降重叠”，而不是再加半导体、科创、港股科技。",
            f"- 不成熟点：{penetration.get('note') or '这是基于主题和仓位的重叠判断，不等同于拿到了基金全部底层持仓明细；后续可继续接基金季报持仓做更精确穿透。'}",
        ]
    )
    return lines


def _scenario_amount(monthly: float, stable: float, growth: float, attack: float, insurance: float) -> dict[str, float]:
    return {
        "stable": round(monthly * stable, 2),
        "growth": round(monthly * growth, 2),
        "attack": round(monthly * attack, 2),
        "insurance": round(monthly * insurance, 2),
    }


def _monthly_scenario_lines(
    summary: dict[str, Any],
    portfolio: dict[str, Any],
    portfolio_quotes: dict[str, Any] | None,
) -> list[str]:
    monthly = _as_float((portfolio.get("profile") or {}).get("monthly_contribution_cny"), 0.0)
    if monthly <= 0:
        return ["- 未设置月度新增资金，暂不输出三档方案。"]

    attack_blocked = bool(_attack_allocation_blockers(portfolio, portfolio_quotes)) or summary.get("attack_pct", 0.0) >= 30
    if attack_blocked:
        normal = _scenario_amount(monthly, 0.68, 0.27, 0.00, 0.05)
        normal_note = "AI/进攻仓偏高，正常市场也先不给进攻仓新增。"
    else:
        normal = _scenario_amount(monthly, 0.50, 0.20, 0.15, 0.15)
        normal_note = "只有在进攻仓未触发纪律时，才允许少量进攻资金。"

    drawdown5 = _scenario_amount(monthly, 0.75, 0.15, 0.00, 0.10)
    drawdown8 = _scenario_amount(monthly, 0.85, 0.00, 0.00, 0.15)

    def row(name: str, trigger: str, amounts: dict[str, float], note: str) -> str:
        return (
            f"| {name} | {trigger} | {_fmt_cny(amounts['stable'])} | {_fmt_cny(amounts['growth'])} | "
            f"{_fmt_cny(amounts['attack'])} | {_fmt_cny(amounts['insurance'])} | {note} |"
        )

    return [
        "- 三档方案不是让系统猜最低价，而是把“正常投、跌5%、跌8%”提前写成纪律，避免临时情绪化。",
        "| 场景 | 触发条件 | 稳底仓 | 成长底仓 | 进攻仓 | 保险仓 | 说明 |",
        "|---|---|---:|---:|---:|---:|---|",
        row("正常市场", "未触发单周回撤；按报告确认后手动投", normal, normal_note),
        row("回撤5%", "组合单周回撤约5%，且新闻主线没有系统性恶化", drawdown5, "优先低吸底仓；创业板只小比例补。"),
        row("回撤8%", "组合单周回撤接近你的警戒线8%", drawdown8, "暂停进攻仓；稳底仓内部沪深300和上证指数大致各半。"),
        "- 执行顺序：先看是否触发单仓上限/只减不加，再看回撤档位，最后才看候选ETF池。",
    ]


def _contribution_execution_lines(portfolio: dict[str, Any]) -> list[str]:
    execution = portfolio.get("contribution_execution") or {}
    if not execution:
        return ["- 未配置新增资金分批执行规则。"]

    monthly = _as_float(execution.get("monthly_contribution_cny"), 0.0)
    lines = [
        f"- 每月新增资金约 {_fmt_cny(monthly)}，采用“看报告后手动分批”的方式，不自动交易。",
        "| 场景 | 分几笔 | 执行节奏 |",
        "|---|---|---|",
    ]
    for key, label in (
        ("normal_market", "正常市场"),
        ("drawdown_5_pct", "回撤5%"),
        ("drawdown_8_pct", "回撤8%"),
    ):
        item = execution.get(key) or {}
        batches = item.get("batches") or []
        batch_text = "+".join(f"{_as_float(batch):.0f}%" for batch in batches) if batches else "未配置"
        lines.append(f"| {label} | {batch_text} | {item.get('timing', '按报告确认后手动执行')} |")
    lines.append(f"- 未用完资金规则：{execution.get('unspent_rule', '不长期留现金，后续默认回流稳底仓。')}")
    return lines


def _trade_checklist_lines(
    portfolio: dict[str, Any],
    portfolio_quotes: dict[str, Any] | None,
    candidate_scores: list[dict[str, Any]],
    execution_checks: dict[str, Any] | None = None,
) -> list[str]:
    top_candidates = "、".join(row.get("theme", "") for row in candidate_scores[:3] if row.get("theme")) or "暂无"
    attack_blockers = _attack_allocation_blockers(portfolio, portfolio_quotes)
    lines = [
        "- 这不是买卖指令；只有下面 6 项都确认后，才考虑手动操作。",
        "1. **仓位纪律**：直接AI≤35%、广义成长/科技≤55%、单个进攻仓≤15%；若触发，先不要加同类。",
        "2. **回撤档位**：确认当前属于正常、回撤5%、还是回撤8%，再套用三档资金方案。",
        "3. **重叠检查**：如果候选是半导体/港股科技，先确认它是否只是继续放大AI暴露。",
        "4. **价格确认**：看ETF当天涨跌、成交额、折溢价/场外基金估值时间，避免追高或买到流动性差的标的。",
        "5. **新闻确认**：至少有新闻主线 + 市场价格两个方向共振，不因为单篇标题操作。",
        f"6. **候选优先级**：今天优先观察：{top_candidates}；低优先级只看不动。",
    ]
    if attack_blockers:
        lines.append(f"- 当前阻断项：{'；'.join(attack_blockers[:3])}。")
    weak_liquidity = [item for item in (execution_checks or {}).get("items", []) if item.get("liquidity_level") == "偏弱"]
    high_chase = [item for item in (execution_checks or {}).get("items", []) if item.get("chase_risk") == "高"]
    high_premium = [item for item in (execution_checks or {}).get("items", []) if item.get("premium_risk") == "高"]
    if weak_liquidity:
        lines.append("- 流动性提醒：" + "、".join(f"{item.get('name')}({item.get('code')})" for item in weak_liquidity[:3]) + " 成交额偏弱，买前要看盘口。")
    if high_chase:
        lines.append("- 追高提醒：" + "、".join(f"{item.get('name')}({item.get('code')})" for item in high_chase[:3]) + " 当日涨幅偏高，不适合情绪化追。")
    if high_premium:
        lines.append("- 折溢价提醒：" + "、".join(f"{item.get('name')}({item.get('code')})" for item in high_premium[:3]) + " 估算折溢价偏高，买前必须看盘口/IOPV。")
    lines.append("- 如果要锁盈：优先复核 `011840`，不是因为它一定差，而是你已明确更愿意先减场外AI主题。")
    return lines


def _fund_lookthrough_lines(fund_holdings: dict[str, Any] | None) -> list[str]:
    if not fund_holdings:
        return ["- 暂未获取基金前十大持仓。"]
    coverage = fund_holdings.get("coverage") or {}
    items = fund_holdings.get("items") or []
    overlaps = fund_holdings.get("overlaps") or []
    stock_exposures = fund_holdings.get("stock_exposures") or []
    lines = [
        f"- 前十大持仓穿透覆盖：{coverage.get('returned_holdings', 0)}/{coverage.get('configured_holdings', 0)}；其中带真实组合权重：{coverage.get('weighted_holdings', 0)}；数据源：{fund_holdings.get('provider', '未知')}。",
        "- 组合暴露口径：单只基金/ETF当前组合权重 × 该基金前十大持仓占净值比例；这是季报前十大，不是实时全持仓。",
    ]
    if items:
        dates = sorted({item.get("report_date") for item in items if item.get("report_date")})
        if dates:
            lines.append(f"- 当前基金持仓报告期：{'、'.join(dates[-3:])}；越靠近季报披露日越可信，季末以后会逐渐滞后。")
        cached_items = [item for item in items if item.get("from_cache")]
        if cached_items:
            lines.append(f"- 有 {len(cached_items)} 个标的使用缓存数据，通常不影响季度穿透判断，但不适合当作日内实时持仓。")
    if overlaps:
        lines.extend(["", "| 重复股票 | 出现基金数 | 估算组合暴露 | 基金内占净值合计 | 涉及基金 |", "|---|---:|---:|---:|---|"])
        for row in overlaps[:8]:
            funds = "、".join(
                f"{fund.get('fund_name')}({_fmt_pct_or_unknown(fund.get('portfolio_exposure_pct'))})"
                for fund in row.get("funds", [])[:4]
            )
            lines.append(
                f"| {row.get('stock_name')} `{row.get('stock_code')}` | {len(row.get('funds') or [])} | {_fmt_pct_or_unknown(row.get('portfolio_exposure_pct_sum'))} | {_fmt_pct(row.get('nav_pct_sum') or 0.0)} | {funds} |"
            )
    else:
        lines.append("- 前十大持仓里暂未发现跨基金重复股票；但这不代表底层完全不重叠。")
    if stock_exposures:
        lines.extend(["", "| 最大底层股票暴露 | 估算组合暴露 | 涉及基金 |", "|---|---:|---|"])
        for row in stock_exposures[:6]:
            funds = "、".join(fund.get("fund_name", "") for fund in row.get("funds", [])[:3])
            lines.append(
                f"| {row.get('stock_name')} `{row.get('stock_code')}` | {_fmt_pct_or_unknown(row.get('portfolio_exposure_pct_sum'))} | {funds} |"
            )
        lines.append("- 这张表用来理解“你实际在押哪些底层股票/风格”，不是让你直接去买单只股票。")
    failures = fund_holdings.get("failures") or []
    if failures:
        lines.append(f"- 获取失败 {len(failures)} 项；报告已继续生成，失败项可稍后重试。")
    return lines


def _execution_check_lines(execution_checks: dict[str, Any] | None) -> list[str]:
    if not execution_checks:
        return ["- 暂未获取ETF执行检查数据。"]
    items = execution_checks.get("items") or []
    if not items:
        return ["- ETF执行检查暂无返回数据。"]
    priority = sorted(
        items,
        key=lambda item: (
            item.get("source") != "holding",
            item.get("liquidity_level") == "偏弱",
            item.get("chase_risk") == "高",
        ),
    )
    lines = ["| 标的 | 来源 | 最新价 | 估算净值 | 折溢价 | 涨跌幅 | 成交额 | 流动性 | 追高风险 |", "|---|---|---:|---:|---:|---:|---:|---|---|"]
    for item in priority[:10]:
        turnover = item.get("turnover_cny")
        turnover_text = "未知" if turnover is None else _fmt_cny(turnover)
        source = "持仓" if item.get("source") == "holding" else f"候选/{item.get('theme', '')}"
        price = item.get("latest_price")
        price_text = "未知" if price is None else f"{price:.4f}"
        indicative_nav = item.get("indicative_nav")
        nav_text = "未知" if indicative_nav is None else f"{indicative_nav:.4f}"
        premium_text = _fmt_pct_or_unknown(item.get("premium_discount_pct"))
        lines.append(
            f"| {item.get('name')} `{item.get('code')}` | {source} | {price_text} | {nav_text} | {premium_text} | {_fmt_pct_or_unknown(item.get('change_pct'))} | {turnover_text} | {item.get('liquidity_level', '未知')} | {item.get('chase_risk', '未知')} |"
        )
    lines.append("- 折溢价使用东方财富估算净值/IOPV近似值计算，适合做交易前风险提醒，不等同于交易所最终官方IOPV。")
    return lines


def _trade_ledger_lines(trade_ledger: dict[str, Any] | None) -> list[str]:
    if not trade_ledger or not trade_ledger.get("enabled"):
        return ["- 暂未启用交易记录文件；当前仍以 portfolio.yaml 的成本和份额为主。"]
    positions = trade_ledger.get("positions") or []
    lines = [
        f"- 交易记录文件：`{trade_ledger.get('path')}`；已汇总 {len(positions)} 个标的、{trade_ledger.get('trade_count', 0)} 条交易，并已作为本次持仓成本/份额的主数据。",
        "| 标的 | 代码 | 份额 | 汇总成本 | 平均成本 |",
        "|---|---|---:|---:|---:|",
    ]
    for item in positions:
        avg_cost = item.get("avg_cost")
        avg_text = "未知" if avg_cost is None else f"{avg_cost:.4f}"
        lines.append(f"| {item.get('name')} | `{item.get('code')}` | {item.get('shares')} | {_fmt_cny(item.get('cost_cny') or 0.0)} | {avg_text} |")
    lines.append("- 后续买卖只要往这个文件追加交易记录，系统就能自动汇总；目前不会自动下单。")
    return lines


def _action_board_lines(
    summary: dict[str, Any],
    portfolio: dict[str, Any],
    portfolio_quotes: dict[str, Any] | None,
    candidate_scores: list[dict[str, Any]],
    event_impacts: list[dict[str, Any]],
) -> list[str]:
    risk_controls = portfolio.get("risk_controls") or {}
    drawdown_limit = _as_float(risk_controls.get("weekly_drawdown_limit_pct"), 8.0)
    week_change = (portfolio_quotes or {}).get("portfolio_week_change_pct")
    attack_blockers = _attack_allocation_blockers(portfolio, portfolio_quotes)
    immediate_events = [item for item in event_impacts if item.get("priority") == "立即确认"]
    top_candidate = candidate_scores[0] if candidate_scores else {}

    if week_change is not None and week_change <= -drawdown_limit:
        default_action = "纪律复核：触发单周回撤警戒，先确认是否按回撤8%方案分批补稳底仓，暂停进攻仓；不自动交易。"
    elif attack_blockers:
        default_action = "纪律优先：进攻仓/AI约束优先级最高，新增资金先不要继续加AI、半导体或港股科技。"
    elif immediate_events:
        default_action = "复核观察：有核心事件影响持仓，但先等新闻主线和市场价格共振，不做单条标题交易。"
    else:
        default_action = "默认不动：今天更适合更新认知和候选池，不急着动仓。"

    candidate_text = "暂无高优先候选"
    if top_candidate:
        candidate_text = f"{top_candidate.get('theme')}（优先级 {top_candidate.get('priority', '未知')}，参考 {top_candidate.get('instrument_refs') or '见候选池'}）"

    lines = [
        f"- **今日纪律**：{default_action}",
        f"- **新增资金**：按每月 {_fmt_cny(_as_float((portfolio.get('profile') or {}).get('monthly_contribution_cny'), 0.0))} 的分批框架执行；没有强信号时，不为了把钱投出去而硬买。",
        f"- **候选方向**：{candidate_text}；候选只代表中长期观察优先级，不代表今天买。",
        "- **执行纪律**：先看仓位上限、回撤档位、基金穿透和ETF折溢价，再决定是否手动操作。",
    ]
    if attack_blockers:
        lines.append("- **当前阻断**：" + "；".join(attack_blockers[:3]) + "。")
    return lines


def _sleeve_label(value: str | None) -> str:
    return {
        "stable_core": "稳底仓",
        "growth_core": "成长底仓",
        "attack": "进攻仓",
        "insurance": "保险仓",
    }.get(value or "", "待分类")


def _event_impacts(clusters: list[EventCluster], portfolio: dict[str, Any]) -> list[dict[str, Any]]:
    holdings = portfolio.get("holdings") or []
    impacts: list[dict[str, Any]] = []
    for cluster in clusters:
        matched_theme_keys = _match_event_themes(cluster)
        if not matched_theme_keys:
            text = _text_for_cluster(cluster)
            if any(_keyword_in_text(keyword, text) for keyword in THEME_RULES["gold"]["keywords"]):
                matched_theme_keys = ["gold"]
            elif any(_keyword_in_text(keyword, text) for keyword in THEME_RULES["china_macro"]["keywords"]):
                matched_theme_keys = ["china_macro"]
            else:
                matched_theme_keys = []
        if not matched_theme_keys:
            continue

        exposed_weight = 0.0
        exposed_holdings: list[str] = []
        for holding in holdings:
            holding_text = _holding_themes(holding)
            bucket = str(holding.get("bucket", "")).lower()
            theme_hit = False
            if "ai" in matched_theme_keys and bucket in {"ai_direct", "growth_broad"}:
                theme_hit = True
            if "ai_power_base" in matched_theme_keys and (
                bucket in {"power", "energy", "new_energy"} or "电力" in holding_text or "电网" in holding_text
            ):
                theme_hit = True
            if "gold" in matched_theme_keys and bucket == "gold":
                theme_hit = True
            if "china_macro" in matched_theme_keys and bucket in {"broad_core", "growth_broad"}:
                theme_hit = True
            if "new_energy" in matched_theme_keys and (bucket == "growth_broad" or "新能源" in holding_text):
                theme_hit = True
            if theme_hit:
                exposed_weight += _as_float(holding.get("weight_pct"))
                exposed_holdings.append(holding.get("name", "未知持仓"))

        priority = "观察"
        if exposed_weight >= 30 or cluster.score >= 10:
            priority = "立即确认"
        if exposed_weight < 8 and "energy" in matched_theme_keys:
            priority = "观察"
        if exposed_weight == 0 and not any(key in matched_theme_keys for key in ("energy", "new_energy", "ai_power_base")):
            priority = "忽略"

        impacts.append(
            {
                "title": cluster.representative.title,
                "cluster_id": cluster.cluster_id,
                "score": cluster.score,
                "direction": cluster.direction,
                "certainty": cluster.certainty,
                "themes": [THEME_RULES[key]["label"] for key in matched_theme_keys],
                "theme_keys": matched_theme_keys,
                "exposed_weight_pct": exposed_weight,
                "holdings": exposed_holdings[:4],
                "priority": priority,
            }
        )
    return sorted(impacts, key=lambda item: (item["priority"] == "立即确认", item["exposed_weight_pct"], item["score"]), reverse=True)


def _portfolio_with_quote_weights(portfolio: dict[str, Any], portfolio_quotes: dict[str, Any] | None) -> dict[str, Any]:
    if not portfolio_quotes:
        return portfolio
    weight_by_name = {
        item.get("holding_name"): item.get("actual_weight_pct")
        for item in portfolio_quotes.get("items") or []
        if item.get("holding_name") and item.get("actual_weight_pct") is not None
    }
    if not weight_by_name:
        return portfolio

    updated = dict(portfolio)
    holdings: list[dict[str, Any]] = []
    for holding in portfolio.get("holdings") or []:
        item = dict(holding)
        if item.get("name") in weight_by_name:
            item["weight_pct"] = weight_by_name[item["name"]]
        holdings.append(item)
    updated["holdings"] = holdings
    return updated


def _holding_impacts(portfolio: dict[str, Any], event_impacts: list[dict[str, Any]]) -> list[HoldingImpact]:
    result: list[HoldingImpact] = []
    for holding in portfolio.get("holdings") or []:
        name = holding.get("name", "未知持仓")
        matched = [impact for impact in event_impacts if name in impact.get("holdings", [])]
        theme_labels: list[str] = []
        for impact in matched:
            for label in impact.get("themes", []):
                if label not in theme_labels:
                    theme_labels.append(label)

        weight_pct = _as_float(holding.get("weight_pct"))
        if len(matched) >= 2 or weight_pct >= 18:
            level = "高"
        elif matched:
            level = "中"
        else:
            level = "低"

        bucket = str(holding.get("bucket", "")).lower()
        if bucket == "gold":
            note = "先定义为组合保险，不和AI/成长仓位比收益；主要看美元、美债实际利率和地缘风险。"
        elif bucket == "ai_direct":
            note = "与科创AI/AI主题重叠较高，重点看直接AI总暴露是否超过上限。"
        elif bucket == "growth_broad":
            note = "成长风格放大器，会同时受AI、新能源、医药和风险偏好影响。"
        else:
            note = "作为A股宽基底仓，主要受中国宏观、政策和整体风险偏好影响。"

        result.append(
            HoldingImpact(
                name=name,
                weight_pct=weight_pct,
                role=holding.get("role", ""),
                matched_themes=theme_labels,
                impact_level=level,
                note=note,
            )
        )
    return result


def _watchlist_lines(portfolio: dict[str, Any], event_impacts: list[dict[str, Any]]) -> list[str]:
    event_theme_keys = {key for impact in event_impacts for key in impact.get("theme_keys", [])}
    lines: list[str] = []
    for item in portfolio.get("watchlist") or []:
        theme = item.get("theme", "未命名主题")
        theme_text = str(theme).lower()
        is_relevant = (
            ("能源" in theme and "energy" in event_theme_keys)
            or ("航运" in theme and "energy" in event_theme_keys)
            or ("新能源" in theme and ("energy" in event_theme_keys or "new_energy" in event_theme_keys))
            or ("AI电力底座" in theme and "ai_power_base" in event_theme_keys)
            or ("AI" in theme.upper() and "ai" in event_theme_keys)
            or ("红利" in theme and any(key in event_theme_keys for key in ("gold", "china_macro")))
            or theme_text in event_theme_keys
        )
        prefix = "观察" if is_relevant else "低优先级"
        signals = "、".join(item.get("confirmation_signals") or [])
        lines.append(f"- {prefix}｜{theme}：{item.get('why', '')} 二次确认：{signals}。")
    return lines


def _china_view(clusters: list[EventCluster]) -> list[str]:
    china_related = []
    for cluster in clusters:
        text = _text_for_cluster(cluster)
        if any(keyword in text for keyword in THEME_RULES["china_macro"]["keywords"]):
            china_related.append(cluster.representative.title)
    if china_related:
        return [
            "- 今日中国视角优先看：" + "；".join(china_related[:3]),
            "- 对A股组合而言，重点不是海外新闻本身，而是它是否改变出口、能源成本、人民币、政策预期和风险偏好。",
        ]
    return [
        "- 本次核心事件没有明显中国直接变量；对A股更可能通过全球风险偏好、能源价格和美元流动性间接传导。",
        "- 若后续出现中国官方政策、人民币异动或A股成交放量，再把优先级上调。",
    ]


def build_portfolio_brief(
    portfolio: dict[str, Any],
    clusters: list[EventCluster],
    market_snapshot: dict[str, Any] | None = None,
    tracking_summary: dict[str, Any] | None = None,
    portfolio_quotes: dict[str, Any] | None = None,
    fund_holdings: dict[str, Any] | None = None,
    execution_checks: dict[str, Any] | None = None,
    trade_ledger: dict[str, Any] | None = None,
    fixed_pool_history: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    del market_snapshot
    portfolio_for_weights = _portfolio_with_quote_weights(portfolio, portfolio_quotes)
    summary = _summary_with_quotes(summarize_portfolio(portfolio_for_weights), portfolio_quotes)
    risk_controls = portfolio.get("risk_controls") or {}
    allocation = portfolio.get("allocation_framework") or {}
    profile = portfolio.get("profile") or {}
    direct_ai_cap = _as_float(risk_controls.get("direct_ai_cap_pct"), 35.0)
    growth_tech_cap = _as_float(risk_controls.get("growth_tech_cap_pct"), 55.0)
    gold_range = risk_controls.get("gold_target_range_pct") or [10, 15]
    event_impacts = _event_impacts(clusters, portfolio_for_weights)
    holding_impacts = _holding_impacts(portfolio_for_weights, event_impacts)
    candidate_scores = _score_candidate_pool(portfolio, event_impacts, summary)
    industry_radar = build_industry_radar(portfolio, clusters, event_impacts, candidate_scores)
    industry_radar_lines = render_industry_radar_lines(industry_radar)
    allocation_deviation = _allocation_deviation_panel(summary, portfolio)
    allocation_deviation_lines = _allocation_deviation_lines(allocation_deviation)
    quote_map = _quote_map(portfolio_quotes)
    monthly_plan_lines = _build_monthly_deployment_plan(summary, portfolio, portfolio_quotes)
    drawdown_lines = _drawdown_trigger_lines(portfolio, portfolio_quotes)
    single_attack_cap_lines = _single_attack_cap_lines(portfolio, portfolio_quotes)
    only_reduce_lines = _only_reduce_watch_lines(portfolio, portfolio_quotes)
    profit_lock_lines = _profit_lock_watch_lines(portfolio, portfolio_quotes)
    stock_policy_lines = _stock_policy_lines(portfolio)
    ai_overlap_lines = _ai_overlap_lines(portfolio, portfolio_quotes, summary)
    monthly_scenario_lines = _monthly_scenario_lines(summary, portfolio, portfolio_quotes)
    contribution_execution_lines = _contribution_execution_lines(portfolio)
    trade_checklist_lines = _trade_checklist_lines(portfolio, portfolio_quotes, candidate_scores, execution_checks)
    fund_lookthrough_lines = _fund_lookthrough_lines(fund_holdings)
    execution_check_lines = _execution_check_lines(execution_checks)
    trade_ledger_lines = _trade_ledger_lines(trade_ledger)
    action_board_lines = _action_board_lines(summary, portfolio, portfolio_quotes, candidate_scores, event_impacts)
    candidate_lines = _candidate_pool_lines(portfolio)
    hard_risk_gate_status = _hard_risk_gate_status(portfolio, trade_ledger)
    hard_risk_gate_lines = _hard_risk_gate_lines(portfolio, summary, trade_ledger)
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
        trade_ledger=trade_ledger,
    )
    fixed_buy_pool_lines = _fixed_buy_pool_lines(fixed_buy_pool_rows)
    fixed_pool_history_panel = build_fixed_pool_60d_panel(portfolio, event_route_rows, fixed_pool_history)
    fixed_pool_backfill_lines = fixed_pool_history_panel.get("backfill_lines") or ["- 固定候选池历史回填暂不可用。"]
    fixed_pool_win_lines = fixed_pool_history_panel.get("win_lines") or ["- T+1/T+3/T+5 先手胜率暂不可用。"]
    action_slot_lines = _action_slot_lines(portfolio, fixed_buy_pool_rows, reduce_candidates, portfolio_quotes)
    annual_objective = _annual_objective_payload(portfolio)
    annual_objective_lines = _annual_objective_lines(portfolio)
    playbook_rule_lines = _playbook_rule_lines(portfolio, summary)
    day_change = (portfolio_quotes or {}).get("portfolio_estimated_day_change_pct")
    week_change = (portfolio_quotes or {}).get("portfolio_week_change_pct")
    total_pnl_cny = summary.get("actual_total_pnl_cny")
    total_pnl_pct = summary.get("actual_total_pnl_pct")
    drawdown_limit = _as_float(risk_controls.get("weekly_drawdown_limit_pct"), 8.0)

    total_value = summary["total_value_cny"]
    lines: list[str] = [
        "# 我的组合影响速览",
        "",
        "## 30秒我的组合",
        "",
        f"- 当前组合约 { _fmt_cny(total_value) }，共 {summary['holdings_count']} 个持仓，定位应是“宽基底仓 + AI进攻 + 黄金保险”。",
        f"- 当前浮盈亏约 {_fmt_cny(total_pnl_cny or 0.0)}（{_fmt_pct_or_unknown(total_pnl_pct)}），单周最大可承受回撤暂记为 {_fmt_pct(drawdown_limit)}。" if total_pnl_cny is not None else "- 还没有成本/份额时无法计算真实浮盈亏。",
        f"- 按最新净值/估值估算，组合日内约 {_fmt_pct_or_unknown(day_change)}，近一周约 {_fmt_pct_or_unknown(week_change)}；更适合看方向，不是精确盈亏。" if portfolio_quotes else "- 还没有拿到净值/价格快照时，先按仓位结构做判断。",
        f"- 直接AI暴露 { _fmt_pct(summary['direct_ai_pct']) }，上限暂设 { _fmt_pct(direct_ai_cap) }，状态：{_cap_status(summary['direct_ai_pct'], direct_ai_cap)}；不成熟点是两只AI基金重叠较高。",
        f"- 广义成长/科技暴露约 { _fmt_pct(summary['growth_tech_pct']) }，上限暂设 { _fmt_pct(growth_tech_cap) }，状态：{_cap_status(summary['growth_tech_pct'], growth_tech_cap)}；创业板会放大波动。",
        f"- 黄金 { _fmt_pct(summary['gold_pct']) }，状态：{_gold_status(summary['gold_pct'], gold_range)}；建议先把它当保险仓，不要和AI主题比短期收益。",
        "- 新能源暂时不应因为“替代石油”就直接加权；A股新能源更看产能出清、价格、订单和政策。",
        "",
        "## 组合画像",
        "",
        "| 维度 | 当前比例 | 判断 |",
        "|---|---:|---|",
        f"| A股权益 | {_fmt_pct(summary['china_equity_pct'])} | 权益仓较高，适合中长期配置，但会吃市场波动 |",
        f"| 稳底仓 | {_fmt_pct(summary['stable_core_pct'])} | {_range_status(summary['stable_core_pct'], allocation.get('stable_core_target_pct') or [35,45])}；沪深300 + 上证指数，才是更稳的底仓 |",
        f"| 成长底仓 | {_fmt_pct(summary['growth_core_pct'])} | {_range_status(summary['growth_core_pct'], allocation.get('growth_core_target_pct') or [15,20])}；创业板是核心仓，但不是防守仓 |",
        f"| 进攻仓 | {_fmt_pct(summary['attack_pct'])} | {_range_status(summary['attack_pct'], allocation.get('attack_target_pct') or [20,30])}；两只AI合计偏高，不建议继续无脑加 |",
        f"| 保险仓 | {_fmt_pct(summary['insurance_pct'])} | {_range_status(summary['insurance_pct'], allocation.get('insurance_target_pct') or [10,15])}；黄金负责对冲，不负责冲锋 |",
        "",
        "## 我帮你重新分类",
        "",
        "- **稳底仓**：`沪深300ETF易方达`、`上证指数ETF富国`。",
        "- **成长底仓**：`创业板ETF易方达`。它可以长期拿，但波动不低，不是防守仓。",
        "- **进攻仓**：`天弘中证人工智能主题指数C`、`科创人工智能ETF银华`。",
        "- **保险仓**：`华安黄金ETF联接A`。",
    ]

    lines.extend(["", "## 今日纪律面板", ""])
    lines.extend(action_board_lines)
    lines.extend(["", "## 组合偏离面板", ""])
    lines.extend(allocation_deviation_lines)
    lines.extend(["", "## 行业雷达", ""])
    lines.extend(industry_radar_lines)
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
    lines.extend(["", "## 今天纪律档位", ""])
    lines.extend(action_slot_lines)
    lines.extend(["", "## 今日3大事件→A股/ETF映射", ""])
    lines.extend(event_route_lines)
    lines.extend(["", "## 这类消息历史上先动谁", ""])
    lines.extend(event_history_lines)
    lines.extend(["", "## 年度目标框架", ""])
    lines.extend(annual_objective_lines)
    lines.extend(["", "## 我的10条操作手册", ""])
    lines.extend(playbook_rule_lines)
    lines.extend(["", "## 今日对我影响最大的事件", ""])

    if event_impacts:
        for index, impact in enumerate(event_impacts[:4], start=1):
            holdings = "、".join(impact["holdings"]) if impact["holdings"] else "暂无直接持仓，更多是观察池"
            themes = "、".join(impact["themes"])
            lines.append(
                f"{index}. **{impact['priority']}**｜{impact['title']}｜映射：{themes}｜组合相关仓位约 {_fmt_pct(impact['exposed_weight_pct'])}｜涉及：{holdings}。"
            )
    else:
        lines.append("- 本次新闻对现有组合没有识别到强直接映射，先按全球风险偏好观察。")

    lines.extend(["", "## 净值/价格跟踪", "", "| 持仓 | 分类 | 代码 | 成本 | 最新 | 日变化 | 近一周 | 市值 | 浮盈亏 |", "|---|---|---|---:|---:|---:|---:|---:|---:|"])
    for holding in portfolio.get("holdings") or []:
        quote = quote_map.get(holding.get("name", ""), {})
        latest = quote.get("estimate_nav") if quote.get("estimate_nav") is not None else quote.get("official_nav")
        latest_text = _fmt_nav(latest)
        cost_text = _fmt_nav(quote.get("cost_nav"))
        day_text = "未知" if quote.get("day_change_pct") is None else _fmt_pct(quote.get("day_change_pct") or 0.0)
        week_text = "未知" if quote.get("week_change_pct") is None else _fmt_pct(quote.get("week_change_pct") or 0.0)
        value_text = "未知" if quote.get("estimated_position_value_cny") is None else _fmt_cny(quote.get("estimated_position_value_cny") or 0.0)
        pnl_text = "未知"
        if quote.get("unrealized_pnl_cny") is not None:
            pnl_text = f"{_fmt_cny(quote.get('unrealized_pnl_cny') or 0.0)} / {_fmt_pct_or_unknown(quote.get('unrealized_pnl_pct'))}"
        lines.append(
            f"| {holding.get('name')} | {_sleeve_label(holding.get('sleeve'))} | {holding.get('code') or '未填'} | {cost_text} | {latest_text} | {day_text} | {week_text} | {value_text} | {pnl_text} |"
        )

    lines.extend(["", "## 持仓逐项影响", "", "| 持仓 | 权重 | 角色 | 今日敏感度 | 说明 |", "|---|---:|---|---|---|"])
    for item in holding_impacts:
        themes = "、".join(item.matched_themes) if item.matched_themes else "暂无强映射"
        lines.append(
            f"| {item.name} | {_fmt_pct(item.weight_pct)} | {item.role} | {item.impact_level} | {themes}；{item.note} |"
        )

    lines.extend(
        [
            "",
            "## 行动优先级",
            "",
            "- **立即确认**：直接AI≤35%、广义成长/科技≤55%、单个进攻仓≤15% 这三条纪律是否继续执行；当前两只AI不适合再无脑叠加。",
            f"- **回撤纪律**：如果组合单周回撤接近 {_fmt_pct(drawdown_limit)}，先暂停新增进攻仓，优先复核AI和创业板仓位。",
            "- **观察**：能源/航运/煤炭/电力链是否出现连续3天以上的价格和新闻共振，再考虑是否进入观察池。",
            "- **忽略**：单日油价、单日海外科技股涨跌、单篇媒体标题，不作为中长期组合的直接操作依据。",
            f"- **定投规则**：每月约 {_fmt_cny(_as_float(profile.get('monthly_contribution_cny'), 0.0))} 新增资金优先补低于目标区间的资产；若AI超过上限，新增资金优先流向宽基/防御，而不是继续堆AI。",
            "",
            "## 每月新增资金怎么手动分配",
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
    lines.extend(["", "## 风险硬闸门", ""])
    lines.extend(hard_risk_gate_lines)
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
    lines.extend(["", "## 候选ETF池", ""])
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
            "> 风险提示：这是新闻到组合的影响映射和二次确认清单，不是自动买卖指令；实际操作前仍需结合净值、仓位、回撤承受力和个人资金安排。",
        ]
    )

    data = {
        "profile": profile,
        "summary": summary,
        "risk_controls": risk_controls,
        "event_impacts": event_impacts,
        "holding_impacts": [asdict(item) for item in holding_impacts],
        "candidate_scores": candidate_scores,
        "allocation_deviation": allocation_deviation,
        "allocation_deviation_lines": allocation_deviation_lines,
        "industry_radar": industry_radar,
        "industry_radar_lines": industry_radar_lines,
        "local_market_lines": local_market_lines,
        "local_market_payload": local_market_payload,
        "reduce_candidates": reduce_candidates,
        "hard_reduce_rule_lines": hard_reduce_rule_lines,
        "hard_risk_gate_lines": hard_risk_gate_lines,
        "hard_risk_gate_status": hard_risk_gate_status,
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
        "annual_objective": annual_objective,
        "annual_objective_lines": annual_objective_lines,
        "playbook_rule_lines": playbook_rule_lines,
        "monthly_plan_lines": monthly_plan_lines,
        "monthly_scenario_lines": monthly_scenario_lines,
        "contribution_execution_lines": contribution_execution_lines,
        "trade_checklist_lines": trade_checklist_lines,
        "fund_lookthrough_lines": fund_lookthrough_lines,
        "execution_check_lines": execution_check_lines,
        "trade_ledger_lines": trade_ledger_lines,
        "action_board_lines": action_board_lines,
        "drawdown_lines": drawdown_lines,
        "ai_overlap_lines": ai_overlap_lines,
        "single_attack_cap_lines": single_attack_cap_lines,
        "only_reduce_lines": only_reduce_lines,
        "profit_lock_lines": profit_lock_lines,
        "candidate_lines": candidate_lines,
        "stock_policy_lines": stock_policy_lines,
        "portfolio_quotes": portfolio_quotes or {},
        "fund_holdings": fund_holdings or {},
        "execution_checks": execution_checks or {},
        "trade_ledger": trade_ledger or {},
        "portfolio_path": portfolio.get("_path"),
    }
    return "\n".join(lines).strip() + "\n", data
