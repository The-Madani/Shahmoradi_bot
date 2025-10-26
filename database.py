import json
import os
from config import POINTS_FILE, LEVELS_FILE, BETS_FILE, LEVEL_CONFIG

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
    from datetime import datetime
    
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
    from config import BET_CONFIG
    
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
