@echo off
echo Killing all Chrome processes...
taskkill /F /IM chrome.exe /T 2>nul
timeout /t 3 /nobreak

echo Starting Chrome with debug port...
start "" "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --profile-directory=Default

echo Waiting for Chrome to load...
timeout /t 5 /nobreak

echo Running script...
python "C:\Users\VCOM\Desktop\Kalyan_Penal_Scraper\fbpages.py"
pause