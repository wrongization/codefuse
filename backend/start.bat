@echo off
chcp 65001 >nul
echo ========================================
echo      CodeFuse 后端启动脚本
echo ========================================
echo.

REM 检查是否已安装依赖
if not exist ".venv" (
    echo [提示] 检测到未安装依赖，正在安装...
    uv sync
    echo.
)

echo [启动] FastAPI 服务器 (http://localhost:8000)...
echo.
uv run python -m app.main

echo.
echo ========================================
echo 后端服务已停止
echo ========================================
pause
