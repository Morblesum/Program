"""
TOPCON眼科数据管理系统
配置管理模块
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any


class Config:
    """配置管理类"""
    
    def __init__(self):
        self._config = {}
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        # 打包后使用当前工作目录（程序所在目录）
        # 开发时使用项目根目录
        try:
            # 尝试从当前工作目录加载
            config_path = Path.cwd() / "config.yaml"
            
            if not config_path.exists():
                # 如果当前目录没有，尝试从项目根目录加载（开发模式）
                config_path = Path(__file__).parent.parent.parent / "config.yaml"
            
            if not config_path.exists():
                raise FileNotFoundError(f"配置文件不存在: {config_path}")
            
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
        except Exception as e:
            raise FileNotFoundError(f"无法加载配置文件: {e}")
    
    @property
    def watcher(self) -> Dict[str, Any]:
        """获取监听器配置"""
        return self._config.get('watcher', {})
    
    @property
    def database(self) -> Dict[str, Any]:
        """获取数据库配置"""
        return self._config.get('database', {})
    
    @property
    def logging(self) -> Dict[str, Any]:
        """获取日志配置"""
        return self._config.get('logging', {})
    
    @property
    def export(self) -> Dict[str, Any]:
        """获取导出配置"""
        return self._config.get('export', {})
    
    def get_watch_folder(self) -> str:
        """获取监听文件夹路径（绝对路径）"""
        watch_folder = self.watcher.get('watch_folder', './')
        # 如果是相对路径，转换为绝对路径（基于当前工作目录而非模块目录）
        if not Path(watch_folder).is_absolute():
            watch_folder = str(Path.cwd() / watch_folder)
        return watch_folder
    
    def get_database_url(self) -> str:
        """获取数据库连接URL"""
        db_path = self.database.get('path', './eye_clinic.db')
        # 如果是相对路径，转换为绝对路径（基于当前工作目录）
        if not Path(db_path).is_absolute():
            db_path = str(Path.cwd() / db_path)
        return f"sqlite:///{db_path}"


# 全局配置实例
config = Config()
