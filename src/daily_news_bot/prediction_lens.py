from __future__ import annotations

from typing import Any

from .models import EventCluster


PREDICTION_RULES: dict[str, dict[str, Any]] = {
    "green_compute_wind": {
        "label": "绿电算力：风电相对光伏",
        "keywords": (
            "data center",
            "ai data center",
            "compute",
            "computing power",
            "green power",
            "renewable power",
            "wind power",
            "solar",
            "photovoltaic",
            "grid",
            "energy storage",
            "inner mongolia",
            "qinghai",
            "ningxia",
            "算力中心",
            "算力",
            "绿电",
            "绿色能源",
            "风电",
            "风机",
            "光伏",
            "源网荷储",
            "电网",
            "储能",
            "内蒙古",
            "青海",
            "宁夏",
            "西北",
        ),
        "tags": ("technology", "energy", "supply_chain"),
        "prediction": "如果算力中心新增负荷继续绑定高比例绿电，风电、电网和储能可能比单纯光伏更先反应。",
        "why": "算力负荷需要稳定电力，风电在部分北方/西北场景具备夜间出力优势；真正的约束是电源、并网、负荷和储能能否闭环。",
        "window": "2-8周",
        "verify": "看数据中心审批/投产、绿电PPA、风电利用小时、电网设备订单、储能配置和风电相对光伏的价格强弱。",
        "invalidate": "如果新增算力项目放缓、并网/消纳受限，或光伏+储能成本明显胜出，这条线降级。",
        "discipline": "只做左侧预警；等项目、订单和相对强弱确认，不因为“绿电”二字直接追高。",
    },
    "currency_anti_involution_pricing": {
        "label": "汇率+反内卷：涨价权",
        "keywords": (
            "yuan",
            "renminbi",
            "currency",
            "tariff",
            "trade war",
            "export",
            "vietnam",
            "india",
            "indonesia",
            "textile",
            "fertilizer",
            "solar panel",
            "overcapacity",
            "anti-involution",
            "人民币",
            "汇率",
            "升值",
            "关税",
            "出口",
            "越南",
            "印度",
            "印尼",
            "纺织",
            "化肥",
            "光伏",
            "产能",
            "反内卷",
            "低价倾销",
            "涨价",
        ),
        "tags": ("macro", "geopolitics", "fx", "policy"),
        "prediction": "如果外部竞争对手被关税/成本打掉，同时国内反内卷约束低价倾销，部分中国优势行业可能获得涨价权。",
        "why": "本币升值不一定只压出口；当外部对手退出、进口成本下降、内部产能纪律加强时，企业可能从拼价格转向修复利润。",
        "window": "1-3个月",
        "verify": "看人民币、油价/原料进口成本、出口报价、行业协会/政策反内卷文件、PPI和龙头毛利率。",
        "invalidate": "如果外部竞争仍强、国内继续低价抢单，或人民币升值直接压缩订单，这条线降级。",
        "discipline": "优先找行业级利润修复证据，不把汇率单因子当买入理由。",
    },
    "policy_capped_industry": {
        "label": "政策压价/格局行业",
        "keywords": (
            "price cap",
            "price control",
            "export ban",
            "subsidy",
            "regulated price",
            "fertilizer",
            "pesticide",
            "grain",
            "food",
            "oil product",
            "gasoline",
            "diesel",
            "价格管制",
            "限价",
            "不能出口",
            "出口限制",
            "补贴",
            "化肥",
            "农药",
            "粮食",
            "成品油",
            "汽油",
            "柴油",
            "民生",
            "保供",
        ),
        "tags": ("policy", "commodities", "energy", "macro"),
        "prediction": "有些行业看起来成本上涨、海外涨价，但利润可能被政策压价或保供任务吃掉。",
        "why": "当行业承担民生、农业、运输或保供任务时，价格传导不一定完整；商品涨价不等于相关资产一定受益。",
        "window": "立即-1个季度",
        "verify": "看官方定价/限价、出口限制、补贴兑现、库存、企业毛利率和现金流。",
        "invalidate": "如果政策允许涨价、补贴覆盖成本，或出口限制解除，行业利润弹性重新上修。",
        "discipline": "这是负面过滤器：先排除“该涨但不能涨”的行业，避免被表面涨价误导。",
    },
    "system_cost_saver_tech": {
        "label": "系统降本技术重估",
        "keywords": (
            "hollow core fiber",
            "optical fiber",
            "photonics",
            "cpo",
            "ocs",
            "optical switching",
            "tpu",
            "gpu",
            "memory",
            "bandwidth",
            "latency",
            "cooling",
            "power consumption",
            "空心光纤",
            "光纤",
            "光模块",
            "光通信",
            "光路由",
            "光交换",
            "共封装",
            "存储",
            "带宽",
            "延迟",
            "散热",
            "能耗",
            "省钱",
            "降本",
        ),
        "tags": ("technology", "ai", "semiconductor"),
        "prediction": "如果一项技术能降低整个算力系统的存储、散热、能耗或时延约束，市场可能重新给它估值。",
        "why": "关键不在单点性能提升，而在它是否让整套系统少用更贵的部件、提高吞吐或降低能耗。",
        "window": "1-6个月",
        "verify": "看大客户采用、订单/现货扫货、毛利率、供给稀缺性、与存储/光模块/算力链的相对强弱。",
        "invalidate": "如果只停留在样品/概念，没有量产订单或系统级降本证据，这条线降级。",
        "discipline": "只把它放进重估候选；等订单和相对强弱，不因技术故事恐高或追高。",
    },
    "wf6_precursor_chokepoint": {
        "label": "六氟化钨/WF6：半导体前驱体卡点",
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
            "3d存储",
            "三维存储",
        ),
        "tags": ("technology", "semiconductor", "supply_chain", "commodities"),
        "prediction": "如果WF6高纯产能、出口规则和先进存储/逻辑需求同时收紧，电子特气可能从小品种变成半导体卡点主线。",
        "why": "它的总市场规模不大，但若不可替代且停线成本远高于材料成本，价格上行和长协重定价会更容易传导给下游。",
        "window": "1-6个月",
        "verify": "看WF6报价和交期、钨/氟原料、出口管制、客户认证、长协价格、库存周数、龙头产能爬坡和毛利率。",
        "invalidate": "如果客户库存充足、替代工艺可行、海外产能快速补上，或新增产能无需认证直接放量，这条线降级。",
        "discipline": "只把它放入电子特气/半导体材料观察；至少等价格、订单、毛利率或客户认证两项确认。",
    },
    "right_side_crowding": {
        "label": "右侧拥挤/普通人劣势",
        "keywords": (
            "right side",
            "certainty",
            "crowded",
            "positioning",
            "leverage",
            "real estate",
            "housing",
            "property",
            "右侧",
            "确定性",
            "拥挤",
            "杠杆",
            "房地产",
            "楼市",
            "限购",
            "首付",
            "核心资产",
        ),
        "tags": ("markets", "macro", "policy"),
        "prediction": "当好消息已经变成大众确定性，普通投资者通常很难拿到真正便宜的筹码。",
        "why": "资金、信息和准入有层级；等所有人都看见右侧，优势资金可能已经完成抢筹或抬价。",
        "window": "立即",
        "verify": "看成交放量、估值分位、融资/杠杆、情绪指标、政策放松后是否被快速抢筹。",
        "invalidate": "如果价格仍低、成交未放量、政策还未被充分交易，仍可保持观察。",
        "discipline": "这是追高刹车：系统应提前建观察线，右侧确认后只做纪律复核，不盲目补仓。",
    },
}


FRAMEWORK_LINES = [
    "左侧线索：先找约束变化，不等所有人都确认后再追。",
    "预测对象：只预测可能发酵的主线和验证条件，不预测必涨必跌。",
    "验证顺序：政策/订单/产能/价格/相对强弱，至少两项同向才升级。",
    "失效条件：如果核心约束被解除，或价格不确认，就降级观察。",
    "组合纪律：预测卡片只提醒你看什么，不直接替你买卖。",
]


def _cluster_text(cluster: EventCluster) -> str:
    parts: list[str] = [cluster.theme, " ".join(cluster.tags or [])]
    for article in cluster.articles[:5]:
        parts.extend([article.title, article.summary, article.content, article.category, article.region])
    return " ".join(part for part in parts if part).casefold()


def _rule_score(rule: dict[str, Any], text: str, tags: set[str]) -> int:
    keyword_score = sum(2 for keyword in rule.get("keywords", ()) if str(keyword).casefold() in text)
    tag_score = sum(1 for tag in rule.get("tags", ()) if str(tag).casefold() in tags)
    return keyword_score + tag_score


def _confidence(score: int, cluster: EventCluster) -> str:
    if score >= 7 and (cluster.credibility_label == "高" or cluster.confirmed_source_count >= 3):
        return "高"
    if score >= 4 and (cluster.credibility_label in {"高", "中"} or cluster.confirmed_source_count >= 2):
        return "中"
    return "低"


def _best_rule(cluster: EventCluster) -> tuple[str, dict[str, Any], int] | None:
    text = _cluster_text(cluster)
    tags = {str(tag).casefold() for tag in cluster.tags or []}
    best_key = ""
    best_rule: dict[str, Any] = {}
    best_score = 0
    for key, rule in PREDICTION_RULES.items():
        score = _rule_score(rule, text, tags)
        if score > best_score:
            best_key = key
            best_rule = rule
            best_score = score
    if best_score < 3:
        return None
    return best_key, best_rule, best_score


def _fmt_pct(value: Any) -> str:
    try:
        if value is None:
            return "未知"
        return f"{float(value):+.2f}%"
    except (TypeError, ValueError):
        return "未知"


def _market_line(rule_key: str, market_snapshot: dict[str, Any] | None) -> str:
    items = (market_snapshot or {}).get("items") or []
    if not items:
        return "本次没有行情快照，不能做价格确认。"
    groups_by_rule = {
        "green_compute_wind": {"equity", "energy", "rates"},
        "currency_anti_involution_pricing": {"fx", "energy", "safe_haven"},
        "policy_capped_industry": {"energy", "fx", "rates"},
        "system_cost_saver_tech": {"equity", "rates", "volatility", "fx"},
        "wf6_precursor_chokepoint": {"equity", "rates", "volatility", "fx"},
        "right_side_crowding": {"equity", "rates", "volatility"},
    }
    groups = groups_by_rule.get(rule_key, {"equity", "fx", "rates", "volatility"})
    picked = [item for item in items if item.get("group") in groups][:4] or items[:4]
    parts = [
        f"{item.get('name') or item.get('symbol')} {_fmt_pct(item.get('change_pct'))} {item.get('movement') or '未知'}"
        for item in picked
    ]
    return "价格验证：" + "；".join(parts) + "。"


def _md_cell(value: Any) -> str:
    text = " ".join(str(value or "").split())
    return text.replace("|", "/")


def build_prediction_lens(
    clusters: list[EventCluster],
    market_snapshot: dict[str, Any] | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    candidates: list[tuple[float, dict[str, Any]]] = []
    for cluster in clusters:
        best = _best_rule(cluster)
        if not best:
            continue
        rule_key, rule, score = best
        representative = cluster.representative
        confidence = _confidence(score, cluster)
        card = {
            "cluster_id": cluster.cluster_id,
            "title": representative.title,
            "rule_key": rule_key,
            "label": rule["label"],
            "score": score,
            "confidence": confidence,
            "window": rule["window"],
            "prediction": rule["prediction"],
            "why": rule["why"],
            "verify": rule["verify"],
            "invalidate": rule["invalidate"],
            "discipline": rule["discipline"],
            "market_check": _market_line(rule_key, market_snapshot),
            "direction": cluster.direction,
            "credibility_label": cluster.credibility_label,
            "confirmed_source_count": cluster.confirmed_source_count,
        }
        confidence_boost = {"高": 6, "中": 3, "低": 0}.get(confidence, 0)
        candidates.append((float(score) * 10 + float(cluster.score or 0) + confidence_boost, card))

    candidates.sort(key=lambda item: item[0], reverse=True)
    cards: list[dict[str, Any]] = []
    used_rules: set[str] = set()
    for _, card in candidates:
        rule_key = str(card.get("rule_key") or "")
        if rule_key in used_rules:
            continue
        cards.append(card)
        used_rules.add(rule_key)
        if len(cards) >= limit:
            break
    if cards:
        summary_lines = [
            f"今天生成 {len(cards)} 张发酵预警卡，只提示可能的主线和验证条件。",
            f"最先盯：{cards[0]['label']}｜{cards[0]['window']}｜置信度 {cards[0]['confidence']}。",
            "预测不是交易指令；至少等政策/订单/价格/相对强弱中两项确认。",
        ]
    else:
        summary_lines = [
            "今天没有生成强发酵预警卡；继续按核心事件、资源博弈和纪律面板观察。",
            "如果只有单一叙事，没有政策、订单或价格确认，先不升级。",
        ]

    return {
        "enabled": True,
        "card_count": len(cards),
        "summary_lines": summary_lines,
        "framework_lines": FRAMEWORK_LINES,
        "cards": cards,
        "disclaimer": "发酵预警是研究辅助，不构成投资建议，不保证准确或盈利。",
    }


def render_prediction_lens_markdown(lens: dict[str, Any]) -> str:
    if not lens:
        return ""
    lines = ["## 发酵预警卡片", ""]
    lines.extend(f"- {line}" for line in lens.get("summary_lines") or [])
    cards = lens.get("cards") or []
    if cards:
        lines.extend(
            [
                "",
                "| 主线 | 窗口 | 预警逻辑 | 验证条件 | 失效条件 | 纪律 |",
                "|---|---|---|---|---|---|",
            ]
        )
        for card in cards[:5]:
            lines.append(
                "| "
                f"{_md_cell(card.get('label'))}（{_md_cell(card.get('confidence'))}） | "
                f"{_md_cell(card.get('window'))} | "
                f"{_md_cell(card.get('prediction'))} {_md_cell(card.get('why'))} | "
                f"{_md_cell(card.get('verify'))} {_md_cell(card.get('market_check'))} | "
                f"{_md_cell(card.get('invalidate'))} | "
                f"{_md_cell(card.get('discipline'))} |"
            )
    else:
        lines.extend(["", "### 固定框架", ""])
        lines.extend(f"- {line}" for line in lens.get("framework_lines") or FRAMEWORK_LINES)
    disclaimer = lens.get("disclaimer")
    if disclaimer:
        lines.extend(["", f"> {disclaimer}"])
    return "\n".join(lines).strip()
