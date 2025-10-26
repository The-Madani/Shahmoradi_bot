from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import BET_CONFIG
from database import (
    get_user_points, add_points, remove_points,
    get_user_level, check_level_up,
    get_active_bet, create_bet, cancel_bet, resolve_bet
)
import random

# ========== دستورات شرط‌بندی ==========

async def bet_command(client, message: Message):
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


# ========== پایان فایل ==========
# هندلرها در main.py ثبت می‌شوند
