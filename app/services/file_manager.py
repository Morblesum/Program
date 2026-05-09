"""
TOPCON眼科数据管理系统
文件管理服务模块
"""
from pathlib import Path
from typing import List, Optional
from app.core.logger import logger
from app.core.config import config
from app.services.file_watcher import file_watcher_service


class FileManagerService:
    """文件管理服务"""
    
    @staticmethod
    def delete_xml_file(filepath: str, force: bool = False) -> bool:
        """
        删除XML文件

        Args:
            filepath: 文件路径
            force: 是否强制删除（即使文件正在被监听）

        Returns:
            bool: 是否删除成功
        """
        try:
            path = Path(filepath)

            if not path.exists():
                logger.warning(f"文件不存在: {filepath}")
                return False

            supported_extensions = config.watcher.get('supported_extensions', ['.xml'])
            if not any(path.suffix.lower() == ext for ext in supported_extensions):
                logger.error(f"不支持的文件类型: {filepath}")
                return False
            
            # 从监听器的已处理记录中移除
            if not force:
                handler = file_watcher_service.get_handler()
                handler.remove_processed_record(str(path.resolve()))
            
            # 删除文件
            path.unlink()
            
            logger.info(f"✓ 已删除文件: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"✗ 删除文件失败: {filepath}, 错误: {e}")
            raise
    
    @staticmethod
    def list_xml_files(folder_path: Optional[str] = None) -> List[Path]:
        """
        列出文件夹中的所有XML文件
        
        Args:
            folder_path: 文件夹路径（可选，默认使用监听目录）
            
        Returns:
            List[Path]: XML文件路径列表
        """
        if not folder_path:
            folder_path = config.get_watch_folder()
        
        path = Path(folder_path)
        
        if not path.exists():
            logger.error(f"文件夹不存在: {folder_path}")
            return []
        
        supported_extensions = config.watcher.get('supported_extensions', ['.xml'])
        xml_files = [f for f in path.iterdir() if f.suffix.lower() in supported_extensions]
        
        # 按创建时间排序（最新的在前）
        xml_files.sort(key=lambda x: x.stat().st_ctime, reverse=True)
        
        return xml_files
    
    @staticmethod
    def get_file_info(filepath: str) -> dict:
        """
        获取文件信息
        
        Args:
            filepath: 文件路径
            
        Returns:
            dict: 文件信息字典
        """
        try:
            path = Path(filepath)
            
            if not path.exists():
                return None
            
            stat = path.stat()
            
            return {
                'filename': path.name,
                'filepath': str(path),
                'size': stat.st_size,
                'created_at': stat.st_ctime,
                'modified_at': stat.st_mtime,
            }
            
        except Exception as e:
            logger.error(f"获取文件信息失败: {filepath}, 错误: {e}")
            return None


# 全局文件管理服务实例
file_manager_service = FileManagerService()
