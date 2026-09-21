import json
import logging
import os
import threading
import time

import requests
import zmq
from dotenv import load_dotenv

from titan.runtime.local_transport import LocalTransport

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("CRITICAL: TELEGRAM_BOT_TOKEN is missing from .env file!")

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("TITAN_TG")

class TitanTelegramBridge:
    def __init__(self):
        self.last_update_id = 0
        self._start_zmq_listener()

    def _start_zmq_listener(self):
        """ZeroMQ SUB listener bound to the Daemon's event publisher for autonomous trade alerts."""
        def zmq_loop():
            context = zmq.Context()
            socket = context.socket(zmq.SUB)
            socket.connect("tcp://127.0.0.1:55556")
            socket.setsockopt_string(zmq.SUBSCRIBE, "paper.trade")
            
            logger.info("ZMQ Trade Event Listener Active on tcp://127.0.0.1:55556")
            
            while True:
                try:
                    topic, payload = socket.recv_multipart(flags=zmq.NOBLOCK)
                    data = json.loads(payload.decode('utf-8'))
                    
                    msg = (
                        f"🚨 *TRADE EXECUTED* 🚨\n"
                        f"  *Symbol*: `{data.get('symbol', 'UNKNOWN')}`\n"
                        f"  *Action*: `{data.get('action', 'N/A')}`\n"
                        f"  *Quantity*: `{data.get('quantity', 0)}`\n"
                        f"  *Entry Price*: `INR {data.get('price', 0):,.2f}`\n"
                    )
                    self._broadcast(msg)
                except zmq.Again:
                    time.sleep(0.5)
                except Exception as e:
                    logger.error(f"ZMQ Listener Error: {e}")
                    time.sleep(1)
                    
        t = threading.Thread(target=zmq_loop, daemon=True)
        t.start()

    def _broadcast(self, msg):
        """Pushes alerts autonomously to all registered chat IDs."""
        if os.path.exists("tg_chat_ids.txt"):
            with open("tg_chat_ids.txt", "r") as f:
                for cid in f:
                    self.send_message(cid.strip(), msg)

    def _register_chat_id(self, chat_id):
        """Remembers chat IDs so the bot can autonomously push alerts without being prompted."""
        chat_id_str = str(chat_id)
        chat_ids = set()
        if os.path.exists("tg_chat_ids.txt"):
            with open("tg_chat_ids.txt", "r") as f:
                chat_ids = {x.strip() for x in f if x.strip()}
        if chat_id_str not in chat_ids:
            chat_ids.add(chat_id_str)
            with open("tg_chat_ids.txt", "w") as f:
                f.write("\n".join(chat_ids))

    def send_message(self, chat_id, text):
        try:
            url = f"{BASE_URL}/sendMessage"
            payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")

    def handle_command(self, chat_id, text):
        self._register_chat_id(chat_id)
        parts = text.strip().split()
        cmd = parts[0].lower()
        
        client = LocalTransport()

        if cmd in ["/start", "/help"]:
            msg = (
                "🛡️ *TITAN Phase 4 Command Center*\n\n"
                "*Core Controls:*\n"
                "  `/status` - Query live background daemon telemetry\n"
                "  `/ignite` - Force connect the market data stream\n"
                "  `/watchlist` - View active multi-symbol array\n"
                "  `/trades` - View paper trading PnL and execution metrics\n"
                "  `/stop` - Stop the daemon gracefully\n\n"
                "*Intelligence & Management:*\n"
                "  `/logs` - Read recent centralized system logs\n"
            )
            self.send_message(chat_id, msg)

        elif cmd == "/status":
            try:
                report = client.status()
                is_running = report.runtime_status.name == "RUNNING"
                status_symbol = "🟢 ONLINE" if is_running else "🔴 OFFLINE"
                
                stream_conn = report.market.stream_connected
                stream_symbol = "🟢 CONNECTED" if stream_conn else "🔴 DISCONNECTED"
                
                syms = list(report.market.symbols)
                execs = report.scheduler.pipeline_executions

                msg = (
                    f"📡 *TITAN Daemon Telemetry*\n"
                    f"  *Daemon*: {status_symbol}\n"
                    f"  *Market Stream*: {stream_symbol}\n"
                    f"  *Watchlist*: `{syms}`\n"
                    f"  *Pipeline Executions*: `{execs}`\n"
                )
                self.send_message(chat_id, msg)
            except Exception as e:
                self.send_message(chat_id, f"⚠️ *Daemon unreachable*: `{e}`")

        elif cmd == "/watchlist":
            try:
                report = client.status()
                syms = list(report.market.symbols)
                if syms:
                    self.send_message(chat_id, f"📋 *Active Watchlist*\n`{syms}`")
                else:
                    self.send_message(chat_id, "⚠️ *Watchlist is empty.* (Stream might be disconnected or awaiting injection)")
            except Exception as e:
                self.send_message(chat_id, f"⚠️ *Daemon unreachable*: `{e}`")

        elif cmd == "/ignite":
            try:
                # The engine is managed by the background daemon process. 
                # We verify the IPC connection instead of trying to boot a detached process.
                report = client.status()
                is_running = report.runtime_status.name == "RUNNING"
                if is_running:
                    self.send_message(chat_id, "🚀 *Engine is online and active.* Stream polling is governed by the background daemon.")
                else:
                    self.send_message(chat_id, "⚠️ *Engine is offline.* Start it via PowerShell using `titan paper start`.")
            except Exception as e:
                self.send_message(chat_id, f"⚠️ *Ignition check failed*: `{e}`")

        elif cmd == "/quote":
            try:
                import yfinance as yf
                # If user types "/quote IDEA.NS", use IDEA.NS. Otherwise, default to the first symbol in the active watchlist.
                report = client.status()
                syms = list(report.market.symbols)
                target = parts[1].upper() if len(parts) > 1 else (syms[0] if syms else "^NSEI")
                
                ticker = yf.Ticker(target)
                price = ticker.fast_info.get("lastPrice")
                
                if price is not None:
                    self.send_message(chat_id, f"📈 *Market Snapshot ({target})*\n  *Last Price*: `INR {price:,.2f}`")
                else:
                    self.send_message(chat_id, f"⚠️ *No live price data found for {target}*")
            except Exception as e:
                self.send_message(chat_id, f"⚠️ *Failed to fetch quote*: `{e}`")
                
        elif cmd == "/trades":
            try:
                raw = client.paper_status()
                flat = {**raw.get("session", {}), **raw.get("portfolio", {}), **raw.get("performance", {})}
                pnl = flat.get("total_pnl", 0.0)
                win_rate = flat.get("win_rate", 0.0)
                total = flat.get("total_orders_count", 0)

                msg = (
                    f"📊 *Paper Trades & PnL*\n"
                    f"  *Total PnL*: `INR {pnl:,.2f}`\n"
                    f"  *Win Rate*: `{win_rate:.1f}%`\n"
                    f"  *Total Orders*: `{total}`\n"
                )
                self.send_message(chat_id, msg)
            except Exception as e:
                self.send_message(chat_id, f"⚠️ *Trades unreachable*: `{e}`")

        elif cmd == "/stop":
            try:
                client.stop()
                self.send_message(chat_id, "🛑 *Daemon halt sequence initiated.*")
            except Exception as e:
                self.send_message(chat_id, f"⚠️ *Error halting daemon*: `{e}`")

        elif cmd == "/logs":
            try:
                log_path = "./logs/titan.log"
                if os.path.exists(log_path):
                    with open(log_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    recent = "".join(lines[-5:]) if lines else "Log file is empty."
                    self.send_message(chat_id, f"📝 *Recent System Logs*\n```\n{recent}\n```")
                else:
                    self.send_message(chat_id, "⚠️ *Log file not found at ./logs/titan.log*")
            except Exception as e:
                self.send_message(chat_id, f"⚠️ *Failed to read logs*: `{e}`")

    def run(self):
        logger.info("Connecting to Telegram Bot gateway persistently...")
        while True:
            try:
                url = f"{BASE_URL}/getUpdates?offset={self.last_update_id + 1}&timeout=30"
                response = requests.get(url, timeout=35).json()

                if "result" in response:
                    for update in response["result"]:
                        self.last_update_id = update["update_id"]
                        if "message" in update and "text" in update["message"]:
                            chat_id = update["message"]["chat"]["id"]
                            text = update["message"]["text"]
                            logger.info(f"Incoming command from {chat_id}: {text}")
                            self.handle_command(chat_id, text)

            except requests.exceptions.RequestException:
                time.sleep(3)
            except Exception as e:
                logger.error(f"Unexpected loop exception: {e}")
                time.sleep(2)

if __name__ == "__main__":
    bot = TitanTelegramBridge()
    bot.run()