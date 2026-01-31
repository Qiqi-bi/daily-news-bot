#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Setup and Run Script for Daily News Bot
自动安装依赖并运行新闻机器人
"""

import subprocess
import sys
import os

def install_requirements():
    """安装项目依赖"""
    print("🔍 检查并安装项目依赖...")
    
    # 检查是否已安装所需包
    required_packages = [
        'requests',
        'feedparser',
        'lxml'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"📦 安装缺失的包: {', '.join(missing_packages)}")
        for package in missing_packages:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print("✅ 依赖安装完成")
    else:
        print("✅ 所有依赖已安装")

def run_news_bot():
    """运行新闻机器人"""
    print("🚀 启动每日新闻机器人...")
    
    # 导入并运行主程序
    try:
        from daily_news_bot import main
        main()
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("尝试直接执行 daily_news_bot.py...")
        subprocess.run([sys.executable, "daily_news_bot.py"])

if __name__ == "__main__":
    print("🌟 Daily News Bot 自动安装与运行脚本")
    print("=" * 50)
    
    # 安装依赖
    install_requirements()
    
    print()
    
    # 运行机器人
    run_news_bot()
    
    print("\n✨ 程序执行完成")