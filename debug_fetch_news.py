import requests
import json

# 新闻来源列表
news_sources = [
    f"https://newsapi.org/v2/top-headlines?country=CN&apiKey={os.environ.get('NEWS_API_KEY', 'YOUR_NEWS_API_KEY_HERE')}",
    f"https://newsapi.org/v2/top-headlines?country=US&apiKey={os.environ.get('NEWS_API_KEY', 'YOUR_NEWS_API_KEY_HERE')}",
    f"https://newsapi.org/v2/top-headlines?category=technology&apiKey={os.environ.get('NEWS_API_KEY', 'YOUR_NEWS_API_KEY_HERE')}"
]

# 使用新的应用认证方式，不再需要webhook URL
pass

def fetch_news(url):
    print(f"正在获取新闻: {url}")
    response = requests.get(url)
    if response.status_code == 200:
        print(f"成功获取新闻，状态码: {response.status_code}")
        return response.json()
    else:
        print(f"获取新闻失败，状态码: {response.status_code}")
        return None

def translate_text(text, target_lang='zh'):
    """简化翻译功能 - 直接返回原文用于调试"""
    if not text:
        return ""
    print(f"处理文本: {text[:50]}...")
    # 简单检测是否包含中文字符
    if any('\u4e00' <= char <= '\u9fff' for char in text):
        print("检测到中文，保持原样")
        return text
    else:
        print("检测到非中文，尝试翻译")
        # 为了调试，先直接返回原文
        return text

def generate_summary(news_data):
    summary = []
    articles = news_data.get('articles', [])
    print(f"找到 {len(articles)} 篇文章")
    for i, article in enumerate(articles[:3]):  # 只处理前3篇用于调试
        title = article.get('title', '')
        description = article.get('description', '')
        url = article.get('url', '')
        print(f"文章 {i+1}: {title[:30]}...")
        
        translated_title = translate_text(title)
        translated_description = translate_text(description)
        
        summary.append({
            'title': translated_title,
            'description': translated_description,
            'url': url
        })
    return summary

def send_to_feishu(summary):
    print(f"准备发送 {len(summary)} 条新闻到飞书")
    content_items = []
    for item in summary[:3]:  # 只发送前3条用于调试
        content_items.extend([
            {
                "tag": "text",
                "text": item['description'] + "\n"
            },
            {
                "tag": "a",
                "text": item['title'],
                "href": item['url']
            },
            {
                "tag": "text",
                "text": "\n\n"
            }
        ])
    
    message = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": "每日新闻摘要",
                    "content": [content_items]
                }
            }
        }
    }
    print("发送消息到飞书...")
    # 使用新的应用认证方式发送消息
    from daily_news_bot import send_to_feishu
    success = send_to_feishu(json.dumps(content_items, ensure_ascii=False))
    print(f"飞书发送结果: {'成功' if success else '失败'}")
    return success

def main():
    all_summaries = []
    for source in news_sources:
        news_data = fetch_news(source)
        if news_data:
            summary = generate_summary(news_data)
            all_summaries.extend(summary)
    
    print(f"总共收集到 {len(all_summaries)} 条新闻")
    if all_summaries:
        success = send_to_feishu(all_summaries)
        if success:
            print("✅ 新闻已成功发送到飞书！")
        else:
            print("❌ 发送到飞书失败")
    else:
        print("❌ 没有收集到任何新闻")

if __name__ == "__main__":
    main()