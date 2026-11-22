"""
bot/test_chat_interactive.py
Simulates the Telegram Bot experience directly in your terminal.
Asks the live EPFO Intelligence Brain and prints the structured perfect solution.
"""

import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from bot.telegram_bot import EPFOTelegramBot


class MockTelegramBot(EPFOTelegramBot):
    """Subclass that prints formatted messages to console instead of network."""
    def __init__(self, api_url: str = "http://127.0.0.1:8000"):
        super().__init__(token="mock-terminal-token", api_url=api_url)

    def send_message(self, chat_id: int, text: str, parse_mode: str = "Markdown"):
        print("\n" + "=" * 70)
        print("🤖 [TELEGRAM BOT PERFECT SOLUTION]")
        print("=" * 70)
        print(text)
        print("=" * 70 + "\n")


def main():
    bot = MockTelegramBot()
    print("=" * 70)
    print("⚖️  EPFO INTELLIGENCE SYSTEM — TELEGRAM BOT TERMINAL SIMULATOR")
    print("=" * 70)
    print("Type any question about EPFO, claims, 50% cap, penalties, or rules.")
    print("Type 'exit' or 'quit' to stop.\n")

    test_queries = [
        "What is the statutory wage ceiling and 2026 revision?",
        "Calculate EPF for basic Rs 45000 and allowances Rs 15000 with 50% cap",
        "Form 19 rejected because member name does not match Aadhaar",
        "Calculate Section 7Q interest and Section 14B damages on Rs 2,50,000 late ECR delayed 45 days",
    ]

    print("Sample queries you can try:")
    for i, q in enumerate(test_queries, 1):
        print(f" [{i}] {q}")
    print()

    # If argument passed via CLI, run that single query
    if len(sys.argv) > 1:
        q = " ".join(sys.argv[1:])
        print(f"Query: {q}")
        bot.handle_ask(chat_id=101, query=q)
        return

    # Interactive prompt loop
    try:
        while True:
            query = input("Ask EPFO Brain > ").strip()
            if not query:
                continue
            if query.lower() in ["exit", "quit", "q"]:
                break
            bot.handle_ask(chat_id=101, query=query)
    except (KeyboardInterrupt, EOFError):
        print("\nExiting simulator.")


if __name__ == "__main__":
    main()
