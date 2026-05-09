from __future__ import annotations

from typing import Any

from .models import EventCluster


FRAMEWORK_LINES = [
    "先问谁被迫交易：谁要补保证金、谁现金流紧、谁必须卖资产换美元。",
    "再问谁有现金等打折：现金方只需要等，缺钱方才会被迫接受折价。",
    "政策只看传导链：降息、缩表、油价、美元、美债和VIX必须放在一起看。",
    "黄金短跌不等于避险失效：美元荒时，黄金可能先被卖掉换现金。",
    "用途是风险闸门：只决定追不追、等不等、留不留现金，不自动生成买卖。",
]

NEWS_RULES: dict[str, dict[str, Any]] = {
    "policy_shift": {
        "name": "美联储/政策换挡",
        "keywords": (
            "fed",
            "federal reserve",
            "fomc",
            "warsh",
            "powell",
            "rate cut",
            "interest rate",
            "qt",
            "quantitative tightening",
            "balance sheet",
            "liquidity",
            "美联储",
            "降息",
            "缩表",
            "资产负债表",
            "流动性",
        ),
        "weight": 2,
        "read": "政策换挡会改变流动性和估值锚，先看降息和缩表谁先落地。",
        "verify": "看美联储声明、利率期货、美元指数和美债收益率是否同向确认。",
        "invalidate": "政策表述转温和，长端利率、美元和VIX没有继续跟随。",
    },
    "energy_shock": {
        "name": "能源/通道冲击",
        "keywords": (
            "oil",
            "crude",
            "brent",
            "wti",
            "hormuz",
            "opec",
            "energy shock",
            "原油",
            "油价",
            "霍尔木兹",
            "能源",
        ),
        "weight": 2,
        "read": "油价上行会推高美元需求和通胀压力，先看是否压迫小国和高杠杆资产。",
        "verify": "看Brent/WTI、库存、航运通道和美元指数是否继续共振。",
        "invalidate": "油价回落、通道风险缓和，美元指数和通胀预期没有继续上行。",
    },
    "forced_trading": {
        "name": "被迫交易/现金方",
        "keywords": (
            "margin",
            "forced selling",
            "dollar shortage",
            "foreign reserves",
            "gold selling",
            "cash",
            "buffett",
            "berkshire",
            "old money",
            "杠杆",
            "爆仓",
            "补保证金",
            "被迫卖出",
            "外汇储备",
            "抛售黄金",
            "巴菲特",
            "现金",
            "老钱",
        ),
        "weight": 3,
        "read": "这条线关注谁缺现金、谁能等折价；它是风险框架，不是阴谋论结论。",
        "verify": "看美元融资压力、VIX、保证金压力、黄金抛售和权益回撤是否同时出现。",
        "invalidate": "美元资金压力缓和，黄金和权益资产同步企稳，现金荒没有扩散。",
    },
    "ai_capex_pressure": {
        "name": "AI资本开支压力",
        "keywords": (
            "ai capex",
            "capital expenditure",
            "free cash flow",
            "hyperscaler",
            "data center",
            "cloud",
            "valuation",
            "nasdaq",
            "资本开支",
            "自由现金流",
            "云厂商",
            "数据中心",
            "估值",
            "纳斯达克",
        ),
        "weight": 2,
        "read": "AI方向可以长期成立，但高估值叠加现金流压力时，好资产也可能先打折。",
        "verify": "看云厂商资本开支、自由现金流、信用利差和纳指是否一起承压。",
        "invalidate": "业绩和现金流继续兑现，纳指相对强势，信用利差没有扩大。",
    },
}


def _cluster_text(cluster: EventCluster) -> str:
    parts: list[str] = [cluster.theme, " ".join(cluster.tags or [])]
    for article in cluster.articles[:5]:
        parts.extend([article.title, article.summary, article.content, article.category, article.region])
    return " ".join(part for part in parts if part).casefold()


def _fmt_pct(value: Any) -> str:
    try:
        if value is None:
            return "未知"
        return f"{float(value):+.2f}%"
    except (TypeError, ValueError):
        return "未知"


def _change(item: dict[str, Any] | None) -> float | None:
    if not item:
        return None
    try:
        value = item.get("change_pct")
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_by_name(items: list[dict[str, Any]], *names: str) -> dict[str, Any] | None:
    for name in names:
        for item in items:
            if str(item.get("name") or "") == name:
                return item
    return None


def _first_by_group(items: list[dict[str, Any]], group: str) -> dict[str, Any] | None:
    for item in items:
        if item.get("group") == group:
            return item
    return None


def _item_line(item: dict[str, Any] | None) -> str:
    if not item:
        return ""
    return f"{item.get('name') or item.get('symbol')} {_fmt_pct(item.get('change_pct'))} {item.get('movement') or '待确认'}"


def _add_row(
    rows: list[dict[str, Any]],
    key: str,
    name: str,
    fact: str,
    inference: str,
    score: int,
    verify: str,
    invalidate: str,
) -> int:
    if any(row.get("key") == key for row in rows):
        return 0
    rows.append(
        {
            "key": key,
            "name": name,
            "evidence": fact,
            "read": inference,
            "fact": fact,
            "inference": inference,
            "verify": verify,
            "invalidate": invalidate,
            "score": score,
        }
    )
    return score


def _news_rows(clusters: list[EventCluster]) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    score = 0
    combined = " ".join(_cluster_text(cluster) for cluster in clusters[:8])
    for key, rule in NEWS_RULES.items():
        hits = [word for word in rule["keywords"] if str(word).casefold() in combined]
        if not hits:
            continue
        fact = "新闻命中：" + " / ".join(str(word) for word in hits[:4])
        score += _add_row(
            rows,
            key,
            rule["name"],
            fact,
            rule["read"],
            int(rule["weight"]),
            rule["verify"],
            rule["invalidate"],
        )
    return rows, score


def _market_rows(market_snapshot: dict[str, Any] | None) -> tuple[list[dict[str, Any]], int]:
    items = (market_snapshot or {}).get("items") or []
    rows: list[dict[str, Any]] = []
    score = 0
    if not items:
        return rows, score

    oil = _first_by_name(items, "布伦特原油", "WTI原油") or _first_by_group(items, "energy")
    dollar = _first_by_name(items, "美元指数") or _first_by_group(items, "fx")
    yield10 = _first_by_name(items, "美国10Y国债收益率") or _first_by_group(items, "rates")
    vix = _first_by_name(items, "VIX") or _first_by_group(items, "volatility")
    gold = _first_by_name(items, "黄金") or _first_by_group(items, "safe_haven")
    nasdaq = _first_by_name(items, "纳斯达克100期货", "标普500期货") or _first_by_group(items, "equity")

    oil_change = _change(oil)
    dollar_change = _change(dollar)
    yield_change = _change(yield10)
    vix_change = _change(vix)
    gold_change = _change(gold)
    equity_change = _change(nasdaq)

    if oil_change is not None and oil_change >= 1.0:
        fact = "；".join(part for part in [_item_line(oil), _item_line(dollar)] if part)
        score += _add_row(
            rows,
            "oil_dollar_pressure",
            "油价/美元压力",
            fact,
            "油价和美元同步走强时，小国、企业融资和风险资产会先承压。",
            2,
            "看油价、美元指数和通胀预期是否继续同步上行。",
            "油价回落或美元转弱，VIX没有继续放大。",
        )

    if (
        (dollar_change is not None and dollar_change >= 0.35)
        and (vix_change is not None and vix_change >= 2.0)
        and (
            (gold_change is not None and gold_change <= -0.35)
            or (yield_change is not None and yield_change >= 0.35)
        )
    ):
        fact = "；".join(part for part in [_item_line(dollar), _item_line(yield10), _item_line(vix), _item_line(gold)] if part)
        score += _add_row(
            rows,
            "liquidity_squeeze",
            "美元荒/被迫卖出",
            fact,
            "美元、利率和VIX一起上行时，黄金短跌可能是换现金，不一定是避险逻辑失效。",
            3,
            "看DXY、VIX、美债收益率继续上行，黄金和股指是否同步承压。",
            "美元和VIX回落，黄金重新走强，股指企稳。",
        )

    if equity_change is not None and equity_change <= -0.8 and vix_change is not None and vix_change >= 2.0:
        fact = "；".join(part for part in [_item_line(nasdaq), _item_line(vix)] if part)
        score += _add_row(
            rows,
            "equity_deleveraging",
            "美股去杠杆",
            fact,
            "高估值资产放量下跌时，先看去杠杆和保证金压力，不急着抄底。",
            2,
            "看纳指/标普继续下行，VIX和信用利差是否扩大。",
            "股指收复跌幅，VIX回落，成交没有继续放大。",
        )

    return rows, score


def _level(score: int) -> str:
    if score >= 12:
        return "极高"
    if score >= 8:
        return "高"
    if score >= 5:
        return "中"
    return "低"


def _posture(level: str) -> str:
    if level == "极高":
        return "只做风险复核，暂停新增进攻仓，保留现金，等待流动性和价格确认。"
    if level == "高":
        return "暂停新增进攻仓，保留现金，等价格确认。"
    if level == "中":
        return "不追涨，降低单次动作，等美元、VIX、油价和股指至少两项缓和。"
    return "正常观察；该框架只做风险提示，不自动买卖。"


def build_macro_burst_risk(
    clusters: list[EventCluster],
    market_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    news_rows, news_score = _news_rows(clusters)
    market_rows, market_score = _market_rows(market_snapshot)
    rows = news_rows + market_rows
    score = news_score + market_score
    level = _level(score)
    posture = _posture(level)

    if rows:
        summary_lines = [
            f"宏观爆破风险{level}：事实和推测分开看，先确认谁被迫交易、谁有现金等打折、谁承担油价和美元压力。",
            f"当前分数 {score}：{posture}",
            "纪律：必须等验证信号，看到失效条件就降级；不把具体日期、人物或单一观点当成买卖指令。",
        ]
    else:
        summary_lines = [
            "宏观爆破风险低：暂未看到政策换挡、油价、美元、VIX和高估值资产形成共振。",
            "纪律：继续观察，不自动买卖。",
        ]

    return {
        "enabled": True,
        "level": level,
        "score": score,
        "posture": posture,
        "summary_lines": summary_lines,
        "framework_lines": FRAMEWORK_LINES,
        "rows": rows,
        "disclaimer": "宏观爆破风险框架只用于识别流动性和被迫交易压力，不构成投资建议，也不保证收益。",
    }


def _md_cell(value: Any) -> str:
    text = " ".join(str(value or "").split())
    return text.replace("|", "/")


def render_macro_burst_risk_markdown(risk: dict[str, Any]) -> str:
    if not risk:
        return ""
    lines = ["## 宏观爆破风险", ""]
    lines.extend(f"- {line}" for line in risk.get("summary_lines") or [])
    rows = risk.get("rows") or []
    if rows:
        lines.extend(["", "| 风险线 | 事实 | 推测 | 验证 | 失效 |", "|---|---|---|---|---|"])
        for row in rows[:6]:
            lines.append(
                "| "
                f"{_md_cell(row.get('name'))} | "
                f"{_md_cell(row.get('fact') or row.get('evidence'))} | "
                f"{_md_cell(row.get('inference') or row.get('read'))} | "
                f"{_md_cell(row.get('verify'))} | "
                f"{_md_cell(row.get('invalidate'))} |"
            )
    else:
        lines.extend(["", "### 固定框架", ""])
        lines.extend(f"- {line}" for line in risk.get("framework_lines") or FRAMEWORK_LINES)
    disclaimer = risk.get("disclaimer")
    if disclaimer:
        lines.extend(["", f"> {disclaimer}"])
    return "\n".join(lines).strip()
