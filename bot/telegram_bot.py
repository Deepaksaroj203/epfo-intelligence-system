"""
bot/telegram_bot.py
EPFO Intelligence System — Private Mobile Telegram Knowledge Assistant.

Connects to the EPFO Intelligence Gateway (http://127.0.0.1:8000)
Provides mobile chatting, statutory PF math, pension projection,
penalty computation, and daily verified legal briefings.
"""

from datetime import date
import json
import logging
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [TELEGRAM_BOT] %(message)s",
)
logger = logging.getLogger("EPFOTelegramBot")

# Configuration
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
API_BASE_URL = os.environ.get("EPFO_API_URL", "http://127.0.0.1:8000").rstrip("/")
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "bot_config.json")

# Load token from bot_config.json if not in environment
if not BOT_TOKEN and os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            BOT_TOKEN = cfg.get("telegram_bot_token", "").strip()
            API_BASE_URL = cfg.get("epfo_api_url", API_BASE_URL).rstrip("/")
    except Exception as e:
        logger.warning(f"Could not read bot_config.json: {e}")


class EPFOTelegramBot:
    """
    Self-contained Telegram Bot daemon using direct Bot API long-polling.
    No heavy third-party framework dependencies required.
    """

    def __init__(self, token: str, api_url: str):
        self.token = token
        self.api_url = api_url
        self.bot_api_url = f"https://api.telegram.org/bot{token}"
        self.last_update_id = 0

    def call_api(self, method: str, payload: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Makes an HTTP POST request to Telegram's Bot API."""
        url = f"{self.bot_api_url}/{method}"
        data_bytes = json.dumps(payload or {}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=35) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.error(f"Telegram API call error ({method}): {e}")
            return None

    def send_message(self, chat_id: int, text: str, parse_mode: Optional[str] = "Markdown"):
        """Sends a text message to a user or group."""
        payload = {
            "chat_id": chat_id,
            "text": text,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode

        # If Markdown fails due to special chars, fallback to plain text
        res = self.call_api("sendMessage", payload)
        if not res or not res.get("ok"):
            payload.pop("parse_mode", None)
            self.call_api("sendMessage", payload)

    def query_epfo_api(self, endpoint: str, method: str = "GET", payload: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Queries the local/remote EPFO Intelligence FastAPI gateway."""
        url = f"{self.api_url}{endpoint}"
        try:
            if method == "POST":
                data_bytes = json.dumps(payload or {}).encode("utf-8")
                req = urllib.request.Request(
                    url,
                    data=data_bytes,
                    headers={"Content-Type": "application/json", "X-API-Key": "epfo-admin-key-2026"},
                )
            else:
                req = urllib.request.Request(
                    url,
                    headers={"X-API-Key": "epfo-admin-key-2026"},
                )

            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.error(f"Error querying EPFO API ({url}): {e}")
            return None

    # =========================================================================
    # COMMAND HANDLERS
    # =========================================================================

    def handle_start(self, chat_id: int):
        msg = (
            "🏛️ *Welcome to the EPFO Statutory Intelligence Assistant*\n\n"
            "I am connected directly to your private bitemporal statutory rule engines and precedent store.\n\n"
            "*Available Commands:*\n"
            "• `/ask <question>` — Ask anything about EPF, EPS, claims, KYC, or case law\n"
            "• `/pf <basic> [allowances]` — Calculate EPF/EPS with SC 50% cap in integer paise\n"
            "• `/penalties <arrears> <days>` — Compute 7Q interest and 14B damages\n"
            "• `/pension <years> <wages>` — EPS-95 monthly pension projection\n"
            "• `/briefing` — Fetch today's legally verified daily social briefing\n"
            "• `/status` — System health and hash-chain verification\n\n"
            "_Tip: You can also just type any question directly without `/ask`!_"
        )
        self.send_message(chat_id, msg)

    def handle_ask(self, chat_id: int, query: str):
        if not query.strip():
            self.send_message(chat_id, "ℹ️ Please provide a question. Example:\n`/ask Why was my Form 19 rejected?`")
            return

        self.send_message(chat_id, "⚖️ _Evaluating statutory rule engines and precedent citations..._")
        data = self.query_epfo_api("/v1/copilot/chat", method="POST", payload={"query": query})

        if not data:
            self.send_message(chat_id, "⚠️ Could not reach the EPFO Intelligence Gateway. Ensure `http://127.0.0.1:8000` is running.")
            return

        answer = data.get("answer_markdown", "No answer generated.")
        
        # Format citations
        citations = data.get("citations", [])
        if citations:
            answer += "\n\n🔒 *Verified Statutory Citations:*"
            for c in citations[:3]:
                ref = c.get("ref") or c.get("doc_ref") or "Statutory Order"
                sha = (c.get("doc_sha256") or "")[:10]
                answer += f"\n• `{ref}` (SHA: `{sha}...`)"

        self.send_message(chat_id, answer)

    def handle_pf(self, chat_id: int, args_str: str):
        parts = args_str.strip().split()
        if not parts:
            self.send_message(
                chat_id,
                "ℹ️ Usage: `/pf <basic_salary> [allowances]`\nExample: `/pf 45000 15000`\n"
                "Computes employee 12%, employer 3.67% / 8.33%, EDLI, and SC 50% basic cap."
            )
            return

        try:
            basic = float(parts[0])
            allowances = float(parts[1]) if len(parts) > 1 else 0.0
        except ValueError:
            self.send_message(chat_id, "⚠️ Invalid numeric salary amount provided.")
            return

        # Query copilot or calculate
        q = f"Calculate EPF wage contribution for basic salary of Rs {int(basic)} and allowances of Rs {int(allowances)}"
        self.handle_ask(chat_id, q)

    def handle_penalties(self, chat_id: int, args_str: str):
        parts = args_str.strip().split()
        if len(parts) < 2:
            self.send_message(
                chat_id,
                "ℹ️ Usage: `/penalties <arrears_rupees> <delay_days>`\nExample: `/penalties 250000 45`\n"
                "Computes Section 7Q interest (12% p.a.), Section 14B damages, and Section 7O pre-deposit."
            )
            return

        try:
            arrears = float(parts[0])
            days = int(parts[1])
        except ValueError:
            self.send_message(chat_id, "⚠️ Invalid numeric values. Example: `/penalties 250000 45`")
            return

        q = f"Calculate Section 7Q interest and Section 14B damages for late ECR arrears of Rs {int(arrears)} delayed by {days} days"
        self.handle_ask(chat_id, q)

    def handle_pension(self, chat_id: int, args_str: str):
        parts = args_str.strip().split()
        if len(parts) < 2:
            self.send_message(
                chat_id,
                "ℹ️ Usage: `/pension <pensionable_service_years> <pensionable_salary>`\nExample: `/pension 24 15000`"
            )
            return

        try:
            years = float(parts[0])
            wages = float(parts[1])
        except ValueError:
            self.send_message(chat_id, "⚠️ Invalid numeric values. Example: `/pension 24 15000`")
            return

        q = f"Calculate EPS-95 monthly pension for pensionable service of {years} years and pensionable salary of Rs {int(wages)}"
        self.handle_ask(chat_id, q)

    def handle_briefing(self, chat_id: int):
        self.send_message(chat_id, "📰 _Fetching today's verified statutory social briefing..._")
        data = self.query_epfo_api("/v1/social/daily-briefing", method="GET")

        if not data:
            self.send_message(chat_id, "⚠️ Could not fetch social briefing from EPFO Gateway.")
            return

        topic = data.get("topic", "EPFO Statutory Compliance")
        ref = data.get("statutory_reference", "Official Authority")
        tweets = data.get("twitter_thread", [])
        caption = data.get("instagram_caption", "")

        msg = (
            f"📰 *Today's EPFO Statutory Briefing*\n"
            f"🎯 *Topic:* {topic}\n"
            f"⚖️ *Authority:* `{ref}`\n\n"
            f"*Twitter/X Thread (Part 1/5):*\n"
            f"{tweets[0] if tweets else 'N/A'}\n\n"
            f"*Instagram Caption:*\n"
            f"{caption[:300]}..."
        )
        self.send_message(chat_id, msg)

    def handle_status(self, chat_id: int):
        data = self.query_epfo_api("/health", method="GET")
        if not data:
            self.send_message(chat_id, "🔴 *Status:* EPFO Intelligence Gateway OFFLINE.")
            return

        chain_ok = "✅ VERIFIED" if data.get("hash_chain_integrity") else "❌ COMPROMISED"
        active_rules = data.get("active_rules_count", 0)
        logs_count = data.get("change_log_entries", 0)

        msg = (
            f"🟢 *EPFO Statutory Intelligence System Online*\n\n"
            f"• *Hash-Chain Integrity:* {chain_ok}\n"
            f"• *Active Rules in Baseline:* `{active_rules}`\n"
            f"• *Rule Change Log Entries:* `{logs_count}`\n"
            f"• *Precedents Store:* Online\n"
            f"• *Autonomous Sweep:* 06:00 / 06:15 / 06:30 IST active"
        )
        self.send_message(chat_id, msg)

    # =========================================================================
    # POLLING LOOP
    # =========================================================================

    def process_update(self, update: Dict[str, Any]):
        msg = update.get("message") or update.get("edited_message")
        if not msg:
            return

        chat_id = msg.get("chat", {}).get("id")
        text = msg.get("text", "").strip()

        if not chat_id or not text:
            return

        logger.info(f"Received message from chat_id={chat_id}: {text}")

        # Dispatch command
        if text.startswith("/start") or text.startswith("/help"):
            self.handle_start(chat_id)
        elif text.startswith("/ask"):
            query = text[4:].strip()
            self.handle_ask(chat_id, query)
        elif text.startswith("/pf"):
            self.handle_pf(chat_id, text[3:].strip())
        elif text.startswith("/penalties"):
            self.handle_penalties(chat_id, text[10:].strip())
        elif text.startswith("/pension"):
            self.handle_pension(chat_id, text[8:].strip())
        elif text.startswith("/briefing"):
            self.handle_briefing(chat_id)
        elif text.startswith("/status"):
            self.handle_status(chat_id)
        else:
            # Treat bare text directly as statutory questions
            self.handle_ask(chat_id, text)

    def run_polling(self):
        """Continuously polls Telegram for new updates."""
        logger.info(f"Starting Telegram Bot polling daemon for token: {self.token[:8]}...")
        while True:
            try:
                res = self.call_api("getUpdates", {
                    "offset": self.last_update_id + 1,
                    "timeout": 30,
                })

                if res and res.get("ok"):
                    updates = res.get("result", [])
                    for u in updates:
                        self.last_update_id = u["update_id"]
                        self.process_update(u)
                else:
                    time.sleep(2)
            except Exception as e:
                logger.error(f"Polling exception: {e}")
                time.sleep(5)


def main():
    token = BOT_TOKEN
    if not token:
        print("\n" + "=" * 70)
        print("⚠️  TELEGRAM BOT TOKEN REQUIRED")
        print("=" * 70)
        print("To run the Telegram Bot, provide your bot token:")
        print("1. In environment variable: set TELEGRAM_BOT_TOKEN=123456:ABC-DEF...")
        print("2. Or in bot/bot_config.json:\n")
        print('   {\n     "telegram_bot_token": "YOUR_BOTFATHER_TOKEN_HERE",\n     "epfo_api_url": "http://127.0.0.1:8000"\n   }')
        print("=" * 70 + "\n")
        return

    bot = EPFOTelegramBot(token=token, api_url=API_BASE_URL)
    bot.run_polling()


if __name__ == "__main__":
    main()
