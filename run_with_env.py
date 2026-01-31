#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用环境变量运行AI新闻机器人
"""

import os
import sys

# 设置环境变量
os.environ['LARK_APP_ID'] = 'cli_a9f6280dd5389bd8'
os.environ['LARK_APP_SECRET'] = 'VHN4Eag0koh7rwEkKXeHSgHzLnH1140x'
os.environ['LARK_CHAT_ID'] = 'oc_efc1ffb36158b2254f263e20b1fef768'

# 现在导入并运行主程序
import daily_news_bot

if __name__ == "__main__":
    print("🚀 正在启动AI新闻机器人...")
    print("📋 使用配置:")
    print(f"   App ID: {os.environ['LARK_APP_ID']}")
    print(f"   Chat ID: {os.environ['LARK_CHAT_ID']}")
    print()
    
    # 运行主程序
    daily_news_bot.main()