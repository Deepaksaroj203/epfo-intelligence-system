# EPFO Intelligence System — Telegram Bot Assistant

Your private mobile knowledge assistant for statutory EPFO compliance, claims, penalties, and daily legal intelligence.

---

## 🚀 Quick Setup (3 Minutes)

1. Open Telegram and search for [@BotFather](https://t.me/BotFather).
2. Type `/newbot` and follow the instructions to create your private bot. Copy the generated API token (e.g., `123456789:ABCdefGhIJKlmNoPQRstuVWXyz`).
3. Create `bot/bot_config.json` (or copy from `bot/bot_config.example.json`):
   ```json
   {
     "telegram_bot_token": "YOUR_COPIED_BOT_TOKEN_HERE",
     "epfo_api_url": "http://127.0.0.1:8000"
   }
   ```
4. Double-click `bot/run_bot.bat` or run:
   ```bash
   python bot/telegram_bot.py
   ```
5. Open your bot on Telegram and send `/start`!

---

## 📱 Mobile Commands & Patterns

| Command | Description | Example |
|---|---|---|
| `/ask <question>` | Ask any statutory question (rules, claims, KYC, case law) | `/ask Why was Form 19 rejected for name mismatch?` |
| `/pf <basic> [allowances]` | Integer-paise EPF/EPS breakdown with SC 50% cap | `/pf 45000 15000` |
| `/penalties <arrears> <days>` | Section 7Q interest, 14B damages, and 7O deposit | `/penalties 250000 45` |
| `/pension <years> <wages>` | EPS-95 monthly pension projection + bonus factor | `/pension 24 15000` |
| `/briefing` | Today's legally verified social media briefing | `/briefing` |
| `/status` | Gateway health & cryptographic hash-chain check | `/status` |
| *(Any plain text)* | Automatically treated as an `/ask` query | `What is the wage ceiling shift in 2026?` |

---

## 🔒 Security & Architecture
- **Zero LLM Math**: All mathematical calculations execute via Stage 2 deterministic rule engines in integer paise.
- **Citation Locked**: All answers include verifiable statutory circulars, gazettes, and court precedents with SHA-256 hashes.
- **Privacy-First**: No personal UAN, Aadhaar, PAN, or phone numbers are ever stored.
