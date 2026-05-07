@echo off
chcp 65001 >nul
echo ========================================
echo      CodeFuse 一键停止所有服务
echo ========================================
echo.

echo [1/2] 停止后端服务...
cd /d %~dp0backend
call stop.bat

echo.
echo [2/2] 停止前端服务...
cd /d %~dp0frontend
call stop.bat

echo.
cd /d %~dp0
echo ========================================
echo ✓ 所有服务已停止！
echo ========================================
echo.
pause
