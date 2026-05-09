"""
TOPCON眼科数据管理系统
测量数据模型
"""
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class Measurement(Base):
    """测量数据表模型（存储 Median 中位数/平均值）"""

    __tablename__ = 'measurements'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键ID')
    patient_id = Column(Integer, ForeignKey('patients.id'), comment='关联患者ID')

    # 检查时间
    exam_date = Column(DateTime, index=True, comment='检查日期时间')

    # 设备信息
    device_model = Column(String(50), comment='设备型号')
    vd = Column(Float, comment='顶点距离(mm)')

    # 右眼数据（Median）
    r_sphere = Column(Float, comment='右眼球镜度数(D)')
    r_cylinder = Column(Float, comment='右眼柱镜度数(D)')
    r_axis = Column(Integer, comment='右眼散光轴位(度)')
    r_se = Column(Float, comment='右眼等效球镜度数(D)')

    # 左眼数据（Median）
    l_sphere = Column(Float, comment='左眼球镜度数(D)')
    l_cylinder = Column(Float, comment='左眼柱镜度数(D)')
    l_axis = Column(Integer, comment='左眼散光轴位(度)')
    l_se = Column(Float, comment='左眼等效球镜度数(D)')

    # 瞳距
    pd_distance = Column(Float, comment='远用瞳距(mm)')
    pd_near = Column(Float, comment='近用瞳距(mm)')

    # 文件信息
    raw_xml_path = Column(String(500), comment='原始XML文件路径')
    file_created_at = Column(DateTime, index=True, comment='文件创建时间')

    created_at = Column(DateTime, default=datetime.now, comment='记录创建时间')

    # 关联关系
    patient = relationship("Patient", back_populates="measurements")
    details = relationship("MeasurementDetail", back_populates="measurement",
                          cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Measurement(id={self.id}, exam_date={self.exam_date}, R:{self.r_sphere}D L:{self.l_sphere}D)>"


class MeasurementDetail(Base):
    """单次测量明细表（存储 XML 中三个独立 List 读数）"""

    __tablename__ = 'measurement_details'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键ID')
    measurement_id = Column(Integer, ForeignKey('measurements.id', ondelete='CASCADE'),
                           index=True, comment='关联测量记录ID')
    eye = Column(String(1), comment='眼别: R=右眼 L=左眼')
    list_no = Column(Integer, comment='测量序号: 1/2/3')

    sphere = Column(Float, comment='球镜度数(D)')
    cylinder = Column(Float, comment='柱镜度数(D)')
    axis = Column(Integer, comment='散光轴位(度)')
    se = Column(Float, comment='等效球镜度数(D)')

    # 关联关系
    measurement = relationship("Measurement", back_populates="details")

    def __repr__(self):
        return f"<Detail(id={self.id}, eye={self.eye}, #{self.list_no}, S:{self.sphere}D)>"


# 为Patient添加反向关系
from app.models.patient import Patient
Patient.measurements = relationship("Measurement", order_by=Measurement.id, back_populates="patient")
