from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ChatJoinRequest
from google import genai
import random
import json
import os
from datetime import datetime, timedelta

# ========== تنظیمات اولیه ==========
app = Client("SM")

# لیست ادمین‌ها (قابل تغییر)
ADMINS = [6996368871]

# کلید API گوگل جمینی (قابل تغییر)
GEMINI_API_KEY = ""

# آیدی مدیر اصلی برای دریافت نوتیفیکیشن (قابل تغییر)
MAIN_ADMIN_ID = 6996368871

# لینک گروه (قابل تغییر)
GROUP_LINK = "https://t.me/+9_ZpTdXrhxJiY2E0"

# فایل‌های JSON برای ذخیره داده‌ها
POINTS_FILE = "user_points.json"
LEVELS_FILE = "user_levels.json"
BETS_FILE = "active_bets.json"

# دیتاهای موقت
box_banned_users = []
msg_count = {}
box_answer = {}
active_bets = {}

# ========== تنظیمات سیستم شرط‌بندی ==========
BET_CONFIG = {
    "min_bet": 10,              # حداقل مقدار شرط
    "max_bet": 1000,            # حداکثر مقدار شرط
    "bet_timeout": 60,          # زمان انقضای شرط (ثانیه)
    "multipliers": {
        "even_odd": 2,          # ضریب زوج/فرد
        "exact": 6,             # ضریب حدس عدد دقیق
        "range_low": 3,         # ضریب محدوده 1-3
        "range_high": 3         # ضریب محدوده 4-6
    }
}

# ========== تنظیمات سیستم جعبه ==========
BOX_CONFIG = {
    "message_threshold": 50,    # تعداد پیام برای ظاهر شدن جعبه
    "min_reward": 5,           # حداقل جایزه
    "max_reward": 15,          # حداکثر جایزه
    "operations": ["+", "-", "*", "/"],  # عملیات‌های ریاضی
    "number_range": (1, 20)    # محدوده اعداد برای سوالات
}

# ========== تنظیمات سیستم لول ==========
LEVEL_CONFIG = {
    "level_1": {"min_points": 0, "max_points": 99, "title": "🔰 نوب", "badge": "🔰"},
    "level_2": {"min_points": 100, "max_points": 249, "title": "🔗 نوپا", "badge": "🔗"},
    "level_3": {"min_points": 250, "max_points": 499, "title": "⭐ ستاره", "badge": "⭐"},
    "level_4": {"min_points": 500, "max_points": 999, "title": "🔥 حرفه‌ای", "badge": "🔥"},
    "level_5": {"min_points": 1000, "max_points": 1999, "title": "💎 الماسی", "badge": "💎"},
    "level_6": {"min_points": 2000, "max_points": 4999, "title": "👑 پادشاه", "badge": "👑"},
    "level_7": {"min_points": 5000, "max_points": 9999, "title": "🌟 افسانه‌ای", "badge": "🌟"},
    "level_8": {"min_points": 10000, "max_points": float('inf'), "title": "🏆 خدا", "badge": "🏆"}
}

# ========== توابع مدیریت امتیاز ==========

def load_points():
    """بارگذاری امتیازات از فایل JSON"""
    if os.path.exists(POINTS_FILE):
        try:
            with open(POINTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_points(points_data):
    """ذخیره امتیازات در فایل JSON"""
    try:
        with open(POINTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(points_data, f, ensure_ascii=False, indent=4)
        return True
    except:
        return False


def get_user_points(user_id):
    """دریافت امتیاز یک کاربر"""
    points_data = load_points()
    return points_data.get(str(user_id), 0)


def add_points(user_id, amount):
    """اضافه کردن امتیاز به کاربر"""
    points_data = load_points()
    user_id_str = str(user_id)
    
    if user_id_str not in points_data:
        points_data[user_id_str] = 0
    
    points_data[user_id_str] += amount
    save_points(points_data)
    return points_data[user_id_str]


def remove_points(user_id, amount):
    """کم کردن امتیاز از کاربر"""
    points_data = load_points()
    user_id_str = str(user_id)
    
    if user_id_str not in points_data:
        points_data[user_id_str] = 0
    
    points_data[user_id_str] -= amount
    save_points(points_data)
    return points_data[user_id_str]


def set_points(user_id, amount):
    """تنظیم امتیاز کاربر (برای ادمین)"""
    points_data = load_points()
    points_data[str(user_id)] = amount
    save_points(points_data)
    return amount


# ========== توابع مدیریت لول ==========

def load_levels():
    """بارگذاری سطح‌های کاربران از فایل JSON"""
    if os.path.exists(LEVELS_FILE):
        try:
            with open(LEVELS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_levels(levels_data):
    """ذخیره سطح‌های کاربران در فایل JSON"""
    try:
        with open(LEVELS_FILE, 'w', encoding='utf-8') as f:
            json.dump(levels_data, f, ensure_ascii=False, indent=4)
        return True
    except:
        return False


def get_user_level(user_id):
    """دریافت لول فعلی کاربر"""
    points = get_user_points(user_id)
    
    for level_key, level_info in LEVEL_CONFIG.items():
        if level_info["min_points"] <= points <= level_info["max_points"]:
            return {
                "level_key": level_key,
                "level_num": int(level_key.split("_")[1]),
                "title": level_info["title"],
                "badge": level_info["badge"],
                "min_points": level_info["min_points"],
                "max_points": level_info["max_points"] if level_info["max_points"] != float('inf') else "∞",
                "current_points": points
            }
    
    return get_level_info(1, points)


def get_level_info(level_num, current_points=0):
    """دریافت اطلاعات یک لول خاص"""
    level_key = f"level_{level_num}"
    
    if level_key not in LEVEL_CONFIG:
        return None
    
    level_info = LEVEL_CONFIG[level_key]
    return {
        "level_key": level_key,
        "level_num": level_num,
        "title": level_info["title"],
        "badge": level_info["badge"],
        "min_points": level_info["min_points"],
        "max_points": level_info["max_points"] if level_info["max_points"] != float('inf') else "∞",
        "current_points": current_points
    }


def get_progress_bar(user_id):
    """دریافت نوار پیشرفت کاربر برای رسیدن به لول بعدی"""
    points = get_user_points(user_id)
    current_level = get_user_level(user_id)
    
    if current_level["max_points"] == "∞":
        return "🎯 شما در بالاترین لول هستید!"
    
    min_pts = current_level["min_points"]
    max_pts = current_level["max_points"]
    
    progress = points - min_pts
    total = max_pts - min_pts
    percent = (progress / total) * 100 if total > 0 else 100
    
    filled = int(percent / 10)
    empty = 10 - filled
    
    progress_bar = "🟩" * filled + "⬜" * empty
    points_needed = max_pts - points
    
    return f"{progress_bar}\n{percent:.1f}% [{points}/{max_pts}]\n💫 تا لول بعدی: {points_needed} امتیاز"


def check_level_up(user_id):
    """بررسی اینکه کاربر لول‌اپ شده یا نه"""
    levels_data = load_levels()
    user_id_str = str(user_id)
    current_level = get_user_level(user_id)
    
    if user_id_str not in levels_data:
        levels_data[user_id_str] = {
            "level": current_level["level_num"],
            "level_up_count": 0
        }
    
    old_level = levels_data[user_id_str].get("level", 1)
    new_level = current_level["level_num"]
    
    if new_level > old_level:
        levels_data[user_id_str]["level"] = new_level
        levels_data[user_id_str]["level_up_count"] = levels_data[user_id_str].get("level_up_count", 0) + 1
        save_levels(levels_data)
        
        return {
            "level_up": True,
            "old_level": old_level,
            "new_level": new_level,
            "level_title": current_level["title"],
            "badge": current_level["badge"]
        }
    
    return {"level_up": False}


# ========== توابع مدیریت شرط‌بندی ==========

def load_bets():
    """بارگذاری شرط‌های فعال از فایل JSON"""
    if os.path.exists(BETS_FILE):
        try:
            with open(BETS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_bets(bets_data):
    """ذخیره شرط‌های فعال در فایل JSON"""
    try:
        with open(BETS_FILE, 'w', encoding='utf-8') as f:
            json.dump(bets_data, f, ensure_ascii=False, indent=4)
        return True
    except:
        return False


def create_bet(chat_id, user_id, amount, bet_type, prediction):
    """ایجاد یک شرط جدید"""
    bet_id = f"{chat_id}_{user_id}_{datetime.now().timestamp()}"
    
    bets_data = load_bets()
    bets_data[bet_id] = {
        "chat_id": chat_id,
        "user_id": user_id,
        "amount": amount,
        "bet_type": bet_type,
        "prediction": prediction,
        "timestamp": datetime.now().isoformat(),
        "status": "active"
    }
    save_bets(bets_data)
    return bet_id


def get_active_bet(user_id, chat_id):
    """بررسی اینکه کاربر شرط فعال دارد یا نه"""
    bets_data = load_bets()
    for bet_id, bet in bets_data.items():
        if bet["user_id"] == user_id and bet["chat_id"] == chat_id and bet["status"] == "active":
            return bet_id, bet
    return None, None


def cancel_bet(bet_id):
    """لغو یک شرط و برگشت امتیاز"""
    bets_data = load_bets()
    if bet_id in bets_data:
        bet = bets_data[bet_id]
        add_points(bet["user_id"], bet["amount"])
        del bets_data[bet_id]
        save_bets(bets_data)
        return True
    return False


def resolve_bet(bet_id, dice_value):
    """تسویه حساب یک شرط بر اساس نتیجه تاس"""
    bets_data = load_bets()
    if bet_id not in bets_data:
        return None
    
    bet = bets_data[bet_id]
    bet_type = bet["bet_type"]
    prediction = bet["prediction"]
    amount = bet["amount"]
    user_id = bet["user_id"]
    
    won = False
    multiplier = 0
    
    # بررسی انواع شرط‌ها
    if bet_type == "even_odd":
        if prediction == "even" and dice_value % 2 == 0:
            won = True
        elif prediction == "odd" and dice_value % 2 == 1:
            won = True
        multiplier = BET_CONFIG["multipliers"]["even_odd"]
    
    elif bet_type == "exact":
        if prediction == dice_value:
            won = True
        multiplier = BET_CONFIG["multipliers"]["exact"]
    
    elif bet_type == "range_low":
        if 1 <= dice_value <= 3:
            won = True
        multiplier = BET_CONFIG["multipliers"]["range_low"]
    
    elif bet_type == "range_high":
        if 4 <= dice_value <= 6:
            won = True
        multiplier = BET_CONFIG["multipliers"]["range_high"]
    
    # محاسبه جایزه یا ضرر
    if won:
        winnings = amount * multiplier
        add_points(user_id, winnings)
        result = {
            "won": True,
            "amount": winnings,
            "multiplier": multiplier
        }
    else:
        result = {
            "won": False,
            "amount": amount,
            "multiplier": 0
        }
    
    # حذف شرط از لیست فعال‌ها
    del bets_data[bet_id]
    save_bets(bets_data)
    
    return result


# ========== دستورات ربات ==========

@app.on_message(filters.command("start"))
async def start(client, message: Message):
    """دستور شروع ربات"""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("شاهمرادی کلاب", url=GROUP_LINK)]
    ])

    await message.reply_text(
        "به ما بپیوند! 👇",
        reply_markup=keyboard
    )


@app.on_message(filters.command("help"))
async def help_command(client, message: Message):
    """راهنمای دستورات ربات"""
    help_text = """
📚 **راهنمای دستورات ربات**

**🎮 بازی و سرگرمی:**
🎲 ارسال تاس (Dice) - شرط‌بندی روی نتیجه
📦 جعبه شانس هر 50 پیام - حل معادله و برد امتیاز

**💰 شرط‌بندی:**
/bet [مقدار] - شروع شرط‌بندی
/cancelbet - لغو شرط فعال
/mybets - مشاهده شرط‌های فعال

**انواع شرط:**
• زوج/فرد (ضریب 2)
• عدد دقیق (ضریب 6)
• محدوده پایین 1-3 (ضریب 3)
• محدوده بالا 4-6 (ضریب 3)

**📊 امتیاز و لول:**
/points - چک کردن امتیاز خودت
/leaderboard - جدول برترین‌ها

**🤖 هوش مصنوعی:**
/ai [سوال] - سوال از Gemini AI

**👑 دستورات ادمین:**
/addpoints [مقدار] - اضافه کردن امتیاز
/removepoints [مقدار] - کم کردن امتیاز
/setpoints [مقدار] - تنظیم امتیاز مستقیم
    """
    
    await message.reply(help_text)


@app.on_message(filters.command("points"))
async def check_points(client, message: Message):
    """چک کردن امتیاز و لول خودت یا کاربر دیگه"""
    if message.reply_to_message:
        user = message.reply_to_message.from_user
        points = get_user_points(user.id)
        level_info = get_user_level(user.id)
        progress = get_progress_bar(user.id)
        
        await message.reply(
            f"{level_info['badge']} **{level_info['title']}**\n"
            f"💎 امتیاز {user.mention}: **{points}**\n\n"
            f"{progress}"
        )
    else:
        user = message.from_user
        points = get_user_points(user.id)
        level_info = get_user_level(user.id)
        progress = get_progress_bar(user.id)
        
        await message.reply(
            f"{level_info['badge']} **{level_info['title']}**\n"
            f"💎 امتیاز شما: **{points}**\n\n"
            f"{progress}"
        )


@app.on_message(filters.command("leaderboard"))
async def leaderboard(client, message: Message):
    """نمایش جدول برترین‌ها با لول"""
    points_data = load_points()
    
    if not points_data:
        await message.reply("❌ هنوز هیچ کاربری امتیازی نداره!")
        return
    
    sorted_users = sorted(points_data.items(), key=lambda x: x[1], reverse=True)[:10]
    
    text = "🏆 **جدول برترین‌ها**\n\n"
    medals = ["🥇", "🥈", "🥉"]
    
    for i, (user_id, points) in enumerate(sorted_users):
        try:
            user = await app.get_users(int(user_id))
            name = user.first_name or "Unknown"
            level_info = get_user_level(int(user_id))
            medal = medals[i] if i < 3 else f"{i+1}."
            
            text += f"{medal} {level_info['badge']} {name}\n"
            text += f"   💎 {points} امتیاز | لول {level_info['level_num']}\n\n"
        except:
            continue
    
    await message.reply(text)


@app.on_message(filters.command("bet"))
async def start_bet(client, message: Message):
    """شروع شرط‌بندی"""
    user = message.from_user
    chat_id = message.chat.id
    
    # بررسی اینکه کاربر شرط فعال دارد یا نه
    bet_id, active_bet = get_active_bet(user.id, chat_id)
    if active_bet:
        await message.reply("❌ شما یک شرط فعال دارید! ابتدا آن را لغو کنید: /cancelbet")
        return
    
    # دریافت مقدار شرط
    try:
        amount = int(message.text.split()[1])
    except (IndexError, ValueError):
        await message.reply(
            f"❌ فرمت: `/bet [مقدار]`\n\n"
            f"💰 حداقل شرط: {BET_CONFIG['min_bet']}\n"
            f"💰 حداکثر شرط: {BET_CONFIG['max_bet']}"
        )
        return
    
    # بررسی محدوده شرط
    if amount < BET_CONFIG["min_bet"]:
        await message.reply(f"❌ حداقل مقدار شرط {BET_CONFIG['min_bet']} امتیاز است!")
        return
    
    if amount > BET_CONFIG["max_bet"]:
        await message.reply(f"❌ حداکثر مقدار شرط {BET_CONFIG['max_bet']} امتیاز است!")
        return
    
    # بررسی اینکه کاربر امتیاز کافی دارد
    user_points = get_user_points(user.id)
    if user_points < amount:
        await message.reply(f"❌ امتیاز کافی ندارید! امتیاز شما: {user_points}")
        return
    
    # نمایش گزینه‌های شرط
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🟢 زوج (×2)", callback_data=f"bet_even_{amount}"),
            InlineKeyboardButton("🔴 فرد (×2)", callback_data=f"bet_odd_{amount}")
        ],
        [
            InlineKeyboardButton("🎯 عدد 1 (×6)", callback_data=f"bet_exact_1_{amount}"),
            InlineKeyboardButton("🎯 عدد 2 (×6)", callback_data=f"bet_exact_2_{amount}"),
            InlineKeyboardButton("🎯 عدد 3 (×6)", callback_data=f"bet_exact_3_{amount}")
        ],
        [
            InlineKeyboardButton("🎯 عدد 4 (×6)", callback_data=f"bet_exact_4_{amount}"),
            InlineKeyboardButton("🎯 عدد 5 (×6)", callback_data=f"bet_exact_5_{amount}"),
            InlineKeyboardButton("🎯 عدد 6 (×6)", callback_data=f"bet_exact_6_{amount}")
        ],
        [
            InlineKeyboardButton("📉 پایین 1-3 (×3)", callback_data=f"bet_low_{amount}"),
            InlineKeyboardButton("📈 بالا 4-6 (×3)", callback_data=f"bet_high_{amount}")
        ],
        [InlineKeyboardButton("❌ لغو", callback_data="bet_cancel")]
    ])
    
    await message.reply(
        f"🎲 **شرط‌بندی با {amount} امتیاز**\n\n"
        f"لطفاً نوع شرط خود را انتخاب کنید:\n\n"
        f"• زوج/فرد: ضریب {BET_CONFIG['multipliers']['even_odd']}\n"
        f"• عدد دقیق: ضریب {BET_CONFIG['multipliers']['exact']}\n"
        f"• محدوده‌ها: ضریب {BET_CONFIG['multipliers']['range_low']}",
        reply_markup=keyboard
    )


@app.on_callback_query(filters.regex(r"^bet_"))
async def handle_bet_callback(client, callback_query: CallbackQuery):
    """مدیریت انتخاب نوع شرط"""
    user = callback_query.from_user
    data = callback_query.data
    
    if data == "bet_cancel":
        await callback_query.edit_message_text("❌ شرط‌بندی لغو شد.")
        return
    
    parts = data.split("_")
    
    # دریافت اطلاعات شرط
    if parts[1] in ["even", "odd"]:
        bet_type = "even_odd"
        prediction = parts[1]
        amount = int(parts[2])
    elif parts[1] == "exact":
        bet_type = "exact"
        prediction = int(parts[2])
        amount = int(parts[3])
    elif parts[1] == "low":
        bet_type = "range_low"
        prediction = "low"
        amount = int(parts[2])
    elif parts[1] == "high":
        bet_type = "range_high"
        prediction = "high"
        amount = int(parts[2])
    else:
        await callback_query.answer("❌ خطا در پردازش!", show_alert=True)
        return
    
    # بررسی امتیاز کاربر
    user_points = get_user_points(user.id)
    if user_points < amount:
        await callback_query.answer(f"❌ امتیاز کافی ندارید!", show_alert=True)
        return
    
    # کسر امتیاز و ایجاد شرط
    remove_points(user.id, amount)
    bet_id = create_bet(callback_query.message.chat.id, user.id, amount, bet_type, prediction)
    
    # نمایش پیام تایید
    prediction_text = {
        "even": "زوج",
        "odd": "فرد",
        "low": "پایین (1-3)",
        "high": "بالا (4-6)"
    }.get(prediction, f"عدد {prediction}")
    
    await callback_query.edit_message_text(
        f"✅ شرط شما ثبت شد!\n\n"
        f"💰 مقدار: {amount} امتیاز\n"
        f"🎯 پیش‌بینی: {prediction_text}\n\n"
        f"🎲 حالا تاس بزنید تا نتیجه مشخص شود!\n"
        f"⏱ زمان: {BET_CONFIG['bet_timeout']} ثانیه"
    )
    
    await callback_query.answer("✅ شرط ثبت شد!", show_alert=False)


@app.on_message(filters.command("cancelbet"))
async def cancel_bet_command(client, message: Message):
    """لغو شرط فعال"""
    user = message.from_user
    chat_id = message.chat.id
    
    bet_id, bet = get_active_bet(user.id, chat_id)
    
    if not bet:
        await message.reply("❌ شما شرط فعالی ندارید!")
        return
    
    if cancel_bet(bet_id):
        await message.reply(f"✅ شرط شما لغو شد و {bet['amount']} امتیاز برگشت داده شد.")
    else:
        await message.reply("❌ خطا در لغو شرط!")


@app.on_message(filters.command("mybets"))
async def my_bets_command(client, message: Message):
    """مشاهده شرط‌های فعال"""
    user = message.from_user
    chat_id = message.chat.id
    
    bet_id, bet = get_active_bet(user.id, chat_id)
    
    if not bet:
        await message.reply("❌ شما شرط فعالی ندارید!")
        return
    
    prediction_text = {
        "even": "زوج",
        "odd": "فرد",
        "low": "پایین (1-3)",
        "high": "بالا (4-6)"
    }.get(bet["prediction"], f"عدد {bet['prediction']}")
    
    await message.reply(
        f"🎲 **شرط فعال شما:**\n\n"
        f"💰 مقدار: {bet['amount']} امتیاز\n"
        f"🎯 پیش‌بینی: {prediction_text}\n"
        f"⏱ زمان باقی‌مانده: محدود\n\n"
        f"برای لغو: /cancelbet"
    )


@app.on_message(filters.dice)
async def dice_handler(client, message: Message):
    """مدیریت تاس و تسویه حساب شرط‌ها"""
    dice_value = message.dice.value
    dice_emoji = message.dice.emoji
    user = message.from_user
    chat_id = message.chat.id

    # فقط تاس را بررسی کن
    if dice_emoji != "🎲":
        return
    
    # بررسی وجود شرط فعال
    bet_id, bet = get_active_bet(user.id, chat_id)
    
    if bet:
        # تسویه حساب شرط
        result = resolve_bet(bet_id, dice_value)
        
        if result:
            level_up_info = check_level_up(user.id)
            current_level = get_user_level(user.id)
            new_points = get_user_points(user.id)
            
            if result["won"]:
                text = f"""🎉 آفرین {user.mention}! برنده شدید! ✅

🎲 عدد تاس: **{dice_value}**
💰 شرط: {result['amount'] // result['multiplier']} امتیاز
🔥 ضریب: ×{result['multiplier']}
💎 برد: **+{result['amount']} امتیاز**
💰 امتیاز کل: **{new_points}**
📊 {current_level['badge']} لول {current_level['level_num']}"""
                
                if level_up_info["level_up"]:
                    text += f"\n\n🎊 **تبریک! لول‌اپ شدید!**\n"
                    text += f"{level_up_info['badge']} **به لول {level_up_info['new_level']}: {level_up_info['level_title']}**"
            else:
                text = f"""❌ متاسفم {user.mention}، باختید!

🎲 عدد تاس: **{dice_value}**
💸 ضرر: {result['amount']} امتیاز
💰 امتیاز کل: **{new_points}**
📊 {current_level['badge']} لول {current_level['level_num']}

دفعه بعد شانس بیشتری خواهید داشت! 💪"""
            
            await message.reply(text)
    else:
        # اگر شرط فعال نداشت، سیستم قدیمی (شیش = جایزه)
        if dice_value == 6:
            points_earned = random.randint(20, 40)
            new_points = add_points(user.id, points_earned)
            
            level_up_info = check_level_up(user.id)
            current_level = get_user_level(user.id)
            
            text = f"""🎉 آفرین {user.mention}! شیش آوردی ✅

💎 **+{points_earned}** امتیاز گرفتی!
💰 امتیاز کل: **{new_points}**
📊 {current_level['badge']} لول {current_level['level_num']}"""
            
            if level_up_info["level_up"]:
                text += f"\n\n🎊 **تبریک! لول‌اپ شدید!**\n"
                text += f"{level_up_info['badge']} **لول {level_up_info['new_level']}**"
            
            await message.reply(text)
        else:
            remove_points(user.id, 5)
            current_level = get_user_level(user.id)
            new_points = get_user_points(user.id)
            
            text = f"""متاسفم عاقبت ادعا همین میشه:(
5 امتیاز ازت کم شد

💎 امتیاز کل: **{new_points}**
📊 {current_level['badge']} لول {current_level['level_num']}"""
            
            await message.reply(text)


@app.on_message(filters.command("addpoints") & filters.user(ADMINS))
async def admin_add_points(client, message: Message):
    """اضافه کردن امتیاز توسط ادمین"""
    if not message.reply_to_message:
        await message.reply("❌ روی پیام کاربر ریپلای کن!")
        return
    
    try:
        amount = int(message.text.split()[1])
        user = message.reply_to_message.from_user
        new_points = add_points(user.id, amount)
        
        level_up_info = check_level_up(user.id)
        
        text = f"✅ {amount} امتیاز به {user.mention} اضافه شد!\n💎 امتیاز جدید: **{new_points}**"
        
        if level_up_info["level_up"]:
            text += f"\n\n🎉 **تبریک! لول‌اپ شدید!**\n"
            text += f"{level_up_info['badge']} **از لول {level_up_info['old_level']} به لول {level_up_info['new_level']}**\n"
            text += f"🏅 {level_up_info['level_title']}"
        
        await message.reply(text)
    except (IndexError, ValueError):
        await message.reply("❌ فرمت: `/addpoints 10` (روی پیام کاربر ریپلای کن)")


@app.on_message(filters.command("removepoints") & filters.user(ADMINS))
async def admin_remove_points(client, message: Message):
    """کم کردن امتیاز توسط ادمین"""
    if not message.reply_to_message:
        await message.reply("❌ روی پیام کاربر ریپلای کن!")
        return
    
    try:
        amount = int(message.text.split()[1])
        user = message.reply_to_message.from_user
        new_points = remove_points(user.id, amount)
        
        await message.reply(f"✅ {amount} امتیاز از {user.mention} کم شد!\n💎 امتیاز جدید: **{new_points}**")
    except (IndexError, ValueError):
        await message.reply("❌ فرمت: `/removepoints 10` (روی پیام کاربر ریپلای کن)")


@app.on_message(filters.command("setpoints") & filters.user(ADMINS))
async def admin_set_points(client, message: Message):
    """تنظیم دستی امتیاز توسط ادمین"""
    if not message.reply_to_message:
        await message.reply("❌ روی پیام کاربر ریپلای کن!")
        return
    
    try:
        amount = int(message.text.split()[1])
        user = message.reply_to_message.from_user
        set_points(user.id, amount)
        
        await message.reply(f"✅ امتیاز {user.mention} به **{amount}** تنظیم شد!")
    except (IndexError, ValueError):
        await message.reply("❌ فرمت: `/setpoints 100` (روی پیام کاربر ریپلای کن)")


# ========== بازی جعبه با عملیات ریاضی ==========

def generate_math_question():
    """تولید یک سوال ریاضی تصادفی"""
    operation = random.choice(BOX_CONFIG["operations"])
    num_1 = random.randint(*BOX_CONFIG["number_range"])
    num_2 = random.randint(*BOX_CONFIG["number_range"])
    
    # برای تقسیم، مطمئن میشویم که باقیمانده نداشته باشه
    if operation == "/":
        num_1 = num_2 * random.randint(1, 10)
    
    # محاسبه جواب
    if operation == "+":
        answer = num_1 + num_2
    elif operation == "-":
        answer = num_1 - num_2
    elif operation == "*":
        answer = num_1 * num_2
    elif operation == "/":
        answer = num_1 // num_2
    
    return num_1, num_2, operation, answer


@app.on_message(filters.group)
async def auto_box(client, message: Message):
    """سیستم خودکار جعبه با عملیات ریاضی"""
    chat_id = message.chat.id

    if chat_id not in msg_count:
        msg_count[chat_id] = 0

    msg_count[chat_id] += 1

    if msg_count[chat_id] >= BOX_CONFIG["message_threshold"]:
        # تولید سوال ریاضی
        num_1, num_2, operation, correct_answer = generate_math_question()
        box_answer[chat_id] = correct_answer

        # تولید گزینه‌های غلط
        correct_pos = random.randint(0, 2)
        options = []

        for i in range(3):
            if i == correct_pos:
                options.append(correct_answer)
            else:
                # تولید جواب غلط که نزدیک به جواب درست باشه
                wrong = correct_answer + random.randint(-10, 10)
                while wrong == correct_answer or wrong in options:
                    wrong = correct_answer + random.randint(-10, 10)
                options.append(wrong)

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(str(options[0]), callback_data=f"box_{chat_id}_{options[0]}"),
                InlineKeyboardButton(str(options[1]), callback_data=f"box_{chat_id}_{options[1]}"),
                InlineKeyboardButton(str(options[2]), callback_data=f"box_{chat_id}_{options[2]}")
            ]
        ])

        # ارسال استیکر
        await app.send_sticker(
            chat_id, 
            "CAACAgQAAyEFAASyTOk5AAMFaN_-Do141GgmCVjw5OIQJgKL1koAAo8YAAJc5gFT_ajtuyWZet8eBA"
        )
        
        # ارسال سوال
        await app.send_message(
            chat_id,
            f"🎁 **جعبه شانس!**\n\n❓ پاسخ `{num_1} {operation} {num_2}` چند میشود؟",
            reply_markup=keyboard
        )
        
        msg_count[chat_id] = 0


@app.on_callback_query(filters.regex(r"^box_"))
async def handle_box_callback(client, callback_query: CallbackQuery):
    """مدیریت پاسخ جعبه با لول‌اپ"""
    data = callback_query.data
    user = callback_query.from_user
    
    parts = data.split("_")
    chat_id = int(parts[1])
    user_answer = int(parts[2])

    # بررسی اینکه کاربر قبلاً جواب داده یا نه
    if user.id in box_banned_users:
        await callback_query.answer(
            "❌ دوباره نمیتونی شرکت کنی!", 
            show_alert=True
        )
        return

    # بررسی جواب
    if user_answer == box_answer.get(chat_id):
        points_earned = random.randint(BOX_CONFIG["min_reward"], BOX_CONFIG["max_reward"])
        new_points = add_points(user.id, points_earned)
        
        level_up_info = check_level_up(user.id)
        current_level = get_user_level(user.id)
        
        text = f"""🎉 آفرین {user.mention}! جواب درست بود ✅

💎 **+{points_earned}** امتیاز گرفتی!
💰 امتیاز کل: **{new_points}**
📊 {current_level['badge']} لول {current_level['level_num']}"""
        
        if level_up_info["level_up"]:
            text += f"\n\n🎊 **تبریک! لول‌اپ شدید!**\n"
            text += f"{level_up_info['badge']} **به لول {level_up_info['new_level']}: {level_up_info['level_title']}**"
        
        await callback_query.edit_message_text(text)
        box_banned_users.clear()
    else:
        await callback_query.answer(
            "❌ اشتباه جواب دادی، دیگه نمیتونی جواب بدی.", 
            show_alert=True
        )
        box_banned_users.append(user.id)


# ========== هوش مصنوعی ==========

@app.on_message(filters.command("ai"))
async def ai_command(client, message: Message):
    """هوش مصنوعی گوگل Gemini"""
    text = message.text[4:].strip()
    
    if not text:
        await message.reply("❌ لطفاً یک سوال بپرسید.\n\n📝 مثال: `/ai سلام`")
        return
    
    try:
        processing_msg = await message.reply("🔄 در حال پردازش...")
        
        genai_client = genai.Client(api_key=GEMINI_API_KEY)
        response = genai_client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=text
        )
        
        await processing_msg.delete()
        
        response_text = response.text
        max_length = 4000
        
        # اگر پاسخ کوتاه بود، یک پیام بفرست
        if len(response_text) <= max_length:
            await message.reply(response_text)
        else:
            # اگر پاسخ بلند بود، به چند پیام تقسیم کن
            chunks = []
            current_chunk = ""
            lines = response_text.split('\n')
            
            for line in lines:
                if len(current_chunk) + len(line) + 1 <= max_length:
                    current_chunk += line + '\n'
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = line + '\n'
            
            if current_chunk:
                chunks.append(current_chunk)
            
            # ارسال تمام چانک‌ها
            for i, chunk in enumerate(chunks):
                if i == 0:
                    await message.reply(chunk)
                else:
                    await message.reply(chunk, reply_to_message_id=message.id)
    
    except TimeoutError:
        await message.reply("❌ خطا: زمان درخواست به پایان رسید. لطفاً دوباره تلاش کنید.")
    except Exception as e:
        await message.reply(f"❌ خطا: {str(e)}")


# ========== مدیریت درخواست عضویت ==========

@app.on_chat_join_request()
async def join_request_handler(client, chat_join_request: ChatJoinRequest):
    """مدیریت درخواست عضویت"""
    user = chat_join_request.from_user
    chat_title = chat_join_request.chat.title
    chat_id = chat_join_request.chat.id

    # ارسال نوتیفیکیشن به ادمین اصلی
    await app.send_message(
        MAIN_ADMIN_ID, 
        f"✅ درخواست عضویت از: {user.mention} برای گروه **{chat_title}** قبول شد."
    )

    # تایید درخواست
    await chat_join_request.approve()

    # پیام خوش‌آمدگویی
    await client.send_message(
        chat_id, 
        f"سلام {user.mention} به شاهمرادی کلاب خوش اومدی! 👋\n\n📌 قوانین پین شده رو حتماً بخون."
    )


# ========== اجرای ربات ==========

if __name__ == "__main__":
    print("🚀 Shahmoradi bot is running...")
    print(f"📊 Level System: {len(LEVEL_CONFIG)} levels")
    print(f"🎲 Betting System: Active")
    print(f"📦 Box System: Every {BOX_CONFIG['message_threshold']} messages")
    app.run()