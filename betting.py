from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import BET_CONFIG
from database import (
    get_user_points, add_points, remove_points,
    get_user_level, check_level_up,
    get_active_bet, create_bet, cancel_bet, resolve_bet
)
import random

# دیتاهای موقت برای شرط‌های بین کاربری
user_vs_user_bets = {}  # {bet_id: {"creator": user_id, "amount": int, "message_id": int, "chat_id": int}}

# ========== دستورات شرط‌بندی ==========

async def bet_command(client, message: Message):
    """شروع شرط‌بندی - انتخاب نوع"""
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
    
    # انتخاب نوع شرط‌بندی با دکمه‌های شیشه‌ای
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎲 شرط با تاس", callback_data=f"bettype_dice_{amount}"),
        ],
        [
            InlineKeyboardButton("👥 شرط با کاربران", callback_data=f"bettype_users_{amount}"),
        ],
        [
            InlineKeyboardButton("❌ لغو", callback_data="bettype_cancel")
        ]
    ])
    
    await message.reply(
        f"💎 **شرط‌بندی با {amount} امتیاز**\n\n"
        f"🎯 نوع شرط‌بندی خود را انتخاب کنید:\n\n"
        f"🎲 **تاس:** شما تاس می‌زنید و بر اساس نتیجه برنده می‌شوید\n"
        f"👥 **کاربران:** با یک کاربر دیگر شرط می‌بندید (50-50)\n\n"
        f"💰 امتیاز شما: **{user_points}**",
        reply_markup=keyboard
    )


async def handle_bettype_callback(client, callback_query: CallbackQuery):
    """مدیریت انتخاب نوع شرط‌بندی"""
    user = callback_query.from_user
    data = callback_query.data
    
    if data == "bettype_cancel":
        await callback_query.edit_message_text("❌ شرط‌بندی لغو شد.")
        return
    
    parts = data.split("_")
    bet_type = parts[1]  # dice یا users
    amount = int(parts[2])
    
    if bet_type == "dice":
        # نمایش گزینه‌های شرط با تاس
        await show_dice_bet_options(client, callback_query, amount)
    
    elif bet_type == "users":
        # ایجاد شرط بین کاربری
        await create_user_vs_user_bet(client, callback_query, amount)


async def show_dice_bet_options(client, callback_query: CallbackQuery, amount: int):
    """نمایش گزینه‌های شرط با تاس"""
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
    
    await callback_query.edit_message_text(
        f"🎲 **شرط‌بندی با تاس - {amount} امتیاز**\n\n"
        f"لطفاً نوع شرط خود را انتخاب کنید:\n\n"
        f"• زوج/فرد: ضریب {BET_CONFIG['multipliers']['even_odd']}\n"
        f"• عدد دقیق: ضریب {BET_CONFIG['multipliers']['exact']}\n"
        f"• محدوده‌ها: ضریب {BET_CONFIG['multipliers']['range_low']}",
        reply_markup=keyboard
    )


async def create_user_vs_user_bet(client, callback_query: CallbackQuery, amount: int):
    """ایجاد شرط بین دو کاربر"""
    user = callback_query.from_user
    chat_id = callback_query.message.chat.id
    
    # بررسی امتیاز کاربر
    user_points = get_user_points(user.id)
    if user_points < amount:
        await callback_query.answer(f"❌ امتیاز کافی ندارید!", show_alert=True)
        return
    
    # کسر امتیاز از ایجادکننده
    remove_points(user.id, amount)
    
    # ایجاد شناسه یکتا
    from datetime import datetime
    bet_id = f"uvs_{chat_id}_{user.id}_{int(datetime.now().timestamp())}"
    
    # ذخیره اطلاعات شرط
    user_vs_user_bets[bet_id] = {
        "creator": user.id,
        "creator_name": user.first_name or "کاربر",
        "amount": amount,
        "chat_id": chat_id,
        "status": "waiting"
    }
    
    # دکمه شیشه‌ای برای پذیرش شرط
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ قبول می‌کنم! ✨", callback_data=f"acceptbet_{bet_id}")],
        [InlineKeyboardButton("❌ لغو شرط", callback_data=f"canceluserbet_{bet_id}")]
    ])
    
    await callback_query.edit_message_text(
        f"🎲 **شرط‌بندی بین کاربری**\n\n"
        f"🎯 ایجادکننده: {user.mention}\n"
        f"💰 مبلغ شرط: **{amount}** امتیاز\n"
        f"🎁 جایزه برنده: **{amount * 2}** امتیاز\n"
        f"📊 احتمال برد: **50%**\n\n"
        f"⏳ منتظر یک شرکت‌کننده...\n\n"
        f"💡 **توجه:** فقط کاربری که امتیاز کافی دارد می‌تواند شرکت کند!",
        reply_markup=keyboard
    )


async def handle_accept_bet(client, callback_query: CallbackQuery):
    """مدیریت پذیرش شرط توسط کاربر دوم"""
    user = callback_query.from_user
    data = callback_query.data
    bet_id = data.split("_", 1)[1]
    
    # بررسی وجود شرط
    if bet_id not in user_vs_user_bets:
        await callback_query.answer("❌ این شرط منقضی شده یا دیگر موجود نیست!", show_alert=True)
        return
    
    bet_info = user_vs_user_bets[bet_id]
    
    # بررسی اینکه خود ایجادکننده نباشد
    if user.id == bet_info["creator"]:
        await callback_query.answer("❌ شما نمی‌توانید در شرط خودتان شرکت کنید!", show_alert=True)
        return
    
    # بررسی اینکه شرط هنوز در انتظار است
    if bet_info["status"] != "waiting":
        await callback_query.answer("❌ این شرط قبلاً تکمیل شده!", show_alert=True)
        return
    
    # بررسی امتیاز کاربر دوم
    user_points = get_user_points(user.id)
    if user_points < bet_info["amount"]:
        await callback_query.answer(
            f"❌ امتیاز کافی ندارید! نیاز: {bet_info['amount']} | دارید: {user_points}",
            show_alert=True
        )
        return
    
    # کسر امتیاز از کاربر دوم
    remove_points(user.id, bet_info["amount"])
    
    # تغییر وضعیت به "در حال پردازش"
    bet_info["status"] = "processing"
    bet_info["accepter"] = user.id
    bet_info["accepter_name"] = user.first_name or "کاربر"
    
    # انتخاب تصادفی برنده
    winner_id = random.choice([bet_info["creator"], user.id])
    loser_id = user.id if winner_id == bet_info["creator"] else bet_info["creator"]
    
    winner_name = bet_info["creator_name"] if winner_id == bet_info["creator"] else bet_info["accepter_name"]
    loser_name = bet_info["accepter_name"] if winner_id == bet_info["creator"] else bet_info["creator_name"]
    
    # اعطای جایزه به برنده
    total_prize = bet_info["amount"] * 2
    add_points(winner_id, total_prize)
    
    # بررسی لول‌اپ برنده
    level_up_info = check_level_up(winner_id)
    winner_level = get_user_level(winner_id)
    winner_points = get_user_points(winner_id)
    
    loser_level = get_user_level(loser_id)
    loser_points = get_user_points(loser_id)
    
    # متن نتیجه
    result_text = f"""🎊 **نتیجه شرط‌بندی**

🎲 انتخاب تصادفی انجام شد...

{'🏆' * 20}

✨ **برنده:** [{winner_name}](tg://user?id={winner_id})
💎 جایزه: **+{total_prize}** امتیاز
💰 امتیاز جدید: **{winner_points}**
📊 {winner_level['badge']} لول {winner_level['level_num']}

{'➖' * 20}

😔 **بازنده:** [{loser_name}](tg://user?id={loser_id})
💸 ضرر: **-{bet_info['amount']}** امتیاز
💰 امتیاز جدید: **{loser_points}**
📊 {loser_level['badge']} لول {loser_level['level_num']}"""
    
    # اگر برنده لول‌اپ شد
    if level_up_info["level_up"]:
        result_text += f"\n\n🎉 **تبریک به برنده!**\n"
        result_text += f"{level_up_info['badge']} **لول‌اپ به لول {level_up_info['new_level']}: {level_up_info['level_title']}**"
    
    result_text += f"\n\n💫 *دفعه بعد شانس بیشتری خواهید داشت!*"
    
    # بروزرسانی پیام
    await callback_query.edit_message_text(result_text)
    
    # حذف شرط از لیست
    del user_vs_user_bets[bet_id]
    
    await callback_query.answer("🎊 نتیجه اعلام شد!", show_alert=False)


async def handle_cancel_userbet(client, callback_query: CallbackQuery):
    """لغو شرط بین کاربری توسط ایجادکننده"""
    user = callback_query.from_user
    data = callback_query.data
    bet_id = data.split("_", 1)[1]
    
    # بررسی وجود شرط
    if bet_id not in user_vs_user_bets:
        await callback_query.answer("❌ این شرط منقضی شده!", show_alert=True)
        return
    
    bet_info = user_vs_user_bets[bet_id]
    
    # فقط ایجادکننده می‌تواند لغو کند
    if user.id != bet_info["creator"]:
        await callback_query.answer("❌ فقط ایجادکننده می‌تواند شرط را لغو کند!", show_alert=True)
        return
    
    # بررسی اینکه شرط هنوز در انتظار است
    if bet_info["status"] != "waiting":
        await callback_query.answer("❌ شرط در حال پردازش است و نمی‌توان لغو کرد!", show_alert=True)
        return
    
    # برگشت امتیاز به ایجادکننده
    add_points(bet_info["creator"], bet_info["amount"])
    
    # بروزرسانی پیام
    await callback_query.edit_message_text(
        f"❌ **شرط لغو شد**\n\n"
        f"💰 {bet_info['amount']} امتیاز به [{bet_info['creator_name']}](tg://user?id={bet_info['creator']}) برگشت داده شد."
    )
    
    # حذف شرط از لیست
    del user_vs_user_bets[bet_id]
    
    await callback_query.answer("✅ شرط لغو شد و امتیاز برگشت داده شد!", show_alert=False)


async def handle_bet_callback(client, callback_query: CallbackQuery):
    """مدیریت انتخاب نوع شرط با تاس"""
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


async def cancelbet_command(client, message: Message):
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


async def mybets_command(client, message: Message):
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


# ========== مدیریت تاس ==========

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


# ========== تابع ثبت callback ها ==========
# این تابع باید در main.py فراخوانی شود

async def register_bet_callbacks(app):
    """ثبت تمام callback های مربوط به شرط‌بندی"""
    
    @app.on_callback_query(filters.regex(r"^bettype_"))
    async def bettype_callback_handler(client, callback_query):
        await handle_bettype_callback(client, callback_query)
    
    @app.on_callback_query(filters.regex(r"^acceptbet_"))
    async def acceptbet_callback_handler(client, callback_query):
        await handle_accept_bet(client, callback_query)
    
    @app.on_callback_query(filters.regex(r"^canceluserbet_"))
    async def canceluserbet_callback_handler(client, callback_query):
        await handle_cancel_userbet(client, callback_query)

# ========== پایان فایل ==========
# هندلرها در main.py ثبت می‌شوند
