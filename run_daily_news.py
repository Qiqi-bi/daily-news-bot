#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日AI新闻机器人启动脚本
运行主程序并显示状态
"""

import subprocess
import sys
import os

def main():
    print("🚀 启动每日AI新闻机器人...")
    print("💡 请确保代理服务已在本地7897端口运行")
    print("📋 功能：RSS抓取 → DeepSeek分析 → 飞书推送")
    print("-" * 50)
    
    try:
        # 运行主程序
        result = subprocess.run([sys.executable, "daily_news_bot.py"], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("\n✅ 任务完成！")
        else:
            print(f"\n❌ 任务执行出错:")
            print(result.stderr)
            
    except KeyboardInterrupt:
        print("\n⚠️  用户中断了程序")
    except Exception as e:
        print(f"\n💥 程序执行异常: {e}")

if __name__ == "__main__":
    main()