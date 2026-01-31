import requests

# 检查API密钥
api_key = "20d102607aea4b37a7ee10f1f76fb91a"
url = f"https://newsapi.org/v2/top-headlines?country=CN&apiKey={api_key}"

print("检查NewsAPI密钥...")
try:
    response = requests.get(url, timeout=10)
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("✅ API密钥有效")
        print(f"文章数量: {len(data.get('articles', []))}")
        if data['articles']:
            print(f"第一条新闻: {data['articles'][0]['title']}")
    else:
        data = response.json()
        print(f"❌ API错误: {data.get('message', 'Unknown error')}")
        print("可能的原因:")
        print("- API密钥无效或已过期")
        print("- 免费账户的请求频率限制")
        print("- 需要注册NewsAPI账户获取有效密钥")
except Exception as e:
    print(f"❌ 请求失败: {e}")