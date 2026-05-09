"""
TOPCON眼科数据管理系统
患者数据模型
"""
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.core.database import Base


class Patient(Base):
    """患者表模型"""
    
    __tablename__ = 'patients'
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键ID')
    patient_no = Column(String(50), index=True, comment='患者编号')
    patient_id = Column(String(50), index=True, comment='患者ID')
    name = Column(String(100), comment='姓名')
    sex = Column(String(10), comment='性别')
    age = Column(Integer, comment='年龄')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    
    def __repr__(self):
        return f"<Patient(id={self.id}, patient_no={self.patient_no}, name={self.name})>"
