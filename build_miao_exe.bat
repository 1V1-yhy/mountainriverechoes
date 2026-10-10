@echo off
REM 苗族音乐播放器 - 一键打包为 miao_player.exe
cd /d "%~dp0"
.\venv\Scripts\python.exe build_miao_exe.py
pause
