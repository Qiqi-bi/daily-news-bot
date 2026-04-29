from __future__ import annotations

from datetime import datetime
from typing import Any

from .models import EventCluster


WEEKDAY_ZH = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


SYSTEM_PROMPT = """
你是一个“全球重大事件雷达 + 宏观市场影响分析师”。
你的目标不是复述新闻，而是帮助用户最快理解：
1. 今天真正最重要的世界事件是什么
2. 为什么重要、影响链条是什么
3. 谁受益、谁受损
4. 对主要资产和市场意味着什么
5. 接下来 24～72 小时最该盯什么

请严格遵守：
- 先结论，后解释
- 按“事件”输出，不按新闻条目机械罗列
- 同一事件的多条报道必须合并
- 只保留 4～6 个最重要的核心事件；公司财报、单个高管评论、单股涨跌通常应降级为“次级信号/侧面验证”
- 只基于提供的素材写作，不要补写素材中没有出现的事实、日期、价格目标、人物履历或概率判断
- 如果某件事仍在推进中，请明确写成“待确认/待观察”，不要写成已经落地
- 明确区分“官方确认 / 多家主流媒体交叉验证 / 单一来源 / 传闻或评论性内容”
- 对低可信、未证实、疑似传闻或二手转述素材，只能作为弱信号，不能写成已确认事实
- 不要直接给买卖指令，不要输出思维链，不要输出 <think> 或任何内部推理痕迹
- 如果市场价格快照没有给出具体数值，就只做方向性表述
- 如果连续事件追踪显示该事件此前几天已出现，请指出“这不是今天第一次出现”
- 遇到能源、稀土、氦气、半导体、航运、制裁、关税、结算等新闻时，加入“资源博弈/产业约束”视角：谁被卡、谁拿到筹码、钱在让谁完成什么任务、价格是否确认；但不能因此直接给买卖指令
- 做预警时只写“可能发酵的主线、验证条件、失效条件和时间窗口”，不要写必涨必跌；尤其注意绿电算力、汇率/反内卷涨价权、政策压价行业、系统降本技术和右侧拥挤风险

建议使用如下结构输出 Markdown：
## 30秒总览
## 今日核心事件分析
### 1. 事件名
### 2. 事件名
## 市场影响地图
## 明天最该盯的5个信号
## 哪些消息不要过度解读
## 一句话总结
""".strip()


MODE_GUIDANCE = {
    "comprehensive": "输出完整日报，重点是世界大事、重大影响、市场含义和未来观察点。",
    "morning": "输出早报，重点是隔夜变化与今日亚洲市场开盘前最值得关注的线索。",
    "noon": "输出午报，重点是上半天发生了什么，以及下午和夜间要盯什么。",
    "evening": "输出晚报，重点是全天总结以及欧美时段最值得关注的风险点。",
}


def _format_number(value: float | None) -> str:
    if value is None:
        return "未知"
    absolute_value = abs(value)
    if absolute_value >= 1000:
        return f"{value:,.2f}"
    if absolute_value >= 100:
        return f"{value:.2f}"
    if absolute_value >= 1:
        return f"{value:.3f}"
    return f"{value:.4f}"


def serialize_clusters(clusters: list[EventCluster]) -> str:
    lines: list[str] = []
    for index, cluster in enumerate(clusters, start=1):
        representative = cluster.representative
        lines.append(f"## 事件 {index}")
        lines.append(f"主题：{cluster.theme}")
        lines.append(
            f"评分：{cluster.score} | 重要性：{cluster.importance} | 方向：{cluster.direction} | 确定性：{cluster.certainty}"
        )
        lines.append(
            f"真实性/可信度：{cluster.credibility_label} ({cluster.credibility_score:.2f}) | 交叉验证来源：{cluster.confirmed_source_count} | 官方确认：{'是' if cluster.official_confirmation else '否'}"
        )
        if cluster.credibility_notes:
            lines.append("真实性说明：" + "；".join(cluster.credibility_notes))
        lines.append(f"标签：{', '.join(cluster.tags) or '未识别'}")
        for article in cluster.articles[:5]:
            source_label = f"{article.source}（官方源）" if article.official_source else article.source
            lines.append(
                f"- [{source_label}] {article.published_at.isoformat()} | 可信度 {article.credibility_label}({article.credibility_score:.2f}) | {article.title} | {article.summary[:220]}"
            )
        if representative.official_source:
            lines.append("- 备注：该事件的代表性素材来自官方源。")
        lines.append("")
    return "\n".join(lines).strip()


def serialize_market_snapshot(snapshot: dict[str, Any] | None) -> str:
    if not snapshot:
        return "暂无市场价格快照。"

    items = snapshot.get("items") or []
    failures = snapshot.get("failures") or []
    if not items:
        error_text = snapshot.get("error") or "无可用行情返回。"
        if failures:
            error_text += f" 失败资产数：{len(failures)}。"
        return error_text

    lines: list[str] = []
    for item in items:
        currency = item.get("currency") or ""
        pct = item.get("change_pct")
        pct_text = "未知" if pct is None else f"{pct:+.3f}%"
        lines.append(
            "- "
            f"{item.get('name', '未知资产')} ({item.get('symbol', '')}) | "
            f"最新：{_format_number(item.get('price'))} {currency} | "
            f"日变动：{pct_text} | "
            f"状态：{item.get('movement', '未知')} | "
            f"时间：{item.get('market_time_utc') or '未知'}"
        )
    if failures:
        lines.append(f"- 未返回价格的资产：{len(failures)} 个。")
    return "\n".join(lines)


def serialize_tracking_summary(tracking_summary: dict[str, Any] | None) -> str:
    if not tracking_summary:
        return "暂无连续事件追踪信息。"

    items = tracking_summary.get("tracked_events") or []
    if not items:
        return "本次没有可追踪的核心事件。"

    lookback_days = tracking_summary.get("lookback_days", 7)
    lines: list[str] = []
    for item in items:
        recent_titles = " / ".join(item.get("recent_titles") or []) or "无"
        seen_text = "是" if item.get("seen_recently") else "否"
        lines.append(
            "- "
            f"主题：{item.get('theme', '未知')} | "
            f"近{lookback_days}天连续出现：{seen_text} | "
            f"出现次数：{item.get('match_count', 0)} | "
            f"上次出现：{item.get('last_seen_utc') or '无'} | "
            f"近期标题：{recent_titles}"
        )
    return "\n".join(lines)


def build_user_prompt(
    mode: str,
    clusters: list[EventCluster],
    market_snapshot: dict[str, Any] | None = None,
    tracking_summary: dict[str, Any] | None = None,
) -> str:
    guidance = MODE_GUIDANCE.get(mode, MODE_GUIDANCE["comprehensive"])
    now_dt = datetime.utcnow()
    now_text = now_dt.strftime("%Y-%m-%d %H:%M UTC")
    weekday = WEEKDAY_ZH[now_dt.weekday()]
    cluster_block = serialize_clusters(clusters)
    market_block = serialize_market_snapshot(market_snapshot)
    tracking_block = serialize_tracking_summary(tracking_summary)

    return f"""
当前时间：{now_text}（{weekday}）
任务说明：{guidance}

请输出一份中文 Markdown 报告，优先给结论，其次给交易/宏观观察上真正有用的解释。

硬性要求：
- 只保留 4～6 个真正重要的核心事件
- 每个核心事件必须包含：发生了什么、为什么重要、影响链条、受益方、受损方、对市场的含义、接下来 24～72 小时看什么
- 每个核心事件还必须明确它的真实性状态：官方确认、主流媒体交叉验证、还是仍偏单一来源/待确认
- 必须有“市场影响地图”“明天最该盯的5个信号”“哪些消息不要过度解读”“一句话总结”
- 如果素材不足以支持具体数字或确定结论，就明确写“素材未提供更多细节”或“仍待确认”
- 如果连续事件追踪显示某主题此前已持续几天，请点出“这是连续事件，不是今天第一次出现”
- 如果有官方源，请优先把官方源当成确认层，不要被单一媒体标题带偏
- 不能写任何未在素材中明确出现的买卖建议、目标位、支撑位、阻力位
- 对资源、能源、半导体、制裁、航运类事件，必须先问：供给/技术/通道/结算/政策许可哪个环节被卡住，谁因此获得谈判筹码，相关价格是否同步确认
- 如果推导预警，必须同时写失效条件；普通投资者不能假设自己一定能等右侧确认后仍拿到好价格

下面是已聚合并排序后的事件素材，请按事件分析，而不是逐条重复转述：

### 事件素材
{cluster_block}

### 市场价格快照
{market_block}

### 连续事件追踪
{tracking_block}
""".strip()
