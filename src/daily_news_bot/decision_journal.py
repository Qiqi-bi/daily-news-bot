from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .config import ROOT_DIR


JOURNAL_PATH = ROOT_DIR / "outputs" / "decision_journal.json"
EVENT_THEME_TO_CANDIDATE_KEYS: dict[str, tuple[str, ...]] = {
    "ai": ("semiconductor", "hk_tech"),
    "energy": ("power", "metals_gold", "dividend_lowvol"),
    "gold": ("metals_gold", "dividend_lowvol"),
    "china_macro": ("dividend_lowvol", "hk_tech"),
    "new_energy": (),
}
EVENT_THEME_LABELS: dict[str, str] = {
    "ai": "AI/科技成长",
    "energy": "能源/航运/大宗链",
    "gold": "黄金/避险",
    "china_macro": "中国宏观/A股宽基",
    "new_energy": "新能源",
}


def _safe_float(value: Any) -> float | None:
    try:
        if value in (None, "", "-"):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _execution_quote_map(execution_checks: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("code") or ""): item
        for item in (execution_checks or {}).get("items") or []
        if item.get("code")
    }


def _candidate_theme_map(snapshot: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for item in snapshot.get("top_candidates") or []:
        theme_key = str(item.get("theme_key") or "")
        if not theme_key:
            continue
        result[theme_key] = list(item.get("instruments") or [])
    return result


def load_decision_journal(path: Path = JOURNAL_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return payload if isinstance(payload, list) else []


def save_decision_journal(records: list[dict[str, Any]], path: Path = JOURNAL_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def build_decision_snapshot(
    generated_at: datetime,
    summary: dict[str, Any],
    event_impacts: list[dict[str, Any]],
    candidate_scores: list[dict[str, Any]],
    action_board_lines: list[str],
    execution_checks: dict[str, Any] | None = None,
) -> dict[str, Any]:
    quote_map = _execution_quote_map(execution_checks)
    top_candidates: list[dict[str, Any]] = []
    for row in candidate_scores[:5]:
        instruments: list[dict[str, Any]] = []
        for instrument in row.get("instruments") or []:
            code = str(instrument.get("code") or "").strip()
            if not code:
                continue
            quote = quote_map.get(code, {})
            instruments.append(
                {
                    "name": instrument.get("name") or code,
                    "code": code,
                    "latest_price": _safe_float(quote.get("latest_price")),
                    "change_pct": _safe_float(quote.get("change_pct")),
                    "premium_discount_pct": _safe_float(quote.get("premium_discount_pct")),
                    "liquidity_level": quote.get("liquidity_level") or "未知",
                }
            )
        top_candidates.append(
            {
                "theme": row.get("theme") or "未命名主题",
                "theme_key": row.get("theme_key") or "",
                "priority": row.get("priority") or "未知",
                "score": _safe_float(row.get("score")) or 0.0,
                "instruments": instruments,
            }
        )

    top_events = [
        {
            "cluster_id": item.get("cluster_id") or "",
            "title": item.get("title") or "未命名事件",
            "priority": item.get("priority") or "观察",
            "theme_keys": list(item.get("theme_keys") or []),
            "exposed_weight_pct": _safe_float(item.get("exposed_weight_pct")) or 0.0,
        }
        for item in event_impacts[:5]
    ]

    return {
        "generated_at_utc": generated_at.isoformat(),
        "portfolio_total_value_cny": _safe_float(summary.get("total_value_cny")),
        "portfolio_total_pnl_pct": _safe_float(summary.get("actual_total_pnl_pct")),
        "portfolio_total_pnl_cny": _safe_float(summary.get("actual_total_pnl_cny")),
        "direct_ai_pct": _safe_float(summary.get("direct_ai_pct")),
        "growth_tech_pct": _safe_float(summary.get("growth_tech_pct")),
        "stable_core_pct": _safe_float(summary.get("stable_core_pct")),
        "insurance_pct": _safe_float(summary.get("insurance_pct")),
        "top_events": top_events,
        "top_candidates": top_candidates,
        "default_action": (action_board_lines or [""])[0],
        "action_board_lines": list(action_board_lines or [])[:4],
    }


def update_decision_journal(
    snapshot: dict[str, Any],
    path: Path = JOURNAL_PATH,
    keep_days: int = 120,
) -> None:
    records = load_decision_journal(path)
    cutoff = datetime.utcnow() - timedelta(days=keep_days)
    kept: list[dict[str, Any]] = []
    for item in records:
        try:
            ts = datetime.fromisoformat(str(item.get("generated_at_utc") or ""))
        except ValueError:
            continue
        if ts >= cutoff:
            kept.append(item)
    kept.append(snapshot)
    kept.sort(key=lambda item: str(item.get("generated_at_utc") or ""))
    save_decision_journal(kept, path)


def _pick_previous_snapshot(records: list[dict[str, Any]], current_time: datetime) -> dict[str, Any] | None:
    candidates: list[tuple[float, dict[str, Any]]] = []
    fallbacks: list[tuple[str, dict[str, Any]]] = []
    for item in records:
        try:
            ts = datetime.fromisoformat(str(item.get("generated_at_utc") or ""))
        except ValueError:
            continue
        if ts >= current_time:
            continue
        delta_days = (current_time - ts).total_seconds() / 86400
        if 4.5 <= delta_days <= 10:
            candidates.append((abs(delta_days - 7), item))
        fallbacks.append((item.get("generated_at_utc") or "", item))
    if candidates:
        candidates.sort(key=lambda item: item[0])
        return candidates[0][1]
    if fallbacks:
        fallbacks.sort(key=lambda item: item[0], reverse=True)
        return fallbacks[0][1]
    return None


def build_event_etf_history(
    current_routes: list[dict[str, Any]],
    path: Path = JOURNAL_PATH,
    max_pairs: int = 120,
) -> dict[str, Any]:
    records = sorted(load_decision_journal(path), key=lambda item: str(item.get("generated_at_utc") or ""))
    pairs = list(zip(records[:-1], records[1:]))[-max_pairs:]
    event_theme_samples: dict[str, int] = {}
    code_stats: dict[str, dict[str, dict[str, Any]]] = {}

    for current, nxt in pairs:
        next_price_by_code: dict[str, float] = {}
        for instruments in _candidate_theme_map(nxt).values():
            for instrument in instruments:
                code = str(instrument.get("code") or "")
                price = _safe_float(instrument.get("latest_price"))
                if code and price not in (None, 0):
                    next_price_by_code[code] = price

        current_candidates = _candidate_theme_map(current)
        event_themes: set[str] = set()
        for event in current.get("top_events") or []:
            for theme_key in event.get("theme_keys") or []:
                if theme_key in EVENT_THEME_TO_CANDIDATE_KEYS:
                    event_themes.add(str(theme_key))

        for event_theme in event_themes:
            event_theme_samples[event_theme] = event_theme_samples.get(event_theme, 0) + 1
            theme_stats = code_stats.setdefault(event_theme, {})
            for candidate_theme in EVENT_THEME_TO_CANDIDATE_KEYS.get(event_theme, ()):  # pragma: no branch
                for instrument in current_candidates.get(candidate_theme, []):
                    code = str(instrument.get("code") or "")
                    current_price = _safe_float(instrument.get("latest_price"))
                    next_price = next_price_by_code.get(code)
                    if not code or current_price in (None, 0) or next_price in (None, 0):
                        continue
                    change_pct = round((next_price - current_price) / current_price * 100, 3)
                    row = theme_stats.setdefault(
                        code,
                        {
                            "code": code,
                            "name": instrument.get("name") or code,
                            "samples": 0,
                            "positive_samples": 0,
                            "sum_change_pct": 0.0,
                            "best_change_pct": None,
                        },
                    )
                    row["samples"] += 1
                    row["sum_change_pct"] += change_pct
                    if change_pct > 0:
                        row["positive_samples"] += 1
                    best = row.get("best_change_pct")
                    if best is None or change_pct > best:
                        row["best_change_pct"] = change_pct

    rows: list[dict[str, Any]] = []
    lines: list[str] = []
    for route in current_routes[:3]:
        event_theme = str(route.get("theme_key") or "")
        sample_count = int(event_theme_samples.get(event_theme, 0))
        stats = list((code_stats.get(event_theme) or {}).values())
        for item in stats:
            item["avg_change_pct"] = round(item["sum_change_pct"] / max(int(item.get("samples") or 0), 1), 3)
            item["win_rate_pct"] = round(item["positive_samples"] / max(int(item.get("samples") or 0), 1) * 100, 1)
        stats = sorted(
            stats,
            key=lambda item: (
                item.get("avg_change_pct") or -999,
                item.get("win_rate_pct") or -999,
                item.get("samples") or 0,
            ),
            reverse=True,
        )
        row = {
            "theme_key": event_theme,
            "theme_label": EVENT_THEME_LABELS.get(event_theme, event_theme or "未命名主题"),
            "sample_count": sample_count,
            "leaders": stats[:3],
        }
        rows.append(row)
        if sample_count <= 0 or not stats:
            lines.append(f"- {row['theme_label']}：历史样本还不够，先继续积累快照；现阶段仍以当下新闻、价格和纪律三项共振为主。")
            continue
        sample_note = "样本偏少，仅供观察；" if sample_count < 5 else ""
        leader_text = "；".join(
            f"{item.get('name')}({item.get('code')}) 平均下一次快照 {item.get('avg_change_pct', 0.0):+.2f}%｜胜率 {item.get('win_rate_pct', 0.0):.0f}%"
            for item in stats[:2]
        )
        lines.append(
            f"- {row['theme_label']}：历史可比样本 {sample_count} 次；{sample_note}候选池里先手更多见 {leader_text}。"
        )
    if not lines:
        lines.append("- 历史先动统计暂无样本。")
    lines.append("- 说明：这是基于你自己的每日快照做的‘候选池先手统计’，不是严格因果回测，也不能替代交易纪律。")
    return {"lines": lines, "rows": rows}


def build_weekly_decision_review(
    current_snapshot: dict[str, Any],
    execution_checks: dict[str, Any] | None = None,
    path: Path = JOURNAL_PATH,
) -> dict[str, Any]:
    records = load_decision_journal(path)
    try:
        current_time = datetime.fromisoformat(str(current_snapshot.get("generated_at_utc") or ""))
    except ValueError:
        current_time = datetime.utcnow()
    previous = _pick_previous_snapshot(records, current_time)
    if not previous:
        return {
            "has_history": False,
            "previous_snapshot": None,
            "lines": ["- 还没有足够的历史快照，等跑满一周后这里会开始复盘“上周提醒后来怎么样”。"],
        }

    comparison_text = "使用最近一份可比快照"
    try:
        previous_time = datetime.fromisoformat(str(previous.get("generated_at_utc") or ""))
        delta_days = (current_time - previous_time).total_seconds() / 86400
        if delta_days >= 4.5:
            comparison_text = "使用最近一份周度可比快照"
        else:
            comparison_text = "周度样本不足，先使用最近一次运行快照"
    except ValueError:
        previous_time = None

    current_themes = {str(item.get("theme_key") or "") for item in current_snapshot.get("top_candidates") or [] if item.get("theme_key")}
    previous_themes = {str(item.get("theme_key") or "") for item in previous.get("top_candidates") or [] if item.get("theme_key")}
    continued = [item.get("theme") for item in current_snapshot.get("top_candidates") or [] if item.get("theme_key") in previous_themes]
    new_themes = [item.get("theme") for item in current_snapshot.get("top_candidates") or [] if item.get("theme_key") not in previous_themes]
    faded = [item.get("theme") for item in previous.get("top_candidates") or [] if item.get("theme_key") not in current_themes]

    current_quote_map = _execution_quote_map(execution_checks)
    followups: list[str] = []
    for item in (previous.get("top_candidates") or [])[:3]:
        matched = None
        for instrument in item.get("instruments") or []:
            code = str(instrument.get("code") or "")
            previous_price = _safe_float(instrument.get("latest_price"))
            current_quote = current_quote_map.get(code, {})
            current_price = _safe_float(current_quote.get("latest_price"))
            if previous_price not in (None, 0) and current_price not in (None, 0):
                change_pct = round((current_price - previous_price) / previous_price * 100, 2)
                matched = f"{item.get('theme')}：{instrument.get('name')}({code}) 自上次快照以来约 {change_pct:+.2f}%"
                break
        if matched:
            followups.append(matched)

    previous_pnl = _safe_float(previous.get("portfolio_total_pnl_pct"))
    current_pnl = _safe_float(current_snapshot.get("portfolio_total_pnl_pct"))
    pnl_delta_text = "未知"
    if previous_pnl is not None and current_pnl is not None:
        pnl_delta_text = f"{current_pnl - previous_pnl:+.2f}pct"

    lines: list[str] = [
        f"- 对比基准：{comparison_text}（{str(previous.get('generated_at_utc') or '')[:10]}）。",
        f"- 组合层面：总浮盈比例相对上次快照变化 {pnl_delta_text}；这里只做复盘，不把单周波动当成长期能力。",
        f"- 延续主线：{'、'.join(continued[:3]) if continued else '暂无明显延续主线，说明市场在切换。'}。",
        f"- 新冒头方向：{'、'.join(new_themes[:3]) if new_themes else '暂无新的候选主线进入前排'}。",
        f"- 退潮方向：{'、'.join(faded[:3]) if faded else '暂无明显退潮方向退出前排'}。",
    ]
    if followups:
        lines.append("- 上周前排候选后来表现：" + "；".join(followups[:3]) + "。")
    else:
        lines.append("- 上周前排候选后来表现：历史价格对比暂不足，先继续积累样本。")
    lines.append("- 复盘结论：只有‘连续主线 + 价格确认 + 纪律允许’三者同时出现，才值得从观察升级到动仓。")
    return {
        "has_history": True,
        "previous_snapshot": previous,
        "lines": lines,
    }
