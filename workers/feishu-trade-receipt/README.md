# Feishu Trade Receipt Worker

This Worker receives Feishu message events, accepts only `BUY ...` or `SELL ...`
trade receipts, and dispatches the GitHub Actions `trade_receipt.yml` workflow.

Required Worker secrets:

- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`
- `FEISHU_VERIFICATION_TOKEN`
- `FEISHU_ENCRYPT_KEY`
- `GITHUB_TOKEN`

`GITHUB_TOKEN` must be able to dispatch workflows in `Qiqi-bi/daily-news-bot`.
Use a fine-grained GitHub token with Actions write permission.

Feishu event subscription:

- Request URL: `https://<worker-subdomain>.workers.dev/`
- Event: `im.message.receive_v1`
- Encryption: enabled, using the same Encrypt Key stored in Worker secrets

Accepted receipts:

```text
BUY 518880 3000 5.12 黄金回落补保险仓
SELL 513100 20% 1.35 AI仓位超线
SELL 513100 100 1.35 减100份
```

Messages that do not start with `BUY` or `SELL` are ignored.
