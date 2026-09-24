@echo off
REM ======================================================================
REM  Browser launcher for the autofill channel (template)
REM
REM  Purpose: one-shot "close old instance -> start resident daemon ->
REM           launch browser with extension flags -> self-check"
REM  Usage:   replace the 4 __placeholders__ below with real values
REM           (see SKILL.md 1.1, config item 8).
REM           Run this file ONLY after the browser is fully closed --
REM           it is single-instance: launching while already open swallows
REM           the new flags (extension will not load).
REM  NOTE:    keep ALL comments ASCII-only. cmd.exe parses .bat files in
REM           the ANSI codepage (GBK on Chinese Windows); non-ASCII text
REM           in this file gets misread and shreds lines into bogus
REM           commands (observed on this box: 2026-09-24).
REM  NOTE:    the window stops at "Press any key to continue" at the end
REM           -- DO NOT close it, the resident daemon needs it.
REM  NOTE:    the extension flag --display-invisible-extension=true is a
REM           REQUIRED switch, not an optional tweak; without it every
REM           channel command times out after 60s.
REM ======================================================================
title Browser Autofill Launcher

set "CLI=__CLI__"
set "BROWSER=__BROWSER__"
set "URL=__URL__"
set "LOG=__LOG__"

REM ---- guard: unreplaced placeholders abort the run (no silent failure) ----
if "%CLI%"=="__CLI__" goto NOCONFIG
if "%BROWSER%"=="__BROWSER__" goto NOCONFIG
if "%URL%"=="__URL__" goto NOCONFIG
if "%LOG%"=="__LOG__" goto NOCONFIG

for %%I in ("%BROWSER%") do set "BROWSER_NAME=%%~nxI"

echo [1/5] Closing any running browser instance... > "%LOG%"
taskkill /F /IM "%BROWSER_NAME%" >> "%LOG%" 2>&1
timeout /t 3 /nobreak >nul

echo [2/5] Starting resident daemon (skips browser checks)... >> "%LOG%"
"%CLI%" stop >> "%LOG%" 2>&1
"%CLI%" serve --daemon --call-mode qbotclaw >> "%LOG%" 2>&1
timeout /t 4 /nobreak >nul

echo [3/5] Starting browser with the built-in extension enabled... >> "%LOG%"
start "" "%BROWSER%" --display-invisible-extension=true --disable-infobars --start-maximized --x5use-automatic-in-tab --no-first-run --no-crashed-bubble-view --no-modal-dialogs --no-external-protocol-dialogs "%URL%"

echo [4/5] Waiting 15s for the extension to connect... >> "%LOG%"
timeout /t 15 /nobreak >nul

echo [5/5] Verifying... >> "%LOG%"
"%CLI%" status >> "%LOG%" 2>&1
findstr /C:"Connected clients: 1" "%LOG%" >nul
if %errorlevel%==0 (echo RESULT: OK - extension connected >> "%LOG%") else (echo RESULT: NOT-CONNECTED - check the steps above / browser may already have been running >> "%LOG%")
echo === DONE === >> "%LOG%"

echo.
echo Launcher finished. Check the log file for "RESULT: OK".
echo *** Keep this window OPEN - the resident daemon needs it. ***
pause >nul
exit /b 0

:NOCONFIG
echo.
echo [ABORT] Placeholders not replaced - nothing was launched.
echo         Fill __CLI__ / __BROWSER__ / __URL__ / __LOG__ first
echo         (values per SKILL.md 1.1, config item 8), then run this file again.
pause
exit /b 1
