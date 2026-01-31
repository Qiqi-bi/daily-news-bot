#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新闻筛选功能
"""

import requests
import json
import logging

# 配置
API_KEY = "sk-1034e8c1dad248ea90ff08fddf2b5bd5"
BASE_URL = "https://api.deepseek.com"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_filtering():
    """测试新闻筛选功能"""
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }
    
    # 测试体育新闻（应该被过滤掉）
    sports_news = "**标题**: NBA Finals Game 7\n**摘要**: Lakers win championship against Celtics in thrilling finale\n**链接**: https://example.com/nba"
    
    system_prompt = """你是一位专业的全球情报与金融分析专家。你的任务是：
1. 首先判断新闻类型，根据以下规则决定是否分析：
   - **必选 (Keep)**：涉及中国的任何新闻(Politics, Economy, Tech)；全球地缘政治(US/EU/Middle East)对中国有潜在影响的；重大金融动向(Fed, Stocks, Crypto)和硬核科技(AI, Chips)
   - **必杀 (Discard/Ignore)**：体育(Sports, NBA, Soccer, Olympics)；娱乐(Entertainment, Celebs, Movies)；纯地方性社会新闻(Local Crimes, Accidents)
2. 如果新闻属于"必杀"类别，请直接返回："SKIP"
3. 如果新闻属于"必选"类别，请按照以下格式进行专业分析：

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
(请按此格式返回分析结果，如果新闻不符合要求则返回"SKIP")"""
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请分析以下新闻：\n\n{sports_news}"}
        ],
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    try:
        logger.info("正在测试体育新闻过滤功能...")
        response = requests.post(
            f"{BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            proxies=None,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            print(f"体育新闻测试结果: {content}")
            
            if "SKIP" in content.strip():
                logger.info("✅ 体育新闻过滤功能正常工作")
            else:
                logger.info("❌ 体育新闻过滤功能未正常工作")
                
        else:
            logger.error(f"❌ API调用失败: {response.status_code}")
            print(f"Error: {response.text}")
            
    except Exception as e:
        logger.error(f"❌ API调用异常: {e}")

    # 测试财经新闻（应该被保留）
    finance_news = "**标题**: US Federal Reserve Announces Interest Rate Decision\n**摘要**: Fed raises rates by 0.25% citing inflation concerns and economic growth\n**链接**: https://example.com/fed-rate"
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请分析以下新闻：\n\n{finance_news}"}
        ],
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    try:
        logger.info("正在测试财经新闻分析功能...")
        response = requests.post(
            f"{BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            proxies=None,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            print(f"财经新闻测试结果: {content[:200]}...")  # 只打印前200个字符
            
            if "SKIP" in content.strip():
                logger.info("❌ 财经新闻被错误过滤")
            else:
                logger.info("✅ 财经新闻分析功能正常工作")
                
        else:
            logger.error(f"❌ API调用失败: {response.status_code}")
            print(f"Error: {response.text}")
            
    except Exception as e:
        logger.error(f"❌ API调用异常: {e}")

if __name__ == "__main__":
    test_filtering()