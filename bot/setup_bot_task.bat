@echo off
REM ============================================================================
REM bot/setup_bot_task.bat
REM Registers the Telegram Bot Daemon in Windows Task Scheduler to start on logon
REM ============================================================================

set TASK_NAME=EPFO_Telegram_Bot_Daemon
set BATCH_PATH=C:\Users\acer\Documents\GitHub\epfo-intelligence-system\bot\start_bot_daemon.bat

echo Registering Windows Scheduled Task for Telegram Bot: %TASK_NAME%...
schtasks.exe /create /tn "%TASK_NAME%" /tr "\"%BATCH_PATH%\"" /sc onlogon /f

if %ERRORLEVEL% EQU 0 (
    echo [SUCCESS] Scheduled task '%TASK_NAME%' registered to start on user logon.
    schtasks.exe /query /tn "%TASK_NAME%"
) else (
    echo [NOTICE] If permission was denied, run this batch file as Administrator.
)
