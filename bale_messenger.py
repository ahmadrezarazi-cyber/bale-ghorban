#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bale Bulk Messenger — send a fixed message to a list of phone numbers
through web.bale.ai (user's logged-in browser session via CDP).

Usage:
    python bale_messenger.py --list contacts.csv --message msg.txt [--dry-run]
CSV format: first column phone, second column name (optional). No header required
unless --has-header is passed. Message can be a file or inline.

Flow per row:
    contacts -> Add contact (phone, name) -> open chat -> type message -> send
    -> small random delay (anti-spam) -> next

Report: printed at end + written to bale_report.jsonl (success/fail per phone).
"""
import argparse
import csv
import json
import random
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

CDP = "http://127.0.0.1:9222"
BASE = Path(__file__).parent
REPORT = BASE / "bale_report.jsonl"

DEFAULT_MESSAGE = (
    "🛍️ سلام دوست عزیز!\n\n"
    "فروشگاه «خرید گجت» برایت یک پیشنهاد ویژه داره 🎁\n\n"
    "✨ جدیدترین گجت‌های هوشمند و لوازم روز دنیا\n"
    "📦 ارسال فوری به سراسر ایران\n"
    "💳 پرداخت امن با نماد اعتماد\n"
    "🛠️ گارانتی تعویض محصولات\n\n"
    "برای مشاهده محصولات و مشاوره رایگان، به سایت ما سرو کنید:\n"
    "👉 kharidgadget.com\n\n"
    "یا هر سوالی داری از ما بپرسید 🤝"
)


def read_list(path: Path, has_header: bool) -> list:
    rows = []
    with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            if i == 0 and has_header:
                continue
            if not row or not row[0].strip():
                continue
            phone = row[0].strip().replace(" ", "").replace("-", "")
            name = (row[1].strip() if len(row) > 1 and row[1].strip() else "مشتری")
            rows.append((phone, name))
    return rows


def open_add_modal(pg):
    """Open the 'add contact' modal; returns True if phone field appeared."""
    pg.goto("https://web.bale.ai/contacts", wait_until="domcontentloaded", timeout=45000)
    ready = False
    for _ in range(20):
        pg.wait_for_timeout(1000)
        if pg.evaluate("Array.from(document.querySelectorAll('BDI')).some(e => e.innerText.trim().includes('افزودن'))"):
            ready = True
            break
    if not ready:
        return False
    opened = pg.evaluate(
        """() => {
        const bd = Array.from(document.querySelectorAll('*')).find(
            e => e.tagName==='BDI' && e.innerText.trim()==='افزودن مخاطب');
        if (!bd) return 'NO_BDI';
        let el = bd;
        for (let i=0;i<7 && el;i++) {
            el = el.parentElement;
            if (el && el.getBoundingClientRect().width>200 && el.getBoundingClientRect().height>24) {
                el.click(); return 'OK';
            }
        }
        return 'NO_ROW';
    }"""
    )
    if opened in ("NO_BDI", "NO_ROW"):
        pg.mouse.click(1153, 185)  # fallback coords
    for _ in range(20):
        pg.wait_for_timeout(1000)
        if pg.query_selector('[aria-label="شماره همراه"]'):
            return True
    return False


def send_to_phone(pg, phone, name, message):
    """Return (True, note) if message sent, else (False, reason)."""
    if not open_add_modal(pg):
        return False, "modal_not_open"

    pg.get_by_label("شماره همراه").fill(phone)
    pg.wait_for_timeout(300)
    pg.get_by_label("نام").fill(name)
    pg.wait_for_timeout(400)

    try:
        pg.get_by_label("افزودن", exact=True).click(timeout=8000)
    except Exception:
        return False, "add_button_fail"
    pg.wait_for_timeout(2500)

    # Click the newly-added contact (top row under header)
    clicked = False
    for _ in range(10):
        rows = pg.evaluate(
            """() => {
            const out = [];
            for (const e of Array.from(document.querySelectorAll('*'))) {
                const r = e.getBoundingClientRect();
                const t = (e.innerText || '').trim();
                if (r.width > 200 && r.height > 24 && r.height < 70 && r.y > 140 && r.y < 800 && t && t.length < 45
                    && t.indexOf('\\n') < 0 && t.indexOf('افزودن') < 0 && t.indexOf('مرتب') < 0 && t.indexOf('برای شروع') < 0) {
                    out.push({ txt: t.slice(0, 35), x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2), y0: Math.round(r.y) });
                }
            }
            const seen = new Set(); const res = [];
            for (const o of out) { if (!seen.has(o.txt)) { seen.add(o.txt); res.push(o); } }
            res.sort((a,b)=>a.y0-b.y0);
            return res.slice(0, 3);
        }"""
        )
        if rows:
            pg.mouse.click(rows[0]["x"], rows[0]["y"])
            clicked = True
            break
        pg.wait_for_timeout(1500)
    if not clicked:
        return False, "contact_row_not_found"

    pg.wait_for_timeout(3000)
    if not pg.evaluate("!!document.querySelector('[contenteditable=true]')"):
        return False, "no_composer"

    ce = pg.locator("[contenteditable=true]").first
    ce.click()
    pg.wait_for_timeout(400)
    pg.keyboard.type(message, delay=6)
    pg.wait_for_timeout(700)
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(3000)

    # sanity: composer emptied
    tail = pg.evaluate('document.body ? document.body.innerText.slice(-80) : ""')
    if "پیام خود را بنویسید" in tail:
        return True, "sent"
    return True, "sent_unverified"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", required=True, help="CSV: phone,name (or phone only)")
    ap.add_argument("--message", default="", help="Path to message file (or inline with --text)")
    ap.add_argument("--text", default="", help="Inline message text")
    ap.add_argument("--has-header", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="Just print what would be done")
    ap.add_argument("--delay-min", type=float, default=15.0)
    ap.add_argument("--delay-max", type=float, default=35.0)
    args = ap.parse_args()

    message = args.text or (Path(args.message).read_text(encoding="utf-8") if args.message else DEFAULT_MESSAGE)
    rows = read_list(Path(args.list), args.has_header)
    if not rows:
        print("NO_ROWS")
        return
    print(f"TOTAL: {len(rows)} | dry_run={args.dry_run}", flush=True)

    if args.dry_run:
        for phone, name in rows:
            print(f"[-] {phone} {name}", flush=True)
        return

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP)
        ctx = browser.contexts[0]
        pg = next((pp for pp in ctx.pages if "bale" in (pp.url or "")), None)
        if not pg:
            print("NO_BALE_PAGE")
            sys.exit(1)
        pg.bring_to_front()

        ok = fail = 0
        for idx, (phone, name) in enumerate(rows, 1):
            print(f"[{idx}/{len(rows)}] {phone} {name} ...", flush=True)
            try:
                sent, note = send_to_phone(pg, phone, name, message)
                status = "OK" if sent else "FAIL"
                if sent:
                    ok += 1
                else:
                    fail += 1
                print(f"    -> {status} ({note})", flush=True)
                with REPORT.open("a", encoding="utf-8") as f:
                    f.write(json.dumps({"phone": phone, "name": name, "status": status, "note": note}) + "\n")
            except Exception as e:
                fail += 1
                print(f"    -> FAIL ({str(e)[:80]})", flush=True)
                with REPORT.open("a", encoding="utf-8") as f:
                    f.write(json.dumps({"phone": phone, "name": name, "status": "FAIL", "note": str(e)[:120]}) + "\n")
            # anti-spam delay
            delay = random.uniform(args.delay_min, args.delay_max)
            print(f"    waiting {delay:.0f}s", flush=True)
            time.sleep(delay)

        print(f"SUMMARY: ok={ok} fail={fail} total={len(rows)}", flush=True)


if __name__ == "__main__":
    main()