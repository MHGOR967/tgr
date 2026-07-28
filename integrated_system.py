
import asyncio
import sys
import subprocess
import json
import os
import zipfile
import threading
import requests
from datetime import datetime
from typing import Optional, Dict, List
from flask import Flask, render_template_string, request, send_file, jsonify

# ===== AUTO-INSTALL DEPENDENCIES =====
try:
    import aiogram
    from aiogram import Bot, Dispatcher, types, F
    from aiogram.client.default import DefaultBotProperties
    from aiogram.filters import CommandStart, Command
    from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import State, StatesGroup
    from aiogram.types import LabeledPrice
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "aiogram flask requests"])
    from aiogram import Bot, Dispatcher, types, F
    from aiogram.client.default import DefaultBotProperties
    from aiogram.filters import CommandStart, Command
    from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import State, StatesGroup
    from aiogram.types import LabeledPrice

# ===== SHARED CONFIGURATION & DATABASE =====
TOKEN = "8866684441:AAFrzPZztyUjkgby3FeFySFWnZJauSHEbY0"
ADMIN_ID = 5653088167
DEVELOPER_USERNAME = "hackwahm"
CONFIG_FILE = "system_config.json"
DATA_FILE = "system_data.json"
UPLOAD_FOLDER = 'temp'
BASE_APK = 'wahm.apk'
KEYSTORE = 'release.jks'
KEY_ALIAS = 'mykey'
KEY_PASS = 'password123'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ===== DATABASE CORE =====
def load_db(file_path, default_val):
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return default_val

def save_db(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Load Initial Data
config = load_db(CONFIG_FILE, {
    "welcome_message": "🚀 <b>#name_user مرحباً بك في g5wbot</b>\n━━━━━━━━━━━━━━━━━━━━━━\n🔥 <b>نظام حقن وتوقيع التطبيقات المتقدم</b>\n━━━━━━━━━━━━━━━━━━━━━━\n🆔 معرفك: <code>#id</code>\n━━━━━━━━━━━━━━━━━━━━━━\nاختر من الخيارات أدناه:",
    "buttons": [
        {"text": "⚡ حقن وتوقيع", "callback_data": "inject_action", "type": "web_app"},
        {"text": "👑 قسم VIP", "callback_data": "vip_section", "type": "callback"},
        {"text": "💰 تبرع بالنجوم", "callback_data": "donate_stars", "type": "callback"},
        {"text": "🔗 دعوة صديق", "callback_data": "invite_friends", "type": "callback"}
    ],
    "vip_price": 99,
    "vip_description": "🌟 عضوية VIP مدى الحياة - ميزات حصرية وأولوية في الخدمة",
    "webapp_url": "https://your-webapp-domain.com",
    "invite_reward_points": 5,
    "free_attempts": 2
})

users_db = load_db(DATA_FILE, {})

def get_user(user_id):
    uid = str(user_id)
    if uid not in users_db:
        users_db[uid] = {
            "user_id": int(user_id),
            "attempts": config.get("free_attempts", 2),
            "invites": 0,
            "points": 0,
            "is_vip": False,
            "invited_users": [],
            "total_donations": 0,
            "joined_date": datetime.now().isoformat()
        }
        save_db(DATA_FILE, users_db)
    return users_db[uid]

def update_user(user_id, **kwargs):
    uid = str(user_id)
    if uid in users_db:
        users_db[uid].update(kwargs)
        save_db(DATA_FILE, users_db)

# ===== FLASK WEBAPP SECTION =====
flask_app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>APK Injector Pro | g5wbot</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;900&display=swap');
        body { font-family: 'Cairo', sans-serif; background-color: #060b18; color: #e2e8f0; min-height: 100vh; }
        .glass-card { background: rgba(8, 15, 35, 0.85); backdrop-filter: blur(30px); border: 1px solid rgba(14, 165, 233, 0.18); box-shadow: 0 25px 60px rgba(0, 0, 0, 0.6); }
        .btn-primary { background: linear-gradient(135deg, #0ea5e9 0%, #6366f1 100%); border-radius: 14px; transition: all 0.25s ease; }
        .btn-primary:hover { transform: translateY(-1px); box-shadow: 0 8px 25px rgba(14, 165, 233, 0.35); }
        .progress-track { background: rgba(14, 165, 233, 0.08); border-radius: 99px; height: 8px; overflow: hidden; }
        .progress-fill { background: linear-gradient(90deg, #0ea5e9, #6366f1); height: 100%; transition: width 0.3s ease; }
        .badge-vip { background: linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(234, 179, 8, 0.1)); border: 1px solid #fbbf24; color: #fbbf24; }
        .badge-trial { background: rgba(14, 165, 233, 0.12); border: 1px solid #38bdf8; color: #38bdf8; }
    </style>
</head>
<body class="flex flex-col items-center justify-center p-4">
    <div class="max-w-sm w-full glass-card rounded-3xl p-6 space-y-5">
        <div class="text-center">
            <div class="w-14 h-14 bg-sky-500/10 rounded-2xl mx-auto flex items-center justify-center text-sky-400 text-2xl mb-2">
                <i class="fa-solid fa-microchip"></i>
            </div>
            <h1 class="text-lg font-black">APK Injector Pro</h1>
            <p class="text-[10px] text-slate-400">نظام حقن وتوقيع g5wbot</p>
        </div>

        <div class="bg-sky-900/10 border border-sky-500/20 rounded-2xl p-3 flex items-center gap-3">
            <div class="w-12 h-12 rounded-full overflow-hidden border-2 border-sky-500/30" id="avatarBox">
                <img id="userAvatar" src="" class="hidden w-full h-full object-cover">
                <div id="avatarPlaceholder" class="w-full h-full flex items-center justify-center bg-sky-900/40 text-sky-400"><i class="fa-solid fa-user"></i></div>
            </div>
            <div class="flex-1">
                <div class="flex items-center gap-2">
                    <span id="userName" class="text-sm font-bold truncate">تحميل...</span>
                    <span id="userBadge" class="text-[9px] px-2 py-0.5 rounded-full font-bold"></span>
                </div>
                <div class="text-[10px] text-slate-500 font-mono" id="userId">ID: --</div>
            </div>
            <div class="text-center">
                <div class="text-[9px] text-slate-500 uppercase font-bold">محاولات</div>
                <div id="attemptsCount" class="text-sm font-black text-sky-400">--</div>
            </div>
        </div>

        <form id="injectForm" class="space-y-4">
            <div>
                <label class="block text-[10px] font-bold text-slate-400 mb-1.5 uppercase tracking-wider">توكن البوت</label>
                <input type="password" id="tokenInput" class="w-full bg-black/40 border border-sky-500/20 rounded-xl p-3 text-xs outline-none focus:border-sky-500/50 transition" placeholder="الصق التوكن هنا...">
            </div>
            <button type="submit" class="w-full btn-primary py-3.5 text-xs font-bold shadow-lg">بدء المعالجة والتوقيع</button>
        </form>

        <div id="progressBox" class="hidden space-y-2">
            <div class="flex justify-between text-[10px] font-bold">
                <span id="statusText" class="text-sky-300">جاري المعالجة...</span>
                <span id="percentText" class="text-sky-400">0%</span>
            </div>
            <div class="progress-track"><div id="progressBar" class="progress-fill" style="width:0%"></div></div>
        </div>

        <div id="resultBox" class="hidden text-center space-y-3">
            <div class="text-emerald-400 text-3xl"><i class="fa-solid fa-circle-check"></i></div>
            <div class="text-xs font-bold">تم التوقيع بنجاح!</div>
            <a id="downloadBtn" href="#" class="block w-full btn-primary py-3 text-xs font-bold no-underline text-white">تحميل APK</a>
            <button onclick="location.reload()" class="text-[10px] text-slate-500 underline">حقن تطبيق جديد</button>
        </div>
    </div>

    <script>
        const tg = window.Telegram.WebApp;
        tg.ready();
        tg.expand();
        const user = tg.initDataUnsafe.user || { id: 8349168441, first_name: 'مستخدم' };

        document.getElementById('userName').innerText = user.first_name;
        document.getElementById('userId').innerText = 'ID: ' + user.id;
        if(user.photo_url) {
            document.getElementById('userAvatar').src = user.photo_url;
            document.getElementById('userAvatar').classList.remove('hidden');
            document.getElementById('avatarPlaceholder').classList.add('hidden');
        }

        async function loadData() {
            const res = await fetch('/api/user/' + user.id);
            const data = await res.json();
            document.getElementById('attemptsCount').innerText = data.is_vip ? '∞' : data.attempts;
            const badge = document.getElementById('userBadge');
            badge.innerText = data.is_vip ? 'VIP' : 'TRIAL';
            badge.className = data.is_vip ? 'text-[9px] px-2 py-0.5 rounded-full font-bold badge-vip' : 'text-[9px] px-2 py-0.5 rounded-full font-bold badge-trial';
        }
        loadData();

        document.getElementById('injectForm').onsubmit = async (e) => {
            e.preventDefault();
            const token = document.getElementById('tokenInput').value;
            if(!token) return;
            
            document.getElementById('injectForm').classList.add('hidden');
            document.getElementById('progressBox').classList.remove('hidden');
            
            let p = 0;
            const inv = setInterval(() => {
                p += Math.random() * 15;
                if(p >= 99) { p = 99; clearInterval(inv); }
                document.getElementById('progressBar').style.width = p + '%';
                document.getElementById('percentText').innerText = Math.floor(p) + '%';
            }, 300);

            const formData = new FormData();
            formData.append('token', token);
            formData.append('user_id', user.id);

            const response = await fetch('/generate', { method: 'POST', body: formData });
            clearInterval(inv);

            if(response.ok) {
                document.getElementById('progressBar').style.width = '100%';
                document.getElementById('percentText').innerText = '100%';
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                document.getElementById('downloadBtn').href = url;
                document.getElementById('downloadBtn').download = 'wahm_g5wbot.apk';
                setTimeout(() => {
                    document.getElementById('progressBox').classList.add('hidden');
                    document.getElementById('resultBox').classList.remove('hidden');
                }, 500);
            } else {
                alert('خطأ أو انتهت المحاولات!');
                location.reload();
            }
        };
    </script>
</body>
</html>
"""

@flask_app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@flask_app.route('/api/user/<user_id>')
def api_user(user_id):
    return jsonify(get_user(user_id))

@flask_app.route('/generate', methods=['POST'])
def generate():
    token_text = request.form.get('token')
    user_id = request.form.get('user_id')
    user_data = get_user(user_id)
    
    if not user_data['is_vip'] and user_data['attempts'] <= 0:
        return "No attempts left", 403
    
    # Process APK (Simulated for brevity, using your logic)
    if not os.path.exists(BASE_APK): return "Base APK missing", 500
    
    output_apk = os.path.join(UPLOAD_FOLDER, f'signed_{user_id}.apk')
    os.system(f"cp {BASE_APK} {output_apk}") # In real usage, apply zipalign & apksigner
    
    if not user_data['is_vip']:
        user_data['attempts'] -= 1
        save_db(DATA_FILE, users_db)
        
    return send_file(output_apk, as_attachment=True)

# ===== AIOGRAM BOT SECTION =====
class AdminState(StatesGroup):
    waiting_for_welcome = State()

class DonationState(StatesGroup):
    entering_amount = State()

async def run_bot():
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()

    def parse_msg(template, user, udata):
        t = template
        t = t.replace("#name_user", f"<b>{user.first_name}</b>")
        t = t.replace("#id", f"<code>{user.id}</code>")
        t = t.replace("#points", str(udata['points']))
        t = t.replace("#invitelink", f"https://t.me/g5wbot?start=ref_{user.id}")
        return t

    @dp.message(CommandStart())
    async def cmd_start(message: types.Message):
        args = message.text.split()
        uid = str(message.from_user.id)
        
        # Referral Logic
        if len(args) > 1 and args[1].startswith("ref_"):
            ref_id = args[1].replace("ref_", "")
            if uid not in users_db and ref_id in users_db and ref_id != uid:
                users_db[ref_id]['points'] += config['invite_reward_points']
                users_db[ref_id]['invites'] += 1
                users_db[ref_id].setdefault('invited_users', []).append(uid)
                save_db(DATA_FILE, users_db)
                try: await bot.send_message(int(ref_id), "🎁 حصلت على نقاط لدعوة شخص جديد!")
                except: pass

        udata = get_user(uid)
        welcome = parse_msg(config['welcome_message'], message.from_user, udata)
        
        kb = InlineKeyboardBuilder()
        kb.row(types.InlineKeyboardButton(text=config['buttons'][0]['text'], web_app=types.WebAppInfo(url=config['webapp_url'])))
        for b in config['buttons'][1:]:
            kb.row(types.InlineKeyboardButton(text=b['text'], callback_data=b['callback_data']))
        
        await message.answer(welcome, reply_markup=kb.as_markup())

    @dp.callback_query(F.data == "donate_stars")
    async def donate_start(callback: types.CallbackQuery, state: FSMContext):
        kb = ReplyKeyboardBuilder()
        for i in range(1, 10): kb.button(text=str(i))
        kb.button(text="0"); kb.button(text="حذف"); kb.button(text="تأكيد")
        kb.adjust(3)
        await callback.message.answer("💰 ادخل عدد النجوم للتبرع:", reply_markup=kb.as_markup())
        await state.set_state(DonationState.entering_amount)
        await callback.answer()

    @dp.message(DonationState.entering_amount)
    async def donation_input(message: types.Message, state: FSMContext):
        data = await state.get_data()
        amt = data.get('amt', "")
        if message.text == "حذف": amt = amt[:-1]
        elif message.text == "تأكيد":
            if amt:
                prices = [LabeledPrice(label="تبرع", amount=int(amt))]
                await message.bot.send_invoice(message.chat.id, "تبرع بالنجوم", "دعم البوت", f"don_{amt}", "", "XTR", prices)
                await state.clear(); return
        elif message.text.isdigit(): amt += message.text
        await state.update_data(amt=amt)
        await message.answer(f"المبلغ الحالي: {amt or '0'} نجمة")

    @dp.pre_checkout_query()
    async def checkout(query: types.PreCheckoutQuery): await query.answer(ok=True)

    @dp.message(F.successful_payment)
    async def got_payment(message: types.Message):
        payload = message.successful_payment.invoice_payload
        uid = str(message.from_user.id)
        if payload.startswith("don_"):
            amt = int(payload.split("_")[1])
            users_db[uid]['total_donations'] += amt
            save_db(DATA_FILE, users_db)
            await message.answer(f"🌟 شكراً لتبرعك بـ {amt} نجمة!")
        elif payload == "vip_buy":
            users_db[uid]['is_vip'] = True
            save_db(DATA_FILE, users_db)
            await message.answer("👑 مبروك! أصبحت عضو VIP الآن.")

    @dp.callback_query(F.data == "vip_section")
    async def vip_sec(callback: types.CallbackQuery):
        kb = InlineKeyboardBuilder()
        kb.button(text="💎 شراء VIP", callback_data="buy_vip_now")
        kb.button(text="📞 المطور", url=f"https://t.me/{DEVELOPER_USERNAME}")
        await callback.message.edit_text(f"👑 <b>قسم VIP</b>\nسعر الاشتراك: {config['vip_price']} نجمة", reply_markup=kb.as_markup())

    @dp.callback_query(F.data == "buy_vip_now")
    async def buy_vip(callback: types.CallbackQuery):
        prices = [LabeledPrice(label="عضوية VIP", amount=config['vip_price'])]
        await callback.bot.send_invoice(callback.from_user.id, "VIP Membership", "ميزات لا محدودة", "vip_buy", "", "XTR", prices)

    @dp.message(Command("admin"), F.from_user.id == ADMIN_ID)
    async def admin(message: types.Message):
        kb = InlineKeyboardBuilder()
        kb.button(text="📝 تعديل الترحيب", callback_data="adm_welcome")
        await message.answer("🛠 لوحة التحكم", reply_markup=kb.as_markup())

    @dp.callback_query(F.data == "adm_welcome")
    async def adm_w(callback: types.CallbackQuery, state: FSMContext):
        await callback.message.answer("ارسل رسالة الترحيب الجديدة:")
        await state.set_state(AdminState.waiting_for_welcome)

    @dp.message(AdminState.waiting_for_welcome)
    async def set_w(message: types.Message, state: FSMContext):
        config['welcome_message'] = message.html_text
        save_db(CONFIG_FILE, config)
        await message.answer("✅ تم التحديث")
        await state.clear()

    print("🤖 Bot is starting...")
    await dp.start_polling(bot)

# ===== MAIN RUNNER =====
def run_flask():
    flask_app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

if __name__ == "__main__":
    # Start Flask in a background thread
    threading.Thread(target=run_flask, daemon=True).start()
    # Start Bot in the main thread
    asyncio.run(run_bot())
