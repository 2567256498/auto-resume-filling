@echo off
REM ======================================================================
REM  浏览器自动化启动器（模板）／ Browser launcher for the autofill channel
REM
REM  作用：一条龙完成「关旧实例 → 起常驻 daemon → 带扩展参数开浏览器 → 自检」
REM  用法：把下面 4 个 __占位符__ 换成目标环境的真实值
REM        （取值见 SKILL.md §1.1 配置项 8）。
REM  用法：**每次使用前必须先完全关闭浏览器**——浏览器是单实例的，
REM        已经开着时再启动，新参数会被吞掉（扩展不加载）。
REM  注意：末尾会停在 "Press any key to continue"，**那个窗口不要关**
REM        ——常驻 daemon 依赖它存活。
REM  注意：扩展加载参数（--display-invisible-extension=true）是**必需开关**，
REM        不是可选优化；缺它通道命令必然 60 秒超时。
REM ======================================================================
title Browser Autofill Launcher

set "CLI=__CLI__"
set "BROWSER=__BROWSER__"
set "URL=__URL__"
set "LOG=__LOG__"

REM ---- 占位符未替换则中止：否则日志会写进名为 __LOG__ 的文件，静默失败 ----
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
