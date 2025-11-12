import PyInstaller.__main__
import os
import shutil

# 清理之前的构建目录
if os.path.exists('build'):
    shutil.rmtree('build')
if os.path.exists('dist'):
    shutil.rmtree('dist')

# 定义打包参数
PyInstaller.__main__.run([
    'funasr_tray_app.py',  # 您的主Python文件
    '--onefile',         # 打包为单个EXE文件
    '--windowed',        # 不显示控制台窗口
    '--icon=icon.ico',   # 设置EXE图标
    '--name=ASRServer',  # 输出EXE名称
    '--add-data=icon.ico;.',  # 包含图标文件
    '--add-data=funasr_wss_server.py;.',  # 包含服务器脚本
    '--hidden-import=pystray._win32',  # 确保包含pystray的Windows支持
    '--hidden-import=pystray._darwin',
    '--hidden-import=pystray._xorg',
    '--clean'  # 清理临时文件
])