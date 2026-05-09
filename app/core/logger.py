"""
TOPCON眼科数据管理系统
日志配置模块
"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from app.core.config import config


def setup_logger(name: str = "topcon_eye_monitor") -> logging.Logger:
    """
    设置日志记录器
    
    Args:
        name: 日志记录器名称
        
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    logger = logging.getLogger(name)
    
    # 获取日志配置
    log_config = config.logging
    log_level = getattr(logging, log_config.get('level', 'INFO'))
    log_file = log_config.get('log_file', './logs/app.log')
    max_bytes = log_config.get('max_bytes', 10485760)
    backup_count = log_config.get('backup_count', 5)
    
    # 如果是相对路径，转换为绝对路径（使用当前工作目录）
    if not Path(log_file).is_absolute():
        log_file = str(Path.cwd() / log_file)
    
    # 创建日志目录
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    
    # 清除已有的handler
    logger.handlers.clear()
    
    # 设置日志级别
    logger.setLevel(log_level)
    
    # 日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台处理器（Windows 兼容：替换 emoji 避免 GBK 编码错误）
    class EmojiSafeFormatter(logging.Formatter):
        """将 emoji 替换为纯文本，仅影响控制台输出"""
        _REPLACEMENTS = str.maketrans({
            '\U0001f680': '-', '✅': 'v', '✓': 'v',
            '✗': 'x', '❌': 'x',
            '\U0001f4c4': '>', '⚠': '!',
            '\U0001f6d1': '#', '\U0001f511': '#',
        })

        def format(self, record):
            result = super().format(record)
            # 移除无法被 GBK 编码的字符
            return result.encode('gbk', errors='replace').decode('gbk')

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(EmojiSafeFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    logger.addHandler(console_handler)
    
    # 文件处理器（带轮转）
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


# 全局日志实例
logger = setup_logger()
