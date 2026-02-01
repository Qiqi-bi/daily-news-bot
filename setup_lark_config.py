#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书Webhook配置设置脚本
"""

import os
import json
from pathlib import Path

def setup_lark_config():
    """
    设置飞书Webhook配置
    """
    print("🔧 飞书Webhook配置设置向导")
    print("=" * 50)
    
    print("\n📋 当前配置状态:")
    print(f"Webhook URL: {'已设置' if os.environ.get('FEISHU_WEBHOOK_URL') else '未设置'}")
    
    print("\n💡 配置说明:")
    print("1. Webhook URL 是必需的，用于发送消息到飞书群聊")
    print("2. 这些配置通过环境变量设置")
    
    print("\n🔐 请输入飞书Webhook配置信息:")
    
    # 获取配置信息
    webhook_url = input("请输入 Webhook URL (留空使用环境变量): ").strip()
    if not webhook_url:
        webhook_url = os.environ.get('FEISHU_WEBHOOK_URL', '')  # 从环境变量获取或使用占位符
    
    # 创建配置字典
    config = {
        "FEISHU_WEBHOOK_URL": webhook_url
    }
    
    # 保存到配置文件
    config_path = Path("lark_config.json")
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 配置已保存到 {config_path}")
    
    # 显示使用说明
    print("\n📖 使用说明:")
    print("1. 在运行机器人脚本前，需要设置环境变量:")
    print("   Windows: set FEISHU_WEBHOOK_URL=你的webhook地址")
    print("   Linux/macOS: export FEISHU_WEBHOOK_URL=你的webhook地址")
    print("   或者使用配置文件方式运行")
    
    print("\n2. 如果您使用的是GitHub Actions，需要在仓库设置中添加Secrets:")
    print("   Settings → Secrets and variables → Actions → New repository secret")
    print("   添加: FEISHU_WEBHOOK_URL")
    
    print("\n3. 验证配置是否正确:")
    print("   python check_config.py")
    
    print("\n4. 发送测试消息:")
    print("   python send_test_message.py")
    
    return config

def load_config_from_file():
    """
    从配置文件加载配置
    """
    config_path = Path("lark_config.json")
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def test_configuration():
    """
    测试配置是否有效
    """
    print("\n🧪 测试配置有效性...")
    
    # 尝试导入并使用配置
    try:
        # 从配置文件加载
        config = load_config_from_file()
        if config:
            print("✅ 从配置文件加载成功")
            for key, value in config.items():
                if 'WEBHOOK' in key or 'URL' in key:
                    # 隐藏敏感信息
                    display_value = '*' * len(value) if value else ''
                    print(f"   {key}: {display_value}")
                else:
                    print(f"   {key}: {value}")
        else:
            print("⚠️  未找到配置文件 lark_config.json")
            print("   请先运行 setup_lark_config.py 进行配置")
    
    except Exception as e:
        print(f"❌ 加载配置时出错: {e}")

def show_setup_options():
    """
    显示配置选项
    """
    print("\n⚙️  配置选项:")
    print("1. 使用环境变量 (推荐用于生产环境)")
    print("2. 使用配置文件 (推荐用于本地开发)")
    
    print("\n🌐 飞书Webhook创建步骤:")
    print("   1. 在飞书群聊中点击右上角群设置")
    print("   2. 机器人 → 添加机器人 → 自定义机器人")
    print("   3. 设置机器人名称（如'每日AI新闻机器人'）")
    print("   4. 完善机器人图标和描述信息")
    print("   5. 复制Webhook地址")

if __name__ == "__main__":
    print("🚀 飞书Webhook配置助手")
    print()
    
    # 显示设置选项
    show_setup_options()
    
    # 询问是否要进行配置
    response = input("\n是否要开始配置飞书Webhook？(y/n): ").strip().lower()
    
    if response in ['y', 'yes', '是', '要']:
        config = setup_lark_config()
        test_configuration()
    else:
        test_configuration()
        print("\n💡 如果需要配置，请运行: python setup_lark_config.py")
    
    print("\n✅ 配置助手执行完毕")
