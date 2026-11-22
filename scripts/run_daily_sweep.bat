@echo off
REM ============================================================================
REM scripts/run_daily_sweep.bat
REM Executes the EPFO Autonomous Daily Ingestion & Regression Sweep at 06:00 IST
REM ============================================================================

cd /d "C:\Users\acer\Documents\GitHub\epfo-intelligence-system"
echo [%date% %time%] Triggering EPFO Autonomous Daily Sweep...
python scripts\run_daily_sweep.py --dry-run
if %ERRORLEVEL% EQU 0 (
    echo [%date% %time%] Daily sweep completed successfully.
) else (
    echo [%date% %time%] Daily sweep encountered errors. Check logs\daily_sweep.log.
)
