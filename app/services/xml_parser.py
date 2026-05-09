"""
TOPCON眼科数据管理系统
XML解析服务模块
"""
from lxml import etree
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from app.core.logger import logger


class TopconXMLParser:
    """TOPCON KR-1 XML解析器"""
    
    # 命名空间映射
    NAMESPACES = {
        'nsCommon': 'http://www.joia.or.jp/standardized/namespaces/Common',
        'nsREF': 'http://www.joia.or.jp/standardized/namespaces/REF'
    }
    
    def parse(self, xml_filepath: str) -> Dict[str, Any]:
        """
        解析XML文件，返回结构化数据
        
        Args:
            xml_filepath: XML文件路径
            
        Returns:
            Dict: 解析后的数据结构
        """
        try:
            tree = etree.parse(xml_filepath)
            root = tree.getroot()
            
            data = {
                # 设备信息
                'device_info': self._parse_device_info(root),
                
                # 患者信息
                'patient_info': self._parse_patient_info(root),
                
                # 检查时间
                'exam_datetime': self._parse_datetime(root),
                
                # 验光参数
                'refraction': self._parse_refraction(root),
                
                # 原始文件路径
                'raw_xml_path': str(xml_filepath),
                
                # 文件创建时间
                'file_created_at': self._get_file_created_time(xml_filepath)
            }
            
            logger.info(f"成功解析XML文件: {xml_filepath}")
            return data
            
        except Exception as e:
            logger.error(f"解析XML文件失败: {xml_filepath}, 错误: {str(e)}")
            raise
    
    def _parse_device_info(self, root) -> Dict[str, Optional[str]]:
        """解析设备信息"""
        return {
            'company': self._get_text(root, './/nsCommon:Company'),
            'model': self._get_text(root, './/nsCommon:ModelName'),
            'machine_no': self._get_text(root, './/nsCommon:MachineNo'),
            'rom_version': self._get_text(root, './/nsCommon:ROMVersion'),
        }
    
    def _parse_patient_info(self, root) -> Dict[str, Any]:
        """解析患者信息"""
        age = self._get_int(root, './/nsCommon:Age')
        return {
            'patient_no': self._get_text(root, './/nsCommon:No.'),
            'patient_id': self._get_text(root, './/nsCommon:ID'),
            'first_name': self._get_text(root, './/nsCommon:FirstName'),
            'middle_name': self._get_text(root, './/nsCommon:MiddleName'),
            'last_name': self._get_text(root, './/nsCommon:LastName'),
            'sex': self._get_text(root, './/nsCommon:Sex'),
            'age': age if age else None,
        }
    
    def _parse_datetime(self, root) -> Optional[datetime]:
        """解析检查时间"""
        date_str = self._get_text(root, './/nsCommon:Date')
        time_str = self._get_text(root, './/nsCommon:Time')
        
        if not date_str or not time_str:
            return None
        
        try:
            return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
        except ValueError as e:
            logger.warning(f"日期时间解析失败: {e}")
            return None
    
    def _parse_refraction(self, root) -> Dict[str, Any]:
        """解析验光数据（Median + 三次独立测量）"""
        return {
            'vd': self._get_float(root, './/nsREF:VD'),
            'right_eye': self._parse_eye_data(root, './/nsREF:R/nsREF:Median'),
            'left_eye': self._parse_eye_data(root, './/nsREF:L/nsREF:Median'),
            'right_eye_lists': self._parse_eye_lists(root, './/nsREF:R'),
            'left_eye_lists': self._parse_eye_lists(root, './/nsREF:L'),
            'pd_distance': self._get_float(root, './/nsREF:PD/nsREF:Distance'),
            'pd_near': self._get_float(root, './/nsREF:PD/nsREF:Near'),
        }

    def _parse_eye_data(self, root, xpath: str) -> Dict[str, Optional[float]]:
        """解析单眼 Median 数据"""
        elements = root.xpath(xpath, namespaces=self.NAMESPACES)
        if not elements:
            return {
                'sphere': None,
                'cylinder': None,
                'axis': None,
                'se': None
            }

        element = elements[0]
        return {
            'sphere': self._get_float(element, './nsREF:Sphere'),
            'cylinder': self._get_float(element, './nsREF:Cylinder'),
            'axis': self._get_int(element, './nsREF:Axis'),
            'se': self._get_float(element, './nsREF:SE'),
        }

    def _parse_eye_lists(self, root, eye_xpath: str) -> List[Dict[str, Optional[float]]]:
        """解析单眼三次独立测量数据 (List No=1/2/3)"""
        results = []
        for list_no in range(1, 4):
            xpath = f'{eye_xpath}/nsREF:List[@No="{list_no}"]'
            elements = root.xpath(xpath, namespaces=self.NAMESPACES)
            if elements:
                el = elements[0]
                results.append({
                    'list_no': list_no,
                    'sphere': self._get_float(el, './nsREF:Sphere'),
                    'cylinder': self._get_float(el, './nsREF:Cylinder'),
                    'axis': self._get_int(el, './nsREF:Axis'),
                    'se': self._get_float(el, './nsREF:SE'),
                })
        return results
    
    def _get_file_created_time(self, filepath: str) -> Optional[datetime]:
        """获取文件创建时间"""
        try:
            path = Path(filepath)
            stat = path.stat()
            # Windows下st_ctime是创建时间，Unix下是最后状态变更时间
            return datetime.fromtimestamp(stat.st_ctime)
        except Exception as e:
            logger.warning(f"获取文件创建时间失败: {filepath}, 错误: {e}")
            return None
    
    # ========== 辅助方法 ==========
    
    def _get_text(self, root, xpath: str) -> Optional[str]:
        """获取文本值"""
        elements = root.xpath(xpath, namespaces=self.NAMESPACES)
        if not elements:
            return None
        text = elements[0].text
        return text.strip() if text else None
    
    def _get_float(self, root, xpath: str) -> Optional[float]:
        """获取浮点数值"""
        text = self._get_text(root, xpath)
        if text is None:
            return None
        try:
            return float(text)
        except ValueError:
            logger.warning(f"无法转换为浮点数: {text}")
            return None
    
    def _get_int(self, root, xpath: str) -> Optional[int]:
        """获取整数值"""
        text = self._get_text(root, xpath)
        if text is None:
            return None
        try:
            return int(text)
        except ValueError:
            logger.warning(f"无法转换为整数: {text}")
            return None
