import telebot
import requests
import time
import re
import threading
import json
import os
import itertools
import binascii
import random
import concurrent.futures
import inspect  
import urllib.parse
from datetime import datetime
from telebot import types
from concurrent.futures import ThreadPoolExecutor
from base64 import b64decode, b64encode
from urllib.parse import quote

# 核心加密组件 (用于新二要素)
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:
    print("❌ 核心加密组件未安装, 请安装: pip install cryptography")

# 屏蔽 SSL 证书报警
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# ================= 1. 核心配置 =================
API_TOKEN = '8505048236:AAFHPC3448Gti60whSAC9mak_oKzd7BN1eY'
ADMIN_ID = 6649617045 
ADMIN_USERNAME = "@aaSm68"
POINTS_FILE = 'points.json'

# 新二要素国政接口配置
API_USERINFO = "https://quickapp.gjzwfw.gov.cn/account/normal/userinfo-desensit"
KEY_BASE64 = "YXVlQmdQTFR1OFY2NXRnVQ=="
IV_BASE64 = "YXVlQmdQTFR1OFY2NXRnVQ=="
ENCRY_AES_KEY = """koKocx3nMhyWVVLVIeIwvczakLlcPFak1ILtZJpjD26FhZAYAG47kKlIQgZYCoT3e+L5yH2FYOT3
5Go847D1ihIvuUbqCenMKHBq5ms2v3Oj+n4lW4rncE5sNDXGO3RJO6yB1gXHl6AOEsTHSqVUSx5B
O5H5c9V6W+zk+ZQXgtg1BOK8uMtN+tfr8nFuyxZnWlMt0kRe/KYb9bw/3P+5XiQHZQcYP5KUNr/X
AatNmX47bA7htq5vowxnvy4gQ5ZGjVa4CZNzp4lrORV2FR/autfXFoEnFvwix9K9tP5SwvUDza8s
YA1fYcstRM2N910pfVaXgYUMSaR2AMtTwiMJ4K3y+sgfA4trXI61J34Lf/AspuuV5q9lTfcHlloH
HOZhIkgRA4wrZGVmxCSYX3uV76OrnupW9hi/nwzCRfmw46PdPE+rjtSoZlc8aLp5CbIvWxlXsScM
q0g/4yr90EC6Gn4BnTbHYJz+yjnVxofPnDWCyz/xkUdFNKCyFfx+XSt7"""

bot = telebot.TeleBot(API_TOKEN)
user_points = {}
user_states = {}

# --- 数据持久化 ---
def load_data():
    pts = {}
    if os.path.exists(POINTS_FILE):
        try:
            with open(POINTS_FILE, 'r') as f:
                data = json.load(f)
                pts = {int(k): float(v) for k, v in data.items()}
        except: pass
    return pts

user_points = load_data()

def save_points():
    with open(POINTS_FILE, 'w') as f:
        json.dump({str(k): v for k, v in user_points.items()}, f)


# ==================== AES加密类 ====================
class AESCipher:
    def __init__(self):
        self.key = b64decode(KEY_BASE64)
        self.iv = b64decode(IV_BASE64)

    def encrypt(self, plaintext: str) -> str:
        aesgcm = AESGCM(self.key)
        encrypted_bytes = aesgcm.encrypt(self.iv, plaintext.encode('utf-8'), None)
        return b64encode(encrypted_bytes).decode('utf-8')

def format_encry_aes_key():
    return ENCRY_AES_KEY.replace('\n', '%0A').replace('+', '%2B').replace('/', '%2F')


# ================= 2. 功能逻辑 =================

def query_3ys_logic(chat_id, name, id_card, phone, uid):
    """三要素核验"""
    wait_msg = bot.send_message(chat_id, "⏳ 正在核验...")
    url = "http://xiaowunb.top/3ys.php"
    params = {"name": name, "sfz": id_card, "sjh": phone}
    try:
        response = requests.get(url, params=params, timeout=15); response.encoding = 'utf-8'
        user_points[uid] -= 0.05; save_points()
        clean_res = re.sub(r'小无 API.*?官方客服:@\w+', '', response.text.strip(), flags=re.DOTALL).strip()
        res_status = "三要素核验成功✅" if ("成功" in clean_res or "一致" in clean_res) else "三要素核验失败❌"
        bot.delete_message(chat_id, wait_msg.message_id)
        bot.send_message(chat_id, f"姓名:{name}\n手机号:{phone}\n身份证:{id_card}\n结果:{res_status}\n\n"
                                  f"<b>已扣除 0.05 积分!</b>\n<b>当前余额:{user_points[uid]:.2f}</b>", parse_mode='HTML')
    except Exception as e: bot.edit_message_text(f"⚠️ 核验异常: {str(e)}", chat_id, wait_msg.message_id)

def single_verify_2ys(chat_id, name, id_card, uid):
    """二要素核验 - 已替换为国政新接口逻辑"""
    wait_msg = bot.send_message(chat_id, "⏳ 正在进行国政二要素核验...")
    
    try:
        cipher = AESCipher()
        enc_name = cipher.encrypt(name)
        enc_id = cipher.encrypt(id_card)
    except Exception as crypto_err:
        bot.edit_message_text(f"❌ 加密组件出错: {crypto_err}\n请确保服务器环境已安装 cryptography 库。", chat_id, wait_msg.message_id)
        return

    body = f"encryAesKey={format_encry_aes_key()}&name={quote(enc_name)}&idNo={quote(enc_id)}"
    headers = {
        'brand': 'huawei',
        'version': '427',
        'user-agent': 'Mozilla/5.0 (Linux; Android 7.1.2)',
        'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
    }

    try:
        resp = requests.post(API_USERINFO, headers=headers, data=body, timeout=15)
        resp_text = resp.text
        
        # 扣除积分
        user_points[uid] -= 0.01
        save_points()
        
        # 默认解析状态
        status_title = "🟡 二要素核验失败"
        status_detail = ""
        
        try:
            data = json.loads(resp_text)
            code = data.get("code")
            has_success = "success" in resp_text

            if has_success and "data" in data and data["data"]:
                status_title = "二要素核验一致✅"
                status_detail = f"\n<b>返回数据:</b> {data['data']}"
            elif "查询不到绑定号码" in resp_text:
                status_title = "二要素核验一致✅"
                status_detail = f"\n<b>国政:</b> 未查询到号码"
            elif "无此用户信息" in resp_text:
                status_title = "二要素核验一致✅"
                status_detail = f"\n<b>详情:</b> 无国政账号"
            elif code == 20000 and "验证失败" in resp_text:
                status_title = "二要素验证失败❌"
            else:
                status_detail = f"\n原始响应: {resp_text}"
        except:
            status_detail = f"\n原始响应: {resp_text}"

        # 组装发给用户的消息
        result_msg = (
            f"<b>姓名:</b> {name}\n"
            f"<b>身份证:</b> <code>{id_card}</code>\n"
            f"<b>结果:</b> {status_title}{status_detail}\n\n"
            f"<b>已扣除 0.01 积分!</b>\n"
            f"<b>当前余额: {user_points[uid]:.2f} 积分</b>"
        )
        bot.delete_message(chat_id, wait_msg.message_id)
        bot.send_message(chat_id, result_msg, parse_mode='HTML')

    except Exception as e: 
        bot.edit_message_text(f"❌ 请求异常: {str(e)}", chat_id, wait_msg.message_id)

# ================= 3. UI 菜单 =================

def get_main_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("使用帮助", callback_data="view_help"), types.InlineKeyboardButton("在线充值", callback_data="view_pay"))
    return markup

def get_pay_markup():
    admin_url = f"https://t.me/{ADMIN_USERNAME.replace('@', '')}"
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("USDT 充值", url=admin_url), types.InlineKeyboardButton("OkPay 充值", url=admin_url), types.InlineKeyboardButton("RMB 充值", url=admin_url), types.InlineKeyboardButton("🔙", callback_data="back_to_main"))
    return markup

def get_help_markup():
    return types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙", callback_data="back_to_main"))

def get_main_text(source, uid, pts):
    first_name = source.from_user.first_name if hasattr(source.from_user, 'first_name') else "User"
    username = f"@{source.from_user.username}" if hasattr(source.from_user, 'username') and source.from_user.username else "未设置"
    return (f"<b>Admin@铭</b>\n\n"
            f"<b>用户 ID:</b> <code>{uid}</code>\n"
            f"<b>用户名称:</b> {first_name}\n"
            f"<b>用户名:</b> {username}\n"
            f"<b>当前余额:</b> <code>{pts:.2f}积分</code>\n\n"
            f"<b>使用帮助可查看使用教程</b>\n"
            f"<b>在线充值可支持24小时</b>\n"
            f"<b>1 USDT = 1 积分</b>")

# ================= 4. 消息处理 =================

@bot.message_handler(commands=['start', '3ys', '2ys', 'add'])
def handle_commands(message):
    uid, chat_id = message.from_user.id, message.chat.id
    cmd_parts = message.text.split()
    cmd = cmd_parts[0][1:]
    current_pts = user_points.get(uid, 0.0)

    if cmd == 'start':
        if uid not in user_points: user_points[uid] = 0.0
        bot.send_message(chat_id, get_main_text(message, uid, user_points[uid]), parse_mode='HTML', reply_markup=get_main_markup())
    elif cmd == '2ys':
        if current_pts < 0.01: return bot.send_message(chat_id, "<b>积分不足,请先充值!</b>", parse_mode='HTML')
        bot.send_message(chat_id, "请输入:姓名 身份证"); user_states[chat_id] = {'step': 'v_2ys'}
    elif cmd == '3ys':
        if current_pts < 0.05: return bot.send_message(chat_id, "<b>积分不足,请先充值!</b>", parse_mode='HTML')
        bot.send_message(chat_id, "请输入:姓名 身份证 手机号"); user_states[chat_id] = {'step': 'v_3ys'}
    elif cmd == 'add':
        if uid == ADMIN_ID:
            try:
                target_uid = int(cmd_parts[1])
                add_amount = float(cmd_parts[2])
                user_points[target_uid] = user_points.get(target_uid, 0.0) + add_amount
                save_points()
                bot.reply_to(message, f"✅ 充值成功!\n用户 ID: <code>{target_uid}</code>\n充值金额: {add_amount}\n<b>当前总余额: {user_points[target_uid]:.2f} 积分</b>", parse_mode='HTML')
            except Exception as e: bot.reply_to(message, f"❌ 格式错误:/add 用户ID 金额")
        else: bot.reply_to(message, "⛔ 您没有权限访问此命令!")

@bot.message_handler(func=lambda m: True)
def handle_all_text(message):
    uid, chat_id, text = message.from_user.id, message.chat.id, message.text.strip()
    if text.startswith('/'): return
    current_pts = user_points.get(uid, 0.0); state = user_states.get(chat_id, {})
    
    parts = re.split(r'[,,\s\n]+', text)
    
    # 三要素自动识别
    if len(parts) >= 3:
        n, p, i = None, None, None
        for x in parts:
            if not n and re.match(r'^[\u4e00-\u9fa5]{2,4}$', x): n = x
            elif not p and re.match(r'^1[3-9]\d{9}$', x): p = x
            elif not i and re.match(r'^[\dXx]{15}$|^[\dXx]{18}$', x): i = x.upper()
        if n and p and i:
            if current_pts < 0.05: return bot.send_message(chat_id, "<b>积分不足,请先充值!</b>", parse_mode='HTML')
            return query_3ys_logic(chat_id, n, i, p, uid)
            
    # 二要素自动识别 (已完美接入新接口)
    if len(parts) == 2:
        n, i = None, None
        for x in parts:
            if not n and re.match(r'^[\u4e00-\u9fa5]{2,4}$', x): n = x
            elif not i and re.match(r'^[\dXx]{15}$|^[\dXx]{18}$', x): i = x.upper()
        if n and i:
            if current_pts < 0.01: return bot.send_message(chat_id, "<b>积分不足,请先充值!</b>", parse_mode='HTML')
            return single_verify_2ys(chat_id, n, i, uid)
    
    bot.send_message(chat_id, "⚠️ 无法识别您的输入,请发送 /start 查看可用功能。")

# ================= 5. 回调处理 =================

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    uid, pts = call.from_user.id, user_points.get(call.from_user.id, 0.0)
    
    if call.data == "view_help":
        help_text = (
            "<b>🛠️ 使用帮助</b>\n"
            "<b>名字-身份证核验 (企业级)</b>\n"
            "<b>全天 24h 秒出 毫秒级响应</b>\n"
            "<b>发送 /2ys 进行核验</b>\n"
            "<b>每次核验扣除 0.01 积分</b>\n"
            "<b>——————————————————</b>\n"
            "<b>名字-手机号-身份证核验 (企业级)</b>\n"
            "<b>全天 24h 秒出 毫秒级响应</b>\n"
            "<b>发送 /3ys 进行核验</b>\n"
            "<b>每次核验扣除 0.05 积分</b>"
        )
        bot.edit_message_text(help_text, call.message.chat.id, call.message.message_id, reply_markup=get_help_markup(), parse_mode='HTML')
    elif call.data == "view_pay":
        bot.edit_message_text("🛍️ <b>请选择充值方式:</b>\n<b>1 USDT = 1 积分</b>", call.message.chat.id, call.message.message_id, reply_markup=get_pay_markup(), parse_mode='HTML')
    elif call.data == "back_to_main":
        bot.edit_message_text(get_main_text(call, uid, pts), call.message.chat.id, call.message.message_id, parse_mode='HTML', reply_markup=get_main_markup())

if __name__ == '__main__':
    print("Bot 正在运行 (二要素已接入国政通新接口)...")
    bot.infinity_polling(timeout=10)
