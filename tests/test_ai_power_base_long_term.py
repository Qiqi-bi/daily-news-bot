from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import Any, cast
import unittest

from src.daily_news_bot.industry_radar import build_industry_radar
from src.daily_news_bot.main import _build_feishu_focus_lines
from src.daily_news_bot.models import Article, EventCluster
from src.daily_news_bot.portfolio import _fixed_buy_pool, _match_event_themes, _score_candidate_pool
from src.daily_news_bot.prediction_lens import build_prediction_lens


class AiPowerBaseLongTermTest(unittest.TestCase):
    def test_ai_power_base_is_a_long_term_radar_theme(self) -> None:
        radar = build_industry_radar(
            {},
            [],
            [],
            [
                {
                    "theme": "AI电力底座",
                    "theme_key": "ai_power_base",
                    "priority": "高",
                    "score": 6,
                    "instruments": [
                        {"name": "电力ETF", "code": "561560"},
                        {"name": "电网设备ETF易方达", "code": "560390"},
                    ],
                }
            ],
        )

        row = next(item for item in radar["rows"] if item["id"] == "ai_power_base")

        self.assertEqual(row["layer"], "secular")
        self.assertIn(row["status"], {"长期必看", "今日关注"})
        self.assertIn("1-5年", row["horizon"])
        self.assertIn("2%-3%", row["action"])
        self.assertIn("5%-8%", row["action"])
        self.assertTrue(any("长期主线" in line for line in radar["summary_lines"]))
        self.assertIn("电网设备ETF易方达(560390)", row["binding_summary"])

    def test_compute_power_news_routes_to_ai_power_base(self) -> None:
        cluster = SimpleNamespace(
            representative=SimpleNamespace(
                title="算电协同政策推进，西部绿色算力中心提高绿电占比",
                summary="数据中心用电、电网设备、液冷和储能订单成为AI产业链新约束。",
                source="官方源",
            )
        )

        themes = _match_event_themes(cast(Any, cluster))

        self.assertIn("ai_power_base", themes)
        self.assertIn("ai", themes)

    def test_candidate_pool_scores_ai_power_base_without_adding_ai_overlap(self) -> None:
        rows = _score_candidate_pool(
            {
                "candidate_etf_pool": [
                    {
                        "theme": "AI电力底座",
                        "theme_key": "ai_power_base",
                        "role": "长期主线底仓候选",
                        "caution": "只做2%-3%试探仓，不能当成AI进攻仓。",
                        "instruments": [
                            {"name": "电力ETF", "code": "561560"},
                            {"name": "电网设备ETF易方达", "code": "560390"},
                        ],
                    }
                ]
            },
            [{"theme_keys": ["ai_power_base"]}],
            {"attack_pct": 36.0},
        )

        row = rows[0]

        self.assertEqual(row["theme_key"], "ai_power_base")
        self.assertEqual(row["priority"], "高")
        self.assertGreaterEqual(row["fit_score"], 4)
        self.assertLessEqual(row["overlap_risk"], 2)
        self.assertIn("560390", row["instrument_refs"])

    def test_ai_power_base_defaults_exist_even_when_private_config_is_old(self) -> None:
        candidate_rows = _score_candidate_pool({}, [{"theme_keys": ["ai_power_base"]}], {"attack_pct": 36.0})
        fixed_pool = _fixed_buy_pool({})

        self.assertEqual(candidate_rows[0]["theme_key"], "ai_power_base")
        self.assertIn("560390", candidate_rows[0]["instrument_refs"])
        self.assertTrue(any(row["code"] == "560390" and row["theme_key"] == "ai_power_base" for row in fixed_pool))

    def test_feishu_focus_keeps_one_long_term_theme_visible(self) -> None:
        lines = _build_feishu_focus_lines(
            {
                "portfolio": {
                    "industry_radar": {
                        "rows": [
                            {
                                "name": "AI基础设施链",
                                "status": "每日必看",
                                "layer": "core",
                                "score_card_text": "16分/观察",
                                "watch": "海外AI龙头、半导体指数、国内算力政策。",
                            },
                            {
                                "name": "A股宽基/中国宏观",
                                "status": "每日必看",
                                "layer": "core",
                                "score_card_text": "13分/观察",
                                "watch": "人民币、成交量、宽基相对强弱。",
                            },
                            {
                                "name": "黄金/实际利率",
                                "status": "每日必看",
                                "layer": "core",
                                "score_card_text": "13分/观察",
                                "watch": "美元、美债和黄金仓位区间。",
                            },
                            {
                                "name": "AI电力底座/算电协同",
                                "status": "长期必看",
                                "layer": "secular",
                                "score_card_text": "长期主线",
                                "watch": "绿电、电网设备、储能、液冷和数据中心用电。",
                                "binding_summary": "候选：电力ETF(561560)、电网设备ETF易方达(560390)",
                            },
                        ]
                    }
                }
            }
        )

        self.assertEqual(len(lines), 3)
        self.assertTrue(any("AI电力底座" in line for line in lines))

    def test_prediction_lens_has_one_to_five_year_compute_power_card(self) -> None:
        article = Article(
            title="算电协同推动AI数据中心提高绿电和电网设备投入",
            url="https://example.com/a",
            source="official",
            category="policy",
            region="CN",
            source_weight=1.0,
            published_at=datetime(2026, 5, 1),
            summary="绿色算力、数据中心用电、液冷、储能和电力交易成为长期约束。",
            content="",
        )
        cluster = EventCluster(
            cluster_id="c1",
            theme="AI电力底座",
            articles=[article],
            score=10,
            tags=["technology", "energy", "policy"],
            credibility_label="高",
            confirmed_source_count=3,
        )

        lens = build_prediction_lens([cluster])
        card = lens["cards"][0]

        self.assertEqual(card["rule_key"], "ai_power_base_secular")
        self.assertIn("1-5年", card["window"])
        self.assertIn("2%-3%", card["discipline"])


if __name__ == "__main__":
    unittest.main()
