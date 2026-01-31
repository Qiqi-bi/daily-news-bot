import requests
import json

# ================= 配置区 =================
# 请把您的 App ID 和 Secret 填在这里
APP_ID = os.environ.get('LARK_APP_ID', 'YOUR_LARK_APP_ID_HERE')  # 您的 App ID
APP_SECRET = os.environ.get('LARK_APP_SECRET', 'YOUR_LARK_APP_SECRET_HERE') # 您的 App Secret (注意：这里填您截图里那个长的，不要填星号)
# =========================================

def get_tenant_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json; charset=utf-8"}
    payload = {
        "app_id": APP_ID,
        "app_secret": APP_SECRET
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json().get("tenant_access_token")
    except Exception as e:
        print(f"❌ 获取 Token 失败: {e}")
        return None

def get_bot_groups():
    token = get_tenant_access_token()
    if not token:
        return

    # 获取机器人所在的群列表
    url = "https://open.feishu.cn/open-apis/im/v1/chats"
    headers = {"Authorization": f"Bearer {token}"}
    # 查找最近的 20 个群
    params = {"page_size": 20} 

    print("\n🔍 正在扫描机器人所在的群组...\n")
    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        
        if data.get("code") != 0:
            print(f"❌ 请求失败: {data.get('msg')}")
            return

        items = data.get("data", {}).get("items", [])
        
        if not items:
            print("⚠️ 未找到任何群组！请确认：\n1. 您已经把机器人拉进了飞书群\n2. App ID 和 Secret 填写正确")
        else:
            print("✅ 找到以下群组 (请复制 Chat ID):")
            print("="*50)
            for chat in items:
                print(f"群名称: {chat.get('name')}")
                print(f"Chat ID: {chat.get('chat_id')}")  # <--- 这就是我们要的！
                print("-" * 30)
            print("="*50)

    except Exception as e:
        print(f"❌ 发生错误: {e}")

if __name__ == "__main__":
    get_bot_groups()