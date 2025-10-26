# Shahmoradi_bot

ربات تلگرام شاهمرادی — طراحی‌شده با پایتون، ساختار ماژولار، مقیاس‌پذیر و قابل توسعه برای پروژه‌های پیشرفته تلگرامی.

---

## ویژگی‌ها

* معماری ماژولار و قابل توسعه
* پشتیبانی از ماژول‌های بازی، شرط‌بندی و هوش مصنوعی
* مدیریت کاربران و داده‌ها با دیتابیس
* قابل اجرا روی سرور لینوکس و سازگار با systemd یا Docker
* ساختار تمیز و آماده برای توسعه بلندمدت

---

## پیش‌نیازها

* Python 3.10 یا بالاتر
* pip
* وابستگی‌ها در فایل `requirements.txt`

---

## نصب و راه‌اندازی

### 1. کلون و ورود به پوشه

```bash
git clone https://github.com/The-Madani/Shahmoradi_bot.git
cd Shahmoradi_bot
```

### 2. ساخت محیط مجازی و نصب وابستگی‌ها

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. پیکربندی

در فایل `.env` یا `config.py` مقادیر زیر را تنظیم کنید:

```
BOT_TOKEN="توکن_ربات"
ADMIN_IDS="123456789,987654321"
DATABASE_URL="sqlite:///data.db"
LOG_LEVEL="INFO"
```

### 4. اجرا

```bash
python main.py
```

---

## اجرای خودکار با systemd

فایل زیر را در مسیر `/etc/systemd/system/shahmoradi.service` ایجاد کنید:

```
[Unit]
Description=Shahmoradi Telegram Bot
After=network.target

[Service]
User=botuser
WorkingDirectory=/path/to/Shahmoradi_bot
EnvironmentFile=/path/to/Shahmoradi_bot/.env
ExecStart=/path/to/Shahmoradi_bot/.venv/bin/python main.py
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

سپس:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now shahmoradi.service
```

---

## ساختار پروژه

| فایل          | توضیح                             |
| ------------- | --------------------------------- |
| `main.py`     | نقطه ورود اصلی و مدیریت حلقه اجرا |
| `commands.py` | دستورات و هندلرهای تلگرام         |
| `config.py`   | بارگذاری تنظیمات و متغیرهای محیطی |
| `database.py` | ارتباط با دیتابیس و مدل‌های داده  |
| `events.py`   | مدیریت رویدادها و منطق پاسخ       |
| `ai.py`       | ماژول هوش مصنوعی و پاسخ خودکار    |
| `betting.py`  | منطق سیستم شرط‌بندی               |
| `box_game.py` | ماژول بازی جعبه                   |

---

## دستورات نمونه

| دستور            | توضیح                    |
| ---------------- | ------------------------ |
| `/start`         | آغاز و ثبت کاربر         |
| `/help`          | نمایش فهرست دستورات      |
| `/bet <amount>`  | ثبت شرط                  |
| `/ai <question>` | پرسش از ماژول هوش مصنوعی |

---

## نکات امنیتی

* توکن را در ریپوی عمومی منتشر نکنید
* شناسه ادمین‌ها را در `ADMIN_IDS` محدود کنید
* لاگ‌ها را از اطلاعات حساس پاک نگه دارید

---

## توسعه

* رعایت استاندارد کدنویسی با `flake8` و `black`
* افزودن تست‌ها با `pytest`
* پیشنهاد تغییرات از طریق Pull Request

---

## نقشه راه

* افزودن Dockerfile و docker-compose
* پشتیبانی کامل PostgreSQL و Alembic
* داشبورد وب برای مدیریت ربات
* تست‌های end-to-end

---

## اشکال‌زدایی

* بررسی توکن و وابستگی‌ها
* مشاهده وضعیت سرویس:

```bash
systemctl status shahmoradi
journalctl -u shahmoradi -f
```

---

## لایسنس

MIT License
