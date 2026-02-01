# 每日AI新闻机器人

这是一个基于DeepSeek大模型API和飞书机器人的自动化新闻分析系统，能够从全球多个RSS源抓取新闻，进行AI分析，并发送到飞书群聊。

## 功能特性

- 🌐 **多源新闻抓取**：从全球主流RSS源抓取新闻（BBC、纽约时报、TechCrunch等）
- 🤖 **AI深度分析**：使用DeepSeek大模型进行智能分级分析，根据新闻重要性自动切换分析深度
- 💬 **飞书推送**：将分析结果推送到飞书群聊
- 🔍 **智能筛选**：自动过滤不感兴趣的内容，突出重要新闻
- 📊 **情绪评分**：为新闻添加情绪分析和重要性评分

## 安装步骤

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd 每日AI新闻
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置环境变量**
   在 `.env` 文件中填入以下信息：
   ```env
   # DeepSeek API密钥 - 请替换为您的实际API密钥
   DEEPSEEK_API_KEY=your_deepseek_api_key_here
   
   # 飞书Webhook URL - 请替换为您的实际Webhook URL
   FEISHU_WEBHOOK_URL=your_feishu_webhook_url_here
   
   # 可选的API密钥（如需使用更多数据源）
   MARKETAUX_API_KEY=your_marketaux_api_key_here
   POLYGON_API_KEY=your_polygon_api_key_here
   ALPHA_VANTAGE_API_KEY=your_alpha_vantage_api_key_here
   FINNHUB_API_KEY=your_finnhub_api_key_here
   ```

4. **运行程序**
   ```bash
   python daily_news_bot.py
   ```

## 配置说明

### DeepSeek API配置
- 访问 [DeepSeek开发者页面](https://platform.deepseek.com/) 注册账号
- 获取API密钥并填入 `.env` 文件中的 `DEEPSEEK_API_KEY`

### 飞书机器人配置
1. 在飞书群聊中添加自定义机器人
2. 选择"通过Webhook添加机器人"
3. 设置机器人名称和头像
4. 复制Webhook地址并填入 `.env` 文件中的 `FEISHU_WEBHOOK_URL`
5. 设置机器人权限和通知范围

## 使用方法

### 手动运行
```bash
python daily_news_bot.py
```

### 定时任务
您可以使用系统的定时任务功能（如Windows的任务计划程序或Linux的cron）来定期运行此脚本。

### 批处理脚本
项目中包含了多种运行脚本：
- `start_news_bot.bat` - Windows批处理运行脚本
- `run_robot.ps1` - PowerShell运行脚本

## 项目结构

```
每日AI新闻/
├── daily_news_bot.py          # 主程序文件
├── enhanced_rss_fetcher.py    # 增强版RSS采集器
├── .env                      # 环境变量配置文件
├── requirements.txt           # 项目依赖
├── history.json              # 新闻缓存记录
├── README.md                 # 项目说明
└── ...                       # 其他辅助文件
```

## RSS源列表

程序会从以下类型的RSS源抓取新闻：
- 国际主流媒体（BBC、纽约时报等）
- 金融财经（CNBC、雅虎财经等）
- 科技新闻（TechCrunch、The Verge等）
- 加密货币（CoinDesk、Cointelegraph等）
- 能源新闻（OilPrice.com等）
- 社交与黑客动向（Hacker News、Reddit等）
- 亚洲/中国商业（南华早报等）
- 学术/AI研究（ArXiv、MIT Technology Review等）

## 安全注意事项

⚠️ **重要**：请确保 `.env` 文件不会被提交到版本控制系统中，以免泄露敏感信息。

项目中的 `.gitignore` 文件已配置忽略 `.env` 文件，但仍请注意不要手动提交包含敏感信息的文件。

## 故障排除

1. **API调用失败**：检查API密钥是否正确，网络连接是否正常
2. **RSS源抓取失败**：部分RSS源可能因网络问题无法访问，程序会自动重试
3. **飞书消息发送失败**：检查Webhook URL是否正确，机器人是否仍在群聊中

## 许可证

本项目仅供学习和参考使用。

这是一个基于DeepSeek大模型的智能新闻分析机器人，能够从全球RSS源抓取新闻，进行AI分析，并发送到飞书群组。

## 功能特点

- 🌍 **全球新闻抓取**：从25个RSS源抓取国际新闻（BBC、纽约时报、CNBC、TechCrunch等）
- 🤖 **AI智能分析**：使用DeepSeek大模型进行智能分级分析，根据新闻重要性自动切换分析深度
- 💰 **金融分析**：特别关注金融、股市、加密货币等领域
- 📱 **飞书推送**：自动发送分析结果到飞书群组（使用Webhook方式）
- 🔍 **智能过滤**：过滤不感兴趣的新闻，专注重要内容
- 📊 **情绪评分**：为每条新闻添加情绪评分
- 💡 **价格注入**：自动注入相关资产的实时价格
- 🎯 **重点突出**：使用表情符号和格式化突出重点信息
- 🎨 **卡片式展示**：支持飞书卡片式消息，提供更好的阅读体验

## 技术架构

- **Python 3.8+**
- **DeepSeek API**：用于新闻分析
- **Feedparser**：RSS解析
- **Requests**：HTTP请求
- **飞书Webhook**：消息推送

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置

1. 复制 `.env` 文件并填入相应配置：

```env
DEEPSEEK_API_KEY=your_deepseek_api_key_here
FEISHU_WEBHOOK_URL=your_feishu_webhook_url_here
```

2. 配置飞书机器人Webhook URL

## 使用方法

### 运行机器人

```bash
python daily_news_bot.py
```

### 定时任务

可以设置定时任务每天运行：

```bash
# Linux/Mac crontab 示例
0 13,0 * * * cd /path/to/project && python daily_news_bot.py
```

### Windows批处理运行

项目提供了Windows批处理脚本：

```bash
# 直接运行
start_news_bot.bat

# 或使用PowerShell
./run_robot.ps1
```

## 项目结构

- `daily_news_bot.py` - 主程序
- `enhanced_rss_fetcher.py` - 增强版RSS抓取器
- `requirements.txt` - 依赖包
- `history.json` - 新闻处理历史记录
- `card_news_template.py` - 飞书卡片式消息模板
- `send_updated_template.py` - 更新版新闻模板发送器
- `send_news_template.py` - 新闻模板发送器

## 分析框架

AI分析遵循智能分级协议：

- **智能分级协议 (Triage Protocol)**：根据新闻重要性自动切换分析深度
  - 🔴 重磅新闻 (8-10分)：启用【深度穿透模式】(500-700字)
  - 🟡 一般新闻 (4-7分)：启用【快讯速读模式】(<250字)
  - 🟢 噪音新闻 (1-3分)：直接丢弃，不输出

### 🔴 深度穿透模式 (针对8-10分重磅新闻)
1. **情绪分**：新闻对市场的情绪影响评分
2. **信号与噪音判定**：区分实质性事件与公关宣传
3. **历史对照分析**：匹配类似历史事件进行推演
4. **三层连锁反应**：分析物理层、逻辑层和反身性博弈
5. **对中国影响**：短期和长期影响
6. **资金流向预测**：预测对相关板块和个股的影响
7. **投资策略建议**：提供具体的操作建议

### 🟡 快讯速读模式 (针对4-7分一般新闻)
1. **情绪分**：新闻对市场的情绪影响评分
2. **核心要点**：新闻核心内容概括
3. **对中国影响**：短期影响
4. **投资建议**：简明操作建议

### 🟢 噪音过滤模式 (针对1-3分噪音新闻)
- 直接丢弃，不输出
- 避免信息噪音干扰

## 新闻分类

- 🌏 **国际新闻**：全球重要事件
- 💰 **金融新闻**：股市、经济、政策
- 🤖 **AI科技**：人工智能、科技创新
- 🪙 **加密货币**：数字货币、区块链
- ⚡ **能源新闻**：石油、新能源等

## 过滤机制

- ✅ **必选新闻**：金融、AI科技、加密货币、能源、中国相关
- ❌ **必杀新闻**：广告、娱乐、体育、游戏等无关内容

## 代理支持

项目支持智能代理配置：

- GitHub Actions环境：直接连接
- 本地环境：通过代理连接（默认 http://127.0.0.1:7897）

## 故障处理

- 自动重试机制
- SSL错误处理
- 连接超时处理
- 错误警报推送

## 飞书消息格式

- 支持富文本格式（卡片式消息）
- 蓝色主题头部
- 结构化布局
- 包含时间戳和系统标识

## 开发

项目采用模块化设计，易于扩展和维护。

## 许可证

MIT License
