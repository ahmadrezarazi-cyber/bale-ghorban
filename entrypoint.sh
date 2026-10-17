#!/bin/bash
set -e
# entrypoint for Coolify — starts Chrome (CDP 9222) + Bale bot
DATA_DIR="${BALE_DATA_DIR:-/data/.bale-chrome}"
mkdir -p "$DATA_DIR"

# Find chrome
CHROME=$(which chromium-browser 2>/dev/null || which chromium 2>/dev/null || which google-chrome 2>/dev/null || echo "")
if [ -z "$CHROME" ]; then
  # fallback to playwright chromium
  CHROME=$(find /ms-playwright -name chrome -type f 2>/dev/null | head -n1 || echo "")
fi

if [ -n "$CHROME" ] && [ -x "$CHROME" ]; then
  echo "Starting Chrome CDP on 127.0.0.1:9222 (data: $DATA_DIR) with $CHROME"
  "$CHROME" \
    --headless=new \
    --no-sandbox \
    --disable-gpu \
    --disable-dev-shm-usage \
    --remote-debugging-port=9222 \
    --remote-allow-origins=* \
    --user-data-dir="$DATA_DIR" \
    https://web.bale.ai &
  echo "Chrome PID $!"
  sleep 3
else
  echo "WARN: Chrome not found — bot will run but Bale CDP will not be available until you add chromium"
fi

# Check BOT_TOKEN
if [ -z "$BOT_TOKEN" ] || echo "$BOT_TOKEN" | grep -q "PUT_YOUR"; then
  echo "ERROR: BOT_TOKEN not set. Set it in Coolify Environment Variables."
  echo "Get token from @BotFather on Telegram, then set BOT_TOKEN=123:ABC..."
  # keep container alive for debugging / chrome VNC
  tail -f /dev/null
fi

echo "Starting بله قربان bot (BALE_CDP=$BALE_CDP)..."
exec python /app/bot.py
