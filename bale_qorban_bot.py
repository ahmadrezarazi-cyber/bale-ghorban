#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
بله قربان — Telegram bot that drives Bale bulk messenger on VPS Turkey.
Commands:
  /start  — راهنما
  /status — وضعیت CDP / بله
  /send 09363233318 — ارسال تستی
  متن بفرست => ذخیره به عنوان پیام
  CSV آپلود کن => ارسال انبوه
"""
import os, sys, time, random, csv, json
from pathlib import Path
from io import BytesIO

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
CDP = os.environ.get("BALE_CDP", "http://127.0.0.1:9222")
BASE = Path(__file__).parent
MSG_FILE = BASE / "message.txt"
DEFAULT_MSG = "فروش حبوبات درجه یک به صورت عمده \nبرای مشاهده قیمت و مشاوره روی لینک زیر کلیک کنید"

HELP = """👋 سلام حاجی! من *بله قربان* هستم — ربات ارسال پیام انبوه بله روی VPS ترکیه.

*دستورات:*
/start — همین راهنما
/status — وضعیت بله (CDP وصل؟)
/send 09363233318 — ارسال تستی به یک شماره

*ارسال انبوه:*
1. متن پیام رو بفرست (همون حبوبات) — ذخیره میشه
2. فایل CSV شماره‌ها رو آپلود کن (هر خط: شماره,نام — نام اختیاری)
3. ربات خودش میفرسته و گزارش میده

CSV نمونه:
09363233318,تست
09123456789,علی
09901234567
"""

def send_to_phone(pg, phone, name, message):
    pg.goto("https://web.bale.ai/contacts", wait_until="domcontentloaded", timeout=45000)
    ready=False
    for _ in range(20):
        pg.wait_for_timeout(1000)
        if pg.evaluate("Array.from(document.querySelectorAll('BDI')).some(e => e.innerText.trim().includes('افزودن'))"):
            ready=True; break
    if not ready:
        return False, "modal_not_open"
    opened = pg.evaluate("""() => {
        const bd = Array.from(document.querySelectorAll('*')).find(e => e.tagName==='BDI' && e.innerText.trim()==='افزودن مخاطب');
        if (!bd) return 'NO_BDI';
        let el=bd; for(let i=0;i<7&&el;i++){ el=el.parentElement; if(el && el.getBoundingClientRect().width>200 && el.getBoundingClientRect().height>24){ el.click(); return 'OK'; } }
        return 'NO_ROW';
    }""")
    if opened in ("NO_BDI","NO_ROW"):
        pg.mouse.click(1153,185)
    for _ in range(20):
        pg.wait_for_timeout(1000)
        if pg.query_selector('[aria-label="شماره همراه"]'):
            break
    else:
        return False, "modal_not_open"
    pg.get_by_label("شماره همراه").fill(phone)
    pg.wait_for_timeout(300)
    pg.get_by_label("نام").fill(name)
    pg.wait_for_timeout(400)
    try:
        pg.get_by_label("افزودن", exact=True).click(timeout=8000)
    except:
        return False, "add_button_fail"
    pg.wait_for_timeout(2500)
    clicked=False
    for _ in range(10):
        rows = pg.evaluate("""() => {
            const out=[]; for(const e of document.querySelectorAll('*')){ const r=e.getBoundingClientRect(); const t=(e.innerText||'').trim(); if(r.width>200&&r.height>24&&r.height<70&&r.y>140&&r.y<800&&t&&t.length<45&&t.indexOf('\\n')<0&&t.indexOf('افزودن')<0&&t.indexOf('مرتب')<0&&t.indexOf('برای شروع')<0){ out.push({txt:t.slice(0,35),x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2),y0:Math.round(r.y)});}}
            const seen=new Set(); const res=[]; for(const o of out){ if(!seen.has(o.txt)){ seen.add(o.txt); res.push(o); } } res.sort((a,b)=>a.y0-b.y0); return res.slice(0,3);
        }""")
        if rows:
            pg.mouse.click(rows[0]["x"], rows[0]["y"])
            clicked=True
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
    for i, part in enumerate(message.split("\n")):
        if i>0:
            pg.keyboard.press("Shift+Enter")
        pg.keyboard.type(part, delay=6)
    pg.wait_for_timeout(700)
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(3000)
    return True, "sent"

# Telegram handlers (lazy)
try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
    HAS_TG = True
except ImportError:
    HAS_TG = False

async def cmd_start(update, ctx):
    await update.message.reply_text(HELP, parse_mode="Markdown")

async def cmd_status(update, ctx):
    import httpx
    try:
        r = httpx.get(f"{CDP}/json/version", timeout=5)
        ver = r.json().get("Browser","?")
        await update.message.reply_text(f"✅ CDP وصل — {ver}\nBale: https://web.bale.ai")
    except Exception as e:
        await update.message.reply_text(f"❌ CDP قطع — {e}\nکروم با --remote-debugging-port=9222 باز نیست.")

async def cmd_send(update, ctx):
    phone = (ctx.args[0] if ctx.args else "").strip().replace(" ","").replace("-","")
    if not phone:
        await update.message.reply_text("بزن: /send 09363233318")
        return
    msg = MSG_FILE.read_text(encoding="utf-8") if MSG_FILE.exists() else DEFAULT_MSG
    await update.message.reply_text(f"⏳ دارم به {phone} میفرستم…")
    from playwright.sync_api import sync_playwright
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(CDP)
            pg = next((pp for pp in browser.contexts[0].pages if "bale" in (pp.url or "")), None)
            if not pg:
                await update.message.reply_text("❌ صفحه web.bale.ai باز نیست.")
                return
            ok, note = send_to_phone(pg, phone, "تست", msg)
            await update.message.reply_text(f"{'✅' if ok else '❌'} {phone} → {note}")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {e}")

async def on_text(update, ctx):
    text = update.message.text.strip()
    if text.startswith("/"):
        return
    MSG_FILE.write_text(text, encoding="utf-8")
    await update.message.reply_text(f"✅ متن ذخیره شد:\n\n{text}\n\nحالا CSV شماره‌ها رو بفرست تا ارسال کنم.")

async def on_document(update, ctx):
    doc = update.message.document
    if not doc.file_name.lower().endswith(".csv"):
        await update.message.reply_text("فقط CSV بده حاجی — هر خط شماره,نام")
        return
    msg = MSG_FILE.read_text(encoding="utf-8") if MSG_FILE.exists() else DEFAULT_MSG
    f = await ctx.bot.get_file(doc.file_id)
    data = BytesIO()
    await f.download_to_memory(data)
    data.seek(0)
    rows=[]
    for line in data.read().decode("utf-8-sig").splitlines():
        if not line.strip():
            continue
        parts=[p.strip() for p in line.split(",")]
        if parts[0].startswith("09"):
            rows.append((parts[0], parts[1] if len(parts)>1 and parts[1] else "مشتری"))
    if not rows:
        await update.message.reply_text("❌ CSV خالی یا شماره‌ها با 09 شروع نمیشن.")
        return
    await update.message.reply_text(f"📋 {len(rows)} شماره — دارم میفرستم (هر پیام ~20 ثانیه)…\nمتن: {msg[:300]}")
    from playwright.sync_api import sync_playwright
    ok=fail=0
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP)
        pg = next((pp for pp in browser.contexts[0].pages if "bale" in (pp.url or "")), None)
        if not pg:
            await update.message.reply_text("❌ web.bale.ai باز نیست.")
            return
        for i,(phone,name) in enumerate(rows,1):
            try:
                sent, note = send_to_phone(pg, phone, name, msg)
                if sent: ok+=1
                else: fail+=1
                if i%5==0 or i==len(rows):
                    await update.message.reply_text(f"⏳ {i}/{len(rows)} — ok={ok} fail={fail} — آخر: {phone} {note}")
                time.sleep(random.uniform(15,35))
            except Exception as e:
                fail+=1
                await update.message.reply_text(f"❌ {phone} خطا: {e}")
    await update.message.reply_text(f"✅ تمام — ok={ok} fail={fail} total={len(rows)}")

def main():
    if not HAS_TG:
        print("pip install python-telegram-bot httpx playwright")
        sys.exit(1)
    if not BOT_TOKEN:
        print("BOT_TOKEN env missing — export BOT_TOKEN=...")
        sys.exit(1)
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("send", cmd_send))
    app.add_handler(MessageHandler(filters.Document.ALL, on_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    print("بله قربان بالا اومد — polling...")
    app.run_polling(drop_pending_updates=True)

if __name__=="__main__":
    main()
