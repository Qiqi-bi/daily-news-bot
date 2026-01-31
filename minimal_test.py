import requests
import json

# 最简化的飞书测试
from daily_news_bot import send_to_feishu

message = "【测试】这是来自新闻机器人的测试消息！"

print("正在发送测试消息...")
try:
    success = send_to_feishu(message)
    print(f"飞书发送结果: {'成功' if success else '失败'}")
    if success:
        print("✅ 测试消息发送成功！请检查您的飞书群。")
    else:
        print("❌ 测试消息发送失败。")
except Exception as e:
    print(f"❌ 发送过程中出现错误: {e}")
