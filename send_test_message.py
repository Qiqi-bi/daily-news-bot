#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
向指定飞书群组发送测试消息
使用您提供的Chat ID: YOUR_LARK_CHAT_ID_HERE
"""

import os
import requests
import json
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 从环境变量获取配置
APP_ID = os.environ.get('LARK_APP_ID', 'YOUR_LARK_APP_ID_HERE')
APP_SECRET = os.environ.get('LARK_APP_SECRET', 'YOUR_LARK_APP_SECRET_HERE')

# 使用您提供的Chat ID
CHAT_ID = os.environ.get('LARK_CHAT_ID', 'YOUR_LARK_CHAT_ID_HERE')

def get_access_token():
    """
    获取飞书访问令牌
    """
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {
        "Content-Type": "application/json; charset=utf-8"
    }
    data = {
        "app_id": APP_ID,
        "app_secret": APP_SECRET
    }

    try:
        logger.info("正在获取飞书访问令牌...")
        response = requests.post(url, headers=headers, json=data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('code') == 0:
                access_token = result.get('tenant_access_token')
                logger.info("✅ 成功获取飞书访问令牌")
                return access_token
            else:
                logger.error(f"获取访问令牌失败: {result.get('msg')}")
                return ""
        else:
            logger.error(f"HTTP错误: {response.status_code} - {response.text}")
            return ""
    except Exception as e:
        logger.error(f"获取访问令牌异常: {e}")
        return ""

def send_message_to_group():
    """
    向指定群组发送测试消息
    """
    # 获取访问令牌
    access_token = get_access_token()
    if not access_token:
        logger.error("❌ 无法获取访问令牌，消息发送失败")
        return False

    # 构建消息内容
    message_content = {
        "config": {
            "wide_screen_mode": True,
            "update_multi": False,
            "enable_forward": True
        },
        "header": {
            "template": "blue",
            "title": {
                "content": "🎉 AI新闻机器人已连接",
                "tag": "plain_text"
            }
        },
        "elements": [
            {
                "tag": "markdown",
                "content": "**✅ 机器人连接测试成功！**\n\n您已成功配置AI新闻机器人，现在可以接收每日新闻推送。\n\n**功能预览**：\n- 🌅 早报 (08:00): 覆盖美股收盘、昨夜欧美大事\n- 🌞 午报 (13:00): 覆盖A股/港股午间动态\n- 🌆 晚报 (21:00): 覆盖欧股开盘、美股盘前动态\n- 📊 智能分析: 情绪评分、价格注入、股市影响预测"
            },
            {
                "tag": "hr"
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {
                            "content": "开始接收新闻",
                            "tag": "plain_text"
                        },
                        "type": "primary",
                        "value": {}
                    }
                ]
            }
        ]
    }

    # 发送消息到群组
    url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Bearer {access_token}"
    }
    
    data = {
        "receive_id": CHAT_ID,
        "msg_type": "interactive",
        "content": json.dumps(message_content, ensure_ascii=False)
    }

    try:
        logger.info(f"正在向群组 'ai每日信息流' (ID: {CHAT_ID}) 发送测试消息...")
        response = requests.post(url, headers=headers, json=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('code') == 0:
                logger.info("✅ 消息成功发送到飞书群组！")
                return True
            else:
                logger.error(f"飞书API返回错误: {result.get('msg')} (code: {result.get('code')})")
                return False
        else:
            logger.error(f"HTTP错误: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"发送消息异常: {e}")
        return False

if __name__ == "__main__":
    print("🚀 开始发送测试消息到 'ai每日信息流' 群组...")
    print(f"📋 群组ID: {CHAT_ID}")
    print()
    
    success = send_message_to_group()
    
    if success:
        print()
        print("🎉 成功！机器人现在可以向您的群组发送消息了。")
        print("🤖 机器人将按照设定的时间自动发送每日新闻。")
    else:
        print()
        print("❌ 发送失败，请检查：")
        print("   1. 机器人是否已加入到 'ai每日信息流' 群组")
        print("   2. 应用是否具有发送消息的权限")
        print("   3. Chat ID是否正确")