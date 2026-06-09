@echo off
cd /d "%~dp0"
python "%~dp0pig_pointer.py"
if errorlevel 1 pause
