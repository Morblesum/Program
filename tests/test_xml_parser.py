"""
TOPCON眼科数据管理系统
XML解析器单元测试
"""
import unittest
from pathlib import Path
from app.services.xml_parser import TopconXMLParser


class TestTopconXMLParser(unittest.TestCase):
    """XML解析器测试类"""
    
    def setUp(self):
        """测试准备"""
        self.parser = TopconXMLParser()
        # 使用用户提供的测试文件
        self.test_file = r"测试数据\1234567890_20260506_191101_TOPCON_KR-1_4462051.xml"
    
    def test_parse_complete_xml(self):
        """测试完整XML文件解析"""
        if not Path(self.test_file).exists():
            self.skipTest(f"测试文件不存在: {self.test_file}")
        
        result = self.parser.parse(self.test_file)
        
        # 验证数据结构完整性
        self.assertIn('device_info', result)
        self.assertIn('patient_info', result)
        self.assertIn('exam_datetime', result)
        self.assertIn('refraction', result)
        
        # 验证设备信息
        self.assertEqual(result['device_info']['company'], 'TOPCON')
        self.assertEqual(result['device_info']['model'], 'KR-1')
        
        # 验证患者信息
        self.assertEqual(result['patient_info']['patient_id'], '1234567890')
        self.assertEqual(result['patient_info']['patient_no'], '6970')
        
        # 验证验光数据
        refraction = result['refraction']
        self.assertEqual(refraction['vd'], 12.0)
        
        # 验证右眼数据
        right_eye = refraction['right_eye']
        self.assertEqual(right_eye['sphere'], -4.75)
        self.assertEqual(right_eye['cylinder'], 0.0)
        self.assertEqual(right_eye['se'], -4.75)
        
        # 验证左眼数据
        left_eye = refraction['left_eye']
        self.assertEqual(left_eye['sphere'], -4.75)
        self.assertEqual(left_eye['cylinder'], 0.0)
        self.assertEqual(left_eye['se'], -4.75)
        
        print(f"\n✅ 解析成功！")
        print(f"   患者ID: {result['patient_info']['patient_id']}")
        print(f"   右眼度数: {right_eye['sphere']}D")
        print(f"   左眼度数: {left_eye['sphere']}D")


if __name__ == '__main__':
    unittest.main(verbosity=2)
