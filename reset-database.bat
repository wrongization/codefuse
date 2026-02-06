@echo off
chcp 65001 > nul
echo.
echo ========================================
echo   CodeFuse 数据库重置工具
echo ========================================
echo.
echo 此脚本将重置数据库到初始状态
echo.

cd /d "%~dp0backend"
uv run python reset_database.py

echo.
pause
