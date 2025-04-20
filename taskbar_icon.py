import os 
import sys 
from PySide6.QtGui import QIcon 
from PySide6.QtWidgets import QApplication, QWidget 
 
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

# 在窗口显示后设置任务栏图标的辅助方法
def ensure_taskbar_icon(window, icon_path=None):
    """
    确保窗口在任务栏上显示正确的图标
    在窗口.show()之后调用此函数
    """
    if not icon_path:
        # 寻找图标文件
        app_icon = set_taskbar_icon()
        if not app_icon:
            return False
    else:
        if not os.path.exists(icon_path):
            return False
        app_icon = QIcon(icon_path)
    
    # 设置窗口图标
    window.setWindowIcon(app_icon)
    
    # 强制刷新任务栏图标
    if sys.platform == 'win32':
        try:
            # 获取窗口的本地句柄
            window_id = window.winId()
            if window_id:
                # 发送刷新消息
                window.setWindowIcon(app_icon)  # 再次设置图标可能会触发刷新
                
                # 可选: 使用更激进的方法强制刷新
                window.hide()
                window.show()
                return True
        except Exception as e:
            print(f"刷新任务栏图标时出错: {e}")
    
    return False 
