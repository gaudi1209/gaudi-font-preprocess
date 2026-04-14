@echo off
title 高迪书法字库预处理工具 - 端口7500
chcp 65001 >nul
echo ========================================
echo   高迪书法字库预处理工具
echo ========================================
echo.

REM 切换到脚本所在目录
cd /d "%~dp0"

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

echo [启动] 正在启动Web服务...
echo.
echo ========================================
echo   访问地址: http://localhost:7500
echo   按 Ctrl+C 停止服务
echo ========================================
echo.

REM 启动Flask应用
python app.py

pause
