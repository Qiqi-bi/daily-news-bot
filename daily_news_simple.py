#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版每日新闻机器人 - 用于验证核心功能
"""

import requests
import json
import logging

# 配置
API_KEY = "sk-8264d22f73804f6a9f924cfeb1816c8b"
BASE_URL = "https://dashscope.aliyuncs.com/api/v1"
# 使用新的应用认证方式，不再需要webhook URL
pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_sample_news():
    """返回示例新闻数据"""
    return [
        {
            'title': '全球AI监管框架取得重大进展',
            'summary': '欧盟今日通过新的人工智能法案，对高风险AI系统实施更严格的监管措施。',
            'link': 'https://example.com/ai-regulation'
        },
        {
            'title': '中国AI芯片产业加速发展',
            'summary': '国内AI芯片企业宣布获得重要技术突破，7nm工艺量产在即。',
            'link': 'https://example.com/china-ai-chip'
        }
    ]

def analyze_with_llm(news_items):
    """调用LLM进行分析"""
    if not news_items:
        return "今日无重要新闻更新。"
    
    # 构建新闻内容
    news_content = ""
    for i, item in enumerate(news_items[:2], 1):
        news_content += f"{i}. **标题**: {item['title']}\n"
        news_content += f"   **摘要**: {item['summary']}\n"
        news_content += f"   **链接**: {item['link']}\n\n"
    
    # System Prompt
    system_prompt = """你是一位专业的全球情报与金融分析专家。请将以下新闻改写为专业的情报分析报告，严格按照以下格式：

### 1. [点击直达：<新闻标题>](<URL链接>)
- **📅 来源**：<媒体名>
- **📝 核心事实**：<30字简述事件>

#### 📊 深度研报
* **🇨🇳 对中国短期影响**：<即时政策/民生/舆论冲击>
* **🔮 对中国长期影响**：<未来1-3年战略/结构影响>
* **📈 股市影响 (A股/港股/美股)**：
    * *利好/利空板块*：<具体概念股或行业>
    * *底层逻辑*：<资金面或基本面分析>

---
(请以此格式列出所有新闻，确保标题是蓝色可点击的Markdown链接)"""
    
    user_message = f"请分析以下新闻：\n\n{news_content}"
    
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        "model": "qwen-max",
        "input": {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
        },
        "parameters": {
            "temperature": 0.7,
            "max_tokens": 1000
        }
    }
    
    try:
        logger.info("正在调用Qwen API进行新闻分析...")
        response = requests.post(
            f"{BASE_URL}/services/aigc/text-generation/generation",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            analysis = result['choices'][0]['message']['content']
            logger.info("LLM分析完成")
            return analysis
        else:
            logger.error(f"LLM API调用失败: {response.status_code}")
            # 返回简化版本
            return f"### 1. [点击直达：{news_items[0]['title']}]({news_items[0]['link']})\n- **📅 来源**: 示例新闻\n- **📝 核心事实**: {news_items[0]['summary'][:30]}...\n\n#### 📊 深度研报\n* **🇨🇳 对中国短期影响**: 待分析\n* **🔮 对中国长期影响**: 待分析\n* **📈 股市影响 (A股/港股/美股)**:\n    * *利好/利空板块*: 待分析\n    * *底层逻辑*: 待分析\n\n---"
            
    except Exception as e:
        logger.error(f"LLM API调用异常: {e}")
        return f"### 1. [点击直达：{news_items[0]['title']}]({news_items[0]['link']})\n- **📅 来源**: 示例新闻\n- **📝 核心事实**: {news_items[0]['summary'][:30]}...\n\n#### 📊 深度研报\n* **🇨🇳 对中国短期影响**: 待分析\n* **🔮 对中国长期影响**: 待分析\n* **📈 股市影响 (A股/港股/美股)**:\n    * *利好/利空板块*: 待分析\n    * *底层逻辑*: 待分析\n\n---"

def send_to_feishu(message):
    """发送到飞书"""
    card_content = {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "blue",
            "title": {"content": "🌍 全球情报与金融分析日报", "tag": "plain_text"}
        },
        "elements": [{"tag": "markdown", "content": message[:15000]}]
    }
    
    payload = {"msg_type": "interactive", "card": card_content}
    
    try:
        # 使用新的应用认证方式发送消息
        from daily_news_bot import send_to_feishu
        success = send_to_feishu(message[:15000])
        if success:
            logger.info("✅ 消息成功发送到飞书群！")
            return True
        else:
            logger.error("飞书API返回错误")
            return False
    except Exception as e:
        logger.error(f"发送飞书消息异常: {e}")
        return False

def main():
    logger.info("🚀 启动简化版每日新闻机器人...")
    
    # 获取新闻
    news_items = get_sample_news()
    logger.info(f"获取到 {len(news_items)} 条示例新闻")
    
    # LLM分析
    analysis = analyze_with_llm(news_items)
    
    # 发送到飞书
    success = send_to_feishu(analysis)
    
    if success:
        logger.info("🎉 简化版每日新闻分析任务完成！")
    else:
        logger.error("❌ 简化版每日新闻分析任务失败")

if __name__ == "__main__":
    main()