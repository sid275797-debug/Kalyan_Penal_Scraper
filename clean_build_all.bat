@echo off
setlocal EnableDelayedExpansion
title Clean Build - FitFuel / SattaMatkaAI Projects

:: ============================================================
::  CLEAN BUILD SCRIPT - All Projects
::  Covers: Flutter | Python | Android | Node.js | Docker
::  Author: Chintu | SattaMatkaAI / FitFuel
:: ============================================================

set "ROOT=%~dp0"
set "LOG_FILE=%ROOT%clean_build_log_%date:~-4,4%%date:~-7,2%%date:~-10,2%.txt"
set "ERRORS=0"
set "STEP=0"

:: ---- ANSI COLOR CODES --------------------------------------
set "RED=[91m"
set "GRN=[92m"
set "YLW=[93m"
set "CYN=[96m"
set "WHT=[97m"
set "DIM=[90m"
set "RST=[0m"

cls
echo.
echo %CYN%  ██████╗██╗     ███████╗ █████╗ ███╗   ██╗%RST%
echo %CYN%  ██╔════╝██║     ██╔════╝██╔══██╗████╗  ██║%RST%
echo %CYN%  ██║     ██║     █████╗  ███████║██╔██╗ ██║%RST%
echo %CYN%  ██║     ██║     ██╔══╝  ██╔══██║██║╚██╗██║%RST%
echo %CYN%  ╚██████╗███████╗███████╗██║  ██║██║ ╚████║%RST%
echo %CYN%   ╚═════╝╚══════╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝%RST%
echo %WHT%         BUILD CACHE CLEANER v2.0%RST%
echo %DIM%  Flutter ^| Python ^| Android ^| Node.js ^| Docker%RST%
echo.
echo %CYN%  ════════════════════════════════════════════%RST%
echo %YLW%  Started : %date%  %time%%RST%
echo %YLW%  Root Dir: %ROOT%%RST%
echo %CYN%  ════════════════════════════════════════════%RST%
echo.

echo [%date% %time%] === CLEAN BUILD STARTED === > "%LOG_FILE%"
echo Root: %ROOT% >> "%LOG_FILE%"


:: ============================================================
:: STEP 1 — FLUTTER CLEAN
:: ============================================================
set /a STEP+=1
echo %CYN%  [%STEP%/6] FLUTTER CLEAN%RST%
echo %DIM%  ────────────────────────────────────────%RST%

set "FLUTTER_PROJ="
if exist "%ROOT%pubspec.yaml"                      set "FLUTTER_PROJ=%ROOT%"
if exist "%ROOT%flutter_app\pubspec.yaml"          set "FLUTTER_PROJ=%ROOT%flutter_app\"
if exist "%ROOT%sattamatkaai\pubspec.yaml"         set "FLUTTER_PROJ=%ROOT%sattamatkaai\"
if exist "%ROOT%app\pubspec.yaml"                  set "FLUTTER_PROJ=%ROOT%app\"

if "%FLUTTER_PROJ%"=="" (
    echo %YLW%  [SKIP] No Flutter pubspec.yaml found%RST%
    echo [%date% %time%] Flutter: SKIPPED >> "%LOG_FILE%"
    goto :PYTHON_CLEAN
)

pushd "%FLUTTER_PROJ%"
echo %DIM%  Project: %FLUTTER_PROJ%%RST%

if exist ".dart_tool"                    rd /s /q ".dart_tool"              && echo %GRN%  [OK] .dart_tool deleted%RST%
if exist "build"                         rd /s /q "build"                   && echo %GRN%  [OK] build\ deleted%RST%
if exist ".flutter-plugins"              del /f /q ".flutter-plugins"       && echo %GRN%  [OK] .flutter-plugins deleted%RST%
if exist ".flutter-plugins-dependencies" del /f /q ".flutter-plugins-dependencies"
if exist "pubspec.lock"                  del /f /q "pubspec.lock"           && echo %GRN%  [OK] pubspec.lock deleted%RST%

echo %DIM%  Running flutter clean ...%RST%
flutter clean >> "%LOG_FILE%" 2>&1
if !errorlevel! neq 0 (
    echo %RED%  [WARN] flutter clean had issues%RST%
    set /a ERRORS+=1
) else ( echo %GRN%  [OK] flutter clean done%RST% )

echo %DIM%  Running flutter pub get ...%RST%
flutter pub get >> "%LOG_FILE%" 2>&1
if !errorlevel! neq 0 (
    echo %RED%  [FAIL] flutter pub get failed%RST%
    set /a ERRORS+=1
) else ( echo %GRN%  [OK] flutter pub get done%RST% )

popd
echo [%date% %time%] Flutter: DONE >> "%LOG_FILE%"
echo.


:PYTHON_CLEAN
:: ============================================================
:: STEP 2 — PYTHON CACHE CLEAN
:: ============================================================
set /a STEP+=1
echo %CYN%  [%STEP%/6] PYTHON CACHE CLEAN%RST%
echo %DIM%  ────────────────────────────────────────%RST%

echo %DIM%  Removing __pycache__ folders ...%RST%
set "PC_COUNT=0"
for /d /r "%ROOT%" %%d in (__pycache__) do (
    if exist "%%d" (
        rd /s /q "%%d" 2>nul
        set /a PC_COUNT+=1
        echo [%date% %time%] pycache: %%d >> "%LOG_FILE%"
    )
)
echo %GRN%  [OK] Removed !PC_COUNT! __pycache__ folder(s)%RST%

echo %DIM%  Removing .pyc / .pyo files ...%RST%
set "PYC_COUNT=0"
for /r "%ROOT%" %%f in (*.pyc *.pyo) do (
    del /f /q "%%f" 2>nul
    set /a PYC_COUNT+=1
)
echo %GRN%  [OK] Removed !PYC_COUNT! compiled Python file(s)%RST%

if exist "%ROOT%.pytest_cache"   rd /s /q "%ROOT%.pytest_cache"  && echo %GRN%  [OK] .pytest_cache deleted%RST%
if exist "%ROOT%.mypy_cache"     rd /s /q "%ROOT%.mypy_cache"    && echo %GRN%  [OK] .mypy_cache deleted%RST%
if exist "%ROOT%.ruff_cache"     rd /s /q "%ROOT%.ruff_cache"    && echo %GRN%  [OK] .ruff_cache deleted%RST%

echo %DIM%  Clearing pip cache ...%RST%
pip cache purge >> "%LOG_FILE%" 2>&1
if !errorlevel! equ 0 ( echo %GRN%  [OK] pip cache purged%RST% ) else ( echo %YLW%  [SKIP] pip not found or no cache%RST% )

echo [%date% %time%] Python: DONE >> "%LOG_FILE%"
echo.


:: ============================================================
:: STEP 3 — ANDROID + GRADLE CLEAN
:: ============================================================
set /a STEP+=1
echo %CYN%  [%STEP%/6] ANDROID + GRADLE CLEAN%RST%
echo %DIM%  ────────────────────────────────────────%RST%

set "ANDROID_DIR="
if exist "%ROOT%android\gradlew.bat"                set "ANDROID_DIR=%ROOT%android"
if exist "%ROOT%sattamatkaai\android\gradlew.bat"   set "ANDROID_DIR=%ROOT%sattamatkaai\android"
if exist "%ROOT%flutter_app\android\gradlew.bat"    set "ANDROID_DIR=%ROOT%flutter_app\android"
if exist "%ROOT%app\android\gradlew.bat"            set "ANDROID_DIR=%ROOT%app\android"

if "%ANDROID_DIR%"=="" (
    echo %YLW%  [SKIP] No Android gradlew.bat found%RST%
    echo [%date% %time%] Android: SKIPPED >> "%LOG_FILE%"
) else (
    pushd "%ANDROID_DIR%"
    echo %DIM%  Project: %ANDROID_DIR%%RST%
    echo %DIM%  Running gradlew clean ...%RST%
    call gradlew.bat clean >> "%LOG_FILE%" 2>&1
    if !errorlevel! neq 0 (
        echo %RED%  [FAIL] gradlew clean failed%RST%
        set /a ERRORS+=1
    ) else ( echo %GRN%  [OK] gradlew clean done%RST% )
    if exist ".gradle"   rd /s /q ".gradle"  && echo %GRN%  [OK] local .gradle deleted%RST%
    if exist "build"     rd /s /q "build"    && echo %GRN%  [OK] Android build\ deleted%RST%
    popd
)

:: Global Gradle user cache
set "GRADLE_CACHE=%USERPROFILE%\.gradle\caches"
if exist "%GRADLE_CACHE%" (
    echo %DIM%  Clearing global Gradle user cache ...%RST%
    rd /s /q "%GRADLE_CACHE%" 2>nul
    echo %GRN%  [OK] Global Gradle cache cleared%RST%
)

echo [%date% %time%] Android+Gradle: DONE >> "%LOG_FILE%"
echo.


:: ============================================================
:: STEP 4 — NODE.JS CLEAN
:: ============================================================
set /a STEP+=1
echo %CYN%  [%STEP%/6] NODE.JS CLEAN%RST%
echo %DIM%  ────────────────────────────────────────%RST%

where node >nul 2>&1
if !errorlevel! neq 0 (
    echo %YLW%  [SKIP] Node.js not found in PATH%RST%
    echo [%date% %time%] Node.js: SKIPPED >> "%LOG_FILE%"
    goto :DOCKER_CLEAN
)

:: Remove all node_modules recursively
echo %DIM%  Removing node_modules folders ...%RST%
set "NM_COUNT=0"
for /d /r "%ROOT%" %%d in (node_modules) do (
    if exist "%%d" (
        rd /s /q "%%d" 2>nul
        set /a NM_COUNT+=1
        echo [%date% %time%] node_modules: %%d >> "%LOG_FILE%"
    )
)
echo %GRN%  [OK] Removed !NM_COUNT! node_modules folder(s)%RST%

:: Remove lock files (forces fresh dependency install)
set "LOCK_COUNT=0"
for /r "%ROOT%" %%f in (package-lock.json yarn.lock pnpm-lock.yaml) do (
    del /f /q "%%f" 2>nul
    set /a LOCK_COUNT+=1
)
if !LOCK_COUNT! gtr 0 echo %GRN%  [OK] Removed !LOCK_COUNT! lock file(s)%RST%

:: Remove build output and framework cache folders
echo %DIM%  Removing build/cache output folders ...%RST%
for /d /r "%ROOT%" %%d in (.next .nuxt dist out .cache .parcel-cache .turbo .svelte-kit) do (
    if exist "%%d" (
        rd /s /q "%%d" 2>nul
        echo %GRN%  [OK] %%d%RST%
    )
)

:: npm global cache
echo %DIM%  Clearing npm cache ...%RST%
npm cache clean --force >> "%LOG_FILE%" 2>&1
if !errorlevel! equ 0 ( echo %GRN%  [OK] npm cache cleared%RST% ) else ( echo %YLW%  [WARN] npm cache issue%RST% )

:: Yarn cache
where yarn >nul 2>&1
if !errorlevel! equ 0 (
    echo %DIM%  Clearing yarn cache ...%RST%
    yarn cache clean >> "%LOG_FILE%" 2>&1
    echo %GRN%  [OK] yarn cache cleared%RST%
)

:: pnpm cache
where pnpm >nul 2>&1
if !errorlevel! equ 0 (
    echo %DIM%  Clearing pnpm store ...%RST%
    pnpm store prune >> "%LOG_FILE%" 2>&1
    echo %GRN%  [OK] pnpm store pruned%RST%
)

echo [%date% %time%] Node.js: DONE >> "%LOG_FILE%"
echo.


:DOCKER_CLEAN
:: ============================================================
:: STEP 5 — DOCKER CLEAN
:: ============================================================
set /a STEP+=1
echo %CYN%  [%STEP%/6] DOCKER CLEAN%RST%
echo %DIM%  ────────────────────────────────────────%RST%

where docker >nul 2>&1
if !errorlevel! neq 0 (
    echo %YLW%  [SKIP] Docker not found in PATH%RST%
    echo [%date% %time%] Docker: SKIPPED - not installed >> "%LOG_FILE%"
    goto :WINDOWS_TEMP
)

docker info >nul 2>&1
if !errorlevel! neq 0 (
    echo %YLW%  [SKIP] Docker daemon not running — start Docker Desktop first%RST%
    echo [%date% %time%] Docker: SKIPPED - daemon not running >> "%LOG_FILE%"
    goto :WINDOWS_TEMP
)

:: Stop all running containers
echo %DIM%  Stopping running containers ...%RST%
set "CONT_COUNT=0"
for /f "tokens=*" %%i in ('docker ps -q 2^>nul') do (
    docker stop %%i >nul 2>&1
    set /a CONT_COUNT+=1
)
echo %GRN%  [OK] Stopped !CONT_COUNT! container(s)%RST%

:: Prune stopped containers
echo %DIM%  Pruning stopped containers ...%RST%
docker container prune -f >> "%LOG_FILE%" 2>&1
echo %GRN%  [OK] Containers pruned%RST%

:: Remove dangling images
echo %DIM%  Removing dangling images ...%RST%
docker image prune -f >> "%LOG_FILE%" 2>&1
echo %GRN%  [OK] Dangling images removed%RST%

:: Prune unused volumes
echo %DIM%  Pruning unused volumes ...%RST%
docker volume prune -f >> "%LOG_FILE%" 2>&1
echo %GRN%  [OK] Volumes pruned%RST%

:: Prune unused networks
echo %DIM%  Pruning unused networks ...%RST%
docker network prune -f >> "%LOG_FILE%" 2>&1
echo %GRN%  [OK] Networks pruned%RST%

:: Clear Docker build cache (most important!)
echo %DIM%  Clearing Docker build cache ...%RST%
docker builder prune -f >> "%LOG_FILE%" 2>&1
echo %GRN%  [OK] Docker build cache cleared%RST%

:: Show disk usage after clean
echo.
echo %DIM%  Docker disk usage after cleanup:%RST%
docker system df 2>nul

echo [%date% %time%] Docker: DONE >> "%LOG_FILE%"
echo.


:WINDOWS_TEMP
:: ============================================================
:: STEP 6 — WINDOWS TEMP FILES
:: ============================================================
set /a STEP+=1
echo %CYN%  [%STEP%/6] WINDOWS TEMP CACHE%RST%
echo %DIM%  ────────────────────────────────────────%RST%

echo %DIM%  Clearing %%TEMP%% ...%RST%
del /f /s /q "%TEMP%\*" >nul 2>&1
for /d %%d in ("%TEMP%\*") do rd /s /q "%%d" >nul 2>&1
echo %GRN%  [OK] User TEMP cleared%RST%

echo %DIM%  Clearing Windows Prefetch (admin required) ...%RST%
del /f /s /q "C:\Windows\Prefetch\*" >nul 2>&1
echo %GRN%  [OK] Prefetch attempted%RST%

echo [%date% %time%] Windows Temp: DONE >> "%LOG_FILE%"
echo.


:: ============================================================
:: FINAL REPORT
:: ============================================================
echo %CYN%  ════════════════════════════════════════════%RST%
echo %WHT%   CLEAN BUILD COMPLETE%RST%
echo %CYN%  ════════════════════════════════════════════%RST%
echo %YLW%  Finished : %date%  %time%%RST%
if !ERRORS! equ 0 (
    echo %GRN%  Status   : ALL STEPS PASSED  ✓%RST%
) else (
    echo %RED%  Status   : !ERRORS! step(s) had issues — check log%RST%
)
echo %DIM%  Log File : %LOG_FILE%%RST%
echo %CYN%  ════════════════════════════════════════════%RST%
echo.

echo [%date% %time%] === FINISHED (Errors: !ERRORS!) === >> "%LOG_FILE%"

pause
endlocal
