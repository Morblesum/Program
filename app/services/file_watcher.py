"""
TOPCON眼科数据管理系统
文件监听服务模块
"""
import time
from pathlib import Path
from typing import Callable, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent
from app.core.logger import logger
from app.core.config import config


class TopconFileHandler(FileSystemEventHandler):
    """TOPCON XML文件处理器"""
    
    def __init__(self, callback: Optional[Callable] = None):
        """
        初始化文件处理器
        
        Args:
            callback: 文件处理完成后的回调函数，接收文件路径作为参数
        """
        super().__init__()
        self.callback = callback
        self._processed_files = set()  # 记录已处理的文件（避免重复处理）
    
    def on_created(self, event):
        """
        文件创建事件处理 - 实时触发
        
        Args:
            event: 文件系统事件
        """
        if event.is_directory:
            return
        
        filepath = event.src_path
        
        # 检查是否为支持的文件类型
        supported_extensions = config.watcher.get('supported_extensions', ['.xml'])
        if not any(filepath.lower().endswith(ext) for ext in supported_extensions):
            return
        
        # 检查是否已处理过
        if filepath in self._processed_files:
            logger.debug(f"文件已处理过，跳过: {filepath}")
            return
        
        logger.info(f"检测到新XML文件: {filepath}")
        
        try:
            # 等待文件写入完成（避免读取不完整文件）
            if not self._wait_for_file_complete(filepath):
                logger.warning(f"文件写入未完成或不存在: {filepath}")
                return
            
            # 标记为已处理
            self._processed_files.add(filepath)
            
            logger.info(f"开始处理文件: {filepath}")
            
            # 执行回调
            if self.callback:
                try:
                    self.callback(filepath)
                except Exception as e:
                    logger.error(f"回调函数执行失败: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
            else:
                logger.warning("未设置回调函数！")
        except Exception as e:
            logger.error(f"文件监听器处理异常: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _wait_for_file_complete(self, filepath: str, timeout: int = 10) -> bool:
        """
        等待文件写入完成

        Args:
            filepath: 文件路径
            timeout: 超时时间（秒）

        Returns:
            bool: 文件是否稳定
        """
        path = Path(filepath)

        if not path.exists():
            return False

        retries = config.watcher.get('file_check_retries', 5)
        check_interval = config.watcher.get('check_interval', 0.2)
        start_time = time.time()

        initial_size = path.stat().st_size

        for i in range(retries):
            # 检查总超时时间
            if time.time() - start_time > timeout:
                logger.warning(f"文件稳定性检查超时 ({timeout}s): {filepath}")
                return True  # 超时后仍尝试处理

            time.sleep(check_interval)

            if not path.exists():
                logger.warning(f"文件在检查过程中被删除: {filepath}")
                return False

            current_size = path.stat().st_size

            if current_size == initial_size:
                logger.debug(f"文件写入完成: {filepath} ({current_size} bytes)")
                return True

            initial_size = current_size

        logger.warning(f"文件稳定性检查达到最大重试次数: {filepath}")
        return True  # 即使超时也尝试处理
    
    def remove_processed_record(self, filepath: str):
        """
        移除已处理文件的记录（允许重新处理）
        
        Args:
            filepath: 文件路径
        """
        abs_path = str(Path(filepath).resolve())
        if abs_path in self._processed_files:
            self._processed_files.remove(abs_path)
            logger.info(f"已移除文件处理记录: {filepath}")


class FileWatcherService:
    """文件监听服务管理器"""
    
    def __init__(self, watch_folder: Optional[str] = None, callback: Optional[Callable] = None):
        """
        初始化文件监听服务
        
        Args:
            watch_folder: 监听的文件夹路径（默认为配置中的路径）
            callback: 文件处理回调函数
        """
        self.watch_folder = watch_folder or config.get_watch_folder()
        self.observer = Observer()
        self.handler = TopconFileHandler(callback)
        self._is_running = False
    
    @property
    def callback(self) -> Optional[Callable]:
        """获取回调函数"""
        return self.handler.callback
    
    @callback.setter
    def callback(self, value: Optional[Callable]):
        """设置回调函数"""
        self.handler.callback = value
        logger.info("已设置文件处理回调函数")
    
    def start(self):
        """启动监听"""
        if self._is_running:
            logger.warning("文件监听服务已在运行")
            return
        
        watch_path = Path(self.watch_folder)
        
        if not watch_path.exists():
            raise FileNotFoundError(f"监听文件夹不存在: {self.watch_folder}")
        
        self.observer.schedule(self.handler, str(watch_path), recursive=False)
        self.observer.start()
        self._is_running = True
        
        logger.info(f"✓ 文件监听服务已启动")
        logger.info(f"  监听目录: {self.watch_folder}")
        logger.info(f"  支持格式: XML")
    
    def stop(self):
        """停止监听"""
        if not self._is_running:
            return
        
        self.observer.stop()
        self.observer.join()
        self._is_running = False
        
        logger.info("✗ 文件监听服务已停止")
    
    @property
    def is_running(self) -> bool:
        """检查服务是否正在运行"""
        return self._is_running
    
    def get_handler(self) -> TopconFileHandler:
        """获取文件处理器实例"""
        return self.handler


# 全局文件监听服务实例
file_watcher_service = FileWatcherService()






