@echo off
chcp 65001 > nul

cd /d D:\personal-blog\topic

call D:\anaconda3\Scripts\activate.bat topic

:: ========================================
:: 环境变量
:: ========================================

set "JAVA_BASE_URL=http://localhost:1100"
set "PORT=8765"
set "DEBUG=true"

echo.
echo ========================================
echo       通用法规 AI 系统
echo ========================================
echo.

echo Python:
python --version

echo.
echo Conda环境:
echo %CONDA_DEFAULT_ENV%

echo.
echo Java接口地址:
echo %JAVA_BASE_URL%

echo.
echo Python服务端口:
echo %PORT%

echo.
echo ========================================
echo       正在启动 Python 服务
echo ========================================
echo.

:: 用 python main.py 启动
python main.py

echo.
echo ========================================
echo       Python 服务已退出
echo ========================================
echo.

pause