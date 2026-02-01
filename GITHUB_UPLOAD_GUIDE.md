# GitHub上传指南

本指南介绍了如何将此项目上传到GitHub仓库。

## 1. 创建GitHub仓库

1. 登录GitHub账户
2. 点击"New repository"按钮
3. 输入仓库名称（例如：daily-ai-news-bot）
4. 添加仓库描述
5. 选择"Public"或"Private"
6. 不要勾选"Initialize this repository with a README"
7. 不要添加.gitignore或license（我们已有这些文件）
8. 点击"Create repository"

## 2. 上传项目到GitHub

打开终端或命令提示符，进入项目目录：

```bash
# 初始化git仓库
git init

# 添加所有文件
git add .

# 提交更改
git commit -m "Initial commit: Daily AI News Bot with DeepSeek integration"

# 添加远程仓库地址（替换为您自己的仓库地址）
git remote add origin https://github.com/yourusername/your-repository-name.git

# 推送到GitHub
git branch -M main
git push -u origin main
```

## 3. 配置环境变量

上传完成后，您需要在运行项目前配置环境变量：

1. 在仓库根目录复制 `.env.example` 文件并重命名为 `.env`
2. 在 `.env` 文件中填入您的API密钥和Webhook URL
3. **注意：不要将包含真实密钥的 `.env` 文件提交到Git仓库**

## 4. 部署到生产环境

### 本地运行
```bash
# 安装依赖
pip install -r requirements.txt

# 运行机器人
python daily_news_bot.py
```

### 使用GitHub Actions（推荐）
1. 在仓库中创建 `.github/workflows/daily_news.yml` 文件
2. 配置Secrets：
   - `DEEPSEEK_API_KEY`
   - `FEISHU_WEBHOOK_URL`
   - （可选）其他API密钥

## 5. 注意事项

- 项目中的 `.gitignore` 文件已经配置好，确保 `.env` 文件不会被提交
- 请勿在代码或提交信息中泄露任何敏感信息
- 定期更新依赖包以确保安全性

## 6. 项目特色

- 🤖 **AI驱动**：使用DeepSeek大模型进行新闻分析
- 🌐 **多源抓取**：从全球25个RSS源抓取新闻
- 💬 **飞书集成**：支持Webhook方式推送消息
- 📊 **智能分析**：包含情绪评分、价格注入等功能
- 🔒 **安全设计**：敏感信息隔离，符合最佳实践