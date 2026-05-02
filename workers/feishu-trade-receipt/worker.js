const TEXT_ENCODER = new TextEncoder();
const TEXT_DECODER = new TextDecoder();

function jsonResponse(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}

function htmlResponse(body, status = 200) {
  return new Response(body, {
    status,
    headers: { "content-type": "text/html; charset=utf-8" },
  });
}

function bytesToHex(bytes) {
  return [...bytes].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

function base64ToBytes(value) {
  const binary = atob(value);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes;
}

async function sha256Bytes(value) {
  return new Uint8Array(await crypto.subtle.digest("SHA-256", TEXT_ENCODER.encode(value)));
}

async function verifySignature(request, rawBody, encryptKey) {
  const signature = request.headers.get("x-lark-signature") || request.headers.get("x-feishu-signature");
  const timestamp = request.headers.get("x-lark-request-timestamp") || request.headers.get("x-feishu-request-timestamp");
  const nonce = request.headers.get("x-lark-request-nonce") || request.headers.get("x-feishu-request-nonce");
  if (!signature || !timestamp || !nonce) {
    return false;
  }
  const digest = await sha256Bytes(`${timestamp}${nonce}${encryptKey}${rawBody}`);
  return bytesToHex(digest) === signature.toLowerCase();
}

async function decryptEvent(encryptValue, encryptKey) {
  const keyBytes = await sha256Bytes(encryptKey);
  const encrypted = base64ToBytes(encryptValue);
  const iv = encrypted.slice(0, 16);
  const ciphertext = encrypted.slice(16);
  const key = await crypto.subtle.importKey("raw", keyBytes, { name: "AES-CBC" }, false, ["decrypt"]);
  const plain = await crypto.subtle.decrypt({ name: "AES-CBC", iv }, key, ciphertext);
  return JSON.parse(TEXT_DECODER.decode(plain));
}

async function parsePayload(request, env, rawBody) {
  const body = JSON.parse(rawBody || "{}");
  if (body.encrypt) {
    if (!env.FEISHU_ENCRYPT_KEY) {
      throw new Error("FEISHU_ENCRYPT_KEY is required for encrypted Feishu events");
    }
    const signed = await verifySignature(request, rawBody, env.FEISHU_ENCRYPT_KEY);
    const payload = await decryptEvent(body.encrypt, env.FEISHU_ENCRYPT_KEY);
    // Feishu URL verification requests can be encrypted but unsigned.
    if (!signed && !isUrlVerification(payload)) {
      throw new Error("Invalid Feishu event signature");
    }
    return payload;
  }
  return body;
}

function eventToken(payload) {
  return payload?.token || payload?.header?.token || payload?.event?.token || "";
}

function isUrlVerification(payload) {
  return payload?.type === "url_verification" || payload?.header?.event_type === "url_verification" || Boolean(payload?.challenge);
}

function challengeValue(payload) {
  return payload?.challenge || payload?.event?.challenge || "";
}

function eventType(payload) {
  return payload?.header?.event_type || payload?.type || "";
}

function messageEvent(payload) {
  return payload?.event || {};
}

function senderOpenId(event) {
  return event?.sender?.sender_id?.open_id || "";
}

function messageId(event) {
  return event?.message?.message_id || "";
}

function messageText(event) {
  if (event?.message?.message_type !== "text") {
    return "";
  }
  try {
    const content = JSON.parse(event.message.content || "{}");
    return String(content.text || "").trim();
  } catch {
    return "";
  }
}

function normalizeReceiptText(text) {
  return text
    .replace(/@\S+\s*/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function isTradeReceipt(text) {
  return /^(BUY|SELL|买入|加仓|卖出|减仓)\s+/i.test(text);
}

function allowedSender(openId, env) {
  const allowList = String(env.FEISHU_ALLOWED_OPEN_IDS || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  return allowList.length === 0 || allowList.includes(openId);
}

async function dispatchTradeReceipt(receiptText, senderId, messageIdValue, env) {
  const owner = env.GITHUB_OWNER;
  const repo = env.GITHUB_REPO;
  const workflow = env.GITHUB_WORKFLOW || "trade_receipt.yml";
  const ref = env.GITHUB_REF || "main";
  if (!owner || !repo || !env.GITHUB_TOKEN) {
    throw new Error("GITHUB_OWNER, GITHUB_REPO and GITHUB_TOKEN are required");
  }
  const response = await fetch(`https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflow}/dispatches`, {
    method: "POST",
    headers: {
      authorization: `Bearer ${env.GITHUB_TOKEN}`,
      accept: "application/vnd.github+json",
      "content-type": "application/json",
      "x-github-api-version": "2022-11-28",
      "user-agent": "daily-news-feishu-trade-receipt",
    },
    body: JSON.stringify({
      ref,
      inputs: {
        receipt_text: receiptText,
        sender_id: senderId,
        message_id: messageIdValue,
      },
    }),
  });
  if (!response.ok) {
    throw new Error(`GitHub workflow dispatch failed: ${response.status} ${await response.text()}`);
  }
}

async function tenantAccessToken(env) {
  if (!env.FEISHU_APP_ID || !env.FEISHU_APP_SECRET) {
    return "";
  }
  const response = await fetch("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ app_id: env.FEISHU_APP_ID, app_secret: env.FEISHU_APP_SECRET }),
  });
  if (!response.ok) {
    return "";
  }
  const payload = await response.json();
  return payload.tenant_access_token || "";
}

async function replyToMessage(messageIdValue, text, env) {
  const token = await tenantAccessToken(env);
  if (!token || !messageIdValue) {
    return;
  }
  await fetch(`https://open.feishu.cn/open-apis/im/v1/messages/${messageIdValue}/reply`, {
    method: "POST",
    headers: {
      authorization: `Bearer ${token}`,
      "content-type": "application/json",
    },
    body: JSON.stringify({
      msg_type: "text",
      content: JSON.stringify({ text }),
    }),
  });
}

async function handleFeishuEvent(request, env) {
  const rawBody = await request.text();
  const payload = await parsePayload(request, env, rawBody);
  const token = eventToken(payload);
  if (env.FEISHU_VERIFICATION_TOKEN && token && token !== env.FEISHU_VERIFICATION_TOKEN) {
    return jsonResponse({ error: "invalid token" }, 401);
  }

  if (isUrlVerification(payload)) {
    return jsonResponse({ challenge: challengeValue(payload) });
  }
  if (eventType(payload) !== "im.message.receive_v1") {
    return jsonResponse({ ok: true, ignored: true });
  }

  const event = messageEvent(payload);
  const openId = senderOpenId(event);
  if (!allowedSender(openId, env)) {
    return jsonResponse({ ok: true, ignored: true });
  }

  const receiptText = normalizeReceiptText(messageText(event));
  if (!isTradeReceipt(receiptText)) {
    return jsonResponse({ ok: true, ignored: true });
  }

  const msgId = messageId(event);
  await dispatchTradeReceipt(receiptText, openId, msgId, env);
  await replyToMessage(msgId, "收到交易回执，已触发入账；下次日报会按新仓位计算。", env);
  return jsonResponse({ ok: true });
}

function formTokenValid(request, env) {
  const expected = String(env.RECEIPT_FORM_TOKEN || "").trim();
  if (!expected) {
    return false;
  }
  const url = new URL(request.url);
  return url.searchParams.get("token") === expected;
}

function receiptFormHtml(request, message = "") {
  const url = new URL(request.url);
  const token = url.searchParams.get("token") || "";
  const action = url.searchParams.get("action") || "";
  const selectedSide = action === "sell" ? "卖出" : "买入";
  const buySelected = selectedSide === "买入" ? " selected" : "";
  const sellSelected = selectedSide === "卖出" ? " selected" : "";
  const escapedMessage = message ? `<div class="notice">${message}</div>` : "";
  const noopPanel = action === "noop" ? `
    <section class="noop">
      <h2>今天没操作</h2>
      <p>不用提交任何内容。系统会按原仓位继续跟踪，下一次日报仍会保留观察和复盘。</p>
      <a href="/receipt?token=${encodeURIComponent(token)}">我其实有操作，要填写回执</a>
    </section>
  ` : "";
  const formPanel = action === "noop" ? "" : `
    <form method="post" action="/receipt?token=${encodeURIComponent(token)}">
      <label>方向<select name="side"><option value="买入"${buySelected}>买入/加仓</option><option value="卖出"${sellSelected}>卖出/减仓</option></select></label>
      <label>代码<input name="code" inputmode="numeric" placeholder="例如 518880" required></label>
      <label>金额或份额<input name="amount" placeholder="例如 3000 或 20%" required></label>
      <label>价格<input name="price" inputmode="decimal" placeholder="例如 5.12" required></label>
      <label>原因<input name="reason" placeholder="例如 回撤到纪律线" required></label>
      <button type="submit">提交回执</button>
    </form>
  `;
  return `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>操作回执</title>
  <style>
    body{margin:0;background:#f3f6fb;color:#0f172a;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
    main{max-width:520px;margin:0 auto;padding:22px 16px}
    form,.noop{background:#fff;border:1px solid #d8e0ea;border-radius:12px;padding:16px;display:grid;gap:12px}
    h1{font-size:24px;margin:0 0 8px}.hint{color:#526173;font-size:14px;line-height:1.6;margin-bottom:14px}
    h2{font-size:18px;margin:0}.noop p{margin:0;color:#334155;line-height:1.7}.noop a{color:#1677ff;text-decoration:none;font-weight:700}
    label{display:grid;gap:6px;font-size:13px;color:#334155;font-weight:650}
    input,select{height:42px;border:1px solid #cbd5e1;border-radius:8px;padding:0 10px;font-size:15px}
    button{height:44px;border:0;border-radius:8px;background:#1677ff;color:#fff;font-size:16px;font-weight:750}
    .notice{background:#ecfdf5;border:1px solid #bbf7d0;color:#166534;border-radius:8px;padding:10px 12px;margin-bottom:12px}
    .warn{color:#64748b;font-size:12px;line-height:1.6;margin-top:12px}
  </style>
</head>
<body>
  <main>
    <h1>操作回执</h1>
    <div class="hint">有操作就填；没操作不用提交。系统只记录你主动回执的买入/卖出，不会猜测你的实际操作。</div>
    ${escapedMessage}
    ${noopPanel}
    ${formPanel}
    <div class="warn">提交后会触发一次入账流程；下一次日报会按新回执复核仓位。</div>
  </main>
</body>
</html>`;
}

async function handleReceiptForm(request, env) {
  if (!formTokenValid(request, env)) {
    return htmlResponse("回执表单未启用或链接无效。", 403);
  }
  if (request.method === "GET") {
    return htmlResponse(receiptFormHtml(request));
  }
  const form = await request.formData();
  const side = String(form.get("side") || "").trim();
  const code = String(form.get("code") || "").trim();
  const amount = String(form.get("amount") || "").trim();
  const price = String(form.get("price") || "").trim();
  const reason = String(form.get("reason") || "").trim();
  if (!/^(买入|卖出)$/.test(side) || !code || !amount || !price || !reason) {
    return htmlResponse(receiptFormHtml(request, "有字段没填完整，请补齐后再提交。"), 400);
  }
  const receiptText = normalizeReceiptText(`${side} ${code} ${amount} ${price} ${reason}`);
  const messageIdValue = `form-${Date.now()}`;
  await dispatchTradeReceipt(receiptText, "receipt-form", messageIdValue, env);
  return htmlResponse(receiptFormHtml(request, "已收到回执，正在触发入账流程。"));
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/receipt") {
      try {
        return await handleReceiptForm(request, env);
      } catch (error) {
        console.error(error);
        return htmlResponse("提交失败，请回飞书群里直接发中文回执。", 500);
      }
    }
    if (request.method === "GET") {
      return jsonResponse({ ok: true, service: "daily-news-bot feishu trade receipt" });
    }
    if (request.method !== "POST") {
      return jsonResponse({ error: "method not allowed" }, 405);
    }
    try {
      return await handleFeishuEvent(request, env);
    } catch (error) {
      console.error(error);
      return jsonResponse({ error: "event handling failed" }, 500);
    }
  },
};
