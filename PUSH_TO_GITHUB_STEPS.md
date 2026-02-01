# 推送代码到 GitHub 的步骤

## 1. 初始化本地 Git 仓库（如果还没有）

```bash
git init
git add .
git commit -m "Initial commit: Daily AI News Bot with Enhanced RSS Fetcher"
```

## 2. 添加远程仓库

```bash
git remote add origin https://github.com/你的用户名/你的仓库名.git
```

## 3. 推送代码到 GitHub

```bash
git branch -M main
git push -u origin main
```

## 4. 验证推送结果

推送完成后，检查 GitHub 仓库确保所有文件都已成功上传。

## 5. 设置 GitHub Actions（可选）

如果你希望使用 GitHub Actions 自动运行机器人：

1. 确保 `.github/workflows/daily_news.yml` 文件已成功上传
2. 在 GitHub 仓库的 Settings > Secrets and variables > Actions 中设置以下密钥：
   - `DEEPSEEK_API_KEY`
   - `FEISHU_WEBHOOK_URL`
   - （可选）`MARKETAUX_API_KEY`
   - （可选）`POLYGON_API_KEY`

## 6. 验证 GitHub Actions（可选）

1. 在 GitHub 仓库页面点击 "Actions" 标签
2. 检查工作流是否正常运行
3. 查看日志以确认机器人是否成功执行

## 7. 本地测试运行

在推送之前，你也可以先在本地测试运行：

```bash
# 确保已安装依赖
pip install -r requirements.txt
playwright install chromium

# 运行机器人
python daily_news_bot.py
```

## 注意事项

- 确保 `.env` 文件不会被推送（已在 `.gitignore` 中配置）
- 确保所有敏感信息都只存在于本地环境变量中
- 推送后检查仓库确保没有泄露任何敏感信息