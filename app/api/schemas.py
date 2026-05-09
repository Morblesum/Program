"""
TOPCON眼科数据管理系统
Pydantic数据模式
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class PatientInfo(BaseModel):
    """患者信息模式"""
    patient_no: Optional[str] = None
    patient_id: Optional[str] = None
    name: Optional[str] = None
    sex: Optional[str] = None
    age: Optional[int] = None


class EyeData(BaseModel):
    """单眼数据模式"""
    sphere: Optional[float] = None
    cylinder: Optional[float] = None
    axis: Optional[int] = None
    se: Optional[float] = None


class MeasurementDetailItem(BaseModel):
    """单次测量明细"""
    eye: Optional[str] = None
    list_no: Optional[int] = None
    sphere: Optional[float] = None
    cylinder: Optional[float] = None
    axis: Optional[int] = None
    se: Optional[float] = None


class MeasurementResponse(BaseModel):
    """测量数据响应模式"""
    id: int
    patient_id: Optional[str] = None
    patient_no: Optional[str] = None
    patient_name: Optional[str] = None
    exam_date: Optional[str] = None
    device_model: Optional[str] = None

    # 右眼数据
    r_sphere: Optional[float] = None
    r_cylinder: Optional[float] = None
    r_axis: Optional[int] = None
    r_se: Optional[float] = None

    # 左眼数据
    l_sphere: Optional[float] = None
    l_cylinder: Optional[float] = None
    l_axis: Optional[int] = None
    l_se: Optional[float] = None

    # 瞳距
    pd_distance: Optional[float] = None
    pd_near: Optional[float] = None

    # 文件信息
    raw_xml_path: Optional[str] = None
    file_created_at: Optional[str] = None
    created_at: Optional[str] = None

    # 三次独立测量明细
    details: Optional[List[MeasurementDetailItem]] = None

    class Config:
        from_attributes = True


class StatisticsResponse(BaseModel):
    """统计信息响应模式"""
    total_count: int
    today_count: int
    avg_r_sphere: float
    avg_l_sphere: float


class DeleteRequest(BaseModel):
    """删除请求模式"""
    measurement_id: int
    delete_file: bool = False


class ExportRequest(BaseModel):
    """导出请求模式"""
    columns: Optional[List[str]] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    patient_search: Optional[str] = None


class FileInfo(BaseModel):
    """文件信息模式"""
    filename: str
    filepath: str
    size: int
    created_at: float
    modified_at: float
