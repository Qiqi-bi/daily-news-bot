#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置检查脚本
检查飞书Webhook配置是否完整
"""

import os

def check_config():
    print("🔍 检查飞书Webhook配置...")
    print("=" * 50)
    
    # 检查必需的环境变量
    webhook_url = os.environ.get('FEISHU_WEBHOOK_URL')
    
    print(f"Webhook URL: {'✅ 已配置' if webhook_url else '❌ 未配置'}")
    
    print()
    
    if not webhook_url:
        print("❌ 错误：缺少必需的配置信息")
        print("请设置以下环境变量：")
        print("- FEISHU_WEBHOOK_URL: 飞书群聊webhook地址")
        return False
    
    print("✅ 配置检查通过！所有必需信息都已设置")
    return True

def get_config_help():
    print("\n💡 如何获取飞书Webhook：")
    print("1. 在飞书群聊中点击右上角群设置")
    print("2. 机器人 → 添加机器人 → 自定义机器人")
    print("3. 设置机器人名称（如'每日AI新闻机器人'）")
    print("4. 完善机器人图标和描述信息")
    print("5. 复制Webhook地址")
    print("6. 在GitHub中设置：Settings → Secrets and variables → Actions → New repository secret")

if __name__ == "__main__":
    print("📋 飞书Webhook配置检查工具")
    print()
    
    config_ok = check_config()
    get_config_help()
    
    print("\n" + "=" * 50)
    if config_ok:
        print("🎉 配置完整，机器人可以正常工作！")
    else:
        print("🔧 请根据以上提示完成配置")
