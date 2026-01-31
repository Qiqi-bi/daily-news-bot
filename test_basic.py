#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本 - 验证基本功能
"""

import requests
import json

# 使用新的应用认证方式，不再需要webhook URL
pass

def test_feishu():
    """测试飞书推送"""
    message = "### 🧪 测试消息\n- **📅 来源**: 测试\n- **📝 核心事实**: 这是一个测试消息\n\n#### 📊 深度研报\n* **🇨🇳 对中国短期影响**: 测试成功\n* **🔮 对中国长期影响**: 系统正常运行\n* **📈 股市影响 (A股/港股/美股)**:\n    * *利好/利空板块*: 科技股\n    * *底层逻辑*: 自动化系统测试\n\n---"
    
    card_content = {
        "config": {
            "wide_screen_mode": True
        },
        "header": {
            "template": "blue",
            "title": {
                "content": "🧪 Daily News Bot 测试",
                "tag": "plain_text"
            }
        },
        "elements": [
            {
                "tag": "markdown",
                "content": message
            }
        ]
    }
    
    payload = {
        "msg_type": "interactive",
        "card": card_content
    }
    
    try:
        # 使用新的应用认证方式发送消息
        from daily_news_bot import send_to_feishu
        success = send_to_feishu(message)
        if success:
            print("✅ 飞书测试消息发送成功！")
            return True
        else:
            print("❌ 飞书测试失败")
            return False
    except Exception as e:
        print(f"❌ 飞书测试异常: {e}")
        return False

if __name__ == "__main__":
    test_feishu()