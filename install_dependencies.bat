@echo off
REM 发票金额统计工具 - 依赖安装脚本
REM 安装PySide6和其他必要的依赖

REM 设置UTF-8代码页
chcp 65001
echo.

echo 正在检查Python...
python --version
if %ERRORLEVEL% NEQ 0 (
    echo 错误: 未找到Python，请先安装Python 3.6或更高版本
    pause
    exit /b 1
)

echo 设置代理环境变量...
set http_proxy=socks5://127.0.0.1:7890
set https_proxy=socks5://127.0.0.1:7890

echo 正在安装PySide6...
python -m pip install -U pip
python -m pip install pyside6

echo 正在安装其他依赖...
python -m pip install -r requirements.txt

echo.
if %ERRORLEVEL% EQU 0 (
    echo 依赖安装完成！
    echo 现在可以运行 python fapiao_gui.py 启动程序
    echo 或者运行 python test_pyside6.py 测试PySide6环境
) else (
    echo 安装过程中出现错误，错误代码: %ERRORLEVEL%
)

pause 