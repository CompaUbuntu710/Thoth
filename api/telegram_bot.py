import os
import asyncio
import threading
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USERS = set()
_engine_ref = None
_bot_app = None
_notification_queue = []
_notif_loop_running = False

def init_engine(engine):
    global _engine_ref
    _engine_ref = engine

def set_allowed(user_id: int):
    ALLOWED_USERS.add(user_id)

async def _start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    set_allowed(uid)
    await update.message.reply_text("Thoth conectado. Usa /chat <mensaje>")

async def _chat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if ALLOWED_USERS and uid not in ALLOWED_USERS:
        await update.message.reply_text("No autorizado")
        return
    text = " ".join(ctx.args) if ctx.args else update.message.text
    if not text or text.startswith("/"):
        await update.message.reply_text("Usa: /chat <mensaje>")
        return
    engine = _engine_ref
    if not engine:
        await update.message.reply_text("Motor no disponible")
        return
    reply = await asyncio.get_event_loop().run_in_executor(
        None, engine.chat, text, f"tg_{uid}"
    )
    await update.message.reply_text(reply[:4096])

async def _stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    engine = _engine_ref
    if not engine:
        await update.message.reply_text("Motor no disponible")
        return
    facts = engine.recall()
    await update.message.reply_text(
        f"Thoth Stats\n"
        f"Modelo: {engine.model}\n"
        f"Memorias: {len(facts)}\n"
        f"Online"
    )

async def _notif_loop(app):
    global _notif_loop_running
    _notif_loop_running = True
    while True:
        await asyncio.sleep(2)
        while _notification_queue:
            text = _notification_queue.pop(0)
            for uid in list(ALLOWED_USERS):
                try:
                    await app.bot.send_message(chat_id=uid, text=text[:4096])
                except Exception:
                    pass

def _run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", _start))
    app.add_handler(CommandHandler("chat", _chat))
    app.add_handler(CommandHandler("stats", _stats))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _chat))
    global _bot_app
    _bot_app = app
    loop.create_task(_notif_loop(app))
    app.run_polling(drop_pending_updates=True)

def start_bot():
    if not TELEGRAM_TOKEN:
        return
    t = threading.Thread(target=_run_bot, daemon=True)
    t.start()

def send_notification(text: str):
    _notification_queue.append(text)
