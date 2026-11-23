@echo off
REM ============================================================================
REM bot/start_bot_daemon.bat
REM Starts the EPFO Intelligence Telegram Bot daemon in the background
REM ============================================================================

cd /d "C:\Users\acer\Documents\GitHub\epfo-intelligence-system"
echo [%date% %time%] Starting EPFO Telegram Bot Daemon...
python bot\telegram_bot.py
