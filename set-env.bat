@echo off
chcp 65001 >nul
echo ========================================
echo      CodeFuse 一键配置环境
echo ========================================
echo.

echo [1/2] 配置后端服务环境变量...
start "CodeFuse Backend" cmd /k "cd /d %~dp0backend && set_env.bat"

echo [等待] 等待配置后端服务环境变量完成...
timeout /t 10 /nobreak >nul

echo [2/2] 配置前端服务环境变量...
start "CodeFuse Frontend" cmd /k "cd /d %~dp0frontend && set_env.bat"

echo.
echo ========================================
echo ✓ 所有环境变量配置完成
echo ========================================
pause