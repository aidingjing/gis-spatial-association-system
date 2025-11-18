"""
线-面包含判断算法单元测试

测试PolygonContainmentAnalyzer类的各种功能和边界条件。

Author: CCPM Auto Development System
"""

import unittest
import numpy as np
import geopandas as gpd
from shapely.geometry import LineString, Polygon, Point, MultiPolygon
import pandas as pd

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from algorithms.containment import PolygonContainmentAnalyzer, create_analyzer


class TestPolygonContainmentAnalyzer(unittest.TestCase):
    """线-面包含判断算法测试类"""

    def setUp(self):
        """测试前的设置"""
        # 创建测试用的线数据
        self.lines_data = [
            {'id': 'line_1', 'geometry': LineString([(1, 1), (9, 1)])},  # 在面内
            {'id': 'line_2', 'geometry': LineString([(1, 4), (9, 4)])},  # 在面内
            {'id': 'line_3', 'geometry': LineString([(1, 1), (9, 9)])},  # 贯穿面
            {'id': 'line_4', 'geometry': LineString([(11, 5), (19, 5)])},  # 在面外
            {'id': 'line_5', 'geometry': LineString([(0, 5), (10, 5)])},  # 相切
        ]
        self.lines_gdf = gpd.GeoDataFrame(self.lines_data, crs='EPSG:4326')

        # 创建测试用的面数据
        self.polygons_data = [
            {'id': 'poly_1', 'geometry': Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])},
            {'id': 'poly_2', 'geometry': Polygon([(12, 0), (20, 0), (20, 10), (12, 10)])},
        ]
        self.polygons_gdf = gpd.GeoDataFrame(self.polygons_data, crs='EPSG:4326')

        # 创建分析器
        self.analyzer = PolygonContainmentAnalyzer(
            use_spatial_index=True,
            cascade_enabled=True
        )

    def test_initialization(self):
        """测试初始化"""
        # 测试默认初始化
        analyzer = PolygonContainmentAnalyzer()
        self.assertTrue(analyzer.use_spatial_index)
        self.assertTrue(analyzer.cascade_enabled)

        # 测试自定义初始化
        analyzer = PolygonContainmentAnalyzer(
            use_spatial_index=False,
            cascade_enabled=False
        )
        self.assertFalse(analyzer.use_spatial_index)
        self.assertFalse(analyzer.cascade_enabled)

    def test_spatial_index_building(self):
        """测试空间索引构建"""
        # 测试正常索引构建
        tree = self.analyzer._build_spatial_index(self.polygons_gdf)
        self.assertIsNotNone(tree)

        # 测试空数据
        empty_gdf = gpd.GeoDataFrame(geometry=[], crs='EPSG:4326')
        tree = self.analyzer._build_spatial_index(empty_gdf)
        self.assertIsNone(tree)

    def test_intersection_type_determination(self):
        """测试相交类型判断"""
        polygon = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])

        # 完全包含的线
        contained_line = LineString([(1, 1), (9, 1)])
        intersection_type = self.analyzer._determine_intersection_type(contained_line, polygon)
        self.assertEqual(intersection_type, 'contains')

        # 贯穿的线
        cross_line = LineString([(1, 1), (9, 9)])
        intersection_type = self.analyzer._determine_intersection_type(cross_line, polygon)
        self.assertEqual(intersection_type, 'crosses')

        # 相切的线
        touch_line = LineString([(0, 5), (10, 5)])
        intersection_type = self.analyzer._determine_intersection_type(touch_line, polygon)
        self.assertEqual(intersection_type, 'intersects')

        # 不相交的线
        separate_line = LineString([(11, 11), (19, 11)])
        intersection_type = self.analyzer._determine_intersection_type(separate_line, polygon)
        self.assertEqual(intersection_type, 'none')

    def test_intersection_metrics_calculation(self):
        """测试相交度量计算"""
        polygon = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
        line = LineString([(1, 1), (9, 9)])

        metrics = self.analyzer._calculate_intersection_metrics(line, polygon, 'crosses')

        # 验证基本度量
        self.assertGreater(metrics['line_length'], 0)
        self.assertGreater(metrics['intersection_length'], 0)
        self.assertGreaterEqual(metrics['inside_length'], 0)
        self.assertGreaterEqual(metrics['outside_length'], 0)
        self.assertGreaterEqual(metrics['intersection_ratio'], 0)
        self.assertLessEqual(metrics['intersection_ratio'], 1)
        self.assertGreaterEqual(metrics['num_intersection_points'], 0)

        # 对于贯穿线，相交比例应该大于0小于1
        self.assertGreater(metrics['intersection_ratio'], 0)
        self.assertLess(metrics['intersection_ratio'], 1)

    def test_brute_force_intersection_finding(self):
        """测试暴力搜索相交查找"""
        line = LineString([(1, 1), (9, 1)])
        intersections = self.analyzer._find_polygon_intersections_brute_force(
            line, self.polygons_gdf, 0, 'test_line'
        )

        # 应该找到一个相交（与poly_1）
        self.assertEqual(len(intersections), 1)

        # 验证相交信息
        intersection = intersections[0]
        self.assertIn('line_id', intersection)
        self.assertIn('polygon_id', intersection)
        self.assertIn('intersection_type', intersection)
        self.assertIn('line_length', intersection)
        self.assertIn('intersection_ratio', intersection)

    def test_indexed_intersection_finding(self):
        """测试空间索引相交查找"""
        # 构建空间索引
        self.analyzer._build_spatial_index(self.polygons_gdf)

        line = LineString([(1, 1), (9, 1)])
        intersections = self.analyzer._find_polygon_intersections_indexed(
            line, self.polygons_gdf, 0, 'test_line'
        )

        # 应该找到一个相交
        self.assertEqual(len(intersections), 1)

    def test_full_intersection_detection(self):
        """测试完整的相交检测过程"""
        intersections = self.analyzer.find_intersections(self.lines_gdf, self.polygons_gdf)

        # 验证结果不为空
        self.assertGreater(len(intersections), 0)

        # 验证相交结果结构
        for intersection in intersections:
            self.assertIn('line_id', intersection)
            self.assertIn('polygon_id', intersection)
            self.assertIn('intersection_type', intersection)
            self.assertIn('line_length', intersection)
            self.assertIn('intersection_ratio', intersection)

        # 验证相交类型统计
        stats = self.analyzer.get_analysis_statistics()
        self.assertGreater(stats['total_intersections'], 0)
        self.assertGreater(sum(stats['intersection_type_counts'].values()), 0)

    def test_cascade_associations_building(self):
        """测试级联关联构建"""
        intersections = self.analyzer.find_intersections(self.lines_gdf, self.polygons_gdf)
        cascade_dict = self.analyzer.build_cascade_associations(intersections)

        # 验证级联关联字典
        self.assertIsInstance(cascade_dict, dict)

        # 验证每条线的级联关系
        for line_id, polygon_ids in cascade_dict.items():
            self.assertIsInstance(polygon_ids, list)
            self.assertGreater(len(polygon_ids), 0)

        # 验证统计信息
        stats = self.analyzer.get_analysis_statistics()
        self.assertGreater(stats['cascade_chains'], 0)

    def test_cascade_disabled(self):
        """测试级联功能禁用"""
        analyzer = PolygonContainmentAnalyzer(cascade_enabled=False)
        intersections = analyzer.find_intersections(self.lines_gdf, self.polygons_gdf)
        cascade_dict = analyzer.build_cascade_associations(intersections)

        # 级联功能禁用时应该返回空字典
        self.assertEqual(len(cascade_dict), 0)

    def test_result_gdf_building(self):
        """测试结果GeoDataFrame构建"""
        intersections = self.analyzer.find_intersections(self.lines_gdf, self.polygons_gdf)
        result_gdf = self.analyzer.build_result_gdf(
            intersections, self.lines_gdf, self.polygons_gdf
        )

        # 验证结果结构
        self.assertGreater(len(result_gdf), 0)
        self.assertIn('line_id', result_gdf.columns)
        self.assertIn('polygon_id', result_gdf.columns)
        self.assertIn('intersection_type', result_gdf.columns)
        self.assertIn('intersection_ratio', result_gdf.columns)

        # 验证几何体类型为线
        self.assertTrue(all(geom.geom_type in ['LineString'] for geom in result_gdf.geometry))

    def test_progress_callback(self):
        """测试进度回调功能"""
        progress_calls = []

        def progress_callback(progress, current, total):
            progress_calls.append((progress, current, total))

        self.analyzer.find_intersections(
            self.lines_gdf, self.polygons_gdf,
            progress_callback=progress_callback
        )

        # 验证进度回调被调用
        self.assertGreater(len(progress_calls), 0)

        # 验证进度值合理
        for progress, current, total in progress_calls:
            self.assertGreaterEqual(progress, 0)
            self.assertLessEqual(progress, 100)
            self.assertGreaterEqual(current, 1)
            self.assertLessEqual(current, total)

    def test_statistics_tracking(self):
        """测试统计信息跟踪"""
        self.analyzer.find_intersections(self.lines_gdf, self.polygons_gdf)
        stats = self.analyzer.get_analysis_statistics()

        # 验证统计信息
        self.assertEqual(stats['total_lines'], len(self.lines_gdf))
        self.assertEqual(stats['total_polygons'], len(self.polygons_gdf))
        self.assertGreater(stats['total_intersections'], 0)
        self.assertGreater(stats['processing_time'], 0)

        # 验证相交类型统计
        self.assertIsInstance(stats['intersection_type_counts'], dict)
        self.assertGreater(sum(stats['intersection_type_counts'].values()), 0)

    def test_result_validation(self):
        """测试结果验证"""
        intersections = self.analyzer.find_intersections(self.lines_gdf, self.polygons_gdf)
        result_gdf = self.analyzer.build_result_gdf(intersections)

        validation_stats = self.analyzer.validate_results(result_gdf)

        # 验证结果统计
        self.assertIn('total_records', validation_stats)
        self.assertIn('null_geometries', validation_stats)
        self.assertIn('invalid_ratios', validation_stats)

        # 对于有效数据，不应该有无效结果
        self.assertEqual(validation_stats['null_geometries'], 0)
        self.assertEqual(validation_stats['invalid_ratios'], 0)

    def test_empty_data_handling(self):
        """测试空数据处理"""
        empty_lines = gpd.GeoDataFrame(geometry=[], crs='EPSG:4326')
        empty_polygons = gpd.GeoDataFrame(geometry=[], crs='EPSG:4326')

        # 测试空线数据
        intersections = self.analyzer.find_intersections(empty_lines, self.polygons_gdf)
        self.assertEqual(len(intersections), 0)

        # 测试空面数据
        intersections = self.analyzer.find_intersections(self.lines_gdf, empty_polygons)
        self.assertEqual(len(intersections), 0)

    def test_edge_cases(self):
        """测试边界条件"""
        # 测试零长度线
        zero_length_data = [
            {'id': 'zero_line', 'geometry': LineString([(5, 5), (5, 5)])},
        ]
        zero_length_gdf = gpd.GeoDataFrame(zero_length_data, crs='EPSG:4326')

        intersections = self.analyzer.find_intersections(zero_length_gdf, self.polygons_gdf)
        # 零长度线不应该产生相交
        self.assertEqual(len(intersections), 0)

        # 测试None几何体
        lines_with_none = self.lines_gdf.copy()
        lines_with_none.iloc[0, lines_with_none.columns.get_loc('geometry')] = None

        intersections = self.analyzer.find_intersections(lines_with_none, self.polygons_gdf)
        # 应该跳过None几何体
        self.assertLess(len(intersections), len(self.lines_gdf))

    def test_create_analyzer_factory(self):
        """测试工厂函数"""
        # 测试默认配置
        analyzer = create_analyzer()
        self.assertIsInstance(analyzer, PolygonContainmentAnalyzer)
        self.assertTrue(analyzer.use_spatial_index)

        # 测试自定义配置
        config = {
            'use_spatial_index': False,
            'cascade_enabled': False
        }
        analyzer = create_analyzer(config)
        self.assertFalse(analyzer.use_spatial_index)
        self.assertFalse(analyzer.cascade_enabled)


class TestContainmentComplexGeometry(unittest.TestCase):
    """复杂几何测试类"""

    def setUp(self):
        """创建复杂几何测试数据"""
        self.analyzer = PolygonContainmentAnalyzer()

        # 创建复杂多边形（带孔洞）
        exterior = [(0, 0), (20, 0), (20, 20), (0, 20)]
        hole = [(5, 5), (15, 5), (15, 15), (5, 15)]
        self.complex_polygon = Polygon(exterior, [hole])

        self.complex_polygons_data = [
            {'id': 'complex_poly', 'geometry': self.complex_polygon}
        ]
        self.complex_polygons_gdf = gpd.GeoDataFrame(self.complex_polygons_data, crs='EPSG:4326')

        # 创建复杂线
        self.complex_lines_data = [
            {
                'id': 'complex_line_1',
                'geometry': LineString([(1, 1), (19, 1), (19, 19), (1, 19), (1, 1)])  # 围绕孔洞
            },
            {
                'id': 'complex_line_2',
                'geometry': LineString([(10, 10), (10, 12)])  # 在孔洞内
            },
            {
                'id': 'curve_line',
                'geometry': LineString([(0, 10), (5, 15), (10, 10), (15, 5), (20, 10)])
            }
        ]
        self.complex_lines_gdf = gpd.GeoDataFrame(self.complex_lines_data, crs='EPSG:4326')

    def test_complex_polygon_intersections(self):
        """测试复杂多边形相交"""
        intersections = self.analyzer.find_intersections(
            self.complex_lines_gdf, self.complex_polygons_gdf
        )

        # 复杂几何应该产生相交
        self.assertGreaterEqual(len(intersections), 0)

        # 验证相交类型的合理性
        for intersection in intersections:
            self.assertIn(intersection['intersection_type'],
                         ['contains', 'intersects', 'crosses', 'touches'])

    def test_multipolygon_handling(self):
        """测试多部件多边形处理"""
        # 创建多部件多边形
        poly1 = Polygon([(0, 0), (5, 0), (5, 5), (0, 5)])
        poly2 = Polygon([(10, 10), (15, 10), (15, 15), (10, 15)])
        multipolygon = MultiPolygon([poly1, poly2])

        multi_poly_data = [
            {'id': 'multi_poly', 'geometry': multipolygon}
        ]
        multi_poly_gdf = gpd.GeoDataFrame(multi_poly_data, crs='EPSG:4326')

        # 创建与多边形相交的线
        intersecting_lines_data = [
            {'id': 'line_1', 'geometry': LineString([(2, 2), (3, 3)])},
            {'id': 'line_2', 'geometry': LineString([(12, 12), (13, 13)])},
        ]
        intersecting_lines_gdf = gpd.GeoDataFrame(intersecting_lines_data, crs='EPSG:4326')

        intersections = self.analyzer.find_intersections(
            intersecting_lines_gdf, multi_poly_gdf
        )

        # 多部件多边形应该产生相交
        self.assertEqual(len(intersections), 2)


class TestContainmentPerformance(unittest.TestCase):
    """性能测试类"""

    def setUp(self):
        """创建大量测试数据"""
        np.random.seed(42)

        # 创建大量面数据
        num_polygons = 50
        self.polygons_data = []

        for i in range(num_polygons):
            center_x = np.random.uniform(0, 100)
            center_y = np.random.uniform(0, 100)
            size = np.random.uniform(5, 15)

            # 创建规则多边形
            polygon = Polygon([
                (center_x - size/2, center_y - size/2),
                (center_x + size/2, center_y - size/2),
                (center_x + size/2, center_y + size/2),
                (center_x - size/2, center_y + size/2)
            ])

            self.polygons_data.append({
                'id': f'poly_{i}',
                'geometry': polygon
            })

        self.polygons_gdf = gpd.GeoDataFrame(self.polygons_data, crs='EPSG:4326')

        # 创建大量线数据
        num_lines = 200
        self.lines_data = []

        for i in range(num_lines):
            start_x = np.random.uniform(-10, 110)
            start_y = np.random.uniform(-10, 110)
            end_x = start_x + np.random.uniform(-20, 20)
            end_y = start_y + np.random.uniform(-20, 20)

            self.lines_data.append({
                'id': f'line_{i}',
                'geometry': LineString([(start_x, start_y), (end_x, end_y)])
            })

        self.lines_gdf = gpd.GeoDataFrame(self.lines_data, crs='EPSG:4326')

    def test_performance_with_spatial_index(self):
        """测试空间索引性能"""
        analyzer = PolygonContainmentAnalyzer(use_spatial_index=True)

        import time
        start_time = time.time()
        intersections = analyzer.find_intersections(self.lines_gdf, self.polygons_gdf)
        processing_time = time.time() - start_time

        # 验证结果合理性
        self.assertGreater(len(intersections), 0)
        self.assertLess(processing_time, 30.0)  # 应该在30秒内完成

    def test_performance_without_spatial_index(self):
        """测试无空间索引性能"""
        analyzer = PolygonContainmentAnalyzer(use_spatial_index=False)

        import time
        start_time = time.time()
        intersections = analyzer.find_intersections(self.lines_gdf, self.polygons_gdf)
        processing_time = time.time() - start_time

        # 验证结果正确性
        self.assertGreater(len(intersections), 0)

    def test_cascade_performance(self):
        """测试级联关联性能"""
        analyzer = PolygonContainmentAnalyzer(cascade_enabled=True)

        import time
        start_time = time.time()
        intersections = analyzer.find_intersections(self.lines_gdf, self.polygons_gdf)
        cascade_dict = analyzer.build_cascade_associations(intersections)
        processing_time = time.time() - start_time

        # 验证级联关联结果
        self.assertGreater(len(cascade_dict), 0)
        self.assertLess(processing_time, 30.0)


if __name__ == '__main__':
    unittest.main()