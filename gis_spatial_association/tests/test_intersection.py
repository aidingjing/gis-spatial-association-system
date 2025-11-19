"""
线-线相交检测算法单元测试

测试LineIntersectionDetector类的各种功能和边界条件。

Author: CCPM Auto Development System
"""

import unittest
import numpy as np
import geopandas as gpd
from shapely.geometry import LineString, Point
import pandas as pd

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from algorithms.intersection import LineIntersectionDetector, create_detector


class TestLineIntersectionDetector(unittest.TestCase):
    """线-线相交检测算法测试类"""

    def setUp(self):
        """测试前的设置"""
        # 创建测试用的横断面线数据
        self.h_lines_data = [
            {'id': 'h_line_1', 'geometry': LineString([(0, 0), (10, 0)])},  # 水平线
            {'id': 'h_line_2', 'geometry': LineString([(0, 5), (10, 5)])},  # 水平线
            {'id': 'h_line_3', 'geometry': LineString([(0, 10), (10, 10)])},  # 水平线
        ]
        self.h_lines_gdf = gpd.GeoDataFrame(self.h_lines_data, crs='EPSG:4326')

        # 创建测试用的纵断面线数据
        self.v_lines_data = [
            {'id': 'v_line_1', 'geometry': LineString([(2, -2), (2, 12)])},  # 垂直线，与所有h_lines相交
            {'id': 'v_line_2', 'geometry': LineString([(8, 3), (8, 8)])},    # 垂直线，与部分h_lines相交
            {'id': 'v_line_3', 'geometry': LineString([(15, 5), (20, 5)])},  # 平行线，不相交
        ]
        self.v_lines_gdf = gpd.GeoDataFrame(self.v_lines_data, crs='EPSG:4326')

        # 创建检测器
        self.detector = LineIntersectionDetector(
            intersection_tolerance=1e-6,
            use_spatial_index=True
        )

    def test_initialization(self):
        """测试初始化"""
        # 测试默认初始化
        detector = LineIntersectionDetector()
        self.assertEqual(detector.intersection_tolerance, 1e-6)
        self.assertTrue(detector.use_spatial_index)

        # 测试自定义初始化
        detector = LineIntersectionDetector(
            intersection_tolerance=1e-5,
            use_spatial_index=False
        )
        self.assertEqual(detector.intersection_tolerance, 1e-5)
        self.assertFalse(detector.use_spatial_index)

    def test_spatial_index_building(self):
        """测试空间索引构建"""
        # 测试正常索引构建
        tree = self.detector._build_spatial_index(self.h_lines_gdf)
        self.assertIsNotNone(tree)

        # 测试空数据
        empty_gdf = gpd.GeoDataFrame(geometry=[], crs='EPSG:4326')
        tree = self.detector._build_spatial_index(empty_gdf)
        self.assertIsNone(tree)

    def test_line_midpoint_calculation(self):
        """测试线段中点计算"""
        line = LineString([(0, 0), (10, 0)])
        midpoint = self.detector._calculate_line_midpoint(line)

        expected = Point(5, 0)
        self.assertAlmostEqual(midpoint.x, expected.x, places=6)
        self.assertAlmostEqual(midpoint.y, expected.y, places=6)

        # 测试垂直线
        v_line = LineString([(0, 0), (0, 10)])
        v_midpoint = self.detector._calculate_line_midpoint(v_line)

        v_expected = Point(0, 5)
        self.assertAlmostEqual(v_midpoint.x, v_expected.x, places=6)
        self.assertAlmostEqual(v_midpoint.y, v_expected.y, places=6)

    def test_intersection_type_determination(self):
        """测试相交类型判断"""
        # 完全相交（垂直）
        h_line = LineString([(0, 0), (10, 0)])
        v_line = LineString([(5, -5), (5, 5)])
        intersection_type = self.detector._determine_intersection_type(v_line, h_line)
        self.assertEqual(intersection_type, 'crosses')

        # 端点相交
        h_line = LineString([(0, 0), (10, 0)])
        v_line = LineString([(10, -5), (10, 5)])
        intersection_type = self.detector._determine_intersection_type(v_line, h_line)
        self.assertIn(intersection_type, ['touches', 'crosses'])

        # 不相交
        h_line = LineString([(0, 0), (10, 0)])
        v_line = LineString([(20, -5), (20, 5)])
        intersection_type = self.detector._determine_intersection_type(v_line, h_line)
        self.assertEqual(intersection_type, 'none')

    def test_brute_force_intersection_finding(self):
        """测试暴力搜索相交查找"""
        v_line = LineString([(2, -2), (2, 12)])
        intersections = self.detector._find_intersections_brute_force(
            v_line, self.h_lines_gdf
        )

        # 应该找到3个相交
        self.assertEqual(len(intersections), 3)

        # 验证相交信息
        for intersection in intersections:
            self.assertIn('h_line_id', intersection)
            self.assertIn('v_line_id', intersection)
            self.assertIn('intersection_point', intersection)
            self.assertIn('distance_to_midpoint', intersection)
            self.assertIsInstance(intersection['intersection_point'], Point)
            self.assertGreaterEqual(intersection['distance_to_midpoint'], 0)

    def test_indexed_intersection_finding(self):
        """测试空间索引相交查找"""
        # 构建空间索引
        self.detector._build_spatial_index(self.h_lines_gdf)

        v_line = LineString([(2, -2), (2, 12)])
        intersections = self.detector._find_intersections_indexed(
            v_line, self.h_lines_gdf
        )

        # 应该找到3个相交
        self.assertEqual(len(intersections), 3)

    def test_intersection_geometry_processing(self):
        """测试相交几何处理"""
        # 测试点相交
        point = Point(5, 0)
        v_line = LineString([(5, -5), (5, 5)])
        h_line = LineString([(0, 0), (10, 0)])

        points = self.detector._process_intersection_geometry(point, v_line, h_line)
        self.assertEqual(len(points), 1)
        self.assertIsInstance(points[0], Point)

    def test_duplicate_points_filtering(self):
        """测试重复点过滤"""
        # 创建几乎相同的点
        points = [
            Point(5.0000001, 0.0),
            Point(5.0000002, 0.0),
            Point(10.0, 0.0)
        ]

        filtered_points = self.detector._filter_duplicate_points(points)

        # 应该过滤掉重复点
        self.assertEqual(len(filtered_points), 2)

    def test_full_intersection_detection(self):
        """测试完整的相交检测过程"""
        intersections = self.detector.find_intersections(self.h_lines_gdf, self.v_lines_gdf)

        # 验证结果不为空
        self.assertGreater(len(intersections), 0)

        # 验证相交结果结构
        for intersection in intersections:
            self.assertIn('h_line_id', intersection)
            self.assertIn('v_line_id', intersection)
            self.assertIn('intersection_point', intersection)
            self.assertIn('distance_to_midpoint', intersection)

    def test_progress_callback(self):
        """测试进度回调功能"""
        progress_calls = []

        def progress_callback(progress, current, total):
            progress_calls.append((progress, current, total))

        self.detector.find_intersections(
            self.h_lines_gdf, self.v_lines_gdf,
            progress_callback=progress_callback
        )

        # 验证进度回调被调用
        self.assertGreater(len(progress_calls), 0)

        # 验证进度值合理
        for progress, current, total in progress_calls:
            self.assertGreaterEqual(progress, 0)
            self.assertLessEqual(progress, 100)

    def test_multiple_intersections_resolution(self):
        """测试一对多相交解决"""
        # 创建一对多相交的情况
        # 一条垂直线与多条水平线相交
        h_lines_multi = [
            {'id': 'h_1', 'geometry': LineString([(0, 0), (10, 0)])},
            {'id': 'h_2', 'geometry': LineString([(0, 1), (10, 1)])},
            {'id': 'h_3', 'geometry': LineString([(0, 2), (10, 2)])},
        ]
        h_lines_multi_gdf = gpd.GeoDataFrame(h_lines_multi, crs='EPSG:4326')

        v_lines_multi = [
            {'id': 'v_1', 'geometry': LineString([(5, -1), (5, 3)])},
        ]
        v_lines_multi_gdf = gpd.GeoDataFrame(v_lines_multi, crs='EPSG:4326')

        intersections = self.detector.find_intersections(h_lines_multi_gdf, v_lines_multi_gdf)
        resolved = self.detector.resolve_intersections(intersections)

        # 对于单条纵断面，应该有3个原始相交
        self.assertEqual(len(intersections), 3)

        # 解决后每条横断面应该只有一个关联
        h_line_ids = set([assoc['h_line_id'] for assoc in resolved])
        self.assertEqual(len(h_line_ids), 3)

    def test_statistics_tracking(self):
        """测试统计信息跟踪"""
        self.detector.find_intersections(self.h_lines_gdf, self.v_lines_gdf)
        stats = self.detector.get_detection_statistics()

        # 验证统计信息
        self.assertEqual(stats['total_h_lines'], len(self.h_lines_gdf))
        self.assertEqual(stats['total_v_lines'], len(self.v_lines_gdf))
        self.assertGreater(stats['raw_intersections'], 0)
        self.assertGreater(stats['processing_time'], 0)

    def test_result_gdf_building(self):
        """测试结果GeoDataFrame构建"""
        intersections = self.detector.find_intersections(self.h_lines_gdf, self.v_lines_gdf)
        resolved = self.detector.resolve_intersections(intersections)

        result_gdf = self.detector.build_result_gdf(
            resolved, self.h_lines_gdf, self.v_lines_gdf
        )

        # 验证结果结构
        self.assertGreater(len(result_gdf), 0)
        self.assertIn('h_line_id', result_gdf.columns)
        self.assertIn('v_line_id', result_gdf.columns)
        self.assertIn('intersection_point', result_gdf.columns)
        self.assertIn('distance_to_midpoint', result_gdf.columns)

        # 验证几何体类型为点
        self.assertTrue(all(geom.geom_type == 'Point' for geom in result_gdf.geometry))

    def test_result_validation(self):
        """测试结果验证"""
        intersections = self.detector.find_intersections(self.h_lines_gdf, self.v_lines_gdf)
        resolved = self.detector.resolve_intersections(intersections)
        result_gdf = self.detector.build_result_gdf(resolved)

        validation_stats = self.detector.validate_associations(result_gdf)

        # 验证结果统计
        self.assertIn('total_associations', validation_stats)
        self.assertIn('null_geometries', validation_stats)
        self.assertIn('invalid_distances', validation_stats)

        # 对于有效数据，不应该有无效结果
        self.assertEqual(validation_stats['null_geometries'], 0)
        self.assertEqual(validation_stats['invalid_distances'], 0)

    def test_empty_data_handling(self):
        """测试空数据处理"""
        empty_h_lines = gpd.GeoDataFrame(geometry=[], crs='EPSG:4326')
        empty_v_lines = gpd.GeoDataFrame(geometry=[], crs='EPSG:4326')

        # 测试空横断面
        intersections = self.detector.find_intersections(empty_h_lines, self.v_lines_gdf)
        self.assertEqual(len(intersections), 0)

        # 测试空纵断面
        intersections = self.detector.find_intersections(self.h_lines_gdf, empty_v_lines)
        self.assertEqual(len(intersections), 0)

    def test_edge_cases(self):
        """测试边界条件"""
        # 测试零长度线
        zero_length_data = [
            {'id': 'zero_line', 'geometry': LineString([(5, 5), (5, 5)])},
        ]
        zero_length_gdf = gpd.GeoDataFrame(zero_length_data, crs='EPSG:4326')

        intersections = self.detector.find_intersections(self.h_lines_gdf, zero_length_gdf)
        # 零长度线不应该产生相交
        self.assertEqual(len(intersections), 0)

        # 测试None几何体
        h_lines_with_none = self.h_lines_gdf.copy()
        h_lines_with_none.iloc[0, h_lines_with_none.columns.get_loc('geometry')] = None

        intersections = self.detector.find_intersections(h_lines_with_none, self.v_lines_gdf)
        # 应该跳过None几何体
        self.assertLess(len(intersections), len(self.v_lines_gdf) * (len(self.h_lines_gdf) - 1))

    def test_create_detector_factory(self):
        """测试工厂函数"""
        # 测试默认配置
        detector = create_detector()
        self.assertIsInstance(detector, LineIntersectionDetector)
        self.assertTrue(detector.use_spatial_index)

        # 测试自定义配置
        config = {
            'intersection_tolerance': 1e-5,
            'use_spatial_index': False
        }
        detector = create_detector(config)
        self.assertEqual(detector.intersection_tolerance, 1e-5)
        self.assertFalse(detector.use_spatial_index)


class TestIntersectionComplexGeometry(unittest.TestCase):
    """复杂几何测试类"""

    def setUp(self):
        """创建复杂几何测试数据"""
        self.detector = LineIntersectionDetector()

        # 创建复杂几何线
        self.complex_lines_data = [
            {
                'id': 'complex_line_1',
                'geometry': LineString([(0, 0), (5, 5), (10, 0), (15, 5), (20, 0)])
            },
            {
                'id': 'complex_line_2',
                'geometry': LineString([(10, -10), (10, 10)])
            },
            {
                'id': 'curve_line',
                'geometry': LineString([(0, 0), (2, 3), (5, 6), (8, 4), (10, 0)])
            }
        ]
        self.complex_lines_gdf = gpd.GeoDataFrame(self.complex_lines_data, crs='EPSG:4326')

    def test_complex_line_intersections(self):
        """测试复杂线相交"""
        intersections = self.detector.find_intersections(
            self.complex_lines_gdf.iloc[:2],
            self.complex_lines_gdf.iloc[1:]
        )

        # 复杂线可能有多个交点
        self.assertGreaterEqual(len(intersections), 0)

        # 验证交点的合理性
        for intersection in intersections:
            self.assertIsInstance(intersection['intersection_point'], Point)
            self.assertGreaterEqual(intersection['distance_to_midpoint'], 0)


class TestIntersectionPerformance(unittest.TestCase):
    """性能测试类"""

    def setUp(self):
        """创建大量测试数据"""
        np.random.seed(42)

        # 创建大量横断面线
        num_h_lines = 100
        self.h_lines_data = []

        for i in range(num_h_lines):
            y = i * 10  # 规则间距
            self.h_lines_data.append({
                'id': f'h_line_{i}',
                'geometry': LineString([(0, y), (100, y)])
            })

        self.h_lines_gdf = gpd.GeoDataFrame(self.h_lines_data, crs='EPSG:4326')

        # 创建大量纵断面线
        num_v_lines = 50
        self.v_lines_data = []

        for i in range(num_v_lines):
            x = i * 20  # 规则间距
            self.v_lines_data.append({
                'id': f'v_line_{i}',
                'geometry': LineString([(x, -10), (x, (num_h_lines - 1) * 10 + 10)])
            })

        self.v_lines_gdf = gpd.GeoDataFrame(self.v_lines_data, crs='EPSG:4326')

    def test_performance_with_spatial_index(self):
        """测试空间索引性能"""
        detector = LineIntersectionDetector(use_spatial_index=True)

        import time
        start_time = time.time()
        intersections = detector.find_intersections(self.h_lines_gdf, self.v_lines_gdf)
        processing_time = time.time() - start_time

        # 验证结果合理性
        expected_intersections = len(self.h_lines_gdf) * len(self.v_lines_gdf)
        self.assertEqual(len(intersections), expected_intersections)
        self.assertLess(processing_time, 30.0)  # 应该在30秒内完成

    def test_performance_without_spatial_index(self):
        """测试无空间索引性能"""
        detector = LineIntersectionDetector(use_spatial_index=False)

        import time
        start_time = time.time()
        intersections = detector.find_intersections(self.h_lines_gdf, self.v_lines_gdf)
        processing_time = time.time() - start_time

        # 验证结果正确性
        expected_intersections = len(self.h_lines_gdf) * len(self.v_lines_gdf)
        self.assertEqual(len(intersections), expected_intersections)


if __name__ == '__main__':
    unittest.main()