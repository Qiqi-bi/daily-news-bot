import requests
import json

# 新闻来源（只使用中文新闻源以确保内容为中文）
news_sources = [
    f"https://newsapi.org/v2/top-headlines?country=CN&apiKey={os.environ.get('NEWS_API_KEY', 'YOUR_NEWS_API_KEY_HERE')}",
    f"https://newsapi.org/v2/top-headlines?country=CN&category=technology&apiKey={os.environ.get('NEWS_API_KEY', 'YOUR_NEWS_API_KEY_HERE')}"
]

# 使用新的应用认证方式，不再需要webhook URL
pass

def fetch_news(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"获取新闻失败: {response.status_code}")
            return None
    except Exception as e:
        print(f"请求错误: {e}")
        return None

def send_to_feishu(articles):
    if not articles:
        print("没有新闻可发送")
        return
    
    # 只取前5条新闻
    selected_articles = articles[:5]
    content_items = []
    
    for article in selected_articles:
        title = article.get('title', '无标题')
        description = article.get('description', '无描述')
        url = article.get('url', '#')
        
        if description and title:
            content_items.extend([
                {
                    "tag": "text",
                    "text": f"{description}\n"
                },
                {
                    "tag": "a",
                    "text": title,
                    "href": url
                },
                {
                    "tag": "text",
                    "text": "\n\n"
                }
            ])
    
    if not content_items:
        print("没有有效的新闻内容")
        return
    
    message = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": "【每日AI新闻】",
                    "content": [content_items]
                }
            }
        }
    }
    
    try:
        # 使用新的应用认证方式发送消息
        from daily_news_bot import send_to_feishu
        # 将内容转换为适合新API的格式
        content_parts = []
        for article in selected_articles:
            title = article.get('title', '无标题')
            description = article.get('description', '无描述')
            url = article.get('url', '#')
            if description and title:
                content_parts.append(f"【{title}】({url})\n{description}\n")
        full_content = "\n".join(content_parts)
        success = send_to_feishu(full_content)
        if success:
            print("✅ 新闻摘要已成功发送到飞书群！")
            print(f"发送了 {len(selected_articles)} 条新闻")
        else:
            print("❌ 发送失败")
    except Exception as e:
        print(f"❌ 发送过程中出现错误: {e}")

def main():
    all_articles = []
    
    for source in news_sources:
        print(f"正在获取新闻: {source}")
        news_data = fetch_news(source)
        if news_data and 'articles' in news_data:
            all_articles.extend(news_data['articles'])
            print(f"获取到 {len(news_data['articles'])} 条新闻")
    
    print(f"总共收集到 {len(all_articles)} 条新闻")
    send_to_feishu(all_articles)

if __name__ == "__main__":
    main()