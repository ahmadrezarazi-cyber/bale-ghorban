#!/bin/bash
# کروم هدلس با CDP برای web.bale.ai
CHROME=$(which chromium-browser 2>/dev/null || which chromium 2>/dev/null || which google-chrome 2>/dev/null || echo chromium-browser)
echo "Chrome: $CHROME"
echo "CDP on 127.0.0.1:9222 — باز کن https://web.bale.ai و لاگین کن"
$CHROME --headless=new --no-sandbox --disable-gpu --remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir=$HOME/.bale-chrome https://web.bale.ai
