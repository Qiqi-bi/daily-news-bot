from __future__ import annotations

import unittest

from src.daily_news_bot.portfolio import _hard_risk_gate_lines


class HardRiskGateTest(unittest.TestCase):
    def test_hard_risk_gates_turn_config_into_plain_limits(self) -> None:
        lines = _hard_risk_gate_lines(
            {
                "profile": {"monthly_contribution_cny": 10000},
                "risk_controls": {
                    "hard_gates": {
                        "max_single_action_pct_of_monthly": 30,
                        "max_monthly_attack_add_pct_of_monthly": 20,
                        "confirmation_required_count": 3,
                        "confirmation_window_days": 14,
                        "max_monthly_action_count": 1,
                    }
                },
            },
            {},
        )

        text = "\n".join(lines)
        self.assertIn("¥3,000.00", text)
        self.assertIn("¥2,000.00", text)
        self.assertIn("14 天内 3 次确认", text)
        self.assertIn("每月最多 1 次主动调仓", text)


if __name__ == "__main__":
    unittest.main()
