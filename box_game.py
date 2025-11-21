from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import BOX_CONFIG
from database import add_points, get_user_level, check_level_up, get_user_points
import random

# دیتاهای موقت برای جعبه
msg_count = {}
box_data = {}  # {chat_id: {"answer": int, "users_answered": [user_ids]}}

# ========== توابع کمکی ==========

def generate_math_question():
    """تولید یک سوال ریاضی تصادفی"""
    operation = random.choice(BOX_CONFIG["operations"])
    num_1 = random.randint(*BOX_CONFIG["number_range"])
    num_2 = random.randint(*BOX_CONFIG["number_range"])
    
    # برای تقسیم، مطمئن میشویم که باقیمانده نداشته باشه
    if operation == "/":
        num_2 = random.randint(1, 10)  # جلوگیری از تقسیم بر صفر
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


# ========== هندلر اصلی ==========

async def auto_box_handler(client, message: Message):
    """سیستم خودکار جعبه با عملیات ریاضی"""
    chat_id = message.chat.id

    # شمارش پیام‌ها
    if chat_id not in msg_count:
        msg_count[chat_id] = 0

    msg_count[chat_id] += 1

    # اگر به تعداد مورد نیاز رسیدیم
    if msg_count[chat_id] >= BOX_CONFIG["message_threshold"]:
        # تولید سوال ریاضی
        num_1, num_2, operation, correct_answer = generate_math_question()
        
        # ذخیره جواب و لیست کسانی که جواب دادن
        box_data[chat_id] = {
            "answer": correct_answer,
            "users_answered": []
        }

        # تولید گزینه‌های غلط
        correct_pos = random.randint(0, 2)
        options = []

        for i in range(3):
            if i == correct_pos:
                options.append(correct_answer)
            else:
                # تولید جواب غلط که نزدیک به جواب درست باشه
                wrong = correct_answer + random.randint(-10, 10)
                # مطمئن شو که جواب غلط تکراری یا برابر با جواب درست نباشه
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
        try:
            await client.send_sticker(chat_id, BOX_CONFIG["sticker_id"])
        except Exception as e:
            print(f"خطا در ارسال استیکر: {e}")
            pass  # اگر استیکر مشکل داشت، ادامه بده
        
        # ارسال سوال
        await client.send_message(
            chat_id,
            f"🎁 **جعبه شانس!**\n\n❓ پاسخ `{num_2} {operation} {num_1}` چند میشود؟",
            reply_markup=keyboard
        )
        
        # ریست کانتر
        msg_count[chat_id] = 0


async def handle_box_callback(client, callback_query: CallbackQuery):
    """مدیریت پاسخ جعبه با لول‌اپ"""
    data = callback_query.data
    user = callback_query.from_user
    
    parts = data.split("_")
    chat_id = int(parts[1])
    user_answer = int(parts[2])

    # بررسی اینکه این چت جعبه فعال داره
    if chat_id not in box_data:
        await callback_query.answer("❌ این جعبه منقضی شده!", show_alert=True)
        return

    # بررسی اینکه کاربر قبلاً جواب داده یا نه
    if user.id in box_data[chat_id]["users_answered"]:
        await callback_query.answer(
            "❌ دوباره نمیتونی شرکت کنی!", 
            show_alert=True
        )
        return

    # اضافه کردن کاربر به لیست کسایی که جواب دادن
    box_data[chat_id]["users_answered"].append(user.id)

    # بررسی جواب
    if user_answer == box_data[chat_id]["answer"]:
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
        
        # پاک کردن دیتای جعبه چون کسی برنده شد
        if chat_id in box_data:
            del box_data[chat_id]
    else:
        await callback_query.answer(
            "❌ اشتباه جواب دادی، دیگه نمیتونی جواب بدی.", 
            show_alert=True
        )


# ========== پایان فایل ==========
# هندلرها در main.py ثبت می‌شوند
