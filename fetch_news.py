import requests
import json
from datetime import datetime

class NewsAnalyzer:
    def __init__(self):
        # 使用新的应用认证方式，不再需要webhook URL
        pass
        
    def analyze_news_impact(self, title, description, source_type="general"):
        """
        分析新闻对中国和股市的影响
        """
        # 这里可以集成更复杂的AI分析逻辑
        # 目前使用基于关键词的简单分析
        
        impact_analysis = {
            "cause": "事件起因待分析",
            "short_term_china": "暂无显著短期影响",
            "long_term_china": "长期影响需进一步观察",
            "stock_market": "对股市影响有限"
        }
        
        # 关键词分析
        title_lower = title.lower()
        desc_lower = description.lower() if description else ""
        combined_text = title_lower + " " + desc_lower
        
        # AI/科技相关
        if any(keyword in combined_text for keyword in ["ai", "人工智能", "大模型", "机器学习", "深度学习", "算法"]):
            impact_analysis["cause"] = "技术进步和市场需求驱动AI技术快速发展"
            impact_analysis["short_term_china"] = "推动AI产业发展，促进技术创新"
            impact_analysis["long_term_china"] = "提升国家科技竞争力，加速数字化转型"
            impact_analysis["stock_market"] = "利好A股AI相关行业，如计算机（科大讯飞、浪潮信息）和电子（韦尔股份、兆易创新）等板块"
            
        # 经济/政策相关
        elif any(keyword in combined_text for keyword in ["经济", "政策", "财政", "金融", "利率", "通胀"]):
            impact_analysis["cause"] = "宏观经济环境变化或政策调整"
            impact_analysis["short_term_china"] = "影响市场信心和投资决策"
            impact_analysis["long_term_china"] = "影响经济结构调整和产业升级"
            impact_analysis["stock_market"] = "可能引发市场波动，金融（招商银行、中国平安）和地产（万科A、保利发展）等板块受影响较大"
            
        # 国际关系相关
        elif any(keyword in combined_text for keyword in ["贸易", "关税", "外交", "国际", "合作", "冲突"]):
            impact_analysis["cause"] = "国际政治经济格局变化或地缘政治因素"
            impact_analysis["short_term_china"] = "影响外贸企业和国际合作"
            impact_analysis["long_term_china"] = "影响全球供应链和战略布局"
            impact_analysis["stock_market"] = "外贸（中远海控、海尔智家）、航运（招商轮船、中远海发）等板块可能波动"
            
        # 医疗/健康相关
        elif any(keyword in combined_text for keyword in ["医疗", "健康", "医药", "疫苗", "生物科技"]):
            impact_analysis["cause"] = "医疗技术进步或公共卫生需求增长"
            impact_analysis["short_term_china"] = "促进医疗健康产业发展"
            impact_analysis["long_term_china"] = "提升公共卫生体系和医疗技术水平"
            impact_analysis["stock_market"] = "利好医药（恒瑞医药、药明康德）、生物科技（华大基因、智飞生物）等板块"
            
        # 新能源/环保相关
        elif any(keyword in combined_text for keyword in ["新能源", "光伏", "风电", "电池", "环保", "碳中和"]):
            impact_analysis["cause"] = "能源转型需求和环保政策推动"
            impact_analysis["short_term_china"] = "促进新能源产业发展，带动相关产业链"
            impact_analysis["long_term_china"] = "助力实现双碳目标，推动能源结构优化"
            impact_analysis["stock_market"] = "利好新能源（宁德时代、隆基绿能）、电力设备（国电南瑞、许继电气）等板块"
            
        return impact_analysis
    
    def calculate_importance_score(self, title, description):
        """
        计算新闻重要性评分，用于排序
        """
        score = 0
        text = (title + " " + description).lower()
        
        # 高重要性关键词（+10分）
        high_importance = ["重大", "突破", "发布", "政策", "法规", "监管", "危机", "冲突", "合作"]
        for keyword in high_importance:
            if keyword in text:
                score += 10
                
        # 中等重要性关键词（+5分）
        medium_importance = ["ai", "人工智能", "大模型", "芯片", "技术", "创新", "经济", "金融", "医疗", "新能源"]
        for keyword in medium_importance:
            if keyword in text:
                score += 5
                
        # 中国相关（+3分）
        china_keywords = ["中国", "国内", "国产", "本土", "华为", "腾讯", "阿里", "百度"]
        for keyword in china_keywords:
            if keyword in text:
                score += 3
                
        return score
    
    def create_news_summary(self, articles):
        """
        创建包含影响分析的新闻摘要，并按重要性排序
        """
        summary_items = []
        
        # 先计算每条新闻的重要性评分
        scored_articles = []
        for article in articles:
            title = article.get('title', '无标题')
            description = article.get('description', '无描述')
            url = article.get('url', '#')
            source = article.get('source', {}).get('name', '未知来源')
            
            if not title or not description or title == '[Removed]' or description == '[Removed]':
                continue
                
            importance_score = self.calculate_importance_score(title, description)
            scored_articles.append({
                'article': article,
                'score': importance_score
            })
        
        # 按重要性评分降序排序
        scored_articles.sort(key=lambda x: x['score'], reverse=True)
        
        # 只处理前5条最重要的新闻
        for item in scored_articles[:5]:
            article = item['article']
            title = article.get('title', '无标题')
            description = article.get('description', '无描述')
            url = article.get('url', '#')
            source = article.get('source', {}).get('name', '未知来源')
            
            # 分析影响
            impact = self.analyze_news_impact(title, description)
            
            # 创建完整的摘要文本（按要求的顺序）
            summary_text = f"【事件简要】\n{description}\n\n"
            summary_text += f"【事件起因】\n{impact['cause']}\n\n"
            summary_text += f"【对中国短期影响】\n{impact['short_term_china']}\n\n"
            summary_text += f"【对中国长期影响】\n{impact['long_term_china']}\n\n"
            summary_text += f"【对股市影响】\n{impact['stock_market']}\n\n"
            summary_text += f"来源: {source}"
            
            summary_items.append({
                'title': title,
                'summary': summary_text,
                'url': url,
                'importance_score': item['score']
            })
        
        return summary_items
    
    def send_to_feishu(self, summary_items):
        """
        使用新的应用认证方式发送消息到飞书
        """
        # 导入daily_news_bot中的send_to_feishu函数
        from daily_news_bot import send_to_feishu
        
        # 构建消息内容
        message_parts = []
        for i, item in enumerate(summary_items, 1):
            message_parts.append(f"### {i}. [{item['title']}]({item['url']})")
            message_parts.append(item['summary'])
            message_parts.append("---")  # 分隔线
        
        full_message = "\n".join(message_parts)
        
        try:
            success = send_to_feishu(full_message)
            if success:
                print("✅ 成功发送新闻摘要到飞书群！")
                return True
            else:
                print("❌ 发送失败")
                return False
        except Exception as e:
            print(f"❌ 发送飞书消息时出错: {e}")
            return False
    
    def get_sample_news_data(self):
        """
        获取示例新闻数据（用于演示）
        """
        sample_articles = [
            {
                "title": "OpenAI发布新一代GPT模型，性能大幅提升",
                "description": "OpenAI宣布推出GPT-5模型，在多个基准测试中表现优异，支持更长的上下文和多模态输入。",
                "url": "https://example.com/openai-gpt5",
                "source": {"name": "科技媒体"}
            },
            {
                "title": "中国AI芯片企业获得重大技术突破",
                "description": "国内某AI芯片公司宣布在7nm工艺上取得突破，将大幅提升国产AI芯片的计算能力。",
                "url": "https://example.com/china-ai-chip",
                "source": {"name": "新华网"}
            },
            {
                "title": "欧盟通过新的人工智能监管法案",
                "description": "欧盟议会通过了全面的人工智能监管框架，对高风险AI系统实施严格管控。",
                "url": "https://example.com/eu-ai-regulation",
                "source": {"name": "路透社"}
            },
            {
                "title": "AI医疗诊断系统获FDA批准",
                "description": "新型AI医疗诊断系统获得美国FDA批准，可用于早期癌症筛查，准确率达到95%以上。",
                "url": "https://example.com/ai-medical-fda",
                "source": {"name": "BBC"}
            },
            {
                "title": "自动驾驶出租车在多个城市开始试点运营",
                "description": "多家科技公司宣布在北上广深等城市启动自动驾驶出租车试点服务，用户可通过APP预约。",
                "url": "https://example.com/autonomous-taxi",
                "source": {"name": "央视新闻"}
            }
        ]
        return sample_articles
    
    def fetch_real_news(self):
        """
        从真实新闻源获取数据（需要有效的API密钥）
        """
        # 这里可以集成真实的新闻API
        # 由于API限制，目前返回示例数据
        return self.get_sample_news_data()
    
    def run(self):
        """
        主执行函数
        """
        print("🚀 开始获取和分析新闻数据...")
        
        # 获取新闻数据
        try:
            articles = self.fetch_real_news()
            print(f"获取到 {len(articles)} 条新闻")
        except Exception as e:
            print(f"获取新闻失败，使用示例数据: {e}")
            articles = self.get_sample_news_data()
        
        if not articles:
            print("❌ 没有获取到任何新闻数据")
            return False
        
        # 生成包含影响分析的摘要
        print("📊 正在分析新闻影响...")
        summary_items = self.create_news_summary(articles)
        print(f"生成 {len(summary_items)} 条新闻摘要")
        
        if not summary_items:
            print("❌ 没有生成有效的新闻摘要")
            return False
        
        # 发送到飞书
        print("📤 正在发送到飞书群...")
        success = self.send_to_feishu(summary_items)
        
        if success:
            print("🎉 任务完成！请检查您的飞书群。")
        else:
            print("❌ 任务失败，请检查配置。")
            
        return success

def main():
    analyzer = NewsAnalyzer()
    analyzer.run()

if __name__ == "__main__":
    main()