# 每日AI新闻机器人

这是一个智能新闻分析机器人，能够从多个RSS源抓取全球新闻，使用AI模型进行深度分析，并将结果发送到飞书群组。

## 功能特点

- 从多个国际RSS源抓取新闻（包括BBC、纽约时报、CNBC、TechCrunch等）
- 使用DeepSeek AI模型进行新闻分析
- 按重要性排序新闻内容
- 实时价格注入（比特币、黄金、股票等）
- 情绪评分和投资建议
- 发送到飞书群组（卡片格式）

## 安装要求

- Python 3.7+
- pip

## 安装步骤

1. 克隆项目：
```bash
git clone <your-repo-url>
cd 每日AI新闻
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 配置API密钥和Webhook：
   - 获取DeepSeek API密钥
   - 设置飞书群机器人webhook

## 配置说明

### API密钥设置

在运行前，需要设置DeepSeek API密钥：

```bash
export DEEPSEEK_API_KEY="your-api-key-here"
```

或者在 `daily_news_bot.py` 中直接修改：

```python
API_KEY = "your-api-key-here"
```

### 飞书Webhook设置

修改 `daily_news_bot.py` 中的webhook URL：

```python
webhook_url = "your-feishu-webhook-url"
```

## 使用方法

### 手动运行

```bash
python daily_news_bot.py
```

### 定时任务

可以使用系统定时任务（如cron或Windows任务计划程序）来定期运行。

在Linux/macOS系统中，编辑crontab：

```bash
# 每天上午9点运行
0 9 * * * cd /path/to/每日AI新闻 && python daily_news_bot.py
```

在Windows系统中，可以使用任务计划程序或直接运行批处理文件。

## 项目结构

```
├── daily_news_bot.py          # 主程序文件
├── requirements.txt           # 依赖包列表
├── .gitignore                 # Git忽略文件
├── README.md                  # 项目说明
├── history.json               # 新闻缓存记录（自动生成）
├── lark_config.json           # 飞书配置（可选）
├── .github/workflows/         # GitHub Actions工作流
└── 各种测试和辅助脚本
```

## 安全注意事项

- 请勿将API密钥和webhook URL提交到版本控制系统
- 使用环境变量或安全的配置管理方式存储敏感信息
- .gitignore文件已包含常见敏感文件的排除规则

## GitHub Actions集成

项目已配置GitHub Actions，可在云端定时运行。需要在仓库设置中添加以下Secrets：

- `DEEPSEEK_API_KEY`: DeepSeek API密钥
- `FEISHU_WEBHOOK_URL`: 飞书机器人webhook URL

## 依赖包

主要依赖包包括：
- feedparser: RSS解析
- requests: HTTP请求
- python-dotenv: 环境变量管理（可选）

## 故障排除

如果遇到网络问题，可能需要配置代理。在代码中可以修改PROXIES设置。

如果API调用失败，请检查API密钥是否正确以及网络连接是否正常。

## 许可证

MIT License