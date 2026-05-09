"""
TOPCON眼科数据管理系统
数据库连接模块
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import config

# 创建数据库引擎
engine = create_engine(
    config.get_database_url(),
    echo=False,  # 生产环境关闭SQL日志
    connect_args={"check_same_thread": False}  # SQLite允许多线程访问
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()


def get_db():
    """
    获取数据库会话（用于FastAPI依赖注入）
    
    Yields:
        Session: 数据库会话
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库（创建所有表）"""
    from app.models import patient, measurement  # 导入模型以注册表
    Base.metadata.create_all(bind=engine)
