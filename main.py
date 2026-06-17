import os
import time
import json
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ================= 配置区 =================
TOKEN = "8338893180:AAH-l_4m1-tweKyt92bliyk4fsPqoPQWzpU"
COOKIE = ".ASPXAUTH=5667F36375B0711EE92DAF9FD07CA48B09F3C438818B82405EF98C5538F63DC86EE1D1A00BCD79251F5B450B5A69900515D6922A61FD024697122F5C7910AC5E145E0C31A46E0D3DE8D408367CBF6B6EF23B38B51E8DFF4D23EC6966013E05301A750DAF12875889E2AD6CB4EC7327D548333109EBD2DA50D577D570B55A05FCD18092FEABA9FA92D91E2C47381E28A3; ASP.NET_SessionId=xrawwvtd11zzdsii4jmvfnod"
DEFAULT_BASE_ID = "20260501-63a2b5f509ca136e"
FIX_NAME = "1"

HEADERS = {
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
    'Cookie': COOKIE,
}

# ================= 业务逻辑函数 =================

async def step1_submit_info(update_msg, user_name, user_id_card, base_id):
    await update_msg.reply_text("[1/4] 提交信息中...")
    url = "https://pub.ytfcjy.com/DataSaveBase/Save"
    params = {'P': "P_YW_ZFBZ_ZGBAWEBCSSQXX"}
    payload = {
        'IniFields': "", 'IniValues': "", 'ConnValue': "", 'NewData': "0", 'ID': base_id, 'SQFS': "11",
        'XZQCODE': "601482", 'SQRLX': "1", 'RULELIBID': "ZFBZYT2018-3", 'SQRXX_ID': base_id, 'SQRXX_DID': base_id,
        'SQRXX_XH': "1", 'SQRXX_SFBDHK': "是", 'SQRXX_SFBZRK': "是", 'SQRXX_RULELIBID': "ZFBZYT2018-3",
        'SQRPOXX_ID': f"{base_id}-2", 'SQRPOXX_DID': base_id, 'SQRPOXX_XH': "2", 'SQRPOXX_GX': "配偶",
        'SQRPOXX_RULELIBID': "ZFBZYT2018-3", 'JKJTNDZSR': "", 'YWLX': "初始申请", 'SQRQ': time.strftime("%Y-%m-%d"),
        'ZFBZDJH': "2026050003", 'XZQ': "莱山区", 'JDCODE': "601482601498", 'JD': "解甲庄街道办事处",
        'SQRXX_XM': "**华", 'SQRXX_LXDH': "153******99", 'SQRXX_HYZK': "已婚", 'SQRXX_SFZH': "3***************5",
        'SQRXX_CSRQ': "1986-12-05", 'SQRXX_XB': "女", 'SQRXX_MZDM': "19", 'SQRXX_MZ': "黎族", 'SQRXX_LHRQ': "2023-01-08",
        'SQRXX_HJJD': "估计", 'SQRXX_GZDW': "放大后4", 'SQRXX_WHCDDM': "00", 'SQRXX_WHCD': "大学", 'SQRXX_ZYDM': "1400",
        'SQRXX_ZY': "公交行业职工", 'SQRXX_CJZBH': "", 'SQRXX_CJLX': "", 'SQRXX_CJDJ': "", 'JJRXM': "呃呃",
        'JJRGX': "", 'JJRLXDH': "", 'SQRPOXX_XM': user_name, 'SQRPOXX_SFBZRK': "是", 'SQRPOXX_FBZRKYY': "",
        'SQRPOXX_SFZH': user_id_card, 'SQRPOXX_ZJHM': "", 'SQRPOXX_CSRQ': "2009-07-05", 'SQRPOXX_LXDH': "15412341234",
        'SQRPOXX_XB': "男", 'SQRPOXX_MZDM': "18", 'SQRPOXX_MZ': "傣族", 'SQRPOXX_LHRQ': "2023-01-30",
        'SQRPOXX_HJJD': "而微软推广", 'SQRPOXX_GZDW': "", 'SQRPOXX_WHCDDM': "10", 'SQRPOXX_ZYDM': "1500",
        'SQRPOXX_CJZBH': "", 'SQRPOXX_CJLX': "", 'SQRPOXX_CJDJ': "", 'JZDZ': "捣鼓捣鼓", 'DBZH': "",
        'ZLFWXZQ': "栖霞市", 'ZLFWZL': "投影机靠圣迭戈", 'ZLJZMJ': "20", 'ZLYZJ': "2222", 'BTKHH': "中信银行",
        'BTYHZH': "2121", 'IsEdit': "1", 'SQRXX_SFTYSB': "", 'SQRXX_SFGR': "", 'SQRXX_SFCJ': "",
        'SQRPOXX_SFBDHK': "", 'SQRPOXX_SFCJ': "", 'SFDB': "", 'SFLM': "", 'SFYFDX': "", 'SFGYTKRY': ""
    }

    headers = HEADERS.copy()
    headers['Origin'] = "https://pub.ytfcjy.com"
    
    try:
        response = requests.post(url, params=params, data=payload, headers=headers, timeout=15)
        if response.status_code != 200:
            await update_msg.reply_text(f"❌ 提交失败，响应代码: {response.status_code}")
            return False
        return True
    except Exception as e:
        await update_msg.reply_text(f"❌ 网络请求异常: {str(e)}")
        return False

async def step2_get_business_id(update_msg, ec_type, base_id):
    await update_msg.reply_text(f"[2/4] 获取 {ec_type} 业务ID...")
    url = f"https://pub.ytfcjy.com/ApiData/GetYWDZZZ/{base_id}"
    params = {'ECType': ec_type, '_': str(int(time.time() * 1000))}
    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=15)
        data = json.loads(response.text)
        if data.get("Result") == 1:
            return data.get("Data", "").replace('\\', '')
    except Exception as e:
        pass
    await update_msg.reply_text(f"❌ 获取 {ec_type} 业务ID失败")
    return None

async def step3_save_business_id(update_msg, base_id, sjcl_id, cert_data):
    await update_msg.reply_text("[3/4] 保存业务ID...")
    url = f"https://pub.ytfcjy.com/ApiData/SaveYWDZZZ/{base_id}"
    params = {'SJCLID': sjcl_id}
    payload = {'DZZZInfo': cert_data}
    headers = HEADERS.copy()
    headers['Origin'] = "https://pub.ytfcjy.com"
    try:
        response = requests.post(url, params=params, data=payload, headers=headers, timeout=15)
        if json.loads(response.text).get("Result") == 1:
            return True
    except:
        pass
    await update_msg.reply_text("❌ 保存业务ID失败")
    return False

async def step4_download_photo(update_msg, base_id, sjcl_id, user_id_card, save_filename, save_dir):
    await update_msg.reply_text(f"[4/4] 正在下载并传输 {save_filename}...")
    url = "https://pub.ytfcjy.com/File/GetScanFileInfoData"
    params = {'Value': sjcl_id, '_': str(int(time.time() * 1000))}
    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=15)
        photo_list = json.loads(response.text)
        os.makedirs(save_dir, exist_ok=True)
        
        for photo in photo_list:
            name = photo.get("Name", "")
            photo_id = photo.get("ID")
            if name.endswith(f"{user_id_card}.png"):
                img_response = requests.get(f"https://pub.ytfcjy.com/File/OpenCMSFile?PICID={photo_id}", headers=HEADERS, timeout=15)
                if img_response.status_code == 200:
                    save_path = os.path.join(save_dir, f"{save_filename}.png")
                    with open(save_path, 'wb') as f:
                        f.write(img_response.content)
                    
                    # 核心改动：直接把文件通过机器人发给当前用户
                    with open(save_path, 'rb') as photo_file:
                        await update_msg.reply_photo(photo=photo_file, caption=f"✅ {save_filename} 获取成功！")
                    return True
        await update_msg.reply_text(f"❌ 未找到匹配的 {save_filename} 照片")
    except Exception as e:
        await update_msg.reply_text(f"❌ 下载 {save_filename} 失败")
    return False

async def process_document(update_msg, ec_type, base_id, sjcl_id, user_id_card, save_name, save_dir):
    cert = await step2_get_business_id(update_msg, ec_type, base_id)
    if not cert:
        return False
    if not await step3_save_business_id(update_msg, base_id, sjcl_id, cert):
        return False
    return await step4_download_photo(update_msg, base_id, sjcl_id, user_id_card, save_name, save_dir)

# ================= TG 机器人事件处理 =================

# 响应 /start 命令
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 欢迎使用数据查询机器人！\n请直接发送 18 位身份证号码开始处理。")

# 响应用户发送的消息（处理身份证）
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id_card = update.message.text.strip()
    
    # 校验身份证长度
    if len(user_id_card) != 18:
        await update.message.reply_text("❌ 身份证格式错误，请输入 18 位身份证号码！")
        return

    await update.message.reply_text(f"🚀 开始处理身份证: {user_id_card}，请稍候...")

    user_name = FIX_NAME
    base_id = DEFAULT_BASE_ID
    root_dir = "山东"
    id_dir = os.path.join(root_dir, user_id_card)

    # 1. 提交信息
    if not await step1_submit_info(update.message, user_name, user_id_card, base_id):
        await update.message.reply_text("❌ 第一步提交信息失败，任务终止。")
        return

    # 2. 处理身份证图片
    await process_document(update.message, "SFZ", base_id, f"{base_id}-1", user_id_card, "身份证", id_dir)
    
    # 3. 处理户口簿图片
    await process_document(update.message, "HKB", base_id, f"{base_id}-2", user_id_card, "户口簿", id_dir)

    await update.message.reply_text("\n✨ 所有人任务已执行完毕。")

# ================= 主函数 =================
def main():
    print("🤖 机器人正在启动中...")
    # 创建 Application 实例
    application = Application.builder().token(TOKEN).build()

    # 注册处理器
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # 启动轮询
    print("🚀 机器人已成功运行，等待消息中...")
    application.run_polling()

if __name__ == "__main__":
    main()
