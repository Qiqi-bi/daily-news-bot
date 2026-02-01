# GitHub 部署指南

## 上传到 GitHub

现在项目代码已经完全准备好上传到 GitHub。由于所有敏感信息都通过环境变量配置，你可以安全地将代码推送到 GitHub 仓库，不用担心密钥泄露。

## 本地运行配置

如果你在本地运行此项目，需要：

1. 在项目根目录创建 `.env` 文件
2. 在 `.env` 文件中配置你的密钥：

```env
DEEPSEEK_API_KEY=your_deepseek_api_key_here
FEISHU_WEBHOOK_URL=your_feishu_webhook_url_here
```

3. 安装依赖并运行：

```bash
pip install -r requirements.txt
playwright install chromium
python daily_news_bot.py
```

## GitHub Actions 部署

如果你想使用 GitHub Actions 实现自动运行，可以按以下步骤操作：

### 1. 创建 GitHub Secrets

在你的 GitHub 仓库中设置以下 Secrets：

- `DEEPSEEK_API_KEY`: 你的 DeepSeek API 密钥
- `FEISHU_WEBHOOK_URL`: 你的飞书 webhook URL
- `MARKETAUX_API_KEY`: (可选) Marketaux API 密钥
- `POLYGON_API_KEY`: (可选) Polygon API 密钥

设置方法：
1. 进入 GitHub 仓库
2. 点击 "Settings" 选项卡
3. 在左侧菜单选择 "Secrets and variables" -> "Actions"
4. 点击 "New repository secret" 添加上述密钥

### 2. GitHub Actions 工作流文件

项目中已经包含了 `.github/workflows/daily_news.yml` 文件，它会自动使用你设置的 Secrets。

## 云服务器部署

如果你想在云服务器上运行：

1. 克隆你的 GitHub 仓库
2. 在服务器上创建 `.env` 文件并配置密钥
3. 安装依赖并运行

## 安全说明

- 所有敏感信息都通过环境变量配置
- `.env` 文件已被添加到 `.gitignore`，不会被提交到 Git 仓库
- GitHub Actions 使用 Secrets 存储敏感信息，同样安全

## 总结

你现在可以安全地将代码推送到 GitHub，因为：
1. 代码中不包含任何硬编码的密钥
2. 所有敏感信息都通过环境变量配置
3. 本地运行时只需在 `.env` 文件中配置密钥
4. GitHub Actions 部署时使用仓库 Secrets