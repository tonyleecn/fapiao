@echo off
REM 发票金额统计工具打包脚本
REM 使用Nuitka打包为独立可执行文件（单文件模式）

REM 设置UTF-8代码页
chcp 65001
echo.

echo 设置代理环境变量...
set http_proxy=socks5://127.0.0.1:7890
set https_proxy=socks5://127.0.0.1:7890

echo 开始打包为单文件...
python.exe -m nuitka --standalone ^
    --enable-plugin=pyqt5 ^
    --onefile ^
    --windows-console-mode=disable ^
    --windows-icon-from-ico="icon.ico" ^
    --include-data-files="icon.ico=icon.ico" ^
    --windows-product-name="发票金额统计工具" ^
    --windows-file-version=1.0.0 ^
    --windows-product-version=1.0.0 ^
    --windows-file-description="发票金额统计工具" ^
    --assume-yes-for-downloads ^
    --output-filename="发票金额统计工具.exe" ^
    fapiao_gui.py

echo.
if %ERRORLEVEL% EQU 0 (
    echo 打包成功！
    echo 单文件可执行文件应该位于当前目录
) else (
    echo 打包失败，错误代码: %ERRORLEVEL%
)

pause 