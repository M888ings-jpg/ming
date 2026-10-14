import telebot
import requests
import json
import os
import re
from telebot import types

# 屏蔽 SSL 证书报警
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# ================= 1. 核心配置 =================
API_TOKEN = '8776613830:AAET0H2FmaNHaAw2wJqbydsdNCbC9MZHXqQ'
ADMIN_ID = 6649617045 
ADMIN_USERNAME = "@aaSm68"
POINTS_FILE = 'points.json'

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
        
        clean_res = response.text.strip()
        res_status = "三要素核验成功✅" if ("成功" in clean_res or "一致" in clean_res) else "三要素核验失败❌"
        
        bot.delete_message(chat_id, wait_msg.message_id)
        bot.send_message(chat_id, f"姓名:{name}\n手机号:{phone}\n身份证:{id_card}\n结果:{res_status}\n详情:{clean_res}\n\n"
                                  f"<b>已扣除 0.05 积分!</b>\n<b>当前余额:{user_points[uid]:.2f}</b>", parse_mode='HTML')
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
        
        clean_res = response.text.strip()
        status_title = "二要素核验一致✅" if ("成功" in clean_res or "一致" in clean_res) else "二要素核验失败❌"

        result_msg = (
            f"<b>姓名:</b> {name}\n"
            f"<b>身份证:</b> <code>{id_card}</code>\n"
            f"<b>结果:</b> {status_title}\n"
            f"<b>返回内容:</b> {clean_res}\n\n"
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

@bot.message_handler(commands=['start', '3ys', '2ys', 'add'])
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
    
    bot.send_message(chat_id, "⚠️ 无法识别您的输入,请发送 /start 查看可用功能。")

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
            bot.edit_message_text(help_text, chat_id, message_id, reply_markup=get_help_markup(), parse_mode='HTML')
        elif call.data == "view_pay":
            pay_text = "🛍️ <b>请选择充值方式:</b>\n<b>1 USDT = 1 积分</b>"
            bot.edit_message_text(pay_text, chat_id, message_id, reply_markup=get_pay_markup(), parse_mode='HTML')
        elif call.data == "back_to_main":
            bot.edit_message_text(get_main_text(uid, first_name, username, pts), chat_id, message_id, parse_mode='HTML', reply_markup=get_main_markup())
    except Exception as e:
        # 忽略由于内容未改变导致的报错，保证切换流畅
        pass

if __name__ == '__main__':
    print("Bot 正在运行...")
    try:
        bot.remove_webhook()
    except Exception as e:
        print(f"清除 webhook 警告: {e}")
        
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
