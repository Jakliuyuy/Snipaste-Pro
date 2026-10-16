@echo off
chcp 65001 >nul
echo ========================================================
echo   Snipaste 全功能增强版 (截图实时翻译) - Windows 打包
echo ========================================================
echo.
echo 请选择打包模式:
echo [1] 轻量极速版 (约 25MB，与官方原版体积持平，利用 Windows 10/11 内置原生 OCR)
echo [2] 完整离线 AI 版 (约 150MB，内嵌本地 PP-OCRv4 神经网络模型，完全离线高精度)
echo.
set /p choice=请输入选项 [1 或 2，默认 1]: 
if "%choice%"=="" set choice=1

echo.
echo 正在安装 PyInstaller 与基础依赖...
pip install pyinstaller PyQt6 requests pillow pynput

if "%choice%"=="1" (
    echo.
    echo 正在打包 [轻量极速版]...
    pyinstaller --onefile --noconsole --name=SnipastePro-Slim ^
        --add-data "snipaste/assets;snipaste/assets" ^
        --exclude-module cv2 ^
        --exclude-module onnxruntime ^
        --exclude-module rapidocr_onnxruntime ^
        --exclude-module numpy ^
        main.py
    echo.
    echo 打包完成！轻量版程序位于: dist\SnipastePro-Slim.exe (体积仅约 25MB)
) else (
    echo.
    echo 正在安装完整 AI 模型依赖库...
    pip install rapidocr_onnxruntime numpy
    echo.
    echo 正在打包 [完整离线 AI 版]...
    pyinstaller --onefile --noconsole --name=SnipastePro-Full ^
        --add-data "snipaste/assets;snipaste/assets" ^
        --collect-all rapidocr_onnxruntime ^
        main.py
    echo.
    echo 打包完成！完整版程序位于: dist\SnipastePro-Full.exe
)

echo.
pause
