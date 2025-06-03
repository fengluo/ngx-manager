#!/usr/bin/env python3
"""
Nginx Manager 容器启动脚本 (Python版本)
负责初始化、配置生成、证书检查和nginx启动
"""

import os
import sys
import yaml
import signal
import subprocess
import time
import threading
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

def setup_logging(logs_dir: str = None):
    """设置日志配置"""
    if logs_dir is None:
        logs_dir = os.environ.get('LOGS_DIR', '/app/logs')
    
    logs_path = Path(logs_dir)
    logs_path.mkdir(parents=True, exist_ok=True)
    
    log_file = logs_path / 'entrypoint.log'
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(str(log_file)),
            logging.StreamHandler()
        ]
    )

# 延迟日志初始化，只在需要时调用
logger = None

def get_logger():
    """获取日志器，延迟初始化"""
    global logger
    if logger is None:
        setup_logging()
        logger = logging.getLogger(__name__)
    return logger

class NginxManager:
    def __init__(self, config_dir=None, logs_dir=None, certs_dir=None, www_dir=None):
        self.script_dir = Path(__file__).parent
        
        # 使用环境变量或提供的参数，回退到默认值
        self.config_dir = Path(config_dir or os.environ.get('CONFIG_DIR', '/app/config'))
        self.logs_dir = Path(logs_dir or os.environ.get('LOGS_DIR', '/app/logs'))
        self.certs_dir = Path(certs_dir or os.environ.get('CERTS_DIR', '/app/certs'))
        self.www_dir = Path(www_dir or os.environ.get('WWW_DIR', '/var/www/html'))
        
        # 确保目录存在
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.certs_dir.mkdir(parents=True, exist_ok=True)
        self.www_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化日志（使用实际的logs_dir）
        setup_logging(str(self.logs_dir))
        self.logger = logging.getLogger(__name__)
        
        # 信号处理
        self.shutdown_event = threading.Event()
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
    def signal_handler(self, signum, frame):
        """信号处理函数"""
        self.logger.info(f"接收到信号 {signum}，正在关闭服务...")
        self.shutdown_event.set()
        self.cleanup()
        
    def cleanup(self):
        """清理函数"""
        self.logger.info("正在关闭服务...")
        
        # 停止nginx
        if self.is_nginx_running():
            self.logger.info("停止nginx...")
            try:
                subprocess.run(['nginx', '-s', 'quit'], timeout=30)
                
                # 等待nginx优雅关闭
                timeout = 30
                while self.is_nginx_running() and timeout > 0:
                    time.sleep(1)
                    timeout -= 1
                    
                if self.is_nginx_running():
                    self.logger.info("强制停止nginx...")
                    subprocess.run(['pkill', '-9', 'nginx'])
                    
            except Exception as e:
                self.logger.error(f"停止nginx失败: {e}")
                
        self.logger.info("服务已停止")
        sys.exit(0)
        
    def run_command(self, cmd: List[str], check: bool = True, timeout: int = None) -> subprocess.CompletedProcess:
        """执行命令"""
        try:
            self.logger.debug(f"执行命令: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=check,
                timeout=timeout
            )
            
            if result.stdout:
                self.logger.debug(f"命令输出: {result.stdout}")
            if result.stderr:
                self.logger.warning(f"命令错误: {result.stderr}")
                
            return result
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"命令执行失败: {e}")
            if e.stderr:
                self.logger.error(f"错误输出: {e.stderr}")
            raise
        except subprocess.TimeoutExpired as e:
            self.logger.error(f"命令执行超时: {e}")
            raise
            
    def is_nginx_running(self) -> bool:
        """检查nginx是否在运行"""
        try:
            result = subprocess.run(['pgrep', 'nginx'], capture_output=True)
            return result.returncode == 0
        except Exception:
            return False
            
    def check_config_files(self):
        """检查配置文件"""
        self.logger.info("检查配置文件...")
        
        # 检查虚拟主机配置
        vhosts_config = self.config_dir / 'vhosts.yml'
        if not vhosts_config.exists():
            self.logger.info("创建默认虚拟主机配置...")
            default_vhosts = [
                {
                    'name': 'default',
                    'domains': ['localhost'],
                    'type': 'static',
                    'root': '/var/www/html',
                    'ssl': False
                }
            ]
            
            with open(vhosts_config, 'w', encoding='utf-8') as f:
                yaml.dump(default_vhosts, f, default_flow_style=False, allow_unicode=True)
                
        # 检查SSL配置
        ssl_config = self.config_dir / 'ssl.yml'
        if not ssl_config.exists():
            self.logger.info("创建默认SSL配置...")
            default_ssl = {
                'ssl': {
                    'email': 'admin@example.com',
                    'ca_server': 'letsencrypt',
                    'key_length': 2048,
                    'auto_upgrade': True
                },
                'acme': {
                    'staging': False,
                    'force': False,
                    'debug': False
                },
                'advanced': {
                    'renewal_check_interval': 24,
                    'renewal_days_before_expiry': 30,
                    'concurrent_cert_limit': 3,
                    'retry_attempts': 3,
                    'retry_interval': 300
                }
            }
            
            with open(ssl_config, 'w', encoding='utf-8') as f:
                yaml.dump(default_ssl, f, default_flow_style=False, allow_unicode=True)
                
        self.logger.info("配置文件检查完成")
        
    def create_default_pages(self):
        """创建默认网页"""
        self.logger.info("创建默认网页...")
        
        # 创建默认首页
        index_file = self.www_dir / 'index.html'
        if not index_file.exists():
            html_content = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nginx Manager</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 40px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            text-align: center;
            max-width: 600px;
        }
        h1 {
            font-size: 3em;
            margin-bottom: 20px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        p {
            font-size: 1.2em;
            margin-bottom: 30px;
            opacity: 0.9;
        }
        .status {
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 10px;
            backdrop-filter: blur(10px);
        }
        .version {
            margin-top: 40px;
            opacity: 0.7;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Nginx Manager</h1>
        <p>Nginx自动化管理配置工具正在运行</p>
        <div class="status">
            <p><strong>状态:</strong> 运行中</p>
            <p><strong>时间:</strong> <span id="time"></span></p>
        </div>
        <div class="version">
            Powered by Nginx Manager v1.0 (Python)
        </div>
    </div>
    
    <script>
        function updateTime() {
            document.getElementById('time').textContent = new Date().toLocaleString('zh-CN');
        }
        updateTime();
        setInterval(updateTime, 1000);
    </script>
</body>
</html>'''
            
            with open(index_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
                
        # 创建健康检查页面
        health_file = self.www_dir / 'health'
        if not health_file.exists():
            with open(health_file, 'w') as f:
                f.write('healthy\n')
                
        self.logger.info("默认网页创建完成")
        
    def init_acme(self):
        """初始化acme.sh"""
        self.logger.info("初始化SSL证书管理...")
        
        acme_home = Path('/root/.acme.sh')
        if not acme_home.exists():
            self.logger.info("首次运行，初始化acme.sh...")
            try:
                cert_manager = self.script_dir / 'cert_manager.py'
                self.run_command([sys.executable, str(cert_manager), '--init'])
            except Exception as e:
                self.logger.error(f"acme.sh初始化失败: {e}")
                
        self.logger.info("SSL证书管理初始化完成")
        
    def generate_nginx_config(self) -> bool:
        """生成nginx配置"""
        self.logger.info("生成nginx配置...")
        
        try:
            config_generator = self.script_dir / 'generate-config.py'
            self.run_command([sys.executable, str(config_generator), '--all', '--no-reload'])
            self.logger.info("nginx配置生成成功")
            return True
            
        except Exception as e:
            self.logger.error(f"nginx配置生成失败: {e}")
            return False
            
    def check_nginx_syntax(self) -> bool:
        """检查nginx配置语法"""
        self.logger.info("检查nginx配置语法...")
        
        try:
            self.run_command(['nginx', '-t'])
            self.logger.info("nginx配置语法检查通过")
            return True
            
        except Exception as e:
            self.logger.error(f"nginx配置语法错误: {e}")
            return False
            
    def start_nginx(self) -> bool:
        """启动nginx"""
        self.logger.info("启动nginx...")
        
        # 确保nginx不在运行
        if self.is_nginx_running():
            self.logger.info("停止现有nginx进程...")
            try:
                self.run_command(['nginx', '-s', 'quit'])
                time.sleep(2)
            except Exception:
                try:
                    self.run_command(['pkill', '-9', 'nginx'])
                    time.sleep(1)
                except Exception:
                    pass
                    
        # 启动nginx
        try:
            self.run_command(['nginx'])
            self.logger.info("nginx启动成功")
            return True
            
        except Exception as e:
            self.logger.error(f"nginx启动失败: {e}")
            return False
            
    def check_ssl_certificates(self):
        """检查和申请SSL证书"""
        self.logger.info("检查SSL证书...")
        
        # 检查是否有需要SSL的虚拟主机
        try:
            vhosts_config = self.config_dir / 'vhosts.yml'
            with open(vhosts_config, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
            # 支持两种格式
            if isinstance(config, dict) and 'vhosts' in config:
                vhosts = config['vhosts']
            elif isinstance(config, list):
                vhosts = config
            else:
                vhosts = []
                
            ssl_count = sum(1 for vhost in vhosts if vhost.get('ssl', False))
            
            if ssl_count > 0:
                self.logger.info(f"发现 {ssl_count} 个需要SSL证书的虚拟主机，开始检查证书...")
                
                # 在后台检查和申请证书，避免阻塞nginx启动
                def check_certs():
                    time.sleep(10)  # 等待nginx完全启动
                    try:
                        cert_manager = self.script_dir / 'cert_manager.py'
                        self.run_command([sys.executable, str(cert_manager), '--check-all'])
                    except Exception as e:
                        self.logger.error(f"证书检查失败: {e}")
                        
                cert_thread = threading.Thread(target=check_certs, daemon=True)
                cert_thread.start()
                
                self.logger.info("SSL证书检查已在后台启动")
            else:
                self.logger.info("没有需要SSL证书的虚拟主机")
                
        except Exception as e:
            self.logger.error(f"检查SSL配置失败: {e}")
            
    def setup_cron_jobs(self):
        """设置定时任务"""
        self.logger.info("设置定时任务...")
        
        # 创建crontab内容
        cron_content = '''# 每天凌晨2点检查证书更新
0 2 * * * /usr/bin/python3 /app/scripts/cert_manager.py --renew-all >> /app/logs/cron.log 2>&1

# 每小时检查配置文件变化并重新生成
0 * * * * /usr/bin/python3 /app/scripts/generate-config.py --all >> /app/logs/cron.log 2>&1
'''
        
        try:
            # 写入临时文件
            cron_file = Path('/tmp/nginx-manager-cron')
            with open(cron_file, 'w') as f:
                f.write(cron_content)
                
            # 安装crontab
            self.run_command(['crontab', str(cron_file)])
            cron_file.unlink()
            
            self.logger.info("定时任务设置完成")
            
        except Exception as e:
            self.logger.warning(f"定时任务设置失败: {e}")
            
    def monitor_config_changes(self):
        """监控配置文件变化"""
        self.logger.info("启动配置文件监控...")
        
        def config_monitor():
            try:
                event_handler = FileSystemEventHandler()
                event_handler.on_modified = lambda event: self.handle_config_change(event)
                observer = Observer()
                observer.schedule(event_handler, str(self.config_dir), recursive=False)
                observer.start()
                
                # 等待关闭信号
                while not self.shutdown_event.is_set():
                    time.sleep(1)
                    
                observer.stop()
                observer.join()
                
            except ImportError:
                self.logger.warning("watchdog模块不可用，跳过配置文件监控")
            except Exception as e:
                self.logger.error(f"配置文件监控失败: {e}")
                
        monitor_thread = threading.Thread(target=config_monitor, daemon=True)
        monitor_thread.start()
        
        self.logger.info("配置文件监控已启动")
        
    def handle_config_change(self, event):
        """处理配置文件变化"""
        if event.is_directory:
            return
        
        if not event.src_path.endswith(('.yml', '.yaml')):
            return
        
        # 重新生成配置
        try:
            config_generator = self.script_dir / 'generate-config.py'
            self.run_command([sys.executable, str(config_generator), '--all'])
            self.logger.info('配置重新生成成功')
        except Exception as e:
            self.logger.error(f'配置重新生成失败: {e}')
        
    def main_loop(self):
        """主循环"""
        self.logger.info("=== Nginx Manager 启动完成 ===")
        
        # 获取nginx版本信息
        try:
            result = self.run_command(['nginx', '-v'])
            nginx_version = result.stderr.strip() if result.stderr else "未知版本"
        except Exception:
            nginx_version = "未知版本"
            
        self.logger.info(f"nginx状态: {nginx_version}")
        self.logger.info("监听端口: 80, 443")
        self.logger.info(f"配置目录: {self.config_dir}")
        self.logger.info(f"证书目录: {self.certs_dir}")
        self.logger.info(f"日志目录: {self.logs_dir}")
        
        # 保持容器运行
        while not self.shutdown_event.is_set():
            try:
                # 检查nginx进程
                if not self.is_nginx_running():
                    self.logger.error("nginx进程异常退出，尝试重启...")
                    if not self.start_nginx():
                        self.logger.error("nginx重启失败，退出容器")
                        break
                        
                # 等待30秒或关闭信号
                self.shutdown_event.wait(30)
                
            except Exception as e:
                self.logger.error(f"主循环异常: {e}")
                time.sleep(5)
                
    def run(self):
        """运行主程序"""
        try:
            self.logger.info("=== Nginx Manager 启动 ===")
            self.logger.info("版本: 1.0 (Python)")
            self.logger.info(f"时间: {datetime.now()}")
            
            # 检查配置文件
            self.check_config_files()
            
            # 创建默认网页
            self.create_default_pages()
            
            # 生成nginx配置
            if not self.generate_nginx_config():
                self.logger.error("配置生成失败，退出")
                sys.exit(1)
                
            # 检查nginx配置语法
            if not self.check_nginx_syntax():
                self.logger.error("nginx配置语法错误，退出")
                sys.exit(1)
                
            # 启动nginx
            if not self.start_nginx():
                self.logger.error("nginx启动失败，退出")
                sys.exit(1)
                
            # 初始化SSL证书管理
            self.init_acme()
            
            # 检查SSL证书
            self.check_ssl_certificates()
            
            # 设置定时任务
            self.setup_cron_jobs()
            
            # 启动配置文件监控
            self.monitor_config_changes()
            
            # 进入主循环
            self.main_loop()
            
        except KeyboardInterrupt:
            self.logger.info("接收到中断信号")
        except Exception as e:
            self.logger.error(f"启动失败: {e}")
            sys.exit(1)
        finally:
            self.cleanup()

def main():
    manager = NginxManager()
    manager.run()

if __name__ == '__main__':
    main() 