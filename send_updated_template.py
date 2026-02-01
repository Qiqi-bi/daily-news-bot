#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发送更新版新闻模板到飞书群
使用您提供的格式
"""

import requests
import json

def send_updated_news_template():
    """
    使用Webhook发送更新版新闻模板到飞书群
    """
    import os
    # 从环境变量获取Webhook地址
    webhook_url = os.environ.get('FEISHU_WEBHOOK_URL', '')
    if not webhook_url:
        print("❌ 未配置FEISHU_WEBHOOK_URL环境变量")
        return False
    
    # 更新版新闻模板内容
    news_template = {
        "msg_type": "text",
        "content": {
            "text": """### [🔥+8] 1. 点击直达：全球AI芯片需求激增，台积电订单爆满
📅 来源：科技日报
📝 核心事实：台积电AI芯片订单增长超过200%，产能严重不足，多家科技巨头排队等待供货。
#### 📊 深度研报
 🇨🇳 对中国短期影响：可能加剧芯片供应紧张局面，推动国产替代进程加速。
 🔮 对中国长期影响：倒逼国内半导体产业链升级，加速自主可控进程。
 📈 股市影响 (A股/港股/美股)：
     * 利好/利空板块：利好半导体设备、材料股，传统芯片设计公司承压。
     * 底层逻辑：AI需求驱动资本开支增加，上游设备材料率先受益。

----------------------------------------

### [🔥+6] 2. 点击直达：央行宣布降准0.25个百分点刺激经济
📅 来源：金融时报
📝 核心事实：中国人民银行意外宣布降准释放流动性，预计将释放约5000亿资金。
#### 📊 深度研报
 🇨🇳 对中国短期影响：利好股市债市，降低融资成本，提振市场信心。
 🔮 对中国长期影响：货币政策宽松周期开启，支持实体经济发展。
 📈 股市影响 (A股/港股/美股)：
     * 利好/利空板块：银行、地产、基建等低估值板块受益明显。
     * 底层逻辑：流动性改善提升风险偏好，低估值板块修复空间较大。

----------------------------------------

### [🔥+4] 3. 点击直达：特斯拉发布新一代自动驾驶芯片
📅 来源：汽车科技
📝 核心事实：FSD芯片性能提升10倍，成本降低30%，将推动自动驾驶商业化进程。
#### 📊 深度研报
 🇨🇳 对中国短期影响：推动智能驾驶板块上涨，引发新一轮技术竞赛。
 🔮 对中国长期影响：加速自动驾驶商业化落地，重塑出行生态格局。
 📈 股市影响 (A股/港股/美股)：
     * 利好/利空板块：自动驾驶、激光雷达、高精度地图等相关概念。
     * 底层逻辑：技术突破带动产业链价值重估，催生新商业模式。"""
        }
    }
    
    try:
        # 发送POST请求到飞书Webhook
        response = requests.post(webhook_url, json=news_template)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("StatusCode") == 0 or result.get("code") == 0:
                print("✅ 更新版新闻模板已成功发送到飞书群！")
                return True
            else:
                print(f"❌ 发送失败，响应内容: {result}")
                return False
        else:
            print(f"❌ HTTP请求失败，状态码: {response.status_code}, 错误信息: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 发送过程中发生异常: {str(e)}")
        return False

if __name__ == "__main__":
    print("正在发送更新版新闻模板到飞书群...")
    success = send_updated_news_template()
    if success:
        print("更新版新闻模板发送完成！")
    else:
        print("发送失败，请检查网络连接或Webhook地址是否正确。")