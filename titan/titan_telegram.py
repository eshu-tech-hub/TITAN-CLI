Set-Content -Path titan_telegram.py -Value @'
import sys
import logging
from unittest.mock import MagicMock
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from titan.cli.common import create_runtime_engine

# --- CONFIGURATION ---
TELEGRAM_TOKEN = "8991345556:AAFM7XKnkQW_u2KM4Y_3yPCK0z4O8RjHaGk"
AUTHORIZED_CHAT_ID = "REPLACE_WITH_YOUR_NUMERIC_CHAT_ID"

# Keep logs clean
logging.getLogger("yfinance").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")

engine = None

async def setup_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    msg = f"🛑 SETUP MODE\nYour Chat ID is: {chat_id}\n\n1. Stop the terminal (Ctrl+C)\n2. Change AUTHORIZED_CHAT_ID in titan_telegram.py to \"{chat_id}\"\n3. Restart the bot."
    print(f"\n[!] SETUP MODE TRIGGERED. Your Chat ID is: {chat_id}")
    await update.message.reply_text(msg)

async def auth(update: Update) -> bool:
    if str(update.effective_chat.id) != AUTHORIZED_CHAT_ID:
        print(f"\n[!] UNAUTHORIZED ACCESS ATTEMPT FROM ID: {update.effective_chat.id}")
        return False
    return True

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth(update): return
    await update.message.reply_text("🟢 TITAN Bridge Online.\nCommands:\n/status - Check pipeline\n/stop - Kill engine")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth(update): return
    
    conn = getattr(engine.stream, "connected", getattr(engine.stream, "is_connected", False))
    execs = getattr(engine, "_pipeline_executions", 0)
    status_text = "🟢 ONLINE" if conn else "🔴 OFFLINE"
    
    await update.message.reply_text(
        f"📊 **TITAN STATUS**\n"
        f"Network: {status_text}\n"
        f"Target: {engine.target_symbol}\n"
        f"Executions: {execs}"
    )

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth(update): return
    await update.message.reply_text("⚠️ Emergency shutdown initiated...")
    if engine:
        engine.stop()
    await update.message.reply_text("🛑 Engine stopped. Bridge going offline.")
    context.application.stop_running()

def main():
    global engine
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # --- SETUP MODE ---
    if AUTHORIZED_CHAT_ID == "REPLACE_WITH_YOUR_NUMERIC_CHAT_ID":
        print("\n[!] WARNING: AUTHORIZED_CHAT_ID is not set.")
        print("[*] Starting in SETUP MODE.")
        print("[*] Go to Telegram, open t.me/EshuTitan_bot, and send /start to get your ID.")
        app.add_handler(MessageHandler(filters.ALL, setup_mode))
        app.run_polling()
        return

    # --- LIVE TRADING MODE ---
    print("\n=== BOOTING TITAN ENGINE ===")
    mock_config = MagicMock()
    mock_config.broker.provider = "paper"
    mock_config.broker.paper_initial_cash = 1000000
    mock_config.trading.mode = "paper"
    
    engine = create_runtime_engine(mock_config)
    engine.target_symbol = "^NSEI"
    engine.start()

    print("\n=== IGNITING TELEGRAM BRIDGE ===")
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("stop", stop_command))

    print("[*] Bridge Online. Send /start to your bot on Telegram.")
    
    try:
        app.run_polling()
    except KeyboardInterrupt:
        print("\n[!] Manual terminal exit.")
    finally:
        print("[*] Securing shutdown...")
        if engine:
            engine.stop()
        print("=== SESSION ENDED ===")

if __name__ == "__main__":
    main()
'@