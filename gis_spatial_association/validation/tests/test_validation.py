"""
验证模块测试用例

提供全面的验证模块功能测试，包括：
- 几何数据验证测试
- 属性数据验证测试
- 坐标系统验证测试
- 数据质量评分测试
- 数据修复功能测试

Author: CCPM Auto Development System
"""

import unittest
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon, MultiPoint
import tempfile
import os

# 导入验证模块
from ..geometry import GeometryValidator
from ..attributes import AttributeValidator, ValidationRule, DataType
from ..coordinate import CoordinateSystemValidator
from ..quality import DataQualityScorer, QualityGrade
from ..repair import DataRepairer


class TestGeometryValidator(unittest.TestCase):
    """几何验证器测试"""

    def setUp(self):
        """设置测试数据"""
        self.validator = GeometryValidator(tolerance=1e-8)

        # 创建测试数据
        valid_point = Point(116.4, 39.9)  # 北京坐标
        invalid_point = Point(float('inf'), 39.9)  # 无效坐标
        empty_geom = Point()  # 空几何

        valid_line = LineString([(116.3, 39.8), (116.5, 40.0)])
        invalid_line = LineString([(116.3, 39.8)])  # 点数不足

        valid_polygon = Polygon([(116.3, 39.8), (116.5, 39.8), (116.5, 40.0), (116.3, 39.8)])
        invalid_polygon = Polygon([(116.3, 39.8), (116.5, 39.8), (116.3, 39.8)])  # 自相交

        self.test_gdf = gpd.GeoDataFrame({
            'id': [1, 2, 3, 4, 5, 6],
            'name': ['valid_point', 'invalid_point', 'empty_geom', 'valid_line', 'invalid_line', 'invalid_polygon'],
            'geometry': [valid_point, invalid_point, empty_geom, valid_line, invalid_line, invalid_polygon]
        })

    def test_validate_geodataframe(self):
        """测试GeoDataFrame验证"""
        report = self.validator.validate_geodataframe(self.test_gdf)

        self.assertIn('summary', report)
        self.assertIn('errors', report)
        self.assertEqual(report['summary']['total_geometries'], 6)
        self.assertGreater(len(report['errors']), 0)  # 应该有错误

    def test_quality_score_calculation(self):
        """测试质量分数计算"""
        report = self.validator.validate_geodataframe(self.test_gdf)
        self.assertIn('quality_score', report)
        self.assertGreaterEqual(report['quality_score'], 0)
        self.assertLessEqual(report['quality_score'], 100)

    def test_error_classification(self):
        """测试错误分类"""
        report = self.validator.validate_geodataframe(self.test_gdf)

        error_types = set(error['error_type'] for error in report['errors'])
        self.assertTrue(any(error_type in ['invalid_coordinates', 'empty_geometry', 'degenerate', 'invalid_geometry']
                          for error_type in error_types))

    def test_repair_suggestions(self):
        """测试修复建议"""
        report = self.validator.validate_geodataframe(self.test_gdf)
        suggestions = self.validator.get_repair_suggestions()

        self.assertIsInstance(suggestions, list)
        self.assertGreater(len(suggestions), 0)


class TestAttributeValidator(unittest.TestCase):
    """属性验证器测试"""

    def setUp(self):
        """设置测试数据"""
        self.validator = AttributeValidator()

        # 创建测试数据
        self.test_data = {
            'id': [1, 2, 3, 4, 5],
            'name': ['A', 'B', None, 'D', 'E'],  # 有缺失值
            'age': [25, 30, '35', 40, 'abc'],  # 类型不一致
            'code': ['001', '002', '003', '002', '005'],  # 有重复
            'elevation': [100.5, 200.3, None, 400.1, 500.0],  # 有缺失值
            'geometry': [Point(0, 0) for _ in range(5)]
        }

        self.test_gdf = gpd.GeoDataFrame(self.test_data)

        # 添加验证规则
        rules = [
            ValidationRule('id', DataType.INTEGER, required=True, unique=True),
            ValidationRule('name', DataType.STRING, required=True),
            ValidationRule('age', DataType.INTEGER, min_value=0, max_value=150),
            ValidationRule('code', DataType.STRING, required=True, unique=True),
            ValidationRule('elevation', DataType.FLOAT, min_value=-1000, max_value=10000)
        ]

        for rule in rules:
            self.validator.add_rule(rule)

    def test_validate_geodataframe(self):
        """测试属性验证"""
        report = self.validator.validate_geodataframe(self.test_gdf)

        self.assertIn('summary', report)
        self.assertIn('errors', report)
        self.assertEqual(report['summary']['total_records'], 5)

    def test_missing_values_detection(self):
        """测试缺失值检测"""
        report = self.validator.validate_geodataframe(self.test_gdf)

        missing_fields = [field for field, count in report['missing_values'].items() if count > 0]
        self.assertIn('name', missing_fields)
        self.assertIn('elevation', missing_fields)

    def test_data_type_validation(self):
        """测试数据类型验证"""
        report = self.validator.validate_geodataframe(self.test_gdf)

        type_errors = [error for error in report['errors'] if error['error_type'] == 'invalid_type']
        self.assertGreater(len(type_errors), 0)  # 应该有类型错误

    def test_uniqueness_validation(self):
        """测试唯一性验证"""
        report = self.validator.validate_geodataframe(self.test_gdf)

        duplicate_errors = [error for error in report['errors'] if error['error_type'] == 'duplicate_value']
        self.assertGreater(len(duplicate_errors), 0)  # 应该有重复值错误

    def test_auto_rule_generation(self):
        """测试自动规则生成"""
        validator_without_rules = AttributeValidator()
        report = validator_without_rules.validate_geodataframe(self.test_gdf)

        self.assertIn('field_types', report)
        self.assertGreater(len(validator_without_rules.rules), 0)


class TestCoordinateSystemValidator(unittest.TestCase):
    """坐标系统验证器测试"""

    def setUp(self):
        """设置测试数据"""
        self.validator = CoordinateSystemValidator()

        # 创建测试数据
        valid_coords = [(116.4, 39.9), (116.5, 40.0), (116.3, 39.8)]
        invalid_coords = [(200, 100), (300, 200)]  # 超出合理范围

        self.test_gdf_with_crs = gpd.GeoDataFrame({
            'id': [1, 2, 3],
            'geometry': [Point(x, y) for x, y in valid_coords]
        }, crs='EPSG:4326')

        self.test_gdf_no_crs = gpd.GeoDataFrame({
            'id': [1, 2],
            'geometry': [Point(x, y) for x, y in invalid_coords]
        })  # 无CRS

        self.test_gdf_invalid_bounds = gpd.GeoDataFrame({
            'id': [1, 2],
            'geometry': [Point(x, y) for x, y in invalid_coords]
        }, crs='EPSG:4326')

    def test_crs_validation(self):
        """测试坐标系统验证"""
        # 测试有CRS的情况
        report_with_crs = self.validator.validate_geodataframe(self.test_gdf_with_crs)
        self.assertEqual(report_with_crs['summary']['current_crs'], 'EPSG:4326')

        # 测试无CRS的情况
        report_no_crs = self.validator.validate_geodataframe(self.test_gdf_no_crs)
        self.assertIsNone(report_no_crs['summary']['current_crs'])

    def test_bounds_validation(self):
        """测试坐标范围验证"""
        report = self.validator.validate_geodataframe(self.test_gdf_invalid_bounds)

        out_of_bounds_errors = [error for error in report['errors'] if error['error_type'] == 'out_of_bounds']
        self.assertGreater(len(out_of_bounds_errors), 0)

    def test_crs_consistency(self):
        """测试坐标系统一致性"""
        validator_with_target = CoordinateSystemValidator(target_crs='EPSG:3857')
        report = validator_with_target.validate_geodataframe(self.test_gdf_with_crs)

        # 应该检测到CRS不匹配
        crs_errors = [error for error in report['errors'] if error['error_type'] == 'crs_mismatch']
        self.assertGreater(len(crs_errors), 0)

    def test_suggest_crs_transformation(self):
        """测试坐标转换建议"""
        suggestions = self.validator.suggest_crs_transformation(self.test_gdf_with_crs)
        self.assertIn('transformation_needed', suggestions)
        self.assertIn('recommended_crs', suggestions)

    def test_transformation_plan(self):
        """测试转换方案"""
        plan = self.validator.create_transformation_plan('EPSG:4326', 'EPSG:3857')
        self.assertTrue(plan['transformation_possible'])
        self.assertEqual(plan['source_crs'], 'EPSG:4326')
        self.assertEqual(plan['target_crs'], 'EPSG:3857')


class TestDataQualityScorer(unittest.TestCase):
    """数据质量评分器测试"""

    def setUp(self):
        """设置测试数据"""
        self.scorer = DataQualityScorer()

        # 创建高质量测试数据
        high_quality_gdf = gpd.GeoDataFrame({
            'id': range(100),
            'name': [f'feature_{i}' for i in range(100)],
            'value': np.random.uniform(0, 100, 100),
            'type': np.random.choice(['A', 'B', 'C'], 100),
            'geometry': [Point(116.4 + np.random.uniform(-0.1, 0.1),
                              39.9 + np.random.uniform(-0.1, 0.1)) for _ in range(100)]
        }, crs='EPSG:4326')

        # 创建低质量测试数据
        low_quality_gdf = gpd.GeoDataFrame({
            'id': range(10),
            'name': [f'feature_{i}' for i in range(8)] + [None, None],  # 缺失值
            'value': [1, 2, 3, 'invalid', 5, None, 7, 8, 9, 10],  # 类型错误和缺失值
            'type': ['A'] * 5 + ['A'] * 5,  # 重复值
            'geometry': [Point(0, 0) for _ in range(9)] + [Point()]  # 空几何
        }, crs='EPSG:4326')

        self.high_quality_gdf = high_quality_gdf
        self.low_quality_gdf = low_quality_gdf

    def test_high_quality_scoring(self):
        """测试高质量数据评分"""
        report = self.scorer.evaluate_geodataframe(self.high_quality_gdf, "high_quality")

        self.assertGreaterEqual(report['quality_summary']['total_score'], 80)
        self.assertIn(report['quality_summary']['quality_grade'], ['A', 'B'])

    def test_low_quality_scoring(self):
        """测试低质量数据评分"""
        report = self.scorer.evaluate_geodataframe(self.low_quality_gdf, "low_quality")

        self.assertLess(report['quality_summary']['total_score'], 80)
        self.assertIn(report['quality_summary']['quality_grade'], ['C', 'D', 'F'])

    def test_dimension_scores(self):
        """测试维度分数"""
        report = self.scorer.evaluate_geodataframe(self.high_quality_gdf, "test")

        self.assertIn('dimension_scores', report)
        dimensions = ['completeness', 'validity', 'consistency', 'accuracy', 'precision', 'timeliness']
        for dimension in dimensions:
            self.assertIn(dimension, report['dimension_scores'])
            self.assertGreaterEqual(report['dimension_scores'][dimension], 0)
            self.assertLessEqual(report['dimension_scores'][dimension], 100)

    def test_improvement_recommendations(self):
        """测试改进建议"""
        report = self.scorer.evaluate_geodataframe(self.low_quality_gdf, "test")

        self.assertIn('improvement_recommendations', report)
        self.assertGreater(len(report['improvement_recommendations']), 0)

    def test_batch_evaluation(self):
        """测试批量评估"""
        datasets = {
            'high_quality': self.high_quality_gdf,
            'low_quality': self.low_quality_gdf
        }

        batch_report = self.scorer.batch_evaluate(datasets)

        self.assertEqual(batch_report['summary']['total_datasets'], 2)
        self.assertIn('dataset_reports', batch_report)
        self.assertIn('cross_dataset_analysis', batch_report)

    def test_quality_grade_determination(self):
        """测试质量等级确定"""
        # 测试各等级边界值
        self.assertEqual(self.scorer._determine_grade(95).value, 'A')
        self.assertEqual(self.scorer._determine_grade(85).value, 'B')
        self.assertEqual(self.scorer._determine_grade(75).value, 'C')
        self.assertEqual(self.scorer._determine_grade(65).value, 'D')
        self.assertEqual(self.scorer._determine_grade(50).value, 'F')


class TestDataRepairer(unittest.TestCase):
    """数据修复器测试"""

    def setUp(self):
        """设置测试数据"""
        self.repairer = DataRepairer()

        # 创建需要修复的测试数据
        from shapely.validation import make_valid

        # 创建无效多边形（自相交）
        invalid_polygon = Polygon([(0, 0), (2, 0), (1, 1), (2, 2), (0, 2), (1, 1), (0, 0)])

        self.test_gdf = gpd.GeoDataFrame({
            'id': [1, 2, 3, 4],
            'name': ['A', None, 'C', 'D'],  # 缺失值
            'age': [25, '30', None, 40],  # 类型问题
            'geometry': [
                Point(116.4, 39.9),  # 正常点
                invalid_polygon,      # 无效多边形
                Point(),             # 空几何
                LineString([(0, 0), (1, 1)])  # 正常线
            ]
        })

    def test_geometry_repair(self):
        """测试几何修复"""
        repaired_gdf, repair_report = self.repairer.repair_geometry_data(self.test_gdf)

        self.assertIn('successful_operations', repair_report['geometry_repairs'])
        # 修复后应该有更多的有效几何
        repaired_validator = GeometryValidator()
        repaired_report = repaired_validator.validate_geodataframe(repaired_gdf)
        original_report = repaired_validator.validate_geodataframe(self.test_gdf)
        self.assertGreaterEqual(
            repaired_report['summary']['valid_geometries'],
            original_report['summary']['valid_geometries']
        )

    def test_attribute_repair(self):
        """测试属性修复"""
        repaired_gdf, repair_report = self.repairer.repair_attribute_data(self.test_gdf)

        self.assertIn('field_repairs', repair_report['attribute_repairs'])
        # 修复后应该减少缺失值
        missing_after = repaired_gdf['name'].isna().sum()
        missing_before = self.test_gdf['name'].isna().sum()
        self.assertLessEqual(missing_after, missing_before)

    def test_coordinate_repair(self):
        """测试坐标系统修复"""
        # 创建无CRS的测试数据
        no_crs_gdf = self.test_gdf.copy()
        no_crs_gdf.crs = None

        repaired_gdf, repair_report = self.repairer.repair_coordinate_system(no_crs_gdf)

        self.assertIn('successful_operations', repair_report['coordinate_repairs'])
        # 修复后应该有CRS
        self.assertIsNotNone(repaired_gdf.crs)

    def test_comprehensive_repair(self):
        """测试综合修复"""
        repaired_gdf, repair_report = self.repairer.repair_geodataframe(self.test_gdf)

        self.assertIn('summary', repair_report)
        self.assertGreater(repair_report['summary']['total_repair_operations'], 0)

        # 验证修复结果
        if self.repairer.auto_validate:
            self.assertIn('validation_after_repair', repair_report)

    def test_batch_repair(self):
        """测试批量修复"""
        datasets = {
            'dataset1': self.test_gdf,
            'dataset2': self.test_gdf.copy()
        }

        repair_results = self.repairer.batch_repair_datasets(datasets)

        self.assertEqual(len(repair_results), 2)
        for name, (repaired_gdf, repair_report) in repair_results.items():
            self.assertIsInstance(repaired_gdf, gpd.GeoDataFrame)
            self.assertIsInstance(repair_report, dict)

    def test_repair_history(self):
        """测试修复历史"""
        # 执行修复操作
        self.repairer.repair_geodataframe(self.test_gdf)

        # 检查修复历史
        history = self.repairer.get_repair_summary()
        self.assertGreater(history['total_repair_sessions'], 0)
        self.assertIn('total_operations', history)

        # 清空历史
        self.repairer.clear_repair_history()
        history_after_clear = self.repairer.get_repair_summary()
        self.assertEqual(history_after_clear['message'], '暂无修复历史')


class TestIntegration(unittest.TestCase):
    """集成测试"""

    def setUp(self):
        """设置集成测试数据"""
        # 创建模拟的真实GIS数据
        np.random.seed(42)  # 确保可重现性

        # 横断面点数据 (20,385个)
        hdm_points = 100  # 使用较小数量进行测试
        self.hdm_points_gdf = gpd.GeoDataFrame({
            'id': range(hdm_points),
            'elevation': np.random.uniform(100, 1000, hdm_points),
            'type': np.random.choice(['A', 'B', 'C'], hdm_points),
            'code': [f'HDM_{i:05d}' for i in range(hdm_points)],
            'geometry': [
                Point(116.0 + np.random.uniform(-1, 1),
                      39.5 + np.random.uniform(-1, 1))
                for _ in range(hdm_points)
            ]
        }, crs='EPSG:4326')

        # 横断面线数据 (583条)
        hdm_lines = 50  # 使用较小数量进行测试
        self.hdm_lines_gdf = gpd.GeoDataFrame({
            'id': range(hdm_lines),
            'length': np.random.uniform(100, 5000, hdm_lines),
            'name': [f'横断面线_{i}' for i in range(hdm_lines)],
            'geometry': [
                LineString([
                    (116.0 + np.random.uniform(-1, 1), 39.5 + np.random.uniform(-1, 1)),
                    (116.0 + np.random.uniform(-1, 1), 39.5 + np.random.uniform(-1, 1)),
                    (116.0 + np.random.uniform(-1, 1), 39.5 + np.random.uniform(-1, 1))
                ])
                for _ in range(hdm_lines)
            ]
        }, crs='EPSG:4326')

    def test_full_validation_pipeline(self):
        """测试完整验证流程"""
        # 创建质量评分器
        scorer = DataQualityScorer()

        # 评估点数据质量
        points_report = scorer.evaluate_geodataframe(self.hdm_points_gdf, "横断面点")
        self.assertIn('quality_summary', points_report)
        self.assertGreater(points_report['quality_summary']['total_score'], 0)

        # 评估线数据质量
        lines_report = scorer.evaluate_geodataframe(self.hdm_lines_gdf, "横断面线")
        self.assertIn('quality_summary', lines_report)
        self.assertGreater(lines_report['quality_summary']['total_score'], 0)

    def test_repair_and_revalidate(self):
        """测试修复和重新验证"""
        # 创建修复器
        repairer = DataRepairer()

        # 人为添加一些问题数据
        damaged_gdf = self.hdm_points_gdf.copy()
        damaged_gdf.loc[0, 'elevation'] = None  # 添加缺失值
        damaged_gdf.loc[1, 'type'] = 999  # 添加无效类型

        # 修复数据
        repaired_gdf, repair_report = repairer.repair_geodataframe(damaged_gdf)

        # 重新评估质量
        scorer = DataQualityScorer()
        original_score = scorer.evaluate_geodataframe(damaged_gdf, "original")['quality_summary']['total_score']
        repaired_score = scorer.evaluate_geodataframe(repaired_gdf, "repaired")['quality_summary']['total_score']

        # 修复后分数应该不低于修复前
        self.assertGreaterEqual(repaired_score, original_score)

    def test_validation_with_algorithms_integration(self):
        """测试与算法模块的集成"""
        try:
            # 尝试导入算法模块
            from ..algorithms.association import NearestNeighborAssociator
            from ..algorithms.intersection import LineIntersectionDetector
            from ..algorithms.containment import PolygonContainmentAnalyzer

            # 验证数据质量
            scorer = DataQualityScorer()
            points_quality = scorer.evaluate_geodataframe(self.hdm_points_gdf, "points_for_algorithm")

            # 如果质量分数足够高，可以尝试运行算法
            if points_quality['quality_summary']['total_score'] > 70:
                # 创建关联器
                associator = NearestNeighborAssociator()
                # 这里只是测试导入和初始化，不实际运行算法
                self.assertIsNotNone(associator)

        except ImportError as e:
            # 算法模块不可用时跳过此测试
            self.skipTest(f"算法模块不可用: {e}")

    def test_export_and_import_quality_reports(self):
        """测试质量报告的导出和导入"""
        scorer = DataQualityScorer()
        report = scorer.evaluate_geodataframe(self.hdm_points_gdf, "test_export")

        # 测试JSON导出
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            scorer.export_quality_report("test_export", f.name, 'json')
            json_path = f.name

        try:
            # 验证文件存在且不为空
            self.assertTrue(os.path.exists(json_path))
            self.assertGreater(os.path.getsize(json_path), 0)
        finally:
            # 清理临时文件
            if os.path.exists(json_path):
                os.unlink(json_path)


def run_validation_tests():
    """运行所有验证测试"""
    # 创建测试套件
    test_suite = unittest.TestSuite()

    # 添加所有测试类
    test_classes = [
        TestGeometryValidator,
        TestAttributeValidator,
        TestCoordinateSystemValidator,
        TestDataQualityScorer,
        TestDataRepairer,
        TestIntegration
    ]

    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    print("开始运行GIS数据验证模块测试...")
    success = run_validation_tests()
    if success:
        print("\n所有测试通过！验证模块功能正常。")
    else:
        print("\n部分测试失败，请检查验证模块实现。")