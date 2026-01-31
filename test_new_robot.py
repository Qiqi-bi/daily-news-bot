#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新版飞书机器人功能
"""

import os
import sys
import logging

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 从daily_news_bot.py导入相关函数
from daily_news_bot import get_access_token, send_to_feishu

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_new_robot():
    """
    测试新版飞书机器人
    """
    print("🚀 开始测试新版飞书机器人...")
    
    # 检查必要的环境变量
    app_id = os.environ.get('LARK_APP_ID', 'YOUR_LARK_APP_ID_HERE')
    app_secret = os.environ.get('LARK_APP_SECRET', 'YOUR_LARK_APP_SECRET_HERE')
    
    print(f"📋 使用的App ID: {app_id}")
    print(f"📋 使用的App Secret: {'*' * len(app_secret) if app_secret else '未设置'}")
    
    # 尝试获取访问令牌
    print("\n🔑 正在获取访问令牌...")
    access_token = get_access_token()
    
    if not access_token:
        print("❌ 获取访问令牌失败，请检查App ID和App Secret是否正确")
        return False
    
    print("✅ 访问令牌获取成功")
    
    # 准备测试消息
    test_message = """# 🤖 新版AI新闻机器人已上线

## 🌟 功能升级
- ✅ 支持应用认证方式
- ✅ 更丰富的消息格式
- ✅ 智能去重和情绪分析
- ✅ 实时资产价格注入

## 📅 一日三报
- 🌅 早报 (08:00): 覆盖美股收盘、昨夜欧美大事
- 🌞 午报 (13:00): 覆盖A股/港股午间动态
- 🌆 晚报 (21:00): 覆盖欧股开盘、美股盘前动态

## 📊 智能分析
- 🔥 情绪评分系统 (-10 到 +10)
- 💰 实时资产价格注入
- 📈 股市影响预测
- 🌏 对中国影响分析

---
*测试时间：{}*
*新版AI新闻机器人 v2.0*""".format("2026-01-30")

    # 发送测试消息
    print("\n📤 正在发送测试消息到飞书...")
    success = send_to_feishu(test_message)
    
    if success:
        print("🎉 新版机器人测试成功！消息已发送到飞书")
        return True
    else:
        print("❌ 新版机器人测试失败！")
        return False

if __name__ == "__main__":
    success = test_new_robot()
    if success:
        print("\n✅ 新版飞书机器人功能测试完成")
    else:
        print("\n❌ 新版飞书机器人功能测试失败")
        print("💡 请检查：")
        print("   1. App ID 和 App Secret 是否正确")
        print("   2. 飞书应用是否已安装到目标群组")
        print("   3. 应用是否具有发送消息的权限")
        print("   4. LARK_CHAT_ID 或 LARK_USER_ID 环境变量是否设置")