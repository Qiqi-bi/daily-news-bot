# 飞书Webhook配置指南

## Webhook创建步骤

1. 在飞书群聊中点击右上角群设置
2. 机器人 → 添加机器人 → 自定义机器人
3. 设置机器人名称（如"每日AI新闻机器人"）
4. 完善机器人图标和描述信息
5. 复制Webhook地址

## 环境变量配置

只需要设置以下环境变量：

```bash
FEISHU_WEBHOOK_URL=你的webhook地址
```

## 环境变量设置

### Linux/macOS
```bash
export LARK_APP_ID=
export LARK_APP_SECRET=
```

### Windows (命令提示符)
```batch
set FEISHU_WEBHOOK_URL=你的webhook地址
```

### GitHub Actions
在仓库设置中添加以下 Secrets:
- `FEISHU_WEBHOOK_URL`: 飞书群聊webhook地址

## 功能对比

| 功能 | Webhook方式 |
|------|-------------|
| 发送文本消息 | ✅ 支持 |
| 发送富文本卡片 | ✅ 支持 |
| 消息格式 | 卡片格式 |

## 故障排除

### 常见问题
1. **无法发送消息**: 检查webhook地址是否正确，确认机器人已在群聊中
2. **消息格式错误**: 检查消息内容是否符合飞书卡片格式规范
3. **网络连接问题**: 确认网络连接正常，代理设置正确

### 调试方法
启用调试模式查看详细日志：
```bash
export DEBUG_LARK=true
```

## 安全建议

1. Webhook地址请妥善保管，不要泄露
2. 在GitHub Actions中使用Secrets存储敏感信息
3. 定期更换webhook地址
