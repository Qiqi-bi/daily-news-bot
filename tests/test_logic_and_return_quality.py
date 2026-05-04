from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import json
import tempfile
import unittest

from src.daily_news_bot.portfolio import _evaluate_fixed_buy_pool, _score_candidate_pool
from src.daily_news_bot.signal_validation import build_signal_validation, render_signal_validation_markdown
from src.daily_news_bot.execution_checks import _configured_execution_assets


class LogicAndReturnQualityTest(unittest.TestCase):
    def test_candidate_score_exposes_evidence_chain_and_advice_tier(self) -> None:
        rows = _score_candidate_pool(
            {},
            [
                {
                    "theme_keys": ["ai_power_base"],
                    "priority": "立即确认",
                    "score": 12,
                    "certainty": "高",
                }
            ],
            {"attack_pct": 36.0, "stable_core_pct": 40.0},
        )

        row = next(item for item in rows if item["theme_key"] == "ai_power_base")

        self.assertEqual(row["advice_tier"], "观察底仓")
        self.assertGreaterEqual(row["evidence_chain"]["total"], 14)
        self.assertGreaterEqual(row["evidence_chain"]["policy"], 3)
        self.assertGreaterEqual(row["evidence_chain"]["supply"], 3)
        self.assertEqual(row["evidence_chain"]["discipline"], 5)
        self.assertIn("证据链", row["comment"])

    def test_fixed_pool_uses_action_tier_instead_of_plain_buy_for_long_term_theme(self) -> None:
        rows = _evaluate_fixed_buy_pool(
            {
                "profile": {"monthly_contribution_cny": 10000},
                "allocation_framework": {
                    "stable_core_target_pct": [35, 45],
                    "growth_core_target_pct": [15, 20],
                    "attack_target_pct": [20, 30],
                    "insurance_target_pct": [10, 15],
                },
                "risk_controls": {
                    "direct_ai_cap_pct": 35,
                    "growth_tech_cap_pct": 55,
                    "single_attack_holding_cap_pct": 15,
                    "hard_gates": {"max_monthly_action_count": 2},
                },
                "holdings": [],
            },
            {
                "direct_ai_pct": 0.0,
                "growth_tech_pct": 20.0,
                "attack_pct": 10.0,
                "gold_pct": 10.0,
                "stable_core_pct": 40.0,
                "growth_core_pct": 15.0,
            },
            None,
            {"items": [{"code": "560390", "change_pct": 0.2, "chase_risk": "低", "liquidity_level": "正常", "turnover_cny": 50_000_000}]},
            [{"theme_key": "ai_power_base", "priority": "高", "score": 8}],
            [{"theme_key": "ai_power_base"}],
            trade_ledger={"enabled": True, "trades": []},
        )

        row = next(item for item in rows if item["theme_key"] == "ai_power_base")

        self.assertEqual(row["action_tier"], "观察底仓")
        self.assertEqual(row["max_position_pct"], 3.0)
        self.assertIn("2%-3%", row["tier_reason"])

    def test_signal_validation_records_relative_return_against_benchmark(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "signal_validation.json"
            now = datetime(2026, 5, 1)
            created_at = now - timedelta(days=35)
            path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "signals": [
                            {
                                "id": "ai-power-base-560390",
                                "created_at_utc": created_at.isoformat(),
                                "source": "candidate_pool",
                                "theme": "AI电力底座",
                                "theme_key": "ai_power_base",
                                "priority": "高",
                                "score": 8,
                                "code": "560390",
                                "name": "电网设备ETF易方达",
                                "start_price": 1.0,
                                "benchmark_code": "510300",
                                "benchmark_name": "沪深300ETF",
                                "benchmark_start_price": 1.0,
                                "observations": {},
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            validation = build_signal_validation(
                generated_at=now,
                portfolio_payload={},
                execution_checks={
                    "items": [
                        {"code": "560390", "latest_price": 1.08},
                        {"code": "510300", "latest_price": 1.03},
                    ]
                },
                path=path,
            )
            row = validation["rows"][0]
            markdown = render_signal_validation_markdown(validation)

        self.assertEqual(row["t30"]["samples"], 1)
        self.assertEqual(row["t30"]["avg_relative_return_pct"], 5.0)
        self.assertEqual(row["t30"]["relative_win_rate_pct"], 100.0)
        self.assertIn("相对基准", markdown)

    def test_signal_validation_downgrades_absolute_winner_that_loses_to_benchmark(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "signal_validation.json"
            now = datetime(2026, 5, 1)
            created_at = now - timedelta(days=35)
            signals = []
            for index in range(3):
                signals.append(
                    {
                        "id": f"power-grid-{index}",
                        "created_at_utc": created_at.isoformat(),
                        "source": "candidate_pool",
                        "theme": "AI电力底座",
                        "theme_key": "ai_power_base",
                        "priority": "高",
                        "score": 8,
                        "code": "560390",
                        "name": "电网设备ETF",
                        "start_price": 1.0,
                        "benchmark_code": "510300",
                        "benchmark_name": "沪深300ETF",
                        "benchmark_start_price": 1.0,
                        "observations": {},
                    }
                )
            path.write_text(json.dumps({"version": 1, "signals": signals}, ensure_ascii=False), encoding="utf-8")

            validation = build_signal_validation(
                generated_at=now,
                portfolio_payload={},
                execution_checks={
                    "items": [
                        {"code": "560390", "latest_price": 1.03},
                        {"code": "510300", "latest_price": 1.08},
                    ]
                },
                path=path,
            )
            row = validation["rows"][0]

        self.assertEqual(row["t30"]["avg_return_pct"], 3.0)
        self.assertEqual(row["t30"]["avg_relative_return_pct"], -5.0)
        self.assertEqual(row["verdict"], "跑输基准降权")
        self.assertEqual(row["adjustment"], "相对收益降权")
        self.assertLess(row["score_delta"], 0)
        self.assertEqual(validation["adjustments"]["ai_power_base"]["score_delta"], row["score_delta"])

    def test_mistake_reviews_include_absolute_winner_that_loses_to_benchmark(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "signal_validation.json"
            now = datetime(2026, 5, 1)
            created_at = now - timedelta(days=35)
            path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "signals": [
                            {
                                "id": "power-grid-underperform",
                                "created_at_utc": created_at.isoformat(),
                                "source": "candidate_pool",
                                "theme": "AI电力底座",
                                "theme_key": "ai_power_base",
                                "priority": "高",
                                "score": 8,
                                "code": "560390",
                                "name": "电网设备ETF",
                                "start_price": 1.0,
                                "benchmark_code": "510300",
                                "benchmark_name": "沪深300ETF",
                                "benchmark_start_price": 1.0,
                                "observations": {},
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            validation = build_signal_validation(
                generated_at=now,
                portfolio_payload={},
                execution_checks={
                    "items": [
                        {"code": "560390", "latest_price": 1.03},
                        {"code": "510300", "latest_price": 1.08},
                    ]
                },
                path=path,
            )

        review = validation["mistake_reviews"][0]
        self.assertEqual(review["reason"], "跑输基准")
        self.assertEqual(review["relative_return_pct"], -5.0)
        self.assertIn("没有贡献超额收益", review["lesson"])

    def test_execution_checks_include_default_benchmarks_for_relative_review(self) -> None:
        assets = _configured_execution_assets({"holdings": [], "candidate_etf_pool": []})

        self.assertIn("510300", assets)
        self.assertIn("159915", assets)
        self.assertIn("518880", assets)
