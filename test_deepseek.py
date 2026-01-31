#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试DeepSeek API连接
"""

import requests
import json
import logging

# 配置
API_KEY = "sk-1034e8c1dad248ea90ff08fddf2b5bd5"
BASE_URL = "https://api.deepseek.com"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_deepseek():
    """测试DeepSeek API连接"""
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": "Hello, this is a test message."}
        ],
        "temperature": 0.7,
        "max_tokens": 100
    }
    
    try:
        logger.info("正在测试DeepSeek API连接...")
        response = requests.post(
            f"{BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            logger.info("✅ DeepSeek API连接成功!")
            print(f"Response: {content}")
            return True
        else:
            logger.error(f"❌ DeepSeek API连接失败: {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ DeepSeek API连接异常: {e}")
        return False

if __name__ == "__main__":
    test_deepseek()