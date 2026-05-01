from __future__ import annotations

from typing import Any


LAYER_LABELS = {
    "core": "一级：持仓相关",
    "watch": "二级：重点观察",
    "event": "三级：事件触发",
    "avoid": "降噪：默认回避",
}

LAYER_ORDER = {"core": 0, "watch": 1, "event": 2, "avoid": 3}


DEFAULT_INDUSTRY_RADAR: list[dict[str, Any]] = [
    {
        "id": "ai_infra",
        "name": "AI基础设施链",
        "layer": "core",
        "theme_keys": ["ai", "semiconductor"],
        "keywords": ["ai", "nvidia", "semiconductor", "chip", "data center", "算力", "人工智能", "半导体", "芯片", "数据中心"],
        "why": "和现有AI/成长仓高度相关，是每天必须看的主线。",
        "watch": "海外AI龙头、半导体指数、国内算力政策、成交量、AI仓位上限。",
        "verify": "至少等价格、订单、政策或相对强弱中两项确认。",
        "action": "默认先复核持仓重叠和上限，不因单日强势继续叠加进攻仓。",
        "instruments": ["011840", "588930", "512480", "588200"],
    },
    {
        "id": "china_broad_core",
        "name": "A股宽基/中国宏观",
        "layer": "core",
        "theme_keys": ["china_macro"],
        "keywords": ["china", "yuan", "pboc", "stimulus", "pmi", "中国", "人民币", "央行", "政策", "消费", "沪深300", "上证"],
        "why": "决定稳底仓和月度新增资金的底盘。",
        "watch": "人民币、政策口径、A股成交、沪深300/上证相对创业板强弱。",
        "verify": "看官方政策、汇率、成交量和宽基价格是否同向。",
        "action": "回撤时优先考虑稳底仓，不把进攻仓当默认补仓方向。",
        "instruments": ["510310", "510210"],
    },
    {
        "id": "gold_real_rates",
        "name": "黄金/实际利率",
        "layer": "core",
        "theme_keys": ["gold"],
        "keywords": ["gold", "treasury", "yield", "dollar", "fed", "inflation", "黄金", "美债", "美元", "美联储", "实际利率", "通胀"],
        "why": "黄金是组合保险仓，不是收益主攻仓。",
        "watch": "黄金价格、美元指数、美债收益率、地缘风险和黄金仓位区间。",
        "verify": "看黄金上涨是否被美元/美债方向支持，仓位是否低于10%-15%保险区间。",
        "action": "低于区间才复核是否补保险仓，高于区间不追。",
        "instruments": ["000216", "518880"],
    },
    {
        "id": "semiconductor_materials",
        "name": "半导体材料/卡脖子链",
        "layer": "watch",
        "theme_keys": ["ai", "semiconductor"],
        "keywords": ["wf6", "helium", "photoresist", "specialty gas", "precursor", "电子特气", "六氟化钨", "氦气", "光刻胶", "靶材", "前驱体"],
        "why": "小品种也可能卡住大产业，适合做左侧观察。",
        "watch": "不可替代性、认证周期、出口限制、长协、库存周数和交期。",
        "verify": "至少看到价格/交期/订单/毛利率/客户认证两项确认。",
        "action": "先放观察池；未验证前不因为题材稀缺追高。",
        "instruments": ["512480", "588200"],
    },
    {
        "id": "energy_power",
        "name": "能源电力链",
        "layer": "watch",
        "theme_keys": ["energy"],
        "keywords": ["oil", "gas", "coal", "power", "grid", "wind power", "原油", "天然气", "煤炭", "电力", "电网", "风电", "绿电"],
        "why": "能源冲击通常先影响电力、煤炭、航运、通胀和防御资产。",
        "watch": "油气价格、煤价、电力ETF、电网订单、风电相对光伏强弱。",
        "verify": "看能源价格和电力/电网板块是否同步确认。",
        "action": "先看传导链，不把新能源当油价上涨的第一反应。",
        "instruments": ["561560", "560390"],
    },
    {
        "id": "resource_metals",
        "name": "资源品/关键矿产",
        "layer": "watch",
        "theme_keys": ["gold", "energy"],
        "keywords": ["rare earth", "copper", "tungsten", "lithium", "critical mineral", "稀土", "铜", "钨", "锂", "关键矿产", "有色"],
        "why": "适合观察资源卡点和价格传导，不适合每天追涨。",
        "watch": "出口管制、库存、价格指数、海外供应扰动和下游议价能力。",
        "verify": "确认价格上涨能否传到企业利润，而不是只停留在商品波动。",
        "action": "只在价格和产业验证同步时升级候选。",
        "instruments": ["512400", "518880"],
    },
    {
        "id": "anti_involution_policy",
        "name": "政策/反内卷链",
        "layer": "watch",
        "theme_keys": ["china_macro", "new_energy"],
        "keywords": ["tariff", "export", "anti-involution", "overcapacity", "关税", "出口", "反内卷", "产能", "低价倾销", "涨价"],
        "why": "决定哪些行业能涨价，哪些只是承担保供或政策任务。",
        "watch": "反内卷文件、出口报价、PPI、行业协会口径、龙头毛利率。",
        "verify": "先确认国内能不能涨价，再确认利润能不能修复。",
        "action": "用作筛选器：政策压价行业先降权。",
        "instruments": [],
    },
    {
        "id": "hk_tech",
        "name": "港股科技/互联网",
        "layer": "watch",
        "theme_keys": ["ai", "china_macro"],
        "keywords": ["hong kong", "hang seng tech", "platform", "internet", "港股", "恒生科技", "平台经济", "互联网"],
        "why": "弹性大，但和AI/成长风险偏好相关，不能当防守仓。",
        "watch": "美元压力、南向资金、平台政策、AI应用侧和港股科技相对强弱。",
        "verify": "确认流动性和政策同时改善，再考虑候选优先级。",
        "action": "只做观察候选；AI仓位偏高时不主动叠加。",
        "instruments": ["513010", "513180"],
    },
    {
        "id": "dividend_defense",
        "name": "红利低波/防御",
        "layer": "watch",
        "theme_keys": ["china_macro", "gold"],
        "keywords": ["dividend", "low volatility", "utility", "bank", "红利", "低波", "公用事业", "银行", "防御"],
        "why": "当AI和成长仓偏高时，用来降低组合波动。",
        "watch": "长端利率、股息率吸引力、风险偏好、红利低波相对成长强弱。",
        "verify": "确认不是纯防守拥挤，而是组合需要降低波动。",
        "action": "新增资金防守候选，不承担进攻收益预期。",
        "instruments": ["512890", "515100"],
    },
    {
        "id": "shipping_routes",
        "name": "航运/通道风险",
        "layer": "event",
        "theme_keys": ["energy"],
        "keywords": ["shipping", "freight", "hormuz", "red sea", "suez", "航运", "油运", "霍尔木兹", "红海", "苏伊士", "运价"],
        "why": "只有通道风险出现时才需要抬高优先级。",
        "watch": "油运费率、BDI、绕航时间、保险费和港口吞吐。",
        "verify": "看运价和能源价格是否同步确认。",
        "action": "事件触发后再看能源/航运/保险链，不日常占用注意力。",
        "instruments": [],
    },
    {
        "id": "new_energy_cycle",
        "name": "新能源价格周期",
        "layer": "event",
        "theme_keys": ["new_energy"],
        "keywords": ["solar", "photovoltaic", "ev", "battery", "lithium", "光伏", "新能源车", "锂电", "锂价", "储能"],
        "why": "新能源要看产能出清和价格周期，不是油价上涨就直接买。",
        "watch": "锂价、光伏链价格、新能源车销量、补贴、龙头盈利修复。",
        "verify": "看价格和利润是否修复，而不是只看政策或情绪。",
        "action": "没有盈利修复前，只保留观察。",
        "instruments": ["159915"],
    },
    {
        "id": "sanctions_tariffs",
        "name": "制裁/关税/结算规则",
        "layer": "event",
        "theme_keys": ["china_macro", "energy"],
        "keywords": ["sanction", "tariff", "export ban", "currency", "swift", "制裁", "关税", "出口禁令", "结算", "美元", "人民币"],
        "why": "规则变化会改变供应链成本、汇率和谈判筹码。",
        "watch": "官方文件、生效日期、豁免条款、汇率、商品价格和替代供应。",
        "verify": "只按官方和主流媒体交叉验证，不按传闻推演。",
        "action": "先影响风险偏好和观察池，不直接生成交易动作。",
        "instruments": [],
    },
    {
        "id": "story_only",
        "name": "纯题材小作文",
        "layer": "avoid",
        "theme_keys": [],
        "keywords": ["rumor", "unconfirmed", "viral", "传闻", "小作文", "网传", "未经证实"],
        "why": "容易制造兴奋感，但不可验证。",
        "watch": "是否有官方源、主流媒体交叉验证、真实价格或订单确认。",
        "verify": "没有验证就不进入操作区。",
        "action": "默认忽略；只记录观察。",
        "instruments": [],
    },
    {
        "id": "crowded_right_side",
        "name": "高拥挤右侧追涨",
        "layer": "avoid",
        "theme_keys": [],
        "keywords": ["crowded", "leverage", "all time high", "拥挤", "杠杆", "新高", "右侧", "一致看好"],
        "why": "确定性越强，价格可能越不划算。",
        "watch": "成交放量、估值分位、融资杠杆、筹码结构和回撤纪律。",
        "verify": "确认赔率而不是只确认故事。",
        "action": "作为追高刹车，不作为买入理由。",
        "instruments": [],
    },
]


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _cluster_text(cluster: Any) -> str:
    representative = getattr(cluster, "representative", None)
    parts = [
        getattr(cluster, "theme", ""),
        " ".join(getattr(cluster, "tags", []) or []),
        getattr(representative, "title", "") if representative else "",
        getattr(representative, "summary", "") if representative else "",
        getattr(representative, "content", "") if representative else "",
    ]
    for article in getattr(cluster, "articles", [])[:4]:
        parts.extend(
            [
                getattr(article, "title", ""),
                getattr(article, "summary", ""),
                getattr(article, "content", ""),
                getattr(article, "category", ""),
                getattr(article, "region", ""),
            ]
        )
    return " ".join(_text(part) for part in parts if _text(part)).casefold()


def _normalize_entries(config: Any) -> list[dict[str, Any]]:
    if isinstance(config, dict):
        if config.get("enabled") is False:
            return []
        if isinstance(config.get("items"), list):
            return [dict(item) for item in config.get("items") or [] if isinstance(item, dict)]
        layers = config.get("layers")
        if isinstance(layers, dict):
            entries: list[dict[str, Any]] = []
            for layer, items in layers.items():
                if not isinstance(items, list):
                    continue
                for item in items:
                    if isinstance(item, dict):
                        row = dict(item)
                        row.setdefault("layer", layer)
                        entries.append(row)
            return entries
    if isinstance(config, list):
        return [dict(item) for item in config if isinstance(item, dict)]
    return [dict(item) for item in DEFAULT_INDUSTRY_RADAR]


def _keyword_hits(entry: dict[str, Any], cluster_texts: list[str]) -> list[str]:
    hits: list[str] = []
    for keyword in entry.get("keywords") or []:
        needle = str(keyword or "").casefold().strip()
        if not needle:
            continue
        if any(needle in text for text in cluster_texts):
            hits.append(str(keyword))
    return hits[:5]


def _theme_hit(entry: dict[str, Any], event_theme_keys: set[str], candidate_theme_keys: set[str]) -> bool:
    theme_keys = {str(item) for item in entry.get("theme_keys") or []}
    return bool(theme_keys & (event_theme_keys | candidate_theme_keys))


def _component_score(text: str, keywords: tuple[str, ...]) -> int:
    lowered = text.casefold()
    hits = sum(1 for keyword in keywords if keyword in lowered)
    return min(5, hits * 2)


def _industry_score_card(
    entry: dict[str, Any],
    *,
    hits: list[str],
    matched_by_theme: bool,
    candidate_bonus: int,
    layer: str,
) -> dict[str, Any]:
    combined = " ".join(
        _text(value)
        for value in (
            entry.get("name"),
            entry.get("why"),
            entry.get("watch"),
            entry.get("verify"),
            " ".join(entry.get("keywords") or []),
            " ".join(hits),
        )
    )
    policy_score = _component_score(
        combined,
        ("policy", "tariff", "sanction", "export", "regulation", "政策", "关税", "制裁", "出口", "管制", "反内卷"),
    )
    supply_score = _component_score(
        combined,
        ("supply", "shortage", "inventory", "capacity", "order", "供应", "库存", "产能", "订单", "交期", "卡脖子"),
    )
    price_score = min(5, int(candidate_bonus / 3) + (1 if matched_by_theme else 0))
    news_score = min(5, len(hits) * 2 + (2 if matched_by_theme else 0))
    hit_rate_score = 1 if layer != "avoid" else 0
    total = policy_score + supply_score + price_score + news_score + hit_rate_score
    if total >= 18:
        label = "强观察"
    elif total >= 12:
        label = "观察"
    elif layer == "avoid":
        label = "降噪"
    else:
        label = "积累"
    return {
        "policy": policy_score,
        "supply": supply_score,
        "price": price_score,
        "news": news_score,
        "hit_rate": hit_rate_score,
        "total": total,
        "label": label,
        "hit_rate_note": "等待事后验算样本",
    }


def _score_card_text(score_card: dict[str, Any] | None) -> str:
    card = score_card or {}
    return (
        f"{card.get('total', 0)}分/{card.get('label', '积累')}；"
        f"政{card.get('policy', 0)} 供{card.get('supply', 0)} "
        f"价{card.get('price', 0)} 闻{card.get('news', 0)} 命{card.get('hit_rate', 0)}"
    )


def _layer_of(entry: dict[str, Any]) -> str:
    layer = str(entry.get("layer") or "watch")
    return layer if layer in LAYER_LABELS else "watch"


def build_industry_radar(
    portfolio: dict[str, Any] | None,
    clusters: list[Any],
    event_impacts: list[dict[str, Any]],
    candidate_scores: list[dict[str, Any]],
) -> dict[str, Any]:
    portfolio = portfolio or {}
    entries = _normalize_entries(portfolio.get("industry_radar"))
    if not entries:
        return {"enabled": False, "rows": [], "summary_lines": ["行业雷达未启用。"]}

    cluster_texts = [_cluster_text(cluster) for cluster in clusters]
    event_theme_keys = {str(key) for impact in event_impacts for key in impact.get("theme_keys", [])}
    candidate_theme_keys = {
        str(row.get("theme_key"))
        for row in candidate_scores
        if row.get("theme_key") and row.get("priority") in {"高", "中"}
    }
    candidate_by_key = {str(row.get("theme_key")): row for row in candidate_scores if row.get("theme_key")}

    rows: list[dict[str, Any]] = []
    for entry in entries:
        layer = _layer_of(entry)
        hits = _keyword_hits(entry, cluster_texts)
        matched_by_theme = _theme_hit(entry, event_theme_keys, candidate_theme_keys)
        matched_candidates = [
            candidate_by_key[key]
            for key in (entry.get("theme_keys") or [])
            if key in candidate_by_key
        ]
        candidate_bonus = max((int(item.get("score") or 0) for item in matched_candidates), default=0)
        score = len(hits) * 2 + (3 if matched_by_theme else 0) + candidate_bonus
        if layer == "core":
            score += 3
        elif layer == "avoid":
            score -= 1

        score_card = _industry_score_card(
            entry,
            hits=hits,
            matched_by_theme=matched_by_theme,
            candidate_bonus=candidate_bonus,
            layer=layer,
        )

        if hits or matched_by_theme:
            status = "今日关注"
        elif layer == "core":
            status = "每日必看"
        elif layer == "avoid":
            status = "降噪"
        else:
            status = "静默观察"

        rows.append(
            {
                "id": entry.get("id") or entry.get("name"),
                "name": entry.get("name") or "未命名行业",
                "layer": layer,
                "layer_label": LAYER_LABELS[layer],
                "status": status,
                "score": score,
                "score_card": score_card,
                "score_card_text": _score_card_text(score_card),
                "why": entry.get("why") or "",
                "watch": entry.get("watch") or "",
                "verify": entry.get("verify") or "",
                "action": entry.get("action") or "",
                "instruments": list(entry.get("instruments") or []),
                "hits": hits,
            }
        )

    rows.sort(key=lambda row: (LAYER_ORDER.get(row["layer"], 9), row["status"] != "今日关注", -int(row["score"])))
    layer_counts = {layer: sum(1 for row in rows if row.get("layer") == layer) for layer in LAYER_LABELS}
    active_rows = [row for row in rows if row.get("status") == "今日关注"]
    core_rows = [row for row in rows if row.get("layer") == "core"]
    focus_names = [row["name"] for row in (active_rows or core_rows)[:3]]
    summary_lines = [
        f"行业雷达共 {len(rows)} 条：持仓相关 {layer_counts.get('core', 0)}，重点观察 {layer_counts.get('watch', 0)}，事件触发 {layer_counts.get('event', 0)}，降噪 {layer_counts.get('avoid', 0)}。",
        "今天优先看：" + "、".join(focus_names) + "。" if focus_names else "今天没有行业雷达触发项。",
        "可买池不随行业雷达自动扩张；雷达只决定看什么，不直接决定买什么。",
    ]
    return {
        "enabled": True,
        "summary_lines": summary_lines,
        "layer_counts": layer_counts,
        "active_count": len(active_rows),
        "rows": rows,
    }


def render_industry_radar_lines(radar: dict[str, Any]) -> list[str]:
    if not radar or not radar.get("enabled"):
        return ["- 行业雷达未启用。"]
    lines = list(radar.get("summary_lines") or [])
    rows = radar.get("rows") or []
    lines.extend(["", "| 层级 | 行业 | 评分 | 状态 | 看什么 | 验证条件 | 动作 |", "|---|---|---:|---|---|---|---|"])
    for row in rows:
        instruments = "、".join(row.get("instruments") or [])
        action = row.get("action") or ""
        if instruments:
            action = f"{action} 参考：{instruments}"
        lines.append(
            "| "
            f"{_text(row.get('layer_label'))} | "
            f"{_text(row.get('name'))} | "
            f"{_text(row.get('score_card_text'))} | "
            f"{_text(row.get('status'))} | "
            f"{_text(row.get('watch'))} | "
            f"{_text(row.get('verify'))} | "
            f"{_text(action)} |"
        )
    return lines
