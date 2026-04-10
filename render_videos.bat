@echo off
title SattaMatkaAI Reel Engine
cd /d "C:\Users\VCOM\Desktop\Kalyan_Penal_Scraper\sattamatka-reels\sattamatka-reels"
echo ========================================
echo   SattaMatkaAI Video Render
echo   %date% %time%
echo ========================================
node scripts/render-all.mjs
echo.
echo Render finished at %time%
pause
