#!/bin/bash
set -e
echo "=== بله قربان — نصب روی VPS ترکیه ==="
sudo apt update
sudo apt install -y python3-pip python3-venv chromium-browser xvfb 2>/dev/null || sudo apt install -y python3-pip python3-venv xvfb
python3 -m venv venv
source venv/bin/activate
pip install -U pip
pip install -r requirements.txt
playwright install chromium
playwright install-deps chromium 2>/dev/null || true
echo ""
echo "1) توکن بات تلگرام رو بذار:"
echo "   nano .env  # کپی از .env.example و BOT_TOKEN رو پر کن"
echo "   # یا: export BOT_TOKEN=123..."
echo ""
echo "2) کروم هدلس بله:"
echo "   ./run_bale_chrome.sh  # در یک ترمینال جدا"
echo "   # بعد web.bale.ai لاگین کن (کد SMS)"
echo ""
echo "3) اجرای بات:"
echo "   source venv/bin/activate && BOT_TOKEN=\$(grep BOT_TOKEN .env | cut -d= -f2) python bot.py"
echo ""
echo "4) یا سرویس systemd:"
echo "   sudo cp bale-ghorban.service /etc/systemd/system/"
echo "   sudo systemctl daemon-reload && sudo systemctl enable --now bale-ghorban"
