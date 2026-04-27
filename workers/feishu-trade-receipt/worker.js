const TEXT_ENCODER = new TextEncoder();
const TEXT_DECODER = new TextDecoder();

function jsonResponse(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
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
  return /^(BUY|SELL)\s+/i.test(text);
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

export default {
  async fetch(request, env) {
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
