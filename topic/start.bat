@echo off
chcp 65001 > nul

cd /d D:\personal-blog\topic
call D:\anaconda3\Scripts\activate.bat topic

set JAVA_BASE_URL=http://localhost:5173/workplace
set PORT=8765
set DEBUG=true

echo.
echo ========================================
echo       通用法规 AI 系统
echo ========================================
echo Python:
python --version
echo 环境:
echo %CONDA_DEFAULT_ENV%
echo.
echo Java接口地址: %JAVA_BASE_URL%
echo.

:: 用 python main.py 启动，会执行 if __name__ == "__main__"
python main.py

pause