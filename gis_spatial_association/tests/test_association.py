"""
点-线最近邻关联算法单元测试

测试NearestNeighborAssociator类的各种功能和边界条件。

Author: CCPM Auto Development System
"""

import unittest
import numpy as np
import geopandas as gpd
from shapely.geometry import Point, LineString
import pandas as pd

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from algorithms.association import NearestNeighborAssociator, create_associator


class TestNearestNeighborAssociator(unittest.TestCase):
    """点-线最近邻关联算法测试类"""

    def setUp(self):
        """测试前的设置"""
        # 创建测试用的线数据
        self.lines_data = [
            {'id': 'line_1', 'geometry': LineString([(0, 0), (10, 0)])},
            {'id': 'line_2', 'geometry': LineString([(0, 5), (10, 5)])},
            {'id': 'line_3', 'geometry': LineString([(5, -2), (5, 7)])}
        ]
        self.lines_gdf = gpd.GeoDataFrame(self.lines_data, crs='EPSG:4326')

        # 创建测试用的点数据
        self.points_data = [
            {'id': 'point_1', 'geometry': Point(2, 0.5)},
            {'id': 'point_2', 'geometry': Point(8, 4.8)},
            {'id': 'point_3', 'geometry': Point(5, 3)},
            {'id': 'point_4', 'geometry': Point(15, 0)},  # 远距离点
        ]
        self.points_gdf = gpd.GeoDataFrame(self.points_data, crs='EPSG:4326')

        # 创建关联器
        self.associator = NearestNeighborAssociator(
            use_spatial_index=True,
            association_threshold=10.0,
            batch_size=2
        )

    def test_initialization(self):
        """测试初始化"""
        # 测试默认初始化
        associator = NearestNeighborAssociator()
        self.assertTrue(associator.use_spatial_index)
        self.assertEqual(associator.association_threshold, float('inf'))
        self.assertEqual(associator.batch_size, 1000)

        # 测试自定义初始化
        associator = NearestNeighborAssociator(
            use_spatial_index=False,
            association_threshold=5.0,
            batch_size=500
        )
        self.assertFalse(associator.use_spatial_index)
        self.assertEqual(associator.association_threshold, 5.0)
        self.assertEqual(associator.batch_size, 500)

    def test_spatial_index_building(self):
        """测试空间索引构建"""
        # 测试正常索引构建
        tree = self.associator.build_spatial_index(self.lines_gdf)
        self.assertIsNotNone(tree)
        self.assertIsNotNone(self.associator.spatial_index)

        # 测试空数据
        empty_gdf = gpd.GeoDataFrame(geometry=[], crs='EPSG:4326')
        tree = self.associator.build_spatial_index(empty_gdf)
        self.assertIsNotNone(tree)

    def test_nearest_line_finding_brute_force(self):
        """测试暴力搜索查找最近线"""
        point = Point(2, 0.5)
        nearest_idx, distance = self.associator._find_nearest_line_brute_force(point, self.lines_gdf)

        # 应该找到第一条线 (line_1)
        self.assertEqual(nearest_idx, 0)
        self.assertAlmostEqual(distance, 0.5, places=6)

    def test_nearest_line_finding_indexed(self):
        """测试空间索引查找最近线"""
        # 构建空间索引
        self.associator.build_spatial_index(self.lines_gdf)

        point = Point(2, 0.5)
        nearest_idx, distance = self.associator._find_nearest_line_indexed(point, self.lines_gdf)

        # 应该找到第一条线
        self.assertEqual(nearest_idx, 0)
        self.assertAlmostEqual(distance, 0.5, places=6)

    def test_batch_processing(self):
        """测试批处理功能"""
        # 创建小批次数据进行测试
        batch_points = self.points_gdf.iloc[:2]
        associations = self.associator._process_batch(batch_points, self.lines_gdf, 0)

        # 应该找到2个关联
        self.assertEqual(len(associations), 2)

        # 验证关联结果
        for assoc in associations:
            self.assertIn('point_idx', assoc)
            self.assertIn('line_idx', assoc)
            self.assertIn('distance', assoc)
            self.assertLessEqual(assoc['distance'], self.associator.association_threshold)

    def test_association_threshold(self):
        """测试关联距离阈值"""
        # 设置较小的阈值
        associator = NearestNeighborAssociator(association_threshold=2.0)

        result_gdf = associator.associate_points_to_lines(self.points_gdf, self.lines_gdf)

        # 远距离的点不应该被关联
        associated_point_ids = set(result_gdf['id'].tolist())
        self.assertNotIn('point_4', associated_point_ids)  # 距离超过阈值

    def test_full_association_process(self):
        """测试完整的关联过程"""
        result_gdf = self.associator.associate_points_to_lines(self.points_gdf, self.lines_gdf)

        # 验证结果不为空
        self.assertGreater(len(result_gdf), 0)

        # 验证必要的列存在
        required_columns = ['geometry', 'association_distance', 'point_idx', 'line_idx']
        for col in required_columns:
            self.assertIn(col, result_gdf.columns)

        # 验证几何体类型为点
        self.assertTrue(all(geom.geom_type == 'Point' for geom in result_gdf.geometry))

        # 验证距离为非负数
        self.assertTrue(all(result_gdf['association_distance'] >= 0))

    def test_empty_data_handling(self):
        """测试空数据处理"""
        empty_points = gpd.GeoDataFrame(geometry=[], crs='EPSG:4326')
        result_gdf = self.associator.associate_points_to_lines(empty_points, self.lines_gdf)

        self.assertEqual(len(result_gdf), 0)

        empty_lines = gpd.GeoDataFrame(geometry=[], crs='EPSG:4326')
        result_gdf = self.associator.associate_points_to_lines(self.points_gdf, empty_lines)

        self.assertEqual(len(result_gdf), 0)

    def test_statistics_tracking(self):
        """测试统计信息跟踪"""
        self.associator.associate_points_to_lines(self.points_gdf, self.lines_gdf)
        stats = self.associator.get_association_statistics()

        # 验证统计信息
        self.assertEqual(stats['total_points'], len(self.points_gdf))
        self.assertEqual(stats['total_lines'], len(self.lines_gdf))
        self.assertGreater(stats['associated_points'], 0)
        self.assertGreater(stats['processing_time'], 0)

    def test_association_validation(self):
        """测试关联结果验证"""
        result_gdf = self.associator.associate_points_to_lines(self.points_gdf, self.lines_gdf)
        validation_stats = self.associator.validate_associations(result_gdf)

        # 验证结果统计
        self.assertIn('total_associations', validation_stats)
        self.assertIn('null_geometries', validation_stats)
        self.assertIn('invalid_distances', validation_stats)

        # 对于有效数据，不应该有无效结果
        self.assertEqual(validation_stats['null_geometries'], 0)
        self.assertEqual(validation_stats['invalid_distances'], 0)

    def test_progress_callback(self):
        """测试进度回调功能"""
        progress_calls = []

        def progress_callback(progress, current, total):
            progress_calls.append((progress, current, total))

        self.associator.associate_points_to_lines(
            self.points_gdf, self.lines_gdf,
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

    def test_attribute_merging(self):
        """测试属性合并功能"""
        # 添加更多属性到测试数据
        lines_with_attrs = self.lines_gdf.copy()
        lines_with_attrs['line_type'] = ['highway', 'railway', 'river']
        lines_with_attrs['length'] = [10, 10, 9]

        points_with_attrs = self.points_gdf.copy()
        points_with_attrs['point_type'] = ['station', 'junction', 'marker', 'remote']

        result_gdf = self.associator.associate_points_to_lines(points_with_attrs, lines_with_attrs)

        # 验证属性合并
        self.assertIn('line_line_type', result_gdf.columns)
        self.assertIn('line_length', result_gdf.columns)
        self.assertIn('point_type', result_gdf.columns)

    def test_edge_cases(self):
        """测试边界条件"""
        # 测试None几何体
        points_with_none = self.points_gdf.copy()
        points_with_none.iloc[0, points_with_none.columns.get_loc('geometry')] = None

        result_gdf = self.associator.associate_points_to_lines(points_with_none, self.lines_gdf)

        # 应该跳过None几何体
        self.assertLess(len(result_gdf), len(self.points_gdf))

        # 测试空几何体
        points_with_empty = self.points_gdf.copy()
        points_with_empty.iloc[0, points_with_empty.columns.get_loc('geometry')] = Point()

        result_gdf = self.associator.associate_points_to_lines(points_with_empty, self.lines_gdf)

        # 应该跳过空几何体
        self.assertLess(len(result_gdf), len(self.points_gdf))

    def test_create_associator_factory(self):
        """测试工厂函数"""
        # 测试默认配置
        associator = create_associator()
        self.assertIsInstance(associator, NearestNeighborAssociator)
        self.assertTrue(associator.use_spatial_index)

        # 测试自定义配置
        config = {
            'use_spatial_index': False,
            'association_threshold': 5.0,
            'batch_size': 200
        }
        associator = create_associator(config)
        self.assertFalse(associator.use_spatial_index)
        self.assertEqual(associator.association_threshold, 5.0)
        self.assertEqual(associator.batch_size, 200)


class TestAssociationPerformance(unittest.TestCase):
    """性能测试类"""

    def setUp(self):
        """创建大量测试数据"""
        # 创建随机线数据
        np.random.seed(42)
        num_lines = 100
        self.lines_data = []

        for i in range(num_lines):
            start_x = np.random.uniform(0, 100)
            start_y = np.random.uniform(0, 100)
            end_x = start_x + np.random.uniform(5, 20)
            end_y = start_y + np.random.uniform(-5, 5)

            self.lines_data.append({
                'id': f'line_{i}',
                'geometry': LineString([(start_x, start_y), (end_x, end_y)])
            })

        self.lines_gdf = gpd.GeoDataFrame(self.lines_data, crs='EPSG:4326')

        # 创建随机点数据
        num_points = 1000
        self.points_data = []

        for i in range(num_points):
            x = np.random.uniform(0, 120)
            y = np.random.uniform(0, 120)

            self.points_data.append({
                'id': f'point_{i}',
                'geometry': Point(x, y)
            })

        self.points_gdf = gpd.GeoDataFrame(self.points_data, crs='EPSG:4326')

    def test_performance_with_spatial_index(self):
        """测试空间索引性能"""
        associator = NearestNeighborAssociator(use_spatial_index=True)

        import time
        start_time = time.time()
        result_gdf = associator.associate_points_to_lines(self.points_gdf, self.lines_gdf)
        processing_time = time.time() - start_time

        # 验证结果合理性
        self.assertGreater(len(result_gdf), 0)
        self.assertLess(processing_time, 30.0)  # 应该在30秒内完成

    def test_performance_without_spatial_index(self):
        """测试无空间索引性能"""
        associator = NearestNeighborAssociator(use_spatial_index=False)

        import time
        start_time = time.time()
        result_gdf = associator.associate_points_to_lines(self.points_gdf, self.lines_gdf)
        processing_time = time.time() - start_time

        # 验证结果合理性
        self.assertGreater(len(result_gdf), 0)
        # 无索引可能会慢一些，但不应该过慢


if __name__ == '__main__':
    unittest.main()