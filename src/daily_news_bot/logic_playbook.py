from __future__ import annotations

from typing import Any


PLAYBOOK_CARDS: list[dict[str, str]] = [
    {
        "name": "资源卡点",
        "question": "小市场会不会卡住大产业？",
        "use_when": "氦气、WF6、稀土、电子特气、关键矿产、航运通道等新闻出现时。",
        "confirm": "看不可替代性、产能集中度、认证周期、库存周数、出口规则和交期。",
        "avoid": "不能只因为市场规模小就否定，也不能只因为概念稀缺就追高。",
    },
    {
        "name": "钱在办事",
        "question": "资金是在追利润，还是让企业完成保供、扩产、替代、卡位任务？",
        "use_when": "企业突然扩产、定增、补贴、长协、政策扶持或产线建设加速时。",
        "confirm": "看钱流向产能、订单、客户认证、国产替代、供应安全，而不是只看短期利润。",
        "avoid": "不要把所有融资都理解成利好；如果只是替国家或产业链兜底，利润弹性可能滞后。",
    },
    {
        "name": "不可替代性",
        "question": "没有它，下游是涨成本，还是直接停线？",
        "use_when": "半导体材料、前驱体、设备、光通信、能源通道等环节被反复提及时。",
        "confirm": "看替代工艺、客户认证难度、停线损失、长协重定价和安全库存。",
        "avoid": "不要只看材料成本占比；成本占比低但停线代价高，反而可能更有议价权。",
    },
    {
        "name": "价格传导",
        "question": "涨价能不能从原料传到产品和利润？",
        "use_when": "原料涨价、出口限制、反内卷、外部竞争对手退出、汇率变化时。",
        "confirm": "看报价、长协、PPI、毛利率、库存和同行是否同步涨价。",
        "avoid": "有政策压价或保供任务时，商品涨价不等于企业利润上涨。",
    },
    {
        "name": "政策格局",
        "question": "这是不是一个该涨但不能完全涨的行业？",
        "use_when": "化肥、成品油、粮食、农药、民生保供、能源价格管制等新闻出现时。",
        "confirm": "看官方定价、补贴兑现、出口限制、企业现金流和政策口径。",
        "avoid": "不要看到海外价格暴涨就直接推国内资产受益，先看国内能不能涨价。",
    },
    {
        "name": "系统降本",
        "question": "一个小技术能不能降低整套系统的存储、散热、能耗或时延？",
        "use_when": "空心光纤、CPO、光模块、光交换、算力集群、数据中心效率相关主题出现时。",
        "confirm": "看大客户采用、订单、现货扫货、单位系统成本下降和相对强弱。",
        "avoid": "不要只看单点性能参数；要看它是否改变整套系统的成本结构。",
    },
    {
        "name": "左侧预警",
        "question": "现在是约束刚变化，还是所有人都已经确认？",
        "use_when": "新闻刚出现、价格未充分反应、但供需/政策/订单已有早期信号时。",
        "confirm": "看政策/订单/产能/价格/相对强弱至少两项同向，再升级预警。",
        "avoid": "左侧不是瞎买；没有验证条件就只是记录观察。",
    },
    {
        "name": "右侧拥挤",
        "question": "等到确定性出来时，普通人还能不能拿到好筹码？",
        "use_when": "市场开始一致看好、成交放量、估值上修、政策落地后资产快速上涨时。",
        "confirm": "看估值分位、融资杠杆、成交拥挤、筹码结构和回撤纪律。",
        "avoid": "不要把右侧确认等同于安全；确定性越强，价格可能越不划算。",
    },
    {
        "name": "可信度防火墙",
        "question": "这是已确认事实，还是小作文/阴谋推断/单一来源？",
        "use_when": "政治暴力、刺杀、爆炸、政变、战争、制裁、社媒传闻等高风险事件出现时。",
        "confirm": "只按官方、主流媒体交叉验证和可追溯文件分层写事实。",
        "avoid": "不写未经证实的幕后势力、动机推断或自导自演结论。",
    },
]


SUMMARY_LINES = [
    "系统每天先用这些框架看新闻，再决定是否生成资源博弈、发酵预警和组合纪律提醒。",
    "核心不是预测必涨必跌，而是提前找约束、筹码、价格传导和失效条件。",
    "任何框架都必须落到验证条件；没有验证，就只进入观察。",
]


def build_logic_playbook() -> dict[str, Any]:
    return {
        "enabled": True,
        "summary_lines": SUMMARY_LINES,
        "cards": PLAYBOOK_CARDS,
        "disclaimer": "思维框架库用于研究和复盘，不构成投资建议，也不保证判断正确。",
    }


def _md_cell(value: Any) -> str:
    text = " ".join(str(value or "").split())
    return text.replace("|", "/")


def render_logic_playbook_markdown(playbook: dict[str, Any]) -> str:
    if not playbook:
        return ""
    lines = ["## 思维框架库", ""]
    lines.extend(f"- {line}" for line in playbook.get("summary_lines") or [])
    cards = playbook.get("cards") or []
    if cards:
        lines.extend(
            [
                "",
                "| 框架 | 先问什么 | 什么时候用 | 验证条件 | 避免什么 |",
                "|---|---|---|---|---|",
            ]
        )
        for card in cards:
            lines.append(
                "| "
                f"{_md_cell(card.get('name'))} | "
                f"{_md_cell(card.get('question'))} | "
                f"{_md_cell(card.get('use_when'))} | "
                f"{_md_cell(card.get('confirm'))} | "
                f"{_md_cell(card.get('avoid'))} |"
            )
    disclaimer = playbook.get("disclaimer")
    if disclaimer:
        lines.extend(["", f"> {disclaimer}"])
    return "\n".join(lines).strip()
