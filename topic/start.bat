@echo off

cd /d D:\personal-blog\topic

call D:\anaconda3\Scripts\activate.bat topic

echo.
echo ========================================
echo       通用法规 AI 系统
echo ========================================
echo Python:
python --version
echo 环境:
echo %CONDA_DEFAULT_ENV%
echo.

python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

pause