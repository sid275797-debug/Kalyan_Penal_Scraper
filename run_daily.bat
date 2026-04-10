@echo off
REM ─────────────────────────────────────────────────────────────────────────────
REM 1) Run your full‐pipeline (all 4 scripts)
REM ─────────────────────────────────────────────────────────────────────────────
cd /d "C:\Users\VCOM\Desktop\Kalyan_Penal_Scraper"
python run_full_pipeline.py
if %errorlevel% neq 0 (
  echo ❌ run_full_pipeline.py failed
  exit /b %errorlevel%
)

REM ─────────────────────────────────────────────────────────────────────────────
REM 2) Push the updated JSON files into your GitHub‐Pages repo
REM ─────────────────────────────────────────────────────────────────────────────
cd /d "C:\Users\VCOM\Desktop\Kalyan_Penal_Scraper\sattaboss-data"
git pull origin main

copy /Y "..\multi_market_predictions_v3\assets\todays_predictions.json"  "data\todays_predictions.json"
copy /Y "..\multi_market_predictions_v3\assets\yesterday_results.json" "data\yesterday_results.json"

git add data\todays_predictions.json data\yesterday_results.json
git diff --cached --quiet || (
  git commit -m "chore: daily JSON update"
  git push origin main
)

echo ✅ Daily pipeline ran and JSON pushed.
