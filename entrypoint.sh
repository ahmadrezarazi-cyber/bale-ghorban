#!/bin/bash
set -e
DATA_DIR="${BALE_DATA_DIR:-/data/.bale-chrome}"
mkdir -p "$DATA_DIR"

CHROME=$(which chromium-browser 2>/dev/null || which chromium 2>/dev/null || which google-chrome 2>/dev/null || echo "")
if [ -z "$CHROME" ]; then
  CHROME=$(find /ms-playwright -name chrome -type f 2>/dev/null | head -n1 || echo "")
fi

if [ -n "$CHROME" ] && [ -x "$CHROME" ]; then
  echo "Starting Chrome CDP on 127.0.0.1:9222 (data: $DATA_DIR) with $CHROME"
  "$CHROME" --headless=new --no-sandbox --disable-gpu --disable-dev-shm-usage --remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir="$DATA_DIR" https://web.bale.ai &
  echo "Chrome PID $!"
  sleep 3
else
  echo "WARN: Chrome not found"
fi

if [ -z "$BOT_TOKEN" ] || echo "$BOT_TOKEN" | grep -q "PUT_YOUR"; then
  echo "BOT_TOKEN not set — Bale-only mode (no Telegram bot)."
  echo "  Use: python bale_messenger.py --list contacts.csv --message message.txt"
  wait
fi

echo "Starting Bale bot (BALE_CDP=$BALE_CDP)..."
exec python /app/bot.py
