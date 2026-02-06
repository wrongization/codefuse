@echo off
chcp 65001 >nul
echo ========================================
echo      CodeFuse 前端停止脚本
echo ========================================
echo.

echo [执行] 正在查找并停止 Node/Vite 进程...

REM 停止所有包含 vite 的 node 进程
for /f "tokens=2" %%i in ('tasklist ^| findstr /i "node.exe"') do (
    wmic process where "ProcessId=%%i and CommandLine like '%%vite%%'" delete 2>nul
)

echo.
echo [完成] 前端服务已停止
echo ========================================
pause
