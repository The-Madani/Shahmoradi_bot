from pyrogram.types import ChatJoinRequest, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from config import MAIN_ADMIN_ID

# ذخیره موقت درخواست‌ها
pending_requests = {}  # {request_id: {"chat_id": ..., "user_id": ..., "user_name": ...}}

# ========== مدیریت درخواست عضویت ==========

async def join_request_handler(client, chat_join_request: ChatJoinRequest):
    """مدیریت درخواست عضویت - ارسال به ادمین برای تایید"""
    user = chat_join_request.from_user
    chat_title = chat_join_request.chat.title
    chat_id = chat_join_request.chat.id
    
    # ساخت شناسه یکتا برای این درخواست
    request_id = f"{chat_id}_{user.id}"
    
    # ذخیره اطلاعات درخواست
    pending_requests[request_id] = {
        "chat_id": chat_id,
        "user_id": user.id,
        "user_name": user.first_name or "کاربر ناشناس",
        "chat_title": chat_title
    }
    
    # دکمه‌های تایید یا رد
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ تایید", callback_data=f"approve_{request_id}"),
            InlineKeyboardButton("❌ رد", callback_data=f"reject_{request_id}")
        ]
    ])
    
    # ارسال درخواست به ادمین اصلی
    try:
        user_link = f"[{user.first_name or 'کاربر'}](tg://user?id={user.id})"
        await client.send_message(
            MAIN_ADMIN_ID,
            f"📨 **درخواست عضویت جدید**\n\n"
            f"👤 کاربر: {user_link}\n"
            f"🆔 آیدی: `{user.id}`\n"
            f"👥 گروه: **{chat_title}**\n"
            f"🆔 آیدی گروه: `{chat_id}`\n\n"
            f"❓ این کاربر رو تایید می‌کنی؟",
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"خطا در ارسال به ادمین: {e}")
        # اگر ارسال به ادمین ناموفق بود، خودکار تایید کن
        await chat_join_request.approve()


async def handle_join_request_callback(client, callback_query: CallbackQuery):
    """مدیریت پاسخ ادمین به درخواست عضویت"""
    data = callback_query.data
    admin_id = callback_query.from_user.id
    
    # بررسی اینکه فقط ادمین اصلی بتونه تایید کنه
    if admin_id != MAIN_ADMIN_ID:
        await callback_query.answer("❌ فقط مدیر اصلی می‌تونه تایید کنه!", show_alert=True)
        return
    
    parts = data.split("_")
    action = parts[0]  # approve یا reject
    request_id = "_".join(parts[1:])  # chat_id_user_id
    
    # بررسی وجود درخواست
    if request_id not in pending_requests:
        await callback_query.answer("❌ این درخواست منقضی شده!", show_alert=True)
        await callback_query.edit_message_text(
            callback_query.message.text + "\n\n⚠️ **این درخواست منقضی شده است.**"
        )
        return
    
    request_info = pending_requests[request_id]
    chat_id = request_info["chat_id"]
    user_id = request_info["user_id"]
    user_name = request_info["user_name"]
    chat_title = request_info["chat_title"]
    
    try:
        if action == "approve":
            # تایید درخواست
            await client.approve_chat_join_request(chat_id, user_id)
            
            # پیام خوش‌آمدگویی در گروه
            try:
                await client.send_message(
                    chat_id,
                    f"سلام [{user_name}](tg://user?id={user_id}) به {chat_title} خوش اومدی! 👋\n\n"
                    f"📌 قوانین پین شده رو حتماً بخون."
                )
            except:
                pass
            
            # بروزرسانی پیام ادمین
            await callback_query.edit_message_text(
                f"✅ **درخواست تایید شد!**\n\n"
                f"👤 کاربر: [{user_name}](tg://user?id={user_id})\n"
                f"🆔 آیدی: `{user_id}`\n"
                f"👥 گروه: **{chat_title}**\n\n"
                f"✅ کاربر با موفقیت به گروه اضافه شد."
            )
            
            await callback_query.answer("✅ درخواست تایید شد!", show_alert=False)
            
        elif action == "reject":
            # رد درخواست
            await client.decline_chat_join_request(chat_id, user_id)
            
            # بروزرسانی پیام ادمین
            await callback_query.edit_message_text(
                f"❌ **درخواست رد شد!**\n\n"
                f"👤 کاربر: [{user_name}](tg://user?id={user_id})\n"
                f"🆔 آیدی: `{user_id}`\n"
                f"👥 گروه: **{chat_title}**\n\n"
                f"❌ درخواست کاربر رد شد."
            )
            
            await callback_query.answer("❌ درخواست رد شد!", show_alert=False)
        
        # حذف درخواست از لیست
        del pending_requests[request_id]
        
    except Exception as e:
        await callback_query.answer(f"❌ خطا: {str(e)}", show_alert=True)
        print(f"خطا در پردازش درخواست: {e}")


async def pending_requests_command(client, message: Message):
    """نمایش درخواست‌های در انتظار تایید (فقط برای ادمین اصلی)"""
    user_id = message.from_user.id
    
    if user_id != MAIN_ADMIN_ID:
        await message.reply("❌ فقط مدیر اصلی می‌تونه این دستور رو استفاده کنه!")
        return
    
    if not pending_requests:
        await message.reply("✅ هیچ درخواستی در انتظار تایید نیست!")
        return
    
    text = "📋 **درخواست‌های در انتظار:**\n\n"
    for i, (request_id, info) in enumerate(pending_requests.items(), 1):
        text += f"{i}. [{info['user_name']}](tg://user?id={info['user_id']})\n"
        text += f"   └─ گروه: {info['chat_title']}\n"
        text += f"   └─ آیدی: `{info['user_id']}`\n\n"
    
    text += f"📊 **مجموع:** {len(pending_requests)} درخواست"
    
    await message.reply(text)


# ========== پایان فایل ==========
# هندلرها در main.py ثبت می‌شوند

