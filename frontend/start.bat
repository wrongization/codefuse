@echo off
chcp 65001 >nul
echo ========================================
echo      CodeFuse 前端启动脚本
echo ========================================
echo.

REM 检查是否已安装依赖
if not exist "node_modules" (
    echo [提示] 检测到未安装依赖，正在安装...
    npm install --cache ./.npm-cache
    echo.
)

echo [启动] Vite 开发服务器 (http://localhost:5173)...
echo.
npm run dev

echo.
echo ========================================
echo 前端服务已停止
echo ========================================
pause
