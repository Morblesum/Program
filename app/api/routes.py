"""
TOPCON眼科数据管理系统
API路由模块
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from app.services import db_service, excel_exporter, file_manager_service
from app.api.schemas import (
    MeasurementResponse,
    StatisticsResponse,
    DeleteRequest,
    ExportRequest,
    FileInfo
)

router = APIRouter()


@router.get("/measurements", response_model=List[MeasurementResponse])
async def get_measurements(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="限制记录数"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    patient_search: Optional[str] = None
):
    """
    获取测量记录列表
    
    - **skip**: 跳过记录数（分页）
    - **limit**: 限制记录数（分页）
    - **start_date**: 开始日期（格式：YYYY-MM-DD HH:MM:SS）
    - **end_date**: 结束日期（格式：YYYY-MM-DD HH:MM:SS）
    - **patient_search**: 患者搜索关键词
    """
    try:
        # 解析日期
        start_dt = datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S') if start_date else None
        end_dt = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S') if end_date else None
        
        measurements = db_service.get_all_measurements(
            skip=skip,
            limit=limit,
            start_date=start_dt,
            end_date=end_dt,
            patient_search=patient_search
        )
        
        return measurements
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics():
    """获取统计信息"""
    try:
        stats = db_service.get_statistics()
        return StatisticsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.delete("/measurements/{measurement_id}")
async def delete_measurement(measurement_id: int, delete_file: bool = False):
    """
    删除测量记录
    
    - **measurement_id**: 测量记录ID
    - **delete_file**: 是否同时删除原始XML文件
    """
    try:
        success = db_service.delete_measurement(
            measurement_id=measurement_id,
            delete_file=delete_file
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="记录不存在")
        
        return {"message": "删除成功", "success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.post("/export/excel")
async def export_to_excel(request: ExportRequest):
    """
    导出Excel
    
    - **columns**: 要导出的列名列表
    - **start_date**: 开始日期
    - **end_date**: 结束日期
    - **patient_search**: 患者搜索关键词
    """
    try:
        # 获取数据
        measurements = db_service.get_all_measurements(
            skip=0,
            limit=10000,
            start_date=datetime.strptime(request.start_date, '%Y-%m-%d %H:%M:%S') if request.start_date else None,
            end_date=datetime.strptime(request.end_date, '%Y-%m-%d %H:%M:%S') if request.end_date else None,
            patient_search=request.patient_search
        )
        
        if not measurements:
            raise HTTPException(status_code=404, detail="没有符合条件的数据")
        
        # 导出Excel
        filepath = excel_exporter.export_to_excel(
            data=measurements,
            columns=request.columns
        )
        
        return {
            "message": "导出成功",
            "filepath": filepath,
            "count": len(measurements)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")


@router.get("/export/columns")
async def get_available_columns():
    """获取可用的列配置"""
    try:
        columns = excel_exporter.get_available_columns()
        return {"columns": columns}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/files/xml-files", response_model=List[FileInfo])
async def list_xml_files():
    """列出所有XML文件"""
    try:
        files = file_manager_service.list_xml_files()
        
        result = []
        for f in files:
            info = file_manager_service.get_file_info(str(f))
            if info:
                result.append(FileInfo(**info))
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.delete("/files/xml-files/{filepath:path}")
async def delete_xml_file(filepath: str, force: bool = False):
    """
    删除XML文件
    
    - **filepath**: 文件路径（URL编码）
    - **force**: 是否强制删除
    """
    try:
        from urllib.parse import unquote
        decoded_path = unquote(filepath)
        
        success = file_manager_service.delete_xml_file(decoded_path, force=force)
        
        if not success:
            raise HTTPException(status_code=404, detail="文件不存在或删除失败")
        
        return {"message": "删除成功", "success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")
