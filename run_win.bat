@echo off
chcp 65001 >nul
echo 正在启动 Snipaste 全功能增强版 (含截图实时翻译)...
python main.py
if errorlevel 1 (
    echo.
    echo 启动出错，正在尝试自动安装依赖...
    pip install -r requirements.txt
    python main.py
)
pause
