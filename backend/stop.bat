@echo off
chcp 65001 >nul
echo ========================================
echo      CodeFuse 后端停止脚本
echo ========================================
echo.

echo [执行] 正在查找并停止 Python/Uvicorn 进程...

REM 停止所有包含 uvicorn 的 python 进程
for /f "tokens=2" %%i in ('tasklist ^| findstr /i "python.exe"') do (
    wmic process where "ProcessId=%%i and CommandLine like '%%uvicorn%%'" delete 2>nul
)

echo.
echo [完成] 后端服务已停止
echo ========================================
pause
