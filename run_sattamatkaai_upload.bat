@echo off
cd /d C:\Users\VCOM\Desktop\Kalyan_Penal_Scraper

start "Meta Uploader" python meta_auto_uploader.py %1
start "FB Group Poster" python fb_group_poster.py %1

pause