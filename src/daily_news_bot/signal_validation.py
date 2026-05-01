from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .config import ROOT_DIR


VALIDATION_PATH = ROOT_DIR / "outputs" / "signal_validation.json"
HORIZONS = (30, 60, 90)
MAX_SIGNALS = 500
KEEP_DAYS = 180
DEDUP_DAYS = 3
MIN_ADJUSTMENT_SAMPLES = 3


def _safe_float(value: Any) -> float | None:
    try:
        if value in (None, "", "-"):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_time(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _load_state(path: Path = VALIDATION_PATH) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "signals": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"version": 1, "signals": []}
    if not isinstance(payload, dict):
        return {"version": 1, "signals": []}
    payload.setdefault("version", 1)
    payload.setdefault("signals", [])
    return payload


def _save_state(payload: dict[str, Any], path: Path = VALIDATION_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _quote_map(execution_checks: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("code") or ""): item
        for item in (execution_checks or {}).get("items") or []
        if item.get("code")
    }


def _pct_change(start: float | None, end: float | None) -> float | None:
    if start in (None, 0) or end in (None, 0):
        return None
    return round((float(end) - float(start)) / float(start) * 100, 3)


def _horizon_key(horizon: int) -> str:
    return f"t{horizon}"


def _horizon_label(horizon: int) -> str:
    return f"T+{horizon}"


def _trim_signals(signals: list[dict[str, Any]], now: datetime) -> list[dict[str, Any]]:
    cutoff = now - timedelta(days=KEEP_DAYS)
    kept: list[dict[str, Any]] = []
    for signal in signals:
        created_at = _parse_time(signal.get("created_at_utc"))
        if created_at is None or created_at < cutoff:
            continue
        kept.append(signal)
    kept.sort(key=lambda item: str(item.get("created_at_utc") or ""), reverse=True)
    return kept[:MAX_SIGNALS]


def _is_duplicate(signals: list[dict[str, Any]], code: str, theme_key: str, now: datetime) -> bool:
    cutoff = now - timedelta(days=DEDUP_DAYS)
    for signal in signals:
        if str(signal.get("code") or "") != code:
            continue
        if str(signal.get("theme_key") or "") != theme_key:
            continue
        created_at = _parse_time(signal.get("created_at_utc"))
        if created_at is not None and created_at >= cutoff:
            return True
    return False


def _candidate_entries(portfolio_payload: dict[str, Any], quote_by_code: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for row in (portfolio_payload.get("candidate_scores") or [])[:6]:
        priority = str(row.get("priority") or "")
        if priority == "低":
            continue
        for instrument in (row.get("instruments") or [])[:2]:
            code = str(instrument.get("code") or "").strip()
            quote = quote_by_code.get(code)
            price = _safe_float((quote or {}).get("latest_price"))
            if not code or price in (None, 0):
                continue
            entries.append(
                {
                    "source": "candidate_pool",
                    "theme": row.get("theme") or row.get("theme_key") or "未命名主题",
                    "theme_key": row.get("theme_key") or "",
                    "priority": priority or "观察",
                    "score": _safe_float(row.get("score")) or 0.0,
                    "code": code,
                    "name": instrument.get("name") or (quote or {}).get("name") or code,
                    "start_price": price,
                }
            )

    for row in (portfolio_payload.get("industry_radar") or {}).get("rows") or []:
        if row.get("layer") == "avoid":
            continue
        if row.get("status") not in {"每日必看", "今日关注"}:
            continue
        for code in (row.get("instruments") or [])[:2]:
            code_text = str(code or "").strip()
            quote = quote_by_code.get(code_text)
            price = _safe_float((quote or {}).get("latest_price"))
            if not code_text or price in (None, 0):
                continue
            entries.append(
                {
                    "source": "industry_radar",
                    "theme": row.get("name") or "行业雷达",
                    "theme_key": row.get("id") or row.get("theme_key") or row.get("name") or "",
                    "priority": row.get("status") or "观察",
                    "score": _safe_float(row.get("score")) or 0.0,
                    "code": code_text,
                    "name": (quote or {}).get("name") or code_text,
                    "start_price": price,
                }
            )
    return entries


def _observe_existing(signals: list[dict[str, Any]], quote_by_code: dict[str, dict[str, Any]], now: datetime) -> None:
    for signal in signals:
        created_at = _parse_time(signal.get("created_at_utc"))
        if created_at is None:
            continue
        elapsed_days = (now - created_at).total_seconds() / 86400
        observations = signal.setdefault("observations", {})
        quote = quote_by_code.get(str(signal.get("code") or ""))
        current_price = _safe_float((quote or {}).get("latest_price"))
        if current_price in (None, 0):
            continue
        for horizon in HORIZONS:
            key = _horizon_key(horizon)
            if key in observations or elapsed_days < horizon:
                continue
            return_pct = _pct_change(_safe_float(signal.get("start_price")), current_price)
            if return_pct is None:
                continue
            observations[key] = {
                "observed_at_utc": now.isoformat(),
                "elapsed_days": round(elapsed_days, 2),
                "price": current_price,
                "return_pct": return_pct,
                "hit": return_pct > 0,
            }


def _add_current_signals(
    signals: list[dict[str, Any]],
    entries: list[dict[str, Any]],
    now: datetime,
) -> int:
    added = 0
    for entry in entries:
        code = str(entry.get("code") or "")
        theme_key = str(entry.get("theme_key") or "")
        if not code or _is_duplicate(signals, code, theme_key, now):
            continue
        signal_id = f"{now.strftime('%Y%m%d%H%M%S')}-{entry.get('source')}-{theme_key}-{code}"
        signals.append(
            {
                "id": signal_id,
                "created_at_utc": now.isoformat(),
                "source": entry.get("source"),
                "theme": entry.get("theme"),
                "theme_key": theme_key,
                "priority": entry.get("priority"),
                "score": entry.get("score"),
                "code": code,
                "name": entry.get("name") or code,
                "start_price": entry.get("start_price"),
                "observations": {},
            }
        )
        added += 1
    return added


def _empty_bucket() -> dict[str, Any]:
    return {"samples": 0, "hits": 0, "sum_return_pct": 0.0}


def _summarize(signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for signal in signals:
        theme_key = str(signal.get("theme_key") or "unknown")
        theme = str(signal.get("theme") or theme_key)
        row = grouped.setdefault(
            theme_key,
            {
                "theme_key": theme_key,
                "theme": theme,
                "signals": 0,
                **{_horizon_key(horizon): _empty_bucket() for horizon in HORIZONS},
            },
        )
        row["signals"] += 1
        observations = signal.get("observations") or {}
        for horizon in HORIZONS:
            key = _horizon_key(horizon)
            obs = observations.get(key) or {}
            return_pct = _safe_float(obs.get("return_pct"))
            if return_pct is None:
                continue
            bucket = row[key]
            bucket["samples"] += 1
            bucket["sum_return_pct"] += return_pct
            if return_pct > 0:
                bucket["hits"] += 1

    rows: list[dict[str, Any]] = []
    for row in grouped.values():
        for horizon in HORIZONS:
            key = f"t{horizon}"
            bucket = row[key]
            samples = int(bucket["samples"])
            if samples:
                bucket["win_rate_pct"] = round(bucket["hits"] / samples * 100, 1)
                bucket["avg_return_pct"] = round(bucket["sum_return_pct"] / samples, 3)
            else:
                bucket["win_rate_pct"] = None
                bucket["avg_return_pct"] = None

        ref_key = _horizon_key(HORIZONS[-1])
        for horizon in reversed(HORIZONS):
            candidate_key = _horizon_key(horizon)
            if row[candidate_key]["samples"] >= MIN_ADJUSTMENT_SAMPLES:
                ref_key = candidate_key
                break
        if row[ref_key]["samples"] < MIN_ADJUSTMENT_SAMPLES:
            ref_key = _horizon_key(HORIZONS[0])
        ref = row[ref_key]
        samples = int(ref["samples"])
        win_rate = _safe_float(ref.get("win_rate_pct"))
        avg_return = _safe_float(ref.get("avg_return_pct"))
        if samples < 3:
            verdict = "继续积累"
            adjustment = "不调整"
            score_delta = 0
        elif win_rate is not None and avg_return is not None and win_rate >= 60 and avg_return > 0:
            verdict = "保留加权"
            adjustment = "小幅加权"
            score_delta = 1
        elif win_rate is not None and avg_return is not None and win_rate <= 40 and avg_return < 0:
            verdict = "降权观察"
            adjustment = "自动降权"
            score_delta = -2
        else:
            verdict = "维持观察"
            adjustment = "不调整"
            score_delta = 0
        row["verdict"] = verdict
        row["adjustment"] = adjustment
        row["score_delta"] = score_delta
        row["adjustment_basis"] = ref_key.upper()
        rows.append(row)

    rows.sort(
        key=lambda item: (
            int((item.get(_horizon_key(HORIZONS[-1])) or {}).get("samples") or 0),
            _safe_float((item.get(_horizon_key(HORIZONS[-1])) or {}).get("avg_return_pct")) or -999,
            int((item.get(_horizon_key(HORIZONS[0])) or {}).get("samples") or 0),
            int(item.get("signals") or 0),
        ),
        reverse=True,
    )
    return rows


def _fmt_bucket(bucket: dict[str, Any]) -> str:
    samples = int(bucket.get("samples") or 0)
    if samples <= 0:
        return "样本不足"
    return f"{samples}次｜胜率 {bucket.get('win_rate_pct'):.0f}%｜均值 {bucket.get('avg_return_pct'):+.2f}%"


def _summary_lines(rows: list[dict[str, Any]], added_count: int) -> list[str]:
    if not rows:
        return [
            "- 事后验算刚启用：今天会先记录候选方向和价格，后续自动回看 T+30/T+60/T+90。",
            f"- 本次新增待验证信号 {added_count} 条；样本不足前不要把胜率当结论。",
        ]
    lines = [f"- 本次新增待验证信号 {added_count} 条；30/60/90天成绩单只用于校准系统，不直接触发买卖。"]
    for row in rows[:4]:
        first = _horizon_key(HORIZONS[0])
        second = _horizon_key(HORIZONS[1])
        third = _horizon_key(HORIZONS[2])
        lines.append(
            f"- {row.get('theme')}：{_horizon_label(HORIZONS[0])} {_fmt_bucket(row[first])}；{_horizon_label(HORIZONS[1])} {_fmt_bucket(row[second])}；{_horizon_label(HORIZONS[2])} {_fmt_bucket(row[third])}；结论：{row.get('verdict')}。"
        )
    return lines


def _build_adjustments(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    adjustments: dict[str, dict[str, Any]] = {}
    for row in rows:
        theme_key = str(row.get("theme_key") or "")
        if not theme_key:
            continue
        score_delta = int(row.get("score_delta") or 0)
        if score_delta == 0:
            continue
        adjustments[theme_key] = {
            "theme": row.get("theme"),
            "verdict": row.get("verdict"),
            "adjustment": row.get("adjustment"),
            "score_delta": score_delta,
            "basis": row.get("adjustment_basis"),
        }
    return adjustments


def _leaderboard_basis(row: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    basis_key = str(row.get("adjustment_basis") or "").lower()
    if basis_key in {_horizon_key(horizon) for horizon in HORIZONS}:
        bucket = row.get(basis_key) or {}
        if int(bucket.get("samples") or 0) > 0:
            return basis_key, bucket
    best_key = _horizon_key(HORIZONS[0])
    best_bucket = row.get(best_key) or {}
    for horizon in HORIZONS:
        key = _horizon_key(horizon)
        bucket = row.get(key) or {}
        if int(bucket.get("samples") or 0) > int(best_bucket.get("samples") or 0):
            best_key = key
            best_bucket = bucket
    return best_key, best_bucket


def _build_industry_leaderboard(rows: list[dict[str, Any]]) -> dict[str, Any]:
    leaderboard_rows: list[dict[str, Any]] = []
    for row in rows:
        basis_key, bucket = _leaderboard_basis(row)
        samples = int(bucket.get("samples") or 0)
        win_rate = _safe_float(bucket.get("win_rate_pct"))
        avg_return = _safe_float(bucket.get("avg_return_pct"))
        if samples <= 0 or win_rate is None or avg_return is None:
            continue
        rank_score = round(win_rate / 10 + avg_return + min(samples, 6) * 0.25, 3)
        if samples < MIN_ADJUSTMENT_SAMPLES:
            action = "继续积累样本"
        elif win_rate >= 60 and avg_return > 0:
            action = "优先保留权重"
        elif win_rate <= 40 and avg_return < 0:
            action = "降权复盘"
        else:
            action = "等待二次确认"
        leaderboard_rows.append(
            {
                "theme_key": row.get("theme_key"),
                "theme": row.get("theme"),
                "signals": row.get("signals", 0),
                "basis": basis_key.upper(),
                "samples": samples,
                "win_rate_pct": round(win_rate, 1),
                "avg_return_pct": round(avg_return, 3),
                "rank_score": rank_score,
                "verdict": row.get("verdict"),
                "action": action,
            }
        )

    leaderboard_rows.sort(
        key=lambda item: (
            int(item.get("samples") or 0) >= MIN_ADJUSTMENT_SAMPLES,
            _safe_float(item.get("rank_score")) or -999,
            int(item.get("samples") or 0),
        ),
        reverse=True,
    )
    if not leaderboard_rows:
        lines = ["- 行业雷达命中率榜还在积累样本；不要用单日涨跌下结论。"]
    else:
        lines = []
        for item in leaderboard_rows[:3]:
            lines.append(
                f"- {item.get('theme')}：{item.get('basis')} 样本 {item.get('samples')}，胜率 {item.get('win_rate_pct'):.0f}%，均值 {item.get('avg_return_pct'):+.2f}%，动作：{item.get('action')}。"
            )
    return {
        "rows": leaderboard_rows,
        "lines": lines,
        "best": leaderboard_rows[0] if leaderboard_rows else None,
        "worst": leaderboard_rows[-1] if leaderboard_rows else None,
    }


def _latest_completed_observation(signal: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    observations = signal.get("observations") or {}
    for horizon in reversed(HORIZONS):
        key = _horizon_key(horizon)
        obs = observations.get(key) or {}
        if _safe_float(obs.get("return_pct")) is not None:
            return key.upper(), obs
    return None


def _mistake_reason(signal: dict[str, Any], return_pct: float) -> str:
    priority = str(signal.get("priority") or "")
    source = str(signal.get("source") or "")
    score = _safe_float(signal.get("score")) or 0.0
    if "追高" in priority or "冲刺" in priority:
        return "追高风险"
    if source == "industry_radar":
        return "行业逻辑未兑现"
    if score >= 10 or priority in {"高", "今日关注", "每日必看", "watch"}:
        return "信号升级过早"
    if return_pct <= -8:
        return "价格确认失败"
    return "证据不足"


def _mistake_lesson(reason: str) -> str:
    lessons = {
        "追高风险": "后续先看回撤和成交确认，不把情绪高点当作加仓点。",
        "行业逻辑未兑现": "同类行业先确认政策、订单和价格三项，不让故事直接升级成交易。",
        "信号升级过早": "先留在观察层，等价格和新闻复核后再提高权重。",
        "价格确认失败": "降低该主题权重，避免把短期叙事当作趋势。",
        "证据不足": "补充更多来源和价格验证，样本不够时只观察。",
    }
    return lessons.get(reason, "先复核假设，再决定是否继续跟踪。")


def _build_mistake_reviews(signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    reviews: list[dict[str, Any]] = []
    for signal in signals:
        latest = _latest_completed_observation(signal)
        if latest is None:
            continue
        horizon, observation = latest
        return_pct = _safe_float(observation.get("return_pct"))
        if return_pct is None or return_pct >= 0:
            continue
        reason = _mistake_reason(signal, return_pct)
        reviews.append(
            {
                "theme_key": signal.get("theme_key"),
                "theme": signal.get("theme"),
                "code": signal.get("code"),
                "name": signal.get("name") or signal.get("code"),
                "created_at_utc": signal.get("created_at_utc"),
                "source": signal.get("source"),
                "horizon": horizon,
                "return_pct": round(return_pct, 3),
                "reason": reason,
                "lesson": _mistake_lesson(reason),
                "status": "待复盘",
            }
        )
    reviews.sort(key=lambda item: _safe_float(item.get("return_pct")) or 0)
    return reviews[:12]


def _build_mistake_summary(reviews: list[dict[str, Any]]) -> dict[str, Any]:
    by_reason: dict[str, int] = {}
    for item in reviews:
        reason = str(item.get("reason") or "未分类")
        by_reason[reason] = by_reason.get(reason, 0) + 1
    if not reviews:
        lines = ["- 错误复盘库暂无完成窗口的负向样本；继续积累，不急着下结论。"]
    else:
        top_reason = max(by_reason, key=lambda reason: by_reason[reason])
        lines = [f"- 错误复盘库记录 {len(reviews)} 条负向样本；最多的问题是：{top_reason}。"]
        for item in reviews[:2]:
            lines.append(
                f"- {item.get('theme')} / {item.get('name')}：{item.get('horizon')} {item.get('return_pct'):+.2f}%，{item.get('reason')}；{item.get('lesson')}"
            )
    return {"total": len(reviews), "by_reason": by_reason, "lines": lines}


def build_signal_validation(
    *,
    generated_at: datetime,
    portfolio_payload: dict[str, Any],
    execution_checks: dict[str, Any] | None,
    path: Path = VALIDATION_PATH,
) -> dict[str, Any]:
    now = generated_at.replace(tzinfo=None, microsecond=0)
    state = _load_state(path)
    signals = _trim_signals(list(state.get("signals") or []), now)
    quote_by_code = _quote_map(execution_checks)
    _observe_existing(signals, quote_by_code, now)
    entries = _candidate_entries(portfolio_payload, quote_by_code)
    added_count = _add_current_signals(signals, entries, now)
    signals = _trim_signals(signals, now)
    rows = _summarize(signals)
    industry_leaderboard = _build_industry_leaderboard(rows)
    mistake_reviews = _build_mistake_reviews(signals)
    mistake_summary = _build_mistake_summary(mistake_reviews)

    output = {
        "version": 1,
        "updated_at_utc": now.isoformat(),
        "signals": signals,
        "rows": rows,
        "industry_leaderboard": industry_leaderboard,
        "mistake_reviews": mistake_reviews,
        "mistake_summary": mistake_summary,
        "adjustments": _build_adjustments(rows),
        "lines": _summary_lines(rows, added_count),
        "added_count": added_count,
        "signal_count": len(signals),
        "note": "这是基于系统每日候选信号和后续价格表现的事后验算，不是收益保证，也不是自动交易指令；样本满足后会对长期低命中的主题自动降权。",
    }
    _save_state(output, path)
    return output


def render_signal_validation_markdown(validation: dict[str, Any]) -> str:
    lines = ["## 事后验算与命中率复盘", ""]
    lines.extend(validation.get("lines") or ["- 暂无验算数据。"])
    rows = validation.get("rows") or []
    if rows:
        horizon_labels = " | ".join(_horizon_label(horizon) for horizon in HORIZONS)
        lines.extend(["", f"| 主题 | 信号数 | {horizon_labels} | 结论 | 权重 |", "|---|---:|---|---|---|---|---|"])
        for row in rows[:8]:
            buckets = " | ".join(_fmt_bucket(row[_horizon_key(horizon)]) for horizon in HORIZONS)
            lines.append(
                f"| {row.get('theme')} | {row.get('signals', 0)} | {buckets} | {row.get('verdict')} | {row.get('adjustment', '不调整')} |"
            )
    leaderboard = validation.get("industry_leaderboard") or {}
    lines.extend(["", "## 行业雷达命中率榜", ""])
    lines.extend(leaderboard.get("lines") or ["- 行业雷达命中率榜还在积累样本。"])
    leaderboard_rows = leaderboard.get("rows") or []
    if leaderboard_rows:
        lines.extend(["", "| 行业 | 窗口 | 样本 | 胜率 | 均值 | 动作 |", "|---|---|---:|---:|---:|---|"])
        for row in leaderboard_rows[:8]:
            lines.append(
                f"| {row.get('theme')} | {row.get('basis')} | {row.get('samples', 0)} | {row.get('win_rate_pct', 0):.0f}% | {row.get('avg_return_pct', 0):+.2f}% | {row.get('action')} |"
            )
    mistake_summary = validation.get("mistake_summary") or {}
    mistake_reviews = validation.get("mistake_reviews") or []
    lines.extend(["", "## 错误复盘库", ""])
    lines.extend(mistake_summary.get("lines") or ["- 暂无完成窗口的负向样本。"])
    if mistake_reviews:
        lines.extend(["", "| 主题 | 标的 | 窗口 | 结果 | 原因 | 下次规则 |", "|---|---|---|---:|---|---|"])
        for item in mistake_reviews[:8]:
            lines.append(
                f"| {item.get('theme')} | {item.get('name')} | {item.get('horizon')} | {item.get('return_pct', 0):+.2f}% | {item.get('reason')} | {item.get('lesson')} |"
            )
    lines.extend(["", f"> {validation.get('note') or '事后验算只用于校准系统，不代表未来收益。'}"])
    return "\n".join(lines).strip() + "\n"
