#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试飞书消息格式的脚本
"""

import requests
import json
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 使用新的应用认证方式，不再需要webhook URL
pass

def test_send_to_feishu():
    """
    测试发送格式化的消息到飞书
    """
    # 创建测试消息内容
    test_message = """### [🔥+7] 1. [点击直达：全球央行宣布降息刺激经济 (当前价格：$102,340)](https://example.com/news1)
- **📅 来源**：国际财经
- **📝 核心事实**：多国央行联合降息以刺激经济增长

#### 📊 深度研报
* **🇨🇳 对中国短期影响**：流动性增加，A股有望受益
* **🔮 对中国长期影响**：推动结构性改革，促进内循环发展
* **📈 股市影响 (A股/港股/美股)**：
    * *利好/利空板块*：银行、地产、消费板块
    * *底层逻辑*：资金成本下降，企业盈利预期改善

---
### [🔥+5] 2. [点击直达：科技巨头发布革命性AI芯片](https://example.com/news2)
- **📅 来源**：科技前沿
- **📝 核心事实**：新一代AI芯片性能提升10倍

#### 📊 深度研报
* **🇨🇳 对中国短期影响**：刺激科技股上涨，吸引资本流入
* **🔮 对中国长期影响**：加速AI产业发展，提升国际竞争力
* **📈 股市影响 (A股/港股/美股)**：
    * *利好/利空板块*：半导体、AI、云计算
    * *底层逻辑*：技术突破带动产业链升级

---
### [❄️-3] 3. [点击直达：国际贸易摩擦加剧](https://example.com/news3)
- **📅 来源**：国际政治
- **📝 核心事实**：多国贸易争端持续升级

#### 📊 深度研报
* **🇨🇳 对中国短期影响**：出口企业面临压力，市场情绪谨慎
* **🔮 对中国长期影响**：推动自主创新，加速内循环转型
* **📈 股市影响 (A股/港股/美股)**：
    * *利好/利空板块*：出口导向型企业承压
    * *底层逻辑*：贸易不确定性影响企业盈利预期

---"""

    # 构建消息内容
    card_content = {
        "config": {
            "wide_screen_mode": True
        },
        "elements": [{
            "tag": "markdown",
            "content": test_message
        }],
        "header": {
            "template": "blue",
            "title": {
                "content": "🌍 全球情报与金融分析日报",
                "tag": "plain_text"
            }
        }
    }

    payload = {
        "msg_type": "interactive",
        "card": card_content
    }

    try:
        logger.info("正在发送测试消息到飞书...")
        # 使用新的应用认证方式发送消息
        from daily_news_bot import send_to_feishu
        success = send_to_feishu(test_message)
        
        if success:
            logger.info("✅ 测试消息成功发送到飞书群！")
            print("排版测试完成，消息已发送到飞书")
        else:
            logger.error("飞书API返回错误")
            print("发送失败")
            
    except Exception as e:
        logger.error(f"发送飞书消息异常: {e}")
        print(f"发送失败: {e}")

if __name__ == "__main__":
    test_send_to_feishu()