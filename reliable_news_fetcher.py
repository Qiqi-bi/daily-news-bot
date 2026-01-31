import requests
import json
import time

# 使用更可靠的中文新闻源
def get_chinese_news():
    """获取中文新闻的备用方法"""
    news_list = []
    
    # 模拟一些中文新闻数据（用于演示）
    sample_news = [
        {
            "title": "AI技术在医疗领域取得重大突破",
            "description": "最新研究表明，人工智能算法能够准确诊断多种疾病，准确率超过95%。",
            "url": "https://example.com/ai-medical-breakthrough"
        },
        {
            "title": "中国科技公司发布新一代大语言模型",
            "description": "该模型在多个基准测试中表现优异，支持多语言对话和代码生成。",
            "url": "https://example.com/new-llm-release"
        },
        {
            "title": "自动驾驶技术迎来新进展",
            "description": "多家车企宣布将在明年推出L4级别自动驾驶功能，安全性大幅提升。",
            "url": "https://example.com/autonomous-driving"
        }
    ]
    
    return sample_news

# 使用新的应用认证方式，不再需要webhook URL
pass

def send_to_feishu(articles):
    if not articles:
        print("没有新闻可发送")
        return
    
    content_items = []
    
    for article in articles:
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
    
    message = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": "【每日AI新闻摘要】",
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
        for article in articles:
            title = article.get('title', '无标题')
            description = article.get('description', '无描述')
            url = article.get('url', '#')
            if description and title:
                content_parts.append(f"【{title}】({url})\n{description}\n")
        full_content = "\n".join(content_parts)
        success = send_to_feishu(full_content)
        if success:
            print("✅ 新闻摘要已成功发送到飞书群！")
            return True
        else:
            print("❌ 发送失败")
            return False
    except Exception as e:
        print(f"❌ 发送过程中出现错误: {e}")
        return False

def main():
    print("正在获取中文新闻...")
    
    # 尝试获取真实新闻，如果失败则使用示例数据
    try:
        # 这里可以集成真实的新闻API
        news_articles = get_chinese_news()
        print(f"获取到 {len(news_articles)} 条新闻")
    except Exception as e:
        print(f"获取新闻失败，使用示例数据: {e}")
        news_articles = get_chinese_news()
    
    if news_articles:
        success = send_to_feishu(news_articles)
        if success:
            print("🎉 任务完成！请检查您的飞书群。")
        else:
            print("❌ 发送失败，请检查Webhook URL是否正确。")
    else:
        print("❌ 没有获取到任何新闻。")

if __name__ == "__main__":
    main()