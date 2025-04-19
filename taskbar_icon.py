import os 
import sys 
from PyQt5.QtGui import QIcon 
from PyQt5.QtWidgets import QApplication, QWidget 
 
def set_taskbar_icon(): 
    """获取应用程序图标路径，优先检查多种图标文件"""
    # 确定应用程序目录
    if getattr(sys, 'frozen', False): 
        # 运行已编译的EXE 
        app_dir = os.path.dirname(sys.executable) 
    else: 
        # 运行脚本
        app_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 按优先级顺序检查多种图标文件
    icon_candidates = [
        os.path.join(app_dir, 'icon.ico'),  # 优先使用icon.ico文件
        os.path.join(app_dir, 'fapiao_icon.ico'),
        os.path.join(app_dir, 'temp_icon.ico'),
        os.path.join(app_dir, 'icon.png')
    ]
    
    # 尝试每个可能的图标文件
    for icon_path in icon_candidates:
        if os.path.exists(icon_path): 
            print(f"任务栏图标使用: {icon_path}")  # 添加日志输出便于调试
            app_icon = QIcon(icon_path) 
            return app_icon 
    
    return None

def set_app_icon(app):
    """为整个应用程序设置图标"""
    app_icon = set_taskbar_icon()
    if app_icon:
        app.setWindowIcon(app_icon)
        return True
    return False 
