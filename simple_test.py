import requests
import json
import os

# 测试NewsAPI是否正常工作
api_key = os.environ.get('NEWS_API_KEY', 'YOUR_NEWS_API_KEY_HERE')
test_url = f"https://newsapi.org/v2/top-headlines?country=CN&apiKey={api_key}"

print("测试NewsAPI连接...")
response = requests.get(test_url)
print(f"状态码: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"获取到新闻数量: {len(data.get('articles', []))}")
    if data['articles']:
        first_article = data['articles'][0]
        print(f"第一条新闻标题: {first_article['title']}")
else:
    print(f"API错误: {response.text}")

# 测试飞书应用认证
from daily_news_bot import send_to_feishu

print("\n测试飞书应用认证...")
success = send_to_feishu("🧪 测试消息：新闻摘要机器人正在工作！")
print(f"飞书发送结果: {'成功' if success else '失败'}")
