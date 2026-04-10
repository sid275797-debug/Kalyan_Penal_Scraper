@echo on
setlocal
REM ======================================================
REM  Daily Auto Reels Builder (for 5AM Schedule)
REM ======================================================

cd /d "C:\Users\VCOM\Desktop\Kalyan_Penal_Scraper"

echo [INFO] Running reels_builder_all_markets.py ...
py -3 -u "C:\Users\VCOM\Desktop\Kalyan_Penal_Scraper\reels_builder_all_markets.py"

echo [DONE] Script finished with ExitCode=%errorlevel%
pause
endlocal