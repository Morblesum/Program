"""
TOPCON眼科数据管理系统
数据库操作服务模块
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.patient import Patient
from app.models.measurement import Measurement, MeasurementDetail
from app.core.logger import logger


class DatabaseService:
    """数据库操作服务"""
    
    def __init__(self):
        self.session_factory = SessionLocal
    
    def save_measurement_data(self, xml_data: Dict[str, Any]) -> int:
        """
        保存测量数据到数据库
        
        Args:
            xml_data: XML解析后的数据字典
            
        Returns:
            int: 测量记录ID
        """
        db = self.session_factory()
        
        try:
            # 1. 查找或创建患者
            patient = self._get_or_create_patient(db, xml_data['patient_info'])
            
            # 2. 创建测量记录
            measurement = Measurement(
                patient_id=patient.id,
                exam_date=xml_data['exam_datetime'],
                device_model=xml_data['device_info'].get('model'),
                vd=xml_data['refraction'].get('vd'),
                
                # 右眼数据
                r_sphere=xml_data['refraction']['right_eye'].get('sphere'),
                r_cylinder=xml_data['refraction']['right_eye'].get('cylinder'),
                r_axis=xml_data['refraction']['right_eye'].get('axis'),
                r_se=xml_data['refraction']['right_eye'].get('se'),
                
                # 左眼数据
                l_sphere=xml_data['refraction']['left_eye'].get('sphere'),
                l_cylinder=xml_data['refraction']['left_eye'].get('cylinder'),
                l_axis=xml_data['refraction']['left_eye'].get('axis'),
                l_se=xml_data['refraction']['left_eye'].get('se'),
                
                # 瞳距
                pd_distance=xml_data['refraction'].get('pd_distance'),
                pd_near=xml_data['refraction'].get('pd_near'),
                
                # 文件信息
                raw_xml_path=xml_data.get('raw_xml_path'),
                file_created_at=xml_data.get('file_created_at')
            )
            
            db.add(measurement)
            db.flush()  # 获取 measurement.id

            # 3. 保存三次独立测量明细
            right_lists = xml_data['refraction'].get('right_eye_lists', [])
            left_lists = xml_data['refraction'].get('left_eye_lists', [])

            for detail_data in right_lists:
                db.add(MeasurementDetail(
                    measurement_id=measurement.id,
                    eye='R',
                    list_no=detail_data['list_no'],
                    sphere=detail_data.get('sphere'),
                    cylinder=detail_data.get('cylinder'),
                    axis=detail_data.get('axis'),
                    se=detail_data.get('se'),
                ))

            for detail_data in left_lists:
                db.add(MeasurementDetail(
                    measurement_id=measurement.id,
                    eye='L',
                    list_no=detail_data['list_no'],
                    sphere=detail_data.get('sphere'),
                    cylinder=detail_data.get('cylinder'),
                    axis=detail_data.get('axis'),
                    se=detail_data.get('se'),
                ))

            db.commit()
            db.refresh(measurement)

            logger.info(f"✓ 保存测量数据成功，ID: {measurement.id}, 明细: {len(right_lists) + len(left_lists)} 条")
            return measurement.id
            
        except Exception as e:
            db.rollback()
            logger.error(f"✗ 保存测量数据失败: {e}")
            raise
        finally:
            db.close()
    
    def _get_or_create_patient(self, db: Session, patient_info: Dict[str, Any]) -> Patient:
        """
        获取或创建患者记录
        
        Args:
            db: 数据库会话
            patient_info: 患者信息字典
            
        Returns:
            Patient: 患者对象
        """
        patient_id = patient_info.get('patient_id')
        patient_no = patient_info.get('patient_no')
        
        # 尝试查找现有患者
        existing_patient = None
        
        if patient_id:
            existing_patient = db.query(Patient).filter(
                Patient.patient_id == patient_id
            ).first()
        
        if not existing_patient and patient_no:
            existing_patient = db.query(Patient).filter(
                Patient.patient_no == patient_no
            ).first()
        
        if existing_patient:
            logger.debug(f"找到现有患者: {existing_patient.id}")
            return existing_patient
        
        # 创建新患者
        # 组合姓名
        first_name = patient_info.get('first_name', '')
        last_name = patient_info.get('last_name', '')
        name = f"{last_name}{first_name}" if (first_name or last_name) else None
        
        new_patient = Patient(
            patient_no=patient_no,
            patient_id=patient_id,
            name=name,
            sex=patient_info.get('sex'),
            age=patient_info.get('age')
        )
        
        db.add(new_patient)
        db.commit()
        db.refresh(new_patient)
        
        logger.info(f"创建新患者: {new_patient.id}")
        return new_patient
    
    def get_all_measurements(
        self, 
        skip: int = 0, 
        limit: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        patient_search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取所有测量记录（带筛选）
        
        Args:
            skip: 跳过记录数
            limit: 限制记录数
            start_date: 开始日期
            end_date: 结束日期
            patient_search: 患者搜索关键词
            
        Returns:
            List[Dict]: 测量记录列表
        """
        db = self.session_factory()
        
        try:
            query = db.query(Measurement).join(Patient)
            
            # 日期筛选
            if start_date:
                query = query.filter(Measurement.file_created_at >= start_date)
            if end_date:
                query = query.filter(Measurement.file_created_at <= end_date)
            
            # 患者搜索
            if patient_search:
                query = query.filter(
                    (Patient.patient_id.like(f"%{patient_search}%")) |
                    (Patient.patient_no.like(f"%{patient_search}%")) |
                    (Patient.name.like(f"%{patient_search}%"))
                )
            
            # 排序（最新的在前）
            query = query.order_by(Measurement.file_created_at.desc())
            
            # 分页
            measurements = query.offset(skip).limit(limit).all()
            
            # 转换为字典
            result = []
            for m in measurements:
                # 收集明细数据
                details = []
                for d in m.details:
                    details.append({
                        'eye': d.eye,
                        'list_no': d.list_no,
                        'sphere': d.sphere,
                        'cylinder': d.cylinder,
                        'axis': d.axis,
                        'se': d.se,
                    })

                result.append({
                    'id': m.id,
                    'patient_id': m.patient.patient_id,
                    'patient_no': m.patient.patient_no,
                    'patient_name': m.patient.name,
                    'exam_date': m.exam_date.strftime('%Y-%m-%d %H:%M:%S') if m.exam_date else None,
                    'device_model': m.device_model,
                    'r_sphere': m.r_sphere,
                    'r_cylinder': m.r_cylinder,
                    'r_axis': m.r_axis,
                    'r_se': m.r_se,
                    'l_sphere': m.l_sphere,
                    'l_cylinder': m.l_cylinder,
                    'l_axis': m.l_axis,
                    'l_se': m.l_se,
                    'pd_distance': m.pd_distance,
                    'pd_near': m.pd_near,
                    'raw_xml_path': m.raw_xml_path,
                    'file_created_at': m.file_created_at.strftime('%Y-%m-%d %H:%M:%S') if m.file_created_at else None,
                    'created_at': m.created_at.strftime('%Y-%m-%d %H:%M:%S') if m.created_at else None,
                    'details': details,
                })
            
            return result
            
        finally:
            db.close()
    
    def delete_measurement(self, measurement_id: int, delete_file: bool = False) -> bool:
        """
        删除测量记录
        
        Args:
            measurement_id: 测量记录ID
            delete_file: 是否同时删除原始XML文件
            
        Returns:
            bool: 是否删除成功
        """
        db = self.session_factory()
        
        try:
            measurement = db.query(Measurement).filter(Measurement.id == measurement_id).first()
            
            if not measurement:
                logger.warning(f"测量记录不存在: ID={measurement_id}")
                return False
            
            # 删除原始文件（如果需要）
            if delete_file and measurement.raw_xml_path:
                from pathlib import Path
                xml_file = Path(measurement.raw_xml_path)
                if xml_file.exists():
                    xml_file.unlink()
                    logger.info(f"已删除原始XML文件: {measurement.raw_xml_path}")
            
            # 删除数据库记录
            db.delete(measurement)
            db.commit()
            
            logger.info(f"✓ 已删除测量记录: ID={measurement_id}")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"✗ 删除测量记录失败: {e}")
            raise
        finally:
            db.close()
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计数据
        
        Returns:
            Dict: 统计信息
        """
        db = self.session_factory()
        
        try:
            total_count = db.query(Measurement).count()
            
            # 今日新增
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_count = db.query(Measurement).filter(
                Measurement.file_created_at >= today
            ).count()
            
            # 平均球镜度数
            from sqlalchemy import func
            avg_r_sphere = db.query(func.avg(Measurement.r_sphere)).scalar()
            avg_l_sphere = db.query(func.avg(Measurement.l_sphere)).scalar()
            
            return {
                'total_count': total_count,
                'today_count': today_count,
                'avg_r_sphere': round(avg_r_sphere, 2) if avg_r_sphere else 0,
                'avg_l_sphere': round(avg_l_sphere, 2) if avg_l_sphere else 0,
            }
            
        finally:
            db.close()


# 全局数据库服务实例
db_service = DatabaseService()
