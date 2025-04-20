#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PySide6环境测试脚本
用于验证PySide6是否安装正确并能正常工作
"""

import sys
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QPushButton
from PySide6.QtCore import Qt

class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle('PySide6 测试窗口')
        self.resize(400, 200)
        
        # 创建布局
        layout = QVBoxLayout()
        
        # 添加标签
        label = QLabel('PySide6 环境测试成功！')
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet('font-size: 16pt;')
        layout.addWidget(label)
        
        # 添加按钮
        button = QPushButton('关闭')
        button.clicked.connect(self.close)
        layout.addWidget(button)
        
        # 设置布局
        self.setLayout(layout)
        
        # 居中显示
        self.center()
        
    def center(self):
        # 获取屏幕几何信息
        screen = QApplication.primaryScreen().availableGeometry()
        # 计算窗口居中位置
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        # 移动窗口
        self.move(x, y)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec()) 