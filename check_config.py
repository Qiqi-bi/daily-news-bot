#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置检查脚本
检查飞书机器人配置是否完整
"""

import os

def check_config():
    print("🔍 检查飞书机器人配置...")
    print("=" * 50)
    
    # 检查必需的环境变量
    app_id = os.environ.get('LARK_APP_ID')
    app_secret = os.environ.get('LARK_APP_SECRET')
    
    print(f"App ID: {'✅ 已配置' if app_id else '❌ 未配置'}")
    print(f"App Secret: {'✅ 已配置' if app_secret else '❌ 未配置'}")
    
    # 检查可选的目标ID
    chat_id = os.environ.get('LARK_CHAT_ID')
    user_id = os.environ.get('LARK_USER_ID')
    
    print(f"Chat ID: {'✅ 已配置' if chat_id else '⚠️ 未配置（可选）'}")
    print(f"User ID: {'✅ 已配置' if user_id else '⚠️ 未配置（可选）'}")
    
    print()
    
    if not app_id or not app_secret:
        print("❌ 错误：缺少必需的配置信息")
        print("请设置以下环境变量：")
        print("- LARK_APP_ID: 飞书应用ID")
        print("- LARK_APP_SECRET: 飞书应用密钥")
        return False
    
    if not chat_id and not user_id:
        print("⚠️  警告：未设置目标ID")
        print("消息将不会发送，因为没有指定发送到哪个群组或用户")
        print()
        print("请设置以下环境变量之一：")
        print("- LARK_CHAT_ID: 飞书群组ID（发送到群组）")
        print("- LARK_USER_ID: 飞书用户ID（发送到个人）")
        return False
    
    print("✅ 配置检查通过！所有必需信息都已设置")
    return True

def get_config_help():
    print("\n💡 如何获取飞书ID：")
    print("1. 获取群组ID：在飞书群组中右键点击群名称 → 复制链接 → 从URL中提取chat_id参数")
    print("2. 获取用户ID：需要通过飞书API查询，或让机器人先接收到用户消息")
    print("3. 在GitHub中设置：Settings → Secrets and variables → Actions → New repository secret")

if __name__ == "__main__":
    print("📋 飞书机器人配置检查工具")
    print()
    
    config_ok = check_config()
    get_config_help()
    
    print("\n" + "=" * 50)
    if config_ok:
        print("🎉 配置完整，机器人可以正常工作！")
    else:
        print("🔧 请根据以上提示完成配置")