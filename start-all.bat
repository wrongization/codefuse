@echo off
chcp 65001 >nul
echo ========================================
echo      CodeFuse 一键启动所有服务
echo ========================================
echo.

echo [1/2] 启动后端服务...
start "CodeFuse Backend" cmd /k "cd /d %~dp0backend && start.bat"

echo [等待] 等待后端服务启动...
timeout /t 3 /nobreak >nul

echo [2/2] 启动前端服务...
start "CodeFuse Frontend" cmd /k "cd /d %~dp0frontend && start.bat"

echo.
echo ========================================
echo ✓ 所有服务启动完成！
echo ========================================
echo.
echo 后端服务: http://localhost:8000
echo 前端服务: http://localhost:5173
echo API 文档: http://localhost:8000/docs
echo.
echo 提示: 后端和前端服务在独立窗口中运行
echo       关闭窗口或按 Ctrl+C 可停止服务
echo.
pause
