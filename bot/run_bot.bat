@echo off
REM ============================================================================
REM bot/run_bot.bat
REM Starts the EPFO Private Knowledge Telegram Bot Daemon
REM ============================================================================

cd /d "C:\Users\acer\Documents\GitHub\epfo-intelligence-system"
echo [%date% %time%] Starting EPFO Intelligence Telegram Bot...
python bot\telegram_bot.py
pause
