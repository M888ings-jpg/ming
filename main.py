import json
import time
import secrets
import ssl
import base64
import requests
import io
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context
from gmssl import sm2, sm4
from gmssl.sm3 import sm3_hash

# 引入 Telegram Bot 相关的库 (python-telegram-bot v20.x 异步版本)
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationManager

# 定义对话状态
NAME, IDCARD = range(2)

# --- 国密与 SSL 适配逻辑 ---
class LegacySSLAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)

session = requests.Session()
session.mount("https://", LegacySSLAdapter())

HOST = "https://video.lccb.com.cn:18011"
LOGIN_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJjdXJyZW50VGltZU1pbGxpcyI6MTt8MTY1Mjk1MjI2OSwiZXhwIjoxNzgxNjYwMTUyLCJhY2NvdW50Ijoie1wib3BlbklkXCI6XCJvbDNGUTQ5eF8wQjJqTFpfN1c0S2ZYOHZTelIwXCIsXCJ0aW1lc3RhbXBcIjoxNzgxNjUyOTUyMjY5fSJ9.JhWnyirZpFQyp4uX3u0Zu3pqjQWm8uIAWOFkrEVtq30"

BASE_HEADERS = {
    'Content-Type': 'application/json',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows',
    'Referer': 'https://servicewechat.com/wxbadde32e3b471476/67/page-frame.html',
}

def random_hex32():
    return ''.join(secrets.choice('0123456789abcdef') for _ in range(32))

def random_nonce32():
    return ''.join(secrets.choice('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz') for _ in range(32))

def sm3_sign(data: str) -> str:
    return sm3_hash([b for b in data.encode('utf-8')])

def sm4_encrypt(key_hex: str, plaintext: str) -> str:
    crypt = sm4.CryptSM4()
    crypt.set_key(bytes.fromhex(key_hex), sm4.SM4_ENCRYPT)
    data = plaintext.encode('utf-8')
    pad = 16 - len(data) % 16
    data += bytes([pad] * pad)
    return crypt.crypt_ecb(data).hex()

def sm4_decrypt(key_hex: str, cipher_hex: str) -> str:
    crypt = sm4.CryptSM4()
    crypt.set_key(bytes.fromhex(key_hex), sm4.SM4_DECRYPT)
    raw = crypt.crypt_ecb(bytes.fromhex(cipher_hex))
    last = raw[-1]
    if 1 <= last <= 16 and all(b == last for b in raw[-last:]):
        raw = raw[:-last]
    return raw.decode('utf-8', errors='replace').rstrip('\x00')

def sm2_encrypt(pub_key_hex: str, sm4_key_str: str) -> str:
    b64 = base64.b64encode(sm4_key_str.encode('utf-8')).decode('utf-8')
    plaintext = b64.encode('utf-8')
    pk = pub_key_hex[-128:] if len(pub_key_hex) > 128 else pub_key_hex
    sm2_obj = sm2.CryptSM2(public_key=pk, private_key="")
    enc = sm2_obj.encrypt(plaintext).hex()
    c1, c2, c3 = enc[:128], enc[128: 128 + len(plaintext) * 2], enc[128 + len(plaintext) * 2:]
    return "04" + c1 + c3 + c2

def get_pub_key() -> str:
    ts, nonce = int(time.time() * 1000), random_nonce32()
    sign = sm3_sign(LOGIN_TOKEN + str(ts) + nonce)
    headers = {**BASE_HEADERS, 'Timestamp': str(ts), 'Nonce': nonce, 'Sign': sign}
    return session.post(f"{HOST}/busiroom/getPubKey", headers=headers, json={}).json()['data']['pubKey']

def post_encrypt(path: str, payload: dict) -> dict:
    ts, nonce, sm4_key = int(time.time() * 1000), random_nonce32(), random_hex32()
    enc_data = sm4_encrypt(sm4_key, json.dumps(payload, ensure_ascii=False, separators=(',', ':')))
    token = sm2_encrypt(get_pub_key(), sm4_key)
    sign = sm3_sign(token + str(ts) + nonce)
    headers = {**BASE_HEADERS, 'Timestamp': str(ts), 'Nonce': nonce, 'Sign': sign, 'Logintoken': LOGIN_TOKEN, 'Token': token}
    resp = session.post(HOST + path, data=json.dumps({"data": enc_data}), headers=headers).json()
    if resp.get('data'):
        dec = sm4_decrypt(sm4_key, resp['data'])
        try: resp['data'] = json.loads(dec)
        except: resp['data'] = dec
    return resp


# --- Telegram 机器人交互逻辑 ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """/start 开始，提示用户输入姓名"""
    await update.message.reply_text("👋 你好！欢迎使用查询系统。\n\n请输入要查询的 **姓名**:")
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """接收姓名，提示输入身份证号"""
    context.user_data['username'] = update.message.text.strip()
    await update.message.reply_text(f"已记录姓名：`{context.user_data['username']}`\n\n请输入对应的 **身份证号**:")
    return IDCARD

async def get_idcard_and_run(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """接收身份证号，运行加密接口并直接下发图片"""
    username = context.user_data.get('username')
    id_card = update.message.text.strip()
    
    status_msg = await update.message.reply_text("正在发起认证请求，请稍候...")

    try:
        # 1. 发起国密加密认证请求
        auth_payload = {
            "name": username,
            "cardId": id_card,
            "imgUrl": "https://video.bankoflangfang.net:8012/busiroom/legalimg/132926197803281746LWHC.png"
        }
        _ = post_encrypt("/busiroom/faceIdent/miniFaceExpand", auth_payload)

        await status_msg.edit_text("认证成功！正在获取图片缓存...")

        # 2. 从服务器请求图片数据
        download_url = f"https://video.lccb.com.cn:18011/busiroom/legalimg/{id_card}LWHC.png"
        img_resp = session.get(download_url, headers=BASE_HEADERS)
        
        if img_resp.status_code == 200:
            await status_msg.edit_text("图片获取成功，正在发送至您的聊天框...")
            
            # 使用 io.BytesIO 直接把内存中的二进制流转化为虚拟文件发送，不占用磁盘空间
            photo_file = io.BytesIO(img_resp.content)
            photo_file.name = f"{id_card}.png"
            
            # 直接给用户发送图片
            await update.message.reply_photo(
                photo=photo_file, 
                caption=f"✅ 成功获取到【{username}】的身份证图片。"
            )
            # 删除中途的提示消息
            await status_msg.delete()
        else:
            await status_msg.edit_text(f"❌ 图片下载失败，接口返回状态码: {img_resp.status_code}")

    except Exception as e:
        await status_msg.edit_text(f"💥 运行中出现异常: {str(e)}")

    return ConversationManager.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """/cancel 取消当前操作"""
    await update.message.reply_text("已取消当前查询。随时可以发送 /start 重新开始。")
    return ConversationManager.END

def main():
    # 填入你提供的 Token
    BOT_TOKEN = "8338893180:AAH-l_4m1-tweKyt92bliyk4fsPqoPQWzpU"

    # 初始化 Telegram 机器人实例
    application = Application.builder().token(BOT_TOKEN).build()

    # 配置引导式对话流程 (姓名 -> 身份证)
    conv_handler = ConversationManager(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            IDCARD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_idcard_and_run)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    # 启动轮询监听
    print("🚀 Telegram Bot 已成功启动并在后台监听中...")
    application.run_polling()

if __name__ == '__main__':
    main()
