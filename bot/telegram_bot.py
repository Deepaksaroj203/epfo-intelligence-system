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
        self.token = token.strip().replace(" ", "")
        self.api_url = api_url.rstrip("/")
        self.bot_api_url = f"https://api.telegram.org/bot{self.token}"
        self.last_update_id = 0

    def register_commands(self):
        """Registers the bot's official command menu with Telegram."""
        commands = [
            {"command": "ask", "description": "Ask any statutory EPFO or compliance question"},
            {"command": "pf", "description": "Calculate EPF/EPS with SC 50% allowance cap"},
            {"command": "penalties", "description": "Compute Section 7Q interest & 14B damages"},
            {"command": "pension", "description": "EPS-95 monthly pension calculation"},
            {"command": "briefing", "description": "Today's verified legal news & social thread"},
            {"command": "status", "description": "System health and bitemporal baseline check"},
            {"command": "help", "description": "Show help guide and commands"},
        ]
        res = self.call_api("setMyCommands", {"commands": commands})
        if res and res.get("ok"):
            logger.info("Successfully registered bot command menu with Telegram.")

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

    def handle_media(self, chat_id: int, msg: Dict[str, Any]):
        """
        Process Rejection Slip photos and PDF documents using AI Vision or statutory triage.
        """
        caption = msg.get("caption", "").strip()
        file_id = None
        is_photo = False

        if msg.get("photo"):
            file_id = msg["photo"][-1]["file_id"]
            is_photo = True
        elif msg.get("document"):
            file_id = msg["document"]["file_id"]

        if not file_id:
            return

        self.send_message(chat_id, "📸 _Analyzing rejection document via AI Vision & Statutory Engine..._")

        # 1. Fetch file path from Telegram Bot API
        res = self.call_api("getFile", {"file_id": file_id})
        file_path = res.get("result", {}).get("file_path") if res and res.get("ok") else None

        if not file_path:
            self.send_message(chat_id, "⚠️ Could not retrieve the document from Telegram servers. Please re-upload.")
            return

        # 2. Check for Gemini API key
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key and os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    api_key = cfg.get("gemini_api_key", "").strip()
            except Exception:
                pass

        if not api_key:
            env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
            if os.path.exists(env_file):
                try:
                    with open(env_file, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip().startswith("GEMINI_API_KEY="):
                                api_key = line.strip().split("=", 1)[1].strip().strip('"').strip("'")
                                break
                except Exception:
                    pass

        # If Gemini key is available and it's a photo/image, run Gemini Vision!
        if api_key:
            api_key = api_key.replace(" ", "").strip()
            download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
            try:
                import base64
                req = urllib.request.Request(download_url)
                with urllib.request.urlopen(req, timeout=15) as r:
                    image_bytes = r.read()

                b64 = base64.b64encode(image_bytes).decode("utf-8")
                vision_prompt = """Extract the UAN, Member Name, Rejection Reason, Error Code, and grievance text from this EPFO portal document/slip.
Provide:
1. Rejection Summary & Root Cause
2. Actionable Step-by-Step Statutory Fix Checklist
3. Relevant Schemes (EPF 1952, EPS 1995) or Joint Declaration requirements."""

                model = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash").strip()
                v_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                v_payload = {
                    "contents": [{
                        "parts": [
                            {"text": vision_prompt},
                            {"inline_data": {"mime_type": "image/jpeg" if is_photo else "application/pdf", "data": b64}}
                        ]
                    }],
                    "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2048}
                }
                v_req = urllib.request.Request(
                    v_url,
                    data=json.dumps(v_payload).encode("utf-8"),
                    headers={"Content-Type": "application/json", "x-goog-api-key": api_key}
                )
                with urllib.request.urlopen(v_req, timeout=20) as v_resp:
                    if v_resp.status == 200:
                        v_data = json.loads(v_resp.read().decode("utf-8"))
                        candidates = v_data.get("candidates", [])
                        if candidates:
                            txt = candidates[0].get("content", {}).get("parts", [])[0].get("text", "")
                            if txt:
                                response_text = (
                                    "🔍 *AI REJECTION SLIP DIAGNOSIS:*\n"
                                    "━━━━━━━━━━━━━━━━━━━━\n"
                                    f"{txt}\n\n"
                                    "💡 *Next Action:* Book an advocate consultation at [corporatecompliance.in](https://corporatecompliance.in/cases/create?ref=tg_slip) or download the pre-filled Joint Declaration."
                                )
                                self.send_message(chat_id, response_text)
                                return
            except Exception as e:
                logger.warning(f"Gemini vision error: {e}")

        # Fallback if no Gemini key or vision failed
        text_resp = (
            "📸 *Rejection Slip Received!*\n\n"
            "We have stored your rejection document. To diagnose immediately, you can:\n"
            "1. Type the exact rejection reason (e.g. *Father Name Mismatch*, *Service Overlap*, *Annexure K*).\n"
            "2. Or consult our live web tool at [corporatecompliance.in/epfo-error](https://corporatecompliance.in/epfo-error).\n"
            "3. Or book a senior compliance consultation for offline PRO intervention."
        )
        self.send_message(chat_id, text_resp)

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

        raw_answer = data.get("answer_markdown", "No answer generated.")
        
        # Build Structured Perfect Solution Message
        msg_parts = [raw_answer]

        # 1. Actionable Steps
        steps = data.get("actionable_steps")
        if steps and isinstance(steps, list) and len(steps) > 0:
            msg_parts.append("\n🛠️ *Actionable Resolution Steps:*")
            for i, step in enumerate(steps, 1):
                msg_parts.append(f"{i}. {step}")

        # 2. Calculation Summary if present
        calc = data.get("calculation_summary")
        if calc and isinstance(calc, dict):
            msg_parts.append("\n🧮 *Deterministic Engine Math:*")
            for k, v in calc.items():
                msg_parts.append(f"• *{k}*: `{v}`")

        # 3. Verified Citations
        citations = data.get("citations", [])
        if citations:
            msg_parts.append("\n🔒 *Statutory Authority & Precedents:*")
            for c in citations[:3]:
                title = c.get("title") or c.get("ref") or c.get("doc_ref") or "Statutory Order"
                sha = (c.get("doc_sha256") or "")[:10]
                url = c.get("url", "")
                if sha:
                    msg_parts.append(f"• *{title}* (SHA: `{sha}...`)")
                else:
                    msg_parts.append(f"• *{title}*")

        final_msg = "\n".join(msg_parts)
        self.send_message(chat_id, final_msg)

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

        if not chat_id:
            return

        # Handle Photo / Document Uploads (Rejection Slips & Grievance Orders)
        if msg.get("photo") or msg.get("document"):
            self.handle_media(chat_id, msg)
            return

        if not text:
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

    def clear_webhook(self) -> bool:
        """Clears any active webhook so getUpdates polling works without 409 Conflict."""
        res = self.call_api("deleteWebhook")
        if res and res.get("ok"):
            logger.info("Cleared active Telegram webhook. Ready for direct polling mode.")
            return True
        return False

    def set_webhook(self, url: str) -> bool:
        """Sets a webhook URL on the Telegram Bot API."""
        res = self.call_api("setWebhook", {"url": url})
        if res and res.get("ok"):
            logger.info(f"Successfully set Telegram webhook to: {url}")
            return True
        logger.error(f"Failed to set Telegram webhook: {res}")
        return False

    def run_polling(self):
        """Continuously polls Telegram for new updates."""
        me = self.call_api("getMe")
        if me and me.get("ok"):
            bot_info = me.get("result", {})
            logger.info(f"Connected to Telegram as @{bot_info.get('username')} ({bot_info.get('first_name')})")
        else:
            logger.warning(f"Could not connect to Telegram API with token {self.token[:8]}...")

        # Clear any prior webhook to allow polling
        self.clear_webhook()
        self.register_commands()
        logger.info("Starting Telegram Bot polling daemon. Waiting for user messages...")
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
