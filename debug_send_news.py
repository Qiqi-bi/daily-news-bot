#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试版 - 发送新闻模板到飞书群
使用Webhook方式发送
"""

import requests
import json

def debug_send_news_template_to_feishu():
    """
    使用Webhook发送新闻模板到飞书群（带调试信息）
    """
    # 您提供的Webhook地址
    webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/5379d0cd-e7d6-41cf-9465-14956a56cf45"
    
    # 新闻模板内容
    news_template = {
        "msg_type": "text",
        "content": {
            "text": """🌍 最终版新闻模板

★ 每日全球情报与金融分析报告

◆ 🔥+8] 1. 【全球AI芯片需求激增，台积电订单爆满】
- 来源：科技日报
- 核心事实：台积电AI芯片订单增长超过200%
- 影响分析：
  * 短期影响：可能加剧芯片供应紧张局面，推动国产替代进程加速
  * 长期影响：倒逼国内半导体产业链升级，加速自主可控进程
  * 股市影响：利好半导体设备、材料股，传统芯片设计公司承压

----------------------------------------
◆ 🔥+6] 2. 【央行宣布降准0.25个百分点刺激经济】
- 来源：金融时报
- 核心事实：中国人民银行意外宣布降准释放流动性
- 影响分析：
  * 短期影响：利好股市债市，降低融资成本，提振市场信心
  * 长期影响：货币政策宽松周期开启，支持实体经济发展
  * 股市影响：银行、地产、基建等低估值板块受益明显

----------------------------------------
◆ 🔥+4] 3. 【特斯拉发布新一代自动驾驶芯片】
- 来源：汽车科技
- 核心事实：FSD芯片性能提升10倍，成本降低30%
- 影响分析：
  * 短期影响：推动智能驾驶板块上涨，引发新一轮技术竞赛
  * 长期影响：加速自动驾驶商业化落地，重塑出行生态格局
  * 股市影响：自动驾驶、激光雷达、高精度地图等相关概念受益"""
        }
    }
    
    print("📝 准备发送的消息内容:")
    print(news_template["content"]["text"])
    print("\n" + "="*50)
    
    try:
        # 发送POST请求到飞书Webhook
        print("📤 正在发送POST请求到Webhook...")
        response = requests.post(webhook_url, json=news_template)
        
        print(f"📊 HTTP响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"📋 API响应详情: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            if result.get("StatusCode") == 0 or result.get("code") == 0:
                print("✅ 消息已成功发送到飞书群！")
                print("💡 请注意：有时消息可能需要几秒钟才会出现在群聊中")
                return True
            else:
                print(f"❌ API返回非预期结果: {result}")
                return False
        else:
            print(f"❌ HTTP请求失败，状态码: {response.status_code}")
            print(f"❌ 错误详情: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 发送过程中发生异常: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔍 开始调试发送新闻模板到飞书群...")
    success = debug_send_news_template_to_feishu()
    if success:
        print("\n🎉 消息发送流程完成！")
        print("💡 如果您仍未在群中看到消息，请检查：")
        print("   1. 机器人是否仍在群中")
        print("   2. 网络延迟（有时消息需要几秒才显示）")
        print("   3. 群消息过滤设置")
    else:
        print("\n💥 消息发送失败！")