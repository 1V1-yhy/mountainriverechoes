@echo off
REM 苗族音乐播放器 - 直接运行(需已部署的 venv)
cd /d "%~dp0"
set MRE_ONLY_GROUP=e04
.\venv\Scripts\python.exe webui\miao_entry.py
pause
