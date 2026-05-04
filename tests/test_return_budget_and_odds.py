from __future__ import annotations

import unittest

from src.daily_news_bot.portfolio import _annual_objective_payload, _evaluate_fixed_buy_pool, _hard_reduce_candidates


class ReturnBudgetAndOddsTest(unittest.TestCase):
    def test_annual_objective_splits_return_budget_by_sleeve(self) -> None:
        payload = _annual_objective_payload(
            {
                "allocation_framework": {
                    "stable_core_target_pct": [35, 45],
                    "growth_core_target_pct": [15, 20],
                    "attack_target_pct": [20, 30],
                    "insurance_target_pct": [10, 15],
                    "reserve_target_pct": [0, 10],
                },
                "annual_objective": {
                    "return_assumptions_pct": {
                        "stable_core": [4, 6],
                        "growth_core": [8, 12],
                        "attack": [12, 18],
                        "insurance": [0, 6],
                        "reserve": [0, 2],
                    }
                },
            }
        )

        budget = payload["return_budget"]
        stable = next(row for row in budget["rows"] if row["key"] == "stable_core")
        attack = next(row for row in budget["rows"] if row["key"] == "attack")

        self.assertEqual(stable["target_mid_pct"], 40.0)
        self.assertEqual(stable["expected_return_mid_pct"], 5.0)
        self.assertEqual(stable["contribution_mid_pct"], 2.0)
        self.assertEqual(attack["target_mid_pct"], 25.0)
        self.assertEqual(attack["contribution_mid_pct"], 3.75)
        self.assertGreater(budget["estimated_return_contribution_pct_range"][1], 10)

    def test_fixed_buy_pool_rows_include_odds_and_confirmation_gate(self) -> None:
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
                "decision_cockpit": {
                    "action_amount_bands": {"buy_probe_cny": [800, 1500]},
                    "fixed_buy_pool": [
                        {
                            "code": "588930",
                            "name": "AI ETF",
                            "type": "ETF",
                            "role": "AI attack ETF",
                            "theme_key": "ai_attack",
                        }
                    ],
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
            {"items": [{"code": "588930", "change_pct": 0.8, "chase_risk": "\u4f4e", "liquidity_level": "\u6b63\u5e38"}]},
            [],
            [{"theme_key": "ai"}],
            trade_ledger={"enabled": True, "trades": []},
        )

        row = rows[0]
        odds = row["opportunity_score"]

        self.assertEqual(row["state"], "\u53ef\u4e70")
        self.assertEqual(odds["label"], "\u53ef\u590d\u6838")
        self.assertGreaterEqual(odds["confirmation_count"], odds["confirmation_required"])
        self.assertIn("expected_upside_pct_range", odds)
        self.assertIn("max_drawdown_pct", odds)

    def test_gold_overweight_with_profit_becomes_reduce_review(self) -> None:
        portfolio = {
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
                "gold_target_range_pct": [10, 15],
                "hard_gates": {"max_monthly_action_count": 2},
            },
            "decision_cockpit": {
                "action_amount_bands": {"reduce_small_cny": [1000, 2500]},
                "fixed_buy_pool": [
                    {
                        "code": "518880",
                        "name": "黄金ETF",
                        "type": "ETF",
                        "role": "保险仓",
                        "theme_key": "gold_insurance",
                    }
                ],
            },
            "holdings": [
                {"code": "518880", "name": "黄金ETF", "sleeve": "insurance", "weight_pct": 18.0},
            ],
        }
        portfolio_quotes = {
            "items": [
                {
                    "holding_name": "黄金ETF",
                    "code": "518880",
                    "actual_weight_pct": 18.0,
                    "unrealized_pnl_pct": 12.0,
                }
            ]
        }

        rows = _evaluate_fixed_buy_pool(
            portfolio,
            {
                "direct_ai_pct": 20.0,
                "growth_tech_pct": 35.0,
                "attack_pct": 20.0,
                "gold_pct": 18.0,
                "insurance_pct": 18.0,
                "stable_core_pct": 40.0,
                "growth_core_pct": 15.0,
            },
            portfolio_quotes,
            {"items": [{"code": "518880", "change_pct": 0.4, "chase_risk": "低", "liquidity_level": "正常"}]},
            [],
            [],
            trade_ledger={"enabled": True, "trades": []},
        )

        row = rows[0]

        self.assertEqual(row["state"], "减仓")
        self.assertEqual(row["action_tier"], "减仓复核")
        self.assertIn("黄金", row["reason"])
        self.assertIn("超过", row["reason"])

    def test_hard_reduce_candidates_include_overweight_gold_insurance(self) -> None:
        portfolio = {
            "risk_controls": {
                "single_attack_holding_cap_pct": 15,
                "gold_target_range_pct": [10, 15],
            },
            "decision_cockpit": {"action_amount_bands": {"reduce_small_cny": [1000, 2500]}},
            "holdings": [
                {"code": "518880", "name": "黄金ETF", "sleeve": "insurance", "weight_pct": 18.0},
            ],
        }
        portfolio_quotes = {
            "items": [
                {
                    "holding_name": "黄金ETF",
                    "code": "518880",
                    "actual_weight_pct": 18.0,
                    "unrealized_pnl_pct": 12.0,
                }
            ]
        }

        rows = _hard_reduce_candidates(
            portfolio,
            {"gold_pct": 18.0, "insurance_pct": 18.0, "direct_ai_pct": 20.0},
            portfolio_quotes,
        )

        self.assertEqual(rows[0]["code"], "518880")
        self.assertEqual(rows[0]["trigger"], "黄金超配")
        self.assertIn("保险仓", rows[0]["reason"])

    def test_growth_core_overweight_with_profit_becomes_reduce_review(self) -> None:
        portfolio = {
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
                "gold_target_range_pct": [10, 15],
                "hard_gates": {"max_monthly_action_count": 2},
            },
            "decision_cockpit": {
                "action_amount_bands": {"reduce_small_cny": [1000, 2500]},
                "fixed_buy_pool": [
                    {
                        "code": "159915",
                        "name": "创业板ETF易方达",
                        "type": "ETF",
                        "role": "成长底仓",
                        "theme_key": "growth_core",
                    }
                ],
            },
            "holdings": [
                {"code": "159915", "name": "创业板ETF易方达", "sleeve": "growth_core", "weight_pct": 24.0},
            ],
        }
        portfolio_quotes = {
            "items": [
                {
                    "holding_name": "创业板ETF易方达",
                    "code": "159915",
                    "actual_weight_pct": 24.0,
                    "unrealized_pnl_pct": 10.0,
                }
            ]
        }

        rows = _evaluate_fixed_buy_pool(
            portfolio,
            {
                "direct_ai_pct": 20.0,
                "growth_tech_pct": 48.0,
                "attack_pct": 20.0,
                "gold_pct": 10.0,
                "insurance_pct": 10.0,
                "stable_core_pct": 40.0,
                "growth_core_pct": 24.0,
            },
            portfolio_quotes,
            {"items": [{"code": "159915", "change_pct": 0.3, "chase_risk": "低", "liquidity_level": "正常"}]},
            [],
            [],
            trade_ledger={"enabled": True, "trades": []},
        )

        row = rows[0]

        self.assertEqual(row["state"], "减仓")
        self.assertEqual(row["action_tier"], "减仓复核")
        self.assertIn("成长底仓", row["reason"])
        self.assertIn("超过", row["reason"])

    def test_hard_reduce_candidates_include_overweight_growth_core(self) -> None:
        portfolio = {
            "allocation_framework": {"growth_core_target_pct": [15, 20]},
            "risk_controls": {"single_attack_holding_cap_pct": 15, "gold_target_range_pct": [10, 15]},
            "decision_cockpit": {"action_amount_bands": {"reduce_small_cny": [1000, 2500]}},
            "holdings": [
                {"code": "159915", "name": "创业板ETF易方达", "sleeve": "growth_core", "weight_pct": 24.0},
            ],
        }
        portfolio_quotes = {
            "items": [
                {
                    "holding_name": "创业板ETF易方达",
                    "code": "159915",
                    "actual_weight_pct": 24.0,
                    "unrealized_pnl_pct": 10.0,
                }
            ]
        }

        rows = _hard_reduce_candidates(
            portfolio,
            {"growth_core_pct": 24.0, "gold_pct": 10.0, "insurance_pct": 10.0, "direct_ai_pct": 20.0},
            portfolio_quotes,
        )

        self.assertEqual(rows[0]["code"], "159915")
        self.assertEqual(rows[0]["trigger"], "成长超配")
        self.assertIn("成长底仓", rows[0]["reason"])


if __name__ == "__main__":
    unittest.main()
