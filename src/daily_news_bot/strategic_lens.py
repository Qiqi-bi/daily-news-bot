from __future__ import annotations

from typing import Any

from .models import EventCluster


STRATEGIC_RULES: dict[str, dict[str, Any]] = {
    "helium_industrial_gas": {
        "label": "氦气/工业气体",
        "keywords": (
            "helium",
            "industrial gas",
            "noble gas",
            "semiconductor gas",
            "氦气",
            "氦",
            "工业气体",
            "稀有气体",
            "电子特气",
        ),
        "tag_boost": ("technology", "energy", "supply_chain"),
        "question": "这件事是在解决谁的供给约束？",
        "constraint": "先看气源、提纯、长协和半导体客户保供，不先按短期利润故事定性。",
        "game_read": "如果扩产只是为了保住关键产线，它的价值可能是稳定供应和谈判筹码，而不是马上赚大钱。",
        "confirm": "确认气源合同、爬坡进度、客户锁量、进口替代比例，以及相关价格是否连续确认。",
        "portfolio_note": "只把它升级为资源安全观察线；没有价格和订单确认前，不因为概念单独加仓。",
    },
    "rare_earths": {
        "label": "稀土/关键矿产",
        "keywords": (
            "rare earth",
            "critical mineral",
            "neodymium",
            "dysprosium",
            "magnet",
            "稀土",
            "关键矿产",
            "镨钕",
            "镝",
            "磁材",
            "永磁",
        ),
        "tag_boost": ("commodities", "supply_chain", "geopolitics"),
        "question": "谁掌握不可替代的上游筹码？",
        "constraint": "重点不是单日价格，而是谁能稳定供给、限制出口、替代进口或提高议价能力。",
        "game_read": "当资源变成谈判筹码，产业链利润可能从下游制造重新分配到上游控制点。",
        "confirm": "确认政策口径、出口数据、价格指数、下游开工和库存变化。",
        "portfolio_note": "适合作为有色/资源候选线观察；中长期仍要等估值、价格和仓位纪律同时允许。",
    },
    "semiconductor_precursor_gases": {
        "label": "半导体前驱体/电子特气",
        "keywords": (
            "wf6",
            "tungsten hexafluoride",
            "tungsten fluoride",
            "tungsten cvd",
            "chemical vapor deposition",
            "atomic layer deposition",
            "ald",
            "cvd",
            "precursor",
            "specialty gas",
            "electronic gas",
            "high purity gas",
            "etch gas",
            "deposition gas",
            "六氟化钨",
            "六氟化物",
            "氟化钨",
            "钨氟",
            "化学气相沉积",
            "原子层沉积",
            "前驱体",
            "电子特气",
            "高纯气体",
            "沉积气体",
            "刻蚀气体",
        ),
        "tag_boost": ("technology", "semiconductor", "supply_chain", "commodities"),
        "question": "这是关键制程不可替代材料，还是普通化工品？",
        "constraint": "先看高纯产能、客户认证、原料钨/氟、出口管制和库存；小市场也可能有高卡点价值。",
        "game_read": "如果材料成本占比低但停线成本极高，议价权来自不可替代和客户安全库存，而不是总市场规模。",
        "confirm": "确认WF6价格、交期、出口规则、客户长协、产能爬坡、下游3D存储/先进逻辑需求和龙头毛利率。",
        "portfolio_note": "升级为电子特气/半导体材料观察线；只在价格、订单和业绩确认后影响候选池，不因小作文追高。",
    },
    "semiconductor_supply": {
        "label": "半导体供应链",
        "keywords": (
            "semiconductor",
            "chip",
            "wafer",
            "lithography",
            "eda",
            "export control",
            "data center",
            "fab",
            "半导体",
            "芯片",
            "晶圆",
            "光刻",
            "先进制程",
            "出口管制",
            "算力",
            "晶圆厂",
        ),
        "tag_boost": ("technology", "geopolitics", "supply_chain"),
        "question": "这条新闻卡住的是技术、设备、材料还是客户需求？",
        "constraint": "半导体新闻要拆成设备、材料、制造、封测和终端需求，不能一概归为科技利好。",
        "game_read": "真正的筹码是不可替代环节；扩产、补贴和限制出口都可能是在抢时间和保底线。",
        "confirm": "确认订单、CapEx、库存、出口许可、核心设备交付和相关指数走势。",
        "portfolio_note": "对AI/芯片仓位只做复核，不自动加仓；先检查直接AI和科技成长是否已经超上限。",
    },
    "energy_chokepoint": {
        "label": "能源/通道约束",
        "keywords": (
            "oil",
            "crude",
            "brent",
            "wti",
            "lng",
            "gas",
            "opec",
            "hormuz",
            "suez",
            "red sea",
            "pipeline",
            "uranium",
            "原油",
            "布伦特",
            "天然气",
            "液化天然气",
            "欧佩克",
            "霍尔木兹",
            "苏伊士",
            "红海",
            "管道",
            "铀",
        ),
        "tag_boost": ("energy", "geopolitics", "commodities"),
        "question": "这件事改变的是供给、运输通道还是风险溢价？",
        "constraint": "先看油气和航运价格是否确认，再看电力、煤炭、化工、航空和通胀链条。",
        "game_read": "能源不是单纯商品价格，它常常是谈判和制裁的杠杆，价格会先反映供给安全边界。",
        "confirm": "确认WTI/Brent、天然气、运价、库存、OPEC口径和通胀预期是否同向。",
        "portfolio_note": "对你这种中长期组合，先升级能源链观察；不把单日油价波动当成换仓理由。",
    },
    "shipping_chokepoint": {
        "label": "航运/港口通道",
        "keywords": (
            "shipping",
            "freight",
            "port",
            "container",
            "canal",
            "vessel",
            "航运",
            "运价",
            "港口",
            "集运",
            "油运",
            "船舶",
            "运河",
        ),
        "tag_boost": ("energy", "supply_chain", "geopolitics"),
        "question": "通道成本会不会变成全产业链成本？",
        "constraint": "航运新闻要先分清是油运、集运、干散还是港口拥堵，不同资产反应不一样。",
        "game_read": "通道被卡时，谁有可替代路线、船队和保险能力，谁就多一张筹码。",
        "confirm": "确认运价指数、绕航时间、保险费、港口吞吐和能源价格是否同向。",
        "portfolio_note": "作为能源/航运链观察，不直接推导到新能源或科技仓位。",
    },
    "sanctions_currency": {
        "label": "制裁/关税/结算",
        "keywords": (
            "sanction",
            "tariff",
            "export ban",
            "swift",
            "currency",
            "dollar",
            "yuan",
            "trade war",
            "制裁",
            "关税",
            "出口禁令",
            "美元",
            "人民币",
            "结算",
            "贸易战",
        ),
        "tag_boost": ("macro", "geopolitics", "fx"),
        "question": "规则改变后，谁的交易成本上升？",
        "constraint": "制裁和关税本质是改变交易规则，要看替代供应、结算路径和成本转嫁能力。",
        "game_read": "这类新闻的筹码不在标题，而在谁能让对方付出更高成本、谁能更快找到替代方案。",
        "confirm": "确认官方文件、生效日期、豁免条款、汇率、美元指数和相关商品价格。",
        "portfolio_note": "先影响宽基风险偏好和资源链，不直接变成买卖；等政策细则和价格确认。",
    },
}


FRAMEWORK_LINES = [
    "谁被卡：供给、技术、运输、结算或政策许可，到底哪个环节变成瓶颈。",
    "谁拿筹码：扩产、库存、长协、替代路线或出口限制，是否改变谈判能力。",
    "钱在办什么事：是追求利润、保供、换时间，还是给产业链兜底。",
    "价格有没有确认：油气、黄金、美元、利率、VIX和相关ETF是否同步验证。",
    "操作纪律：先升级观察和等待触发，不把叙事直接变成买入/卖出。",
]


def _cluster_text(cluster: EventCluster) -> str:
    parts: list[str] = [cluster.theme, " ".join(cluster.tags or [])]
    for article in cluster.articles[:5]:
        parts.extend([article.title, article.summary, article.content, article.category, article.region])
    return " ".join(part for part in parts if part).casefold()


def _keyword_hit(keyword: str, text: str) -> bool:
    return keyword.casefold() in text


def _rule_score(rule: dict[str, Any], text: str, tags: set[str]) -> int:
    keyword_score = sum(2 for keyword in rule.get("keywords", ()) if _keyword_hit(str(keyword), text))
    tag_score = sum(1 for tag in rule.get("tag_boost", ()) if str(tag) in tags)
    return keyword_score + tag_score


def _best_rule(cluster: EventCluster) -> tuple[str, dict[str, Any], int] | None:
    text = _cluster_text(cluster)
    tags = {str(tag).casefold() for tag in cluster.tags or []}
    best_key = ""
    best_rule: dict[str, Any] = {}
    best_score = 0
    for key, rule in STRATEGIC_RULES.items():
        score = _rule_score(rule, text, tags)
        if score > best_score:
            best_key = key
            best_rule = rule
            best_score = score
    if best_score < 2:
        return None
    return best_key, best_rule, best_score


def _fmt_pct(value: Any) -> str:
    try:
        if value is None:
            return "未知"
        return f"{float(value):+.2f}%"
    except (TypeError, ValueError):
        return "未知"


def _md_cell(value: Any) -> str:
    text = " ".join(str(value or "").split())
    return text.replace("|", "/")


def _market_check(theme_key: str, market_snapshot: dict[str, Any] | None) -> str:
    items = (market_snapshot or {}).get("items") or []
    if not items:
        return "本次没有行情快照，先不做价格确认。"

    groups_by_theme = {
        "helium_industrial_gas": {"equity", "fx", "safe_haven"},
        "rare_earths": {"safe_haven", "fx", "equity"},
        "semiconductor_precursor_gases": {"equity", "fx", "rates", "volatility"},
        "semiconductor_supply": {"equity", "fx", "rates", "volatility"},
        "energy_chokepoint": {"energy", "safe_haven", "fx", "rates", "volatility"},
        "shipping_chokepoint": {"energy", "fx", "volatility"},
        "sanctions_currency": {"fx", "safe_haven", "rates", "energy", "volatility"},
    }
    groups = groups_by_theme.get(theme_key, {"energy", "safe_haven", "fx", "rates", "volatility"})
    picked = [item for item in items if item.get("group") in groups][:4]
    if not picked:
        picked = items[:3]

    parts = []
    for item in picked:
        parts.append(f"{item.get('name') or item.get('symbol')} {_fmt_pct(item.get('change_pct'))} {item.get('movement') or '未知'}")
    return "价格确认看：" + "；".join(parts) + "。"


def build_strategic_lens(
    clusters: list[EventCluster],
    market_snapshot: dict[str, Any] | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    candidates: list[tuple[float, dict[str, Any]]] = []
    seen_clusters: set[str] = set()
    for cluster in clusters:
        if cluster.cluster_id in seen_clusters:
            continue
        best = _best_rule(cluster)
        if not best:
            continue
        theme_key, rule, score = best
        representative = cluster.representative
        row = {
            "cluster_id": cluster.cluster_id,
            "title": representative.title,
            "theme_key": theme_key,
            "theme_label": rule["label"],
            "score": score,
            "question": rule["question"],
            "constraint": rule["constraint"],
            "game_read": rule["game_read"],
            "confirm": rule["confirm"],
            "portfolio_note": rule["portfolio_note"],
            "price_check": _market_check(theme_key, market_snapshot),
            "direction": cluster.direction,
            "certainty": cluster.certainty,
            "credibility_label": cluster.credibility_label,
            "confirmed_source_count": cluster.confirmed_source_count,
        }
        priority_score = float(score) * 10 + float(cluster.score or 0)
        candidates.append((priority_score, row))
        seen_clusters.add(cluster.cluster_id)
    candidates.sort(key=lambda item: item[0], reverse=True)

    rows: list[dict[str, Any]] = []
    theme_counts: dict[str, int] = {}
    for _, row in candidates:
        theme_key = str(row.get("theme_key") or "")
        current_count = theme_counts.get(theme_key, 0)
        if current_count >= 2:
            continue
        rows.append(row)
        theme_counts[theme_key] = current_count + 1
        if len(rows) >= limit:
            break

    if rows:
        summary_lines = [
            f"今天识别到 {len(rows)} 条资源/产业约束线，先看它们是否改变供给、通道、技术或结算筹码。",
            f"最先看：{rows[0]['theme_label']}｜{rows[0]['question']}",
            "固定五问：谁被卡、谁拿筹码、钱在办什么事、价格有没有确认、是否触发你的纪律。",
            "中长期纪律：这只是研究框架，先升级观察和确认条件，不自动给买卖指令。",
        ]
    else:
        summary_lines = [
            "今天没有识别到很强的资源/产业约束线；仍可用三问法检查前几条核心事件。",
            "三问法：谁被卡、谁拿筹码、钱在让谁完成什么任务。",
            "没有价格、政策或订单确认时，只记录观察，不做动作。",
        ]

    return {
        "enabled": True,
        "match_count": len(rows),
        "summary_lines": summary_lines,
        "framework_lines": FRAMEWORK_LINES,
        "rows": rows,
        "disclaimer": "资源博弈视角用于理解产业约束和筹码变化，不构成投资建议，也不保证盈利。",
    }


def render_strategic_lens_markdown(lens: dict[str, Any]) -> str:
    if not lens:
        return ""
    lines = ["## 资源博弈视角", ""]
    lines.extend(f"- {line}" for line in lens.get("summary_lines") or [])
    rows = lens.get("rows") or []
    if rows:
        lines.extend(
            [
                "",
                "| 事件 | 视角 | 先问什么 | 价格确认 | 组合纪律 |",
                "|---|---|---|---|---|",
            ]
        )
        for row in rows[:5]:
            lines.append(
                "| "
                f"{_md_cell(row.get('title', '未命名事件'))} | "
                f"{_md_cell(row.get('theme_label', '资源约束'))} | "
                f"{_md_cell(str(row.get('question', '')) + ' ' + str(row.get('game_read', '')))} | "
                f"{_md_cell(row.get('price_check', ''))} | "
                f"{_md_cell(row.get('portfolio_note', ''))} |"
            )
    else:
        lines.extend(["", "### 三问框架", ""])
        lines.extend(f"- {line}" for line in lens.get("framework_lines") or FRAMEWORK_LINES)

    disclaimer = lens.get("disclaimer")
    if disclaimer:
        lines.extend(["", f"> {disclaimer}"])
    return "\n".join(lines).strip()
