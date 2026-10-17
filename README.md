# بله قربان — Bale Bulk Messenger (VPS Turkey)

> ربات «امید به خدا» — تبلیغ در شبکه‌های اجتماعی

Telegram bot -> Bale web.bale.ai (CDP 9222) -> bulk send

## نصب روی VPS ترکیه
```bash
unzip bale-ghorban.zip && cd bale-ghorban
chmod +x install.sh run_bale_chrome.sh
./install.sh
```

## لاگین بله
```bash
./run_bale_chrome.sh  # لاگین با شماره + SMS در web.bale.ai
```

## اجرا
```bash
# روش 1: مستقیم
BOT_TOKEN=xxx BALE_CDP=http://127.0.0.1:9222 python bot.py

# روش 2: با .env
cp .env.example .env  # توکن رو پر کن
python bot.py  # .env خودکار خونده نمی‌شود — از systemd یا export استفاده کن

# روش 3: سرویس دائمی
sudo cp bale-ghorban.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now bale-ghorban
```

## CLI انبوه (بدون تلگرام)
```bash
python bale_messenger.py --list contacts_sample.csv --dry-run
python bale_messenger.py --list contacts.csv --message message.txt
python bale_messenger.py --list contacts.csv --text "سلام..."
```

## فایل‌ها
| فایل | توضیح |
|------|-------|
| `bot.py` | ربات تلگرام (polling) |
| `bale_messenger.py` | CLI انبوه |
| `message.txt` | متن پیش‌فرض (حبوبات) |
| `contacts_sample.csv` | نمونه مخاطبین |
