from __future__ import annotations

from types import SimpleNamespace
import unittest

from src.daily_news_bot.industry_radar import build_industry_radar


class IndustryRadarFactsTest(unittest.TestCase):
    def test_default_fact_library_is_kept_when_custom_config_overrides_one_field(self) -> None:
        radar = build_industry_radar(
            {
                "industry_radar": {
                    "items": [
                        {
                            "id": "semiconductor_materials",
                            "watch": "自定义：只看价格、订单和出口限制。",
                        }
                    ]
                }
            },
            [],
            [{"theme_keys": ["semiconductor"]}],
            [{"theme_key": "semiconductor", "priority": "高", "score": 9}],
        )

        row = next(item for item in radar["rows"] if item["id"] == "semiconductor_materials")
        self.assertEqual(row["watch"], "自定义：只看价格、订单和出口限制。")
        self.assertIn("不可替代", row["fact_summary"])
        self.assertIn("确认", row["facts"])
        self.assertGreaterEqual(row["score_card"]["policy"], 1)
        self.assertGreaterEqual(row["score_card"]["supply"], 1)

    def test_fact_library_uses_news_hits_for_daily_attention(self) -> None:
        cluster = SimpleNamespace(
            theme="半导体材料",
            tags=["semiconductor"],
            representative=SimpleNamespace(
                title="出口管制与库存紧张推高六氟化钨价格",
                summary="半导体前驱体出现供应约束和订单排队。",
                content="",
            ),
            articles=[],
        )

        radar = build_industry_radar({}, [cluster], [], [])
        row = next(item for item in radar["rows"] if item["id"] == "semiconductor_materials")

        self.assertEqual(row["status"], "今日关注")
        self.assertIn("六氟化钨", row["hits"])
        self.assertGreaterEqual(row["score_card"]["news"], 1)

    def test_sub_industry_radar_binds_to_portfolio_and_candidate_pool(self) -> None:
        cluster = SimpleNamespace(
            theme="电子特气",
            tags=["semiconductor"],
            representative=SimpleNamespace(
                title="电子级氦气供应紧张，半导体客户长协推进",
                summary="气源和提纯产线成为新约束。",
                content="",
            ),
            articles=[],
        )

        radar = build_industry_radar(
            {
                "holdings": [{"name": "半导体ETF", "code": "512480"}],
            },
            [cluster],
            [],
            [
                {
                    "theme_key": "semiconductor",
                    "priority": "高",
                    "score": 10,
                    "instruments": [{"name": "科创芯片ETF", "code": "588200"}],
                }
            ],
        )
        row = next(item for item in radar["rows"] if item["id"] == "helium_supply_chain")

        self.assertEqual(row["status"], "今日关注")
        self.assertIn("氦气", row["hits"])
        self.assertIn("半导体ETF(512480)", row["binding_summary"])
        self.assertIn("科创芯片ETF(588200)", row["binding_summary"])
        self.assertGreaterEqual(len(radar["rows"]), 18)

    def test_optical_interconnect_is_tracked_as_ai_infra_sub_industry(self) -> None:
        cluster = SimpleNamespace(
            theme="AI数据中心互联",
            tags=["ai", "semiconductor"],
            representative=SimpleNamespace(
                title="空心光纤、CPO与OCS推动AI数据中心光通信互联升级",
                summary="光模块和高速互联降低延迟、功耗和存储压力，成为算力集群新瓶颈。",
                content="",
            ),
            articles=[],
        )

        radar = build_industry_radar({}, [cluster], [], [])
        row = next(item for item in radar["rows"] if item["id"] == "optical_interconnect")

        self.assertEqual(row["status"], "今日关注")
        self.assertIn("空心光纤", row["hits"])
        self.assertIn("CPO", row["hits"])
        self.assertIn("AI数据中心", row["why"])
        self.assertIn("客户导入", row["verify"])
        self.assertGreaterEqual(row["score_card"]["news"], 1)


if __name__ == "__main__":
    unittest.main()
