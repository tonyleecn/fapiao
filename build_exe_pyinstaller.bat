@echo off
REM 发票金额统计工具打包脚本(PyInstaller版本)
chcp 65001
echo.

echo 开始构建发票金额统计工具EXE...

REM 设置输出的exe文件名 (不需要在此处修改，直接在pyinstaller命令中使用)

REM 如果已存在spec文件，先删除
if exist "发票金额统计工具.spec" (
    del "发票金额统计工具.spec"
    echo 已删除旧的spec文件
)

REM 如果已存在icon文件，使用现有图标，否则使用默认图标
set ICON_PARAM=
if exist "icon.ico" (
    set ICON_PARAM=--icon=icon.ico
    echo 使用图标: icon.ico
) else if exist "fapiao_icon.ico" (
    set ICON_PARAM=--icon=fapiao_icon.ico
    echo 使用图标: fapiao_icon.ico
) else if exist "temp_icon.ico" (
    set ICON_PARAM=--icon=temp_icon.ico
    echo 使用图标: temp_icon.ico
)

REM 检查是否存在taskbar_icon.py文件
set TASKBAR_DATA=
if exist "taskbar_icon.py" (
    set TASKBAR_DATA=--add-data "taskbar_icon.py;."
    echo 添加任务栏图标模块: taskbar_icon.py
)

REM 执行PyInstaller命令生成可执行文件
echo 正在打包...
pyinstaller --noconfirm --onefile --windowed --clean ^
    --name "发票金额统计工具" ^
    %ICON_PARAM% ^
    --hidden-import pdfplumber.pdf ^
    --add-data "icon.ico;." ^
    %TASKBAR_DATA% ^
    fapiao_gui.py

echo.
if exist "dist\发票金额统计工具.exe" (
    echo 构建成功! 文件位置: dist\发票金额统计工具.exe
) else (
    echo 构建失败，请检查错误信息。
)

echo.
echo 按任意键退出...
pause >nul 