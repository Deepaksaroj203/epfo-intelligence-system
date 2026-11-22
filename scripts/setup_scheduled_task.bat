@echo off
REM ============================================================================
REM scripts/setup_scheduled_task.bat
REM Registers the EPFO Daily Intelligence Sweep in Windows Task Scheduler at 06:00 IST
REM ============================================================================

set TASK_NAME=EPFO_Daily_Intelligence_Sweep
set BATCH_PATH=C:\Users\acer\Documents\GitHub\epfo-intelligence-system\scripts\run_daily_sweep.bat

echo Registering Windows Scheduled Task: %TASK_NAME%...
schtasks /create /tn "%TASK_NAME%" /tr "\"%BATCH_PATH%\"" /sc daily /st 06:00 /f

if %ERRORLEVEL% EQU 0 (
    echo [SUCCESS] Scheduled task '%TASK_NAME%' registered to run daily at 06:00 AM IST.
    schtasks /query /tn "%TASK_NAME%"
) else (
    echo [NOTICE] If permission was denied, run this batch file as Administrator.
)
