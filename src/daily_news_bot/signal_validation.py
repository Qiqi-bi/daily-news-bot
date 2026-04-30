from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .config import ROOT_DIR


VALIDATION_PATH = ROOT_DIR / "outputs" / "signal_validation.json"
HORIZONS = (1, 5, 20)
MAX_SIGNALS = 500
KEEP_DAYS = 180
DEDUP_DAYS = 3


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
            key = f"t{horizon}"
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
                "t1": _empty_bucket(),
                "t5": _empty_bucket(),
                "t20": _empty_bucket(),
            },
        )
        row["signals"] += 1
        observations = signal.get("observations") or {}
        for horizon in HORIZONS:
            key = f"t{horizon}"
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

        ref = row["t5"] if row["t5"]["samples"] >= 3 else row["t1"]
        samples = int(ref["samples"])
        win_rate = _safe_float(ref.get("win_rate_pct"))
        avg_return = _safe_float(ref.get("avg_return_pct"))
        if samples < 3:
            verdict = "继续积累"
        elif win_rate is not None and avg_return is not None and win_rate >= 60 and avg_return > 0:
            verdict = "保留加权"
        elif win_rate is not None and avg_return is not None and win_rate <= 40 and avg_return < 0:
            verdict = "降权观察"
        else:
            verdict = "维持观察"
        row["verdict"] = verdict
        rows.append(row)

    rows.sort(
        key=lambda item: (
            int((item.get("t5") or {}).get("samples") or 0),
            _safe_float((item.get("t5") or {}).get("avg_return_pct")) or -999,
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
            "- 事后验算刚启用：今天会先记录候选方向和价格，后续自动回看 T+1/T+5/T+20。",
            f"- 本次新增待验证信号 {added_count} 条；样本不足前不要把胜率当结论。",
        ]
    lines = [f"- 本次新增待验证信号 {added_count} 条；命中率只用于校准系统，不直接触发买卖。"]
    for row in rows[:4]:
        lines.append(
            f"- {row.get('theme')}：T+1 {_fmt_bucket(row['t1'])}；T+5 {_fmt_bucket(row['t5'])}；结论：{row.get('verdict')}。"
        )
    return lines


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

    output = {
        "version": 1,
        "updated_at_utc": now.isoformat(),
        "signals": signals,
        "rows": rows,
        "lines": _summary_lines(rows, added_count),
        "added_count": added_count,
        "signal_count": len(signals),
        "note": "这是基于系统每日候选信号和后续价格表现的事后验算，不是收益保证，也不是自动交易指令。",
    }
    _save_state(output, path)
    return output


def render_signal_validation_markdown(validation: dict[str, Any]) -> str:
    lines = ["## 事后验算与命中率复盘", ""]
    lines.extend(validation.get("lines") or ["- 暂无验算数据。"])
    rows = validation.get("rows") or []
    if rows:
        lines.extend(["", "| 主题 | 信号数 | T+1 | T+5 | T+20 | 结论 |", "|---|---:|---|---|---|---|"])
        for row in rows[:8]:
            lines.append(
                f"| {row.get('theme')} | {row.get('signals', 0)} | {_fmt_bucket(row['t1'])} | {_fmt_bucket(row['t5'])} | {_fmt_bucket(row['t20'])} | {row.get('verdict')} |"
            )
    lines.extend(["", f"> {validation.get('note') or '事后验算只用于校准系统，不代表未来收益。'}"])
    return "\n".join(lines).strip() + "\n"
