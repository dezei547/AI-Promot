import os
import subprocess
import sys
from pathlib import Path
import pystray
from PIL import Image
import psutil
import logging
from logging.handlers import RotatingFileHandler
import threading
import time

class ServerManager:
    def __init__(self):
        self.process = None
        self.tray_icon = None
        self.log_file = "Log.txt"
        self.should_stop = False
        self.server_running = False
        self.menu_item_start_stop = None
        self.output_threads = []
        
        # 初始化日志系统
        self.setup_logging()
        
        # 设置代码页为UTF-8
        os.system("chcp 65001")
        self.logger.info("设置控制台编码为UTF-8")
        
        # 设置环境变量
        self.conda_path = Path("./Miniconda3")
        os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
        os.environ["HF_HOME"] = str(Path.cwd() / "hf_download")
        os.environ["MODELSCOPE_CACHE"] = str(Path.cwd() / "hf_download")
        os.environ["disable_update"] = "True"
        self.logger.info("环境变量设置完成")

    def setup_logging(self):
        """配置日志系统，同时输出到控制台和文件"""
        # 清空之前的日志文件
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write("")
        
        # 创建logger
        self.logger = logging.getLogger('ASR_Server')
        self.logger.setLevel(logging.INFO)
        
        # 创建文件handler，使用RotatingFileHandler防止日志过大
        file_handler = RotatingFileHandler(
            self.log_file, 
            maxBytes=5*1024*1024,  # 5MB
            backupCount=2,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        
        # 创建控制台handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 创建formatter并添加到handler
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # 添加handler到logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def start_server(self):
        try:
            self.logger.info("正在启动ASR服务器...")
            
            # 激活conda环境
            activate_script = self.conda_path / "Scripts" / "activate.bat"
            activate_cmd = f'call "{activate_script}"'
            
            # 构建运行funasr_wss_server.py的命令
            server_cmd = (
                "python funasr_wss_server.py "
                "--port 10096 --certfile \"\" "
                "--asr_model iic/SenseVoiceSmall --asr_model_revision master "
                "--asr_model_online iic/SenseVoiceSmall --asr_model_online_revision master"
            )
            
            # 在激活conda环境后运行服务器命令
            full_cmd = f'cmd /c "{activate_cmd} && {server_cmd}"'
            
            # 启动进程并捕获输出
            self.process = subprocess.Popen(
                full_cmd,
                shell=True,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=1
            )
            
            self.server_running = True
            self.should_stop = False
            self.logger.info(f"服务器已启动，PID: {self.process.pid}")
            
            # 清理旧的输出线程
            self.output_threads = []
            
            # 标准输出线程
            stdout_thread = threading.Thread(
                target=self.read_output,
                args=(self.process.stdout,),
                daemon=True
            )
            stdout_thread.start()
            self.output_threads.append(stdout_thread)
            
            # 错误输出线程
            stderr_thread = threading.Thread(
                target=self.read_output,
                args=(self.process.stderr,),
                daemon=True
            )
            stderr_thread.start()
            self.output_threads.append(stderr_thread)
            
            # 更新菜单项
            self.update_menu()
            
        except Exception as e:
            self.logger.error(f"启动服务器时出错: {str(e)}")
            raise

    def read_output(self, stream):
        """从指定的流中读取输出并记录日志"""
        while not self.should_stop and self.process is not None:
            try:
                # 使用更健壮的方式读取输出
                output = stream.readline()
                if not output and self.process and self.process.poll() is not None:
                    break
                if output:
                    try:
                        # 尝试UTF-8解码
                        decoded = output.decode('utf-8').strip()
                    except UnicodeDecodeError:
                        # 如果UTF-8失败，尝试其他编码
                        try:
                            decoded = output.decode('gbk').strip()
                        except:
                            decoded = output.decode('latin-1').strip()
                    self.logger.info(decoded)
            except Exception as e:
                if not self.should_stop:
                    self.logger.error(f"读取输出时出错: {str(e)}")
                break
            time.sleep(0.1)

    def stop_server(self):
        if self.process:
            try:
                self.logger.info("正在停止服务器...")
                self.should_stop = True
                
                # 终止进程及其子进程
                try:
                    parent = psutil.Process(self.process.pid)
                    children = parent.children(recursive=True)
                    for child in children:
                        try:
                            child.terminate()
                        except psutil.NoSuchProcess:
                            pass
                    
                    try:
                        parent.terminate()
                    except psutil.NoSuchProcess:
                        pass
                except psutil.NoSuchProcess:
                    pass
                
                # 等待进程结束
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                
                self.server_running = False
                self.process = None
                self.logger.info("服务器已成功停止")
                
                # 更新菜单项
                self.update_menu()
                
            except Exception as e:
                self.logger.error(f"停止服务器时出错: {str(e)}")
            finally:
                self.process = None

    def toggle_server(self):
        """切换服务器状态"""
        if self.server_running:
            self.stop_server()
        else:
            self.start_server()

    def update_menu(self):
        """更新托盘菜单"""
        if self.tray_icon:
            # 重新创建菜单项
            start_stop_text = "停止服务器" if self.server_running else "启动服务器"
            self.menu_item_start_stop = pystray.MenuItem(
                start_stop_text,
                self.toggle_server
            )
            
            # 创建新菜单
            menu = pystray.Menu(
                self.menu_item_start_stop,
                pystray.MenuItem('打开日志', self.open_log),
                pystray.MenuItem('退出', self.exit_app)
            )
            
            # 更新菜单
            self.tray_icon.menu = menu

    def create_tray_icon(self):
        try:
            # 判断是否是打包后的环境
            if getattr(sys, 'frozen', False):
                # 打包后的情况 - 从EXE资源中加载图标
                try:
                    # 尝试从临时解压目录加载图标
                    base_path = sys._MEIPASS
                except AttributeError:
                    base_path = os.path.dirname(sys.executable)
                
                icon_path = os.path.join(base_path, 'icon.ico')
                if os.path.exists(icon_path):
                    image = Image.open(icon_path)
                else:
                    # 创建默认图标
                    image = self._create_default_icon()
            else:
                # 开发环境 - 从文件系统加载
                try:
                    image = Image.open("icon.ico")
                except FileNotFoundError:
                    # 创建默认图标
                    image = self._create_default_icon()
            
            # 初始菜单项
            self.menu_item_start_stop = pystray.MenuItem(
                "停止服务器",  # 初始状态为"停止服务器"，因为会自动启动
                self.toggle_server
            )
            
            menu = pystray.Menu(
                self.menu_item_start_stop,
                pystray.MenuItem('打开日志', self.open_log),
                pystray.MenuItem('退出', self.exit_app)
            )
            
            self.tray_icon = pystray.Icon("ASR Server", image, "ASR 语音识别服务器", menu)
            
            # 启动服务器后再运行托盘图标
            self.start_server()
            self.tray_icon.run()
            
        except Exception as e:
            self.logger.error(f"创建托盘图标时出错: {str(e)}")
            raise

    def _create_default_icon(self):
        """创建默认图标"""
        # 创建一个简单的默认图标
        image = Image.new('RGB', (64, 64), color='blue')
        # 在图标上添加文字
        from PIL import ImageDraw, ImageFont
        try:
            draw = ImageDraw.Draw(image)
            font = ImageFont.load_default()
            draw.text((10, 25), "ASR", font=font, fill="white")
        except:
            pass
        return image

    def open_log(self):
        try:
            os.startfile(self.log_file)
        except Exception as e:
            self.logger.error(f"打开日志文件时出错: {str(e)}")

    def exit_app(self):
        self.logger.info("正在退出应用程序...")
        self.stop_server()
        if self.tray_icon:
            self.tray_icon.stop()
        sys.exit(0)

    def run(self):
        try:
            self.create_tray_icon()  # 这会自动启动服务器
        except Exception as e:
            self.logger.error(f"应用程序运行出错: {str(e)}")
            sys.exit(1)

def main():
    manager = ServerManager()
    manager.run()

if __name__ == "__main__":
    main()