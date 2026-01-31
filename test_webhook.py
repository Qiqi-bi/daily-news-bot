#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试飞书Webhook是否正常工作
"""

import requests
import json

def test_webhook():
    """
    测试Webhook连接
    """
    webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/5379d0cd-e7d6-41cf-9465-14956a56cf45"
    
    # 简单的测试消息
    test_message = {
        "msg_type": "text",
        "content": {
            "text": "🔧 Webhook测试消息：此消息用于验证Webhook连接是否正常工作"
        }
    }
    
    try:
        print("正在发送测试消息到飞书群...")
        response = requests.post(
            webhook_url, 
            json=test_message,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"HTTP状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"API响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            if result.get("StatusCode") == 0 or result.get("code") == 0:
                print("✅ Webhook连接正常，消息发送成功！")
                return True
            else:
                print(f"❌ API返回错误: {result}")
                return False
        else:
            print(f"❌ HTTP请求失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 发送过程中发生异常: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_webhook()
    if success:
        print("\n🎉 Webhook测试成功！")
    else:
        print("\n💥 Webhook测试失败，请检查Webhook地址是否正确或是否具有发送权限。")