# 飞书应用配置指南

## 应用创建步骤

1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 登录后进入"开发者后台"
3. 点击"创建企业自建应用"
4. 填写应用名称（如"每日AI新闻机器人"）
5. 完善应用图标和描述信息

## 获取凭证信息

1. 在应用详情页面找到"凭证与基础信息"
2. 记录以下信息：
   - App ID: `cli_a9f6280dd5389bd8`
   - App Secret: `VHN4Eag0koh7rwEkKXeHSgHzLnH1140x`
   - 租户Token（如果需要）

## 权限配置

### 必需权限
- `im:message:send` - 发送消息权限
- `im:chat:read` - 读取群组信息权限
- `contact:user.employee_id:readonly` - 获取用户信息权限（解决Access denied错误）
- `im:image:upload` - 上传图片权限（用于发送图片）

### 授权范围
- 个人
- 团队
- 全员

### 权限配置步骤
1. 在飞书开发者后台进入应用详情页面
2. 点击「权限管理」选项卡
3. 点击「添加权限」按钮
4. 搜索并添加上述必需权限
5. 提交审核并发布

## 环境变量配置

在使用应用认证方式时，需要设置以下环境变量：

```bash
# 飞书应用凭证
export LARK_APP_ID=cli_a9f6280dd5389bd8
export LARK_APP_SECRET=VHN4Eag0koh7rwEkKXeHSgHzLnH1140x

# 可选：指定发送消息的目标
export LARK_CHAT_ID="your_chat_id_here"  # 发送到特定群组
export LARK_USER_ID="your_user_id_here"  # 发送到特定用户
```

## 使用方法

### 本地运行
```bash
# 设置环境变量
export LARK_APP_ID=cli_a9f6280dd5389bd8
export LARK_APP_SECRET=VHN4Eag0koh7rwEkKXeHSgHzLnH1140x

# 运行程序
python daily_news_bot.py
```

### GitHub Actions
在仓库设置中添加以下 Secrets:
- `LARK_APP_ID`: 飞书应用ID
- `LARK_APP_SECRET`: 飞书应用密钥
- `LARK_CHAT_ID`: 目标群组ID（可选）
- `LARK_USER_ID`: 目标用户ID（可选）

## 功能对比

| 功能 | Webhook方式 | 应用认证方式 |
|------|-------------|---------------|
| 发送文本消息 | ✅ 支持 | ✅ 支持 |
| 发送图片 | ❌ 不支持 | ✅ 支持 |
| 发送表格 | ❌ 不支持 | ✅ 支持 |
| 发送富文本 | 有限支持 | 完全支持 |
| 用户交互 | 有限 | 丰富 |
| 消息格式 | 卡片格式 | 多种格式 |

## 故障排除

### 常见问题
1. **认证失败**: 检查App ID和App Secret是否正确
2. **无法发送消息**: 确认应用已获得相应权限
3. **图片上传失败**: 检查上传文件权限是否开启

### 调试方法
启用调试模式查看详细日志：
```bash
export DEBUG_LARK=true
```

## 安全建议

1. App Secret请妥善保管，不要泄露
2. 在GitHub Actions中使用Secrets存储敏感信息
3. 定期更换App Secret
4. 限制应用权限范围，遵循最小权限原则