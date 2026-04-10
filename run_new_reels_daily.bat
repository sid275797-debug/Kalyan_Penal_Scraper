@echo off
title SattaMatka Reels Auto Runner

echo ======================================
echo   Starting Reels Render Script...
echo ======================================

cd /d "C:\Users\VCOM\Desktop\Kalyan_Penal_Scraper\sattamatka-reels\sattamatka-reels"

echo Running Node Script...
node scripts/render-all.mjs

echo.
echo ======================================
echo   Script Completed Successfully!
echo ======================================

pause