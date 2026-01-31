#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书机器人配置设置脚本
"""

import os
import json
from pathlib import Path

def setup_lark_config():
    """
    设置飞书机器人配置
    """
    print("🔧 飞书机器人配置设置向导")
    print("=" * 50)
    
    print("\n📋 当前配置状态:")
    print(f"App ID: {'已设置' if os.environ.get('LARK_APP_ID') else '未设置'}")
    print(f"App Secret: {'已设置' if os.environ.get('LARK_APP_SECRET') else '未设置'}")
    print(f"Chat ID: {'已设置' if os.environ.get('LARK_CHAT_ID') else '未设置'}")
    print(f"User ID: {'已设置' if os.environ.get('LARK_USER_ID') else '未设置'}")
    
    print("\n💡 配置说明:")
    print("1. App ID 和 App Secret 是必需的，用于身份验证")
    print("2. Chat ID 或 User ID 至少需要设置一个，用于指定消息发送目标")
    print("3. 这些配置可以通过环境变量或配置文件设置")
    
    print("\n🔐 请输入飞书应用配置信息:")
    
    # 获取配置信息
    app_id = input("请输入 App ID (留空使用默认值): ").strip()
    if not app_id:
        app_id = "cli_a9f6280dd5389bd8"  # 默认值
    
    app_secret = input("请输入 App Secret (留空使用默认值): ").strip()
    if not app_secret:
        app_secret = "VHN4Eag0koh7rwEkKXeHSgHzLnH1140x"  # 默认值
    
    chat_id = input("请输入 Chat ID (可选，留空跳过): ").strip()
    user_id = input("请输入 User ID (可选，留空跳过): ").strip()
    
    # 创建配置字典
    config = {
        "LARK_APP_ID": app_id,
        "LARK_APP_SECRET": app_secret
    }
    
    if chat_id:
        config["LARK_CHAT_ID"] = chat_id
    if user_id:
        config["LARK_USER_ID"] = user_id
    
    # 保存到配置文件
    config_path = Path("lark_config.json")
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 配置已保存到 {config_path}")
    
    # 显示使用说明
    print("\n📖 使用说明:")
    print("1. 在运行机器人脚本前，需要设置环境变量:")
    print("   Windows: set LARK_APP_ID=your_app_id")
    print("            set LARK_APP_SECRET=your_app_secret")
    print("   或者使用配置文件方式运行")
    
    print("\n2. 如果您使用的是GitHub Actions，需要在仓库设置中添加Secrets:")
    print("   Settings → Secrets and variables → Actions → New repository secret")
    print("   添加: LARK_APP_ID, LARK_APP_SECRET, LARK_CHAT_ID (可选), LARK_USER_ID (可选)")
    
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
                if 'SECRET' in key or 'ID' in key:
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
    print("3. 直接在代码中设置 (不推荐，安全性低)")
    
    print("\n🌐 飞书应用创建步骤:")
    print("   1. 访问 https://open.feishu.cn/")
    print("   2. 登录后进入'开发者后台'")
    print("   3. 点击'创建企业自建应用'")
    print("   4. 填写应用名称（如'每日AI新闻机器人'）")
    print("   5. 在应用详情页面的'凭证与基础信息'中获取App ID和App Secret")
    
    print("\n🔒 必需权限:")
    print("   - im:message:send (发送消息权限)")
    print("   - im:chat:read (读取群组信息权限)")
    print("   - contact:user.employee_id:readonly (获取用户信息权限)")

if __name__ == "__main__":
    print("🚀 飞书机器人配置助手")
    print()
    
    # 显示设置选项
    show_setup_options()
    
    # 询问是否要进行配置
    response = input("\n是否要开始配置飞书机器人？(y/n): ").strip().lower()
    
    if response in ['y', 'yes', '是', '要']:
        config = setup_lark_config()
        test_configuration()
    else:
        test_configuration()
        print("\n💡 如果需要配置，请运行: python setup_lark_config.py")
    
    print("\n✅ 配置助手执行完毕")