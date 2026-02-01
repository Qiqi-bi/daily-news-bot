# Daily News Bot - 全球情报与金融分析自动化脚本

## 项目简介

这是一个高度智能化的新闻分析机器人，能够自动抓取全球主流新闻源，通过AI大模型进行深度分析，并将结果推送到飞书群聊。该机器人具备以下核心功能：

- 自动抓取全球主流RSS新闻源
- 使用DeepSeek大模型进行深度分析
- 智能情绪评分与重要性排序
- 实时资产价格注入（比特币、黄金、股票等）
- 飞书群聊推送（富文本卡片格式）
- 智能缓存与去重机制

## 功能特点

- ✅ **自动抓取全球新闻**：从多个高质量新闻源抓取信息，涵盖国际、金融、科技、加密货币等领域
- ✅ **AI驱动深度分析**：采用顶级游资操盘手和宏观策略师角色，提供深入的市场分析
- ✅ **飞书机器人推送**：使用webhook方式发送富文本卡片消息，视觉效果更佳
- ✅ **情绪分析和影响评估**：对每条新闻进行情绪评分和市场影响分析
- ✅ **智能缓存和去重**：避免重复推送相同新闻
- ✅ **紧急新闻监控**：独立的紧急监控系统，仅在检测到高情绪分新闻时推送
- ✅ **实时价格注入**：自动获取比特币、黄金、英伟达股票等资产的实时价格
- ✅ **富文本卡片格式**：美观的飞书卡片消息展示，支持多种交互元素
- ✅ **增强错误处理**：解决403、404、429等常见HTTP错误，提高抓取成功率
- ✅ **智能频率控制**：域名级请求频率限制，避免触发反爬虫机制
- ✅ **反爬虫对策**：使用fake-useragent库，随机User-Agent，智能延迟机制
- ✅ **API调用优化**：LLM分批处理，避免超时，增加超时冗余（120秒）
- ✅ **多重错误处理**：SSL证书错误处理，完整日志记录与透明化
- ✅ **性能优化**：新闻分批处理（每批30条），智能缓存机制，重要性评分算法

## 新闻源覆盖

系统集成了来自全球的多个RSS源，分为以下类别：

1. **国际顶流**：BBC、纽约时报
2. **华尔街金融**：CNBC、雅虎财经
3. **硅谷科技**：TechCrunch、Hacker News
4. **加密货币**：CoinDesk、Cointelegraph
5. **能源与战争**：OilPrice.com
6. **亚洲中国**：南华早报、百度新闻、人民网
7. **学术AI研究**：ArXiv、MIT Technology Review
8. **科技公司**：Google、OpenAI、NVIDIA、Meta博客
9. **主流财经**：路透社、彭博社、华尔街日报
10. **商业领袖**：Tesla、SpaceX、Neuralink博客

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置

### 环境变量设置

需要在环境变量中设置：

- `DEEPSEEK_API_KEY`: DeepSeek API密钥 (或其他AI模型API密钥)
- `FEISHU_WEBHOOK_URL`: 飞书群聊webhook地址

### 代理配置（可选）

如需使用代理，请修改代码中的PROXIES配置，默认使用7897端口的代理

## 使用方法

### 日常新闻分析
```bash
python daily_news_bot.py
```

### 紧急新闻监控
```bash
python urgent_news_monitor.py
```

或者使用批处理脚本：

```bash
# Windows日常新闻
start_news_bot.bat

# Windows紧急监控
run_urgent_monitor.bat

# 使用环境变量运行
python run_with_env.py
```

## 分析框架

AI分析采用以下结构：

### [情绪分 | 分数] 新闻标题 (中文，加粗)

> [🔗 点击直达原新闻](新闻URL) | 来源：新闻Source

* **📍 核心事实**：一句话概括发生了什么（Who + What）。
* **🕵️‍♂️ 幕后真相 (一句话逻辑)**：资本/政客的真实意图是什么？资金链条如何传导？（用 `->` 箭头表示逻辑）。
* **🇨🇳 对中国影响**：
    * **⚡ 短期**：对汇率、情绪、具体行业的直接冲击。
    * **⏳ 长期**：是否改变国运、产业链地位或监管风向？
* **📉 股市/资产影响**：
    * **利好**：[代码/板块]
    * **利空**：[代码/板块]
* **🛑 操作建议 (关键)**：[空仓/止盈/抄底/观望] + 一句话理由。

## 项目结构

- `daily_news_bot.py`: 日常新闻分析主程序（核心文件）
- `urgent_news_monitor.py`: 紧急新闻监控程序
- `history.json`: 新闻缓存记录
- `requirements.txt`: 依赖包列表
- `start_news_bot.bat`: Windows日常新闻启动脚本
- `run_urgent_monitor.bat`: Windows紧急监控启动脚本
- `run_with_env.py`: 使用环境变量运行脚本
- `run_with_env.bat`: Windows环境变量运行脚本
- `run_robot.ps1`: PowerShell运行脚本
- `fetch_news.py`: 新闻获取模块
- `reliable_news_fetcher.py`: 可靠新闻获取器
- `test_*.py`: 测试脚本
- `card_news_template.py`: 卡片消息模板
- `simple_test.py`: 简单测试脚本
- `check_api.py`: API检查脚本
- `check_config.py`: 配置检查脚本
- `send_test_message.py`: 发送测试消息脚本

## 环境要求

- Python 3.8+
- AI模型API访问权限 (推荐DeepSeek)
- fake-useragent库 (用于反爬虫对策)
- requests库 (用于HTTP请求)
- feedparser库 (用于RSS解析)

## 部署建议

1. 设置定时任务（如cron job）定期运行日常新闻分析
2. 部署紧急监控程序作为后台服务
3. 配置适当的代理以访问国外RSS源
4. 定期清理历史缓存文件
5. 在GitHub Actions等CI/CD环境中使用Secrets管理敏感信息
6. 使用虚拟环境隔离项目依赖
7. 配置日志监控以便及时发现和解决问题

## 安全注意事项

- 所有敏感信息（API密钥、webhook地址等）都应通过环境变量管理
- 不要在代码中硬编码任何敏感信息
- 在GitHub等公共平台上使用Secrets存储敏感信息
- 定期轮换API密钥
- 使用虚拟环境隔离项目依赖

## 测试和验证

运行以下命令验证配置：

```bash
# 检查API密钥
python check_api.py

# 检查飞书配置
python check_config.py

# 发送测试消息
python send_test_message.py

# 运行简单测试
python simple_test.py
```

## 项目状态

- **飞书消息格式优化**：将消息格式从纯文本改为富文本（卡片）格式，使用 `msg_type: "interactive"`，并添加了蓝色主题的头部和结构化布局
- **飞书认证简化**：完全移除了飞书应用认证相关的代码（`get_access_token`函数等），简化了`send_to_feishu`函数，只保留webhook发送方式
- **Prompt优化**：更新了LLM分析提示词，采用顶级游资操盘手和宏观策略师的角色定位，实现严格的Markdown输出格式
- **分隔线优化**：减少了分隔线长度，现在只保留一条简洁的分隔线（`──────`）
- **分析框架完善**：实现了包含情绪分、核心事实、幕后真相、对中国影响、股市影响和操作建议的完整分析框架
- **功能保留**：保留了所有新闻抓取、去重、价格注入、情绪评分等功能
