@echo off
setlocal
set "APP_DIR=%~dp0"
if not exist "%APP_DIR%logs" mkdir "%APP_DIR%logs"

where py >nul 2>nul
if errorlevel 1 goto try_python
py -3 "%APP_DIR%text-cleaner.pyz" --portable-dir "%APP_DIR%"
if not errorlevel 1 exit /b 0

:try_python
where python >nul 2>nul
if errorlevel 1 goto no_python
python "%APP_DIR%text-cleaner.pyz" --portable-dir "%APP_DIR%"
exit /b

:no_python
echo Python was not found. Install Python or run with an available Python command. > "%APP_DIR%logs\startup-error.log"
echo Python was not found.
exit /b 1
