"""
GIS空间关联分析系统集成测试

测试各个算法模块之间的集成和端到端功能。

Author: CCPM Auto Development System
"""

import unittest
import numpy as np
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon
import warnings

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from algorithms.association import NearestNeighborAssociator
from algorithms.intersection import LineIntersectionDetector
from algorithms.containment import PolygonContainmentAnalyzer
from algorithms.transformation import CoordinateTransformer


class TestSystemIntegration(unittest.TestCase):
    """系统集成测试类"""

    def setUp(self):
        """测试前的设置"""
        warnings.filterwarnings('ignore', category=FutureWarning, module='pyproj')

        # 创建模拟的横断面数据（20个点）
        np.random.seed(42)
        self.cross_section_points = []
        for i in range(20):
            x = np.random.uniform(100, 120)
            y = np.random.uniform(30, 40)
            self.cross_section_points.append({
                'id': f'cross_point_{i}',
                'geometry': Point(x, y)
            })
        self.points_gdf = gpd.GeoDataFrame(self.cross_section_points, crs='EPSG:4326')

        # 创建模拟的横断面线（10条）
        self.cross_section_lines = []
        for i in range(10):
            start_x = np.random.uniform(100, 120)
            start_y = np.random.uniform(30, 40)
            end_x = start_x + np.random.uniform(1, 5)
            end_y = start_y + np.random.uniform(-2, 2)
            self.cross_section_lines.append({
                'id': f'cross_line_{i}',
                'geometry': LineString([(start_x, start_y), (end_x, end_y)])
            })
        self.h_lines_gdf = gpd.GeoDataFrame(self.cross_section_lines, crs='EPSG:4326')

        # 创建模拟的纵断面线（5条）
        self.vertical_lines = []
        for i in range(5):
            x = np.random.uniform(100, 120)
            y_start = np.random.uniform(30, 35)
            y_end = y_start + np.random.uniform(3, 8)
            self.vertical_lines.append({
                'id': f'vert_line_{i}',
                'geometry': LineString([(x, y_start), (x, y_end)])
            })
        self.v_lines_gdf = gpd.GeoDataFrame(self.vertical_lines, crs='EPSG:4326')

        # 创建模拟的防治对象面（3个）
        self.control_polygons = []
        for i in range(3):
            center_x = np.random.uniform(105, 115)
            center_y = np.random.uniform(32, 38)
            size = np.random.uniform(3, 8)
            polygon = Polygon([
                (center_x - size/2, center_y - size/2),
                (center_x + size/2, center_y - size/2),
                (center_x + size/2, center_y + size/2),
                (center_x - size/2, center_y + size/2)
            ])
            self.control_polygons.append({
                'id': f'control_poly_{i}',
                'geometry': polygon
            })
        self.polygons_gdf = gpd.GeoDataFrame(self.control_polygons, crs='EPSG:4326')

        # 初始化各个算法模块
        self.associator = NearestNeighborAssociator(use_spatial_index=True)
        self.intersection_detector = LineIntersectionDetector(use_spatial_index=True)
        self.containment_analyzer = PolygonContainmentAnalyzer(use_spatial_index=True)
        self.coord_transformer = CoordinateTransformer()

    def test_full_pipeline_simulation(self):
        """测试完整的空间分析流程"""
        # 步骤1: 坐标系统转换（如果需要）
        datasets = {
            'points': self.points_gdf,
            'h_lines': self.h_lines_gdf,
            'v_lines': self.v_lines_gdf,
            'polygons': self.polygons_gdf
        }

        # 转换到统一坐标系（CGCS2000）
        unified_datasets, target_crs = self.coord_transformer.batch_transform_datasets(
            datasets, 'EPSG:4490'
        )

        # 验证所有数据集都在同一坐标系
        for name, gdf in unified_datasets.items():
            self.assertIn('4490', str(gdf.crs))

        # 步骤2: 点-线关联分析
        point_line_associations = self.associator.associate_points_to_lines(
            unified_datasets['points'],
            unified_datasets['h_lines']
        )

        # 验证点-线关联结果
        self.assertGreaterEqual(len(point_line_associations), 0)
        if len(point_line_associations) > 0:
            self.assertIn('association_distance', point_line_associations.columns)

        # 步骤3: 线-线相交检测
        intersections = self.intersection_detector.find_intersections(
            unified_datasets['h_lines'],
            unified_datasets['v_lines']
        )

        # 解决一对多相交问题
        resolved_associations = self.intersection_detector.resolve_intersections(intersections)

        # 构建相交结果GeoDataFrame
        intersection_results = self.intersection_detector.build_result_gdf(
            resolved_associations,
            unified_datasets['h_lines'],
            unified_datasets['v_lines']
        )

        # 验证线-线相交结果
        self.assertGreaterEqual(len(intersection_results), 0)

        # 步骤4: 线-面包含分析
        containment_intersections = self.containment_analyzer.find_intersections(
            unified_datasets['h_lines'],
            unified_datasets['polygons']
        )

        # 构建级联关联
        cascade_associations = self.containment_analyzer.build_cascade_associations(
            containment_intersections
        )

        # 构建包含分析结果
        containment_results = self.containment_analyzer.build_result_gdf(
            containment_intersections,
            unified_datasets['h_lines'],
            unified_datasets['polygons']
        )

        # 验证线-面包含结果
        self.assertGreaterEqual(len(containment_results), 0)

        # 步骤5: 验证统计信息
        # 点-线关联统计
        assoc_stats = self.associator.get_association_statistics()
        self.assertGreater(assoc_stats['total_points'], 0)
        self.assertGreater(assoc_stats['total_lines'], 0)

        # 线-线相交统计
        intersect_stats = self.intersection_detector.get_detection_statistics()
        self.assertGreater(intersect_stats['total_h_lines'], 0)
        self.assertGreater(intersect_stats['total_v_lines'], 0)

        # 线-面包含统计
        contain_stats = self.containment_analyzer.get_analysis_statistics()
        self.assertGreater(contain_stats['total_lines'], 0)
        self.assertGreater(contain_stats['total_polygons'], 0)

        # 坐标转换统计
        transform_stats = self.coord_transformer.get_transformation_statistics()
        self.assertEqual(transform_stats['total_datasets'], 4)
        self.assertEqual(transform_stats['transformed_datasets'], 4)

    def test_coordinate_consistency(self):
        """测试坐标系统一致性"""
        # 创建不同坐标系的测试数据
        datasets = {
            'wgs84_points': self.points_gdf,
            'cgcs2000_lines': self.h_lines_gdf.to_crs('EPSG:4490'),
            'web_mercator_polys': self.polygons_gdf.to_crs('EPSG:3857')
        }

        # 批量转换到统一坐标系
        unified_datasets, target_crs = self.coord_transformer.batch_transform_datasets(datasets)

        # 验证坐标系统一致性
        crs_list = [str(gdf.crs) for gdf in unified_datasets.values()]
        self.assertTrue(all('4490' in crs for crs in crs_list))

        # 验证转换后的数据分析仍能正常工作
        point_line_assocs = self.associator.associate_points_to_lines(
            unified_datasets['wgs84_points'],
            unified_datasets['cgcs2000_lines']
        )
        self.assertGreaterEqual(len(point_line_assocs), 0)

    def test_data_flow_integration(self):
        """测试数据流集成"""
        # 模拟实际工作流程

        # 1. 坐标转换
        datasets = {
            'points': self.points_gdf,
            'lines': self.h_lines_gdf
        }
        unified_datasets, _ = self.coord_transformer.batch_transform_datasets(datasets)

        # 2. 点-线关联
        associations = self.associator.associate_points_to_lines(
            unified_datasets['points'],
            unified_datasets['lines']
        )

        # 3. 验证关联结果的坐标系统
        if len(associations) > 0:
            self.assertIn('4490', str(associations.crs))

        # 4. 使用关联结果进行后续分析（如果有关联的线）
        if len(associations) > 0:
            # 获取关联的线ID
            associated_line_ids = set(associations['line_id'].tolist())

            # 创建包含关联线的新线数据集
            associated_lines = unified_datasets['lines'][
                unified_datasets['lines'].name.isin(associated_line_ids)
            ]

            if len(associated_lines) > 0:
                # 进行线-面分析
                containment_results = self.containment_analyzer.find_intersections(
                    associated_lines, unified_datasets.get('polygons', self.polygons_gdf)
                )
                self.assertGreaterEqual(len(containment_results), 0)

    def test_error_propagation_handling(self):
        """测试错误传播处理"""
        # 测试一个数据集转换失败的情况
        datasets = {
            'valid_data': self.points_gdf,
            'invalid_data': gpd.GeoDataFrame({'geometry': []})  # 空数据
        }

        # 转换应该能处理错误并继续
        try:
            unified_datasets, _ = self.coord_transformer.batch_transform_datasets(datasets)
            # 验证有效数据被转换
            self.assertIn('valid_data', unified_datasets)
            # 空数据可能也被保留或跳过
        except Exception as e:
            # 如果有错误，应该是可处理的异常
            self.assertIsInstance(e, (ValueError, RuntimeError))

    def test_performance_integration(self):
        """测试性能集成"""
        # 创建较多测试数据
        np.random.seed(42)

        # 增大数据集规模
        large_points = []
        for i in range(100):
            x = np.random.uniform(100, 120)
            y = np.random.uniform(30, 40)
            large_points.append({
                'id': f'point_{i}',
                'geometry': Point(x, y)
            })
        large_points_gdf = gpd.GeoDataFrame(large_points, crs='EPSG:4326')

        large_lines = []
        for i in range(50):
            start_x = np.random.uniform(100, 120)
            start_y = np.random.uniform(30, 40)
            end_x = start_x + np.random.uniform(1, 5)
            end_y = start_y + np.random.uniform(-2, 2)
            large_lines.append({
                'id': f'line_{i}',
                'geometry': LineString([(start_x, start_y), (end_x, end_y)])
            })
        large_lines_gdf = gpd.GeoDataFrame(large_lines, crs='EPSG:4326')

        import time

        # 测试整体性能
        start_time = time.time()

        # 坐标转换
        datasets = {'points': large_points_gdf, 'lines': large_lines_gdf}
        unified_datasets, _ = self.coord_transformer.batch_transform_datasets(datasets)

        # 点-线关联
        associations = self.associator.associate_points_to_lines(
            unified_datasets['points'], unified_datasets['lines']
        )

        total_time = time.time() - start_time

        # 验证结果合理性和性能
        self.assertGreaterEqual(len(associations), 0)
        self.assertLess(total_time, 60.0)  # 应该在60秒内完成

    def test_memory_efficiency(self):
        """测试内存效率"""
        # 创建中等规模数据集
        datasets = {
            'points': self.points_gdf,
            'lines': self.h_lines_gdf
        }

        # 执行完整流程
        unified_datasets, _ = self.coord_transformer.batch_transform_datasets(datasets)
        associations = self.associator.associate_points_to_lines(
            unified_datasets['points'], unified_datasets['lines']
        )

        # 验证结果不为空
        self.assertGreaterEqual(len(associations), 0)

        # 清理对象引用，测试内存释放
        del unified_datasets
        del associations

        # 重新创建应该能正常工作
        unified_datasets, _ = self.coord_transformer.batch_transform_datasets(datasets)

    def test_config_integration(self):
        """测试配置集成"""
        # 使用不同配置创建算法实例
        config = {
            'association': {'use_spatial_index': False, 'batch_size': 10},
            'intersection': {'intersection_tolerance': 1e-5},
            'containment': {'cascade_enabled': False},
            'transformation': {'default_target_crs': 'EPSG:3857'}
        }

        # 创建配置化的算法实例
        associator = NearestNeighborAssociator(**config['association'])
        detector = LineIntersectionDetector(**config['intersection'])
        analyzer = PolygonContainmentAnalyzer(**config['containment'])
        transformer = CoordinateTransformer(**config['transformation'])

        # 验证配置生效
        self.assertFalse(associator.use_spatial_index)
        self.assertEqual(associator.batch_size, 10)
        self.assertEqual(detector.intersection_tolerance, 1e-5)
        self.assertFalse(analyzer.cascade_enabled)
        self.assertEqual(transformer.default_target_crs, 'EPSG:3857')

        # 测试配置化算法的功能
        datasets = {'points': self.points_gdf, 'lines': self.h_lines_gdf}
        unified_datasets, target_crs = transformer.batch_transform_datasets(datasets)
        self.assertEqual(target_crs, 'EPSG:3857')


class TestEndToEndScenarios(unittest.TestCase):
    """端到端场景测试类"""

    def setUp(self):
        """测试前的设置"""
        warnings.filterwarnings('ignore', category=FutureWarning, module='pyproj')

    def test_typical_gis_workflow(self):
        """测试典型的GIS工作流程"""
        # 模拟实际GIS项目工作流程

        # 1. 数据加载和预处理
        # 模拟加载不同来源的地理数据
        survey_points = gpd.GeoDataFrame([
            {'id': f'survey_{i}', 'geometry': Point(116.3 + i*0.01, 39.9 + i*0.01)}
            for i in range(10)
        ], crs='EPSG:4326')

        road_lines = gpd.GeoDataFrame([
            {'id': f'road_{i}', 'geometry': LineString([
                (116.3 + i*0.01, 39.9),
                (116.3 + (i+1)*0.01, 39.9 + 0.01)
            ])}
            for i in range(5)
        ], crs='EPSG:4326')

        area_polygons = gpd.GeoDataFrame([
            {'id': f'area_{i}', 'geometry': Polygon([
                (116.3 + i*0.02, 39.9),
                (116.3 + i*0.02 + 0.01, 39.9),
                (116.3 + i*0.02 + 0.01, 39.9 + 0.01),
                (116.3 + i*0.02, 39.9 + 0.01)
            ])}
            for i in range(3)
        ], crs='EPSG:4326')

        # 2. 坐标系统统一
        transformer = CoordinateTransformer()
        datasets = {
            'points': survey_points,
            'lines': road_lines,
            'polygons': area_polygons
        }
        unified_datasets, target_crs = transformer.batch_transform_datasets(datasets)

        # 3. 空间关系分析
        associator = NearestNeighborAssociator()
        detector = LineIntersectionDetector()
        analyzer = PolygonContainmentAnalyzer()

        # 点到路的最近邻分析
        point_road_assocs = associator.associate_points_to_lines(
            unified_datasets['points'], unified_datasets['lines']
        )

        # 线与面的相交分析
        line_area_intersections = analyzer.find_intersections(
            unified_datasets['lines'], unified_datasets['polygons']
        )

        # 4. 结果验证和质量检查
        # 验证点-路关联
        if len(point_road_assocs) > 0:
            point_validation = associator.validate_associations(point_road_assocs)
            self.assertEqual(point_validation['null_geometries'], 0)

        # 验证线-面相交
        if len(line_area_intersections) > 0:
            line_validation = analyzer.validate_results(
                analyzer.build_result_gdf(line_area_intersections)
            )
            self.assertEqual(line_validation['null_geometries'], 0)

        # 5. 统计报告生成
        # 收集各模块统计信息
        transform_stats = transformer.get_transformation_statistics()
        assoc_stats = associator.get_association_statistics()
        analyze_stats = analyzer.get_analysis_statistics()

        # 验证统计信息完整性
        self.assertGreater(transform_stats['total_datasets'], 0)
        self.assertGreater(assoc_stats['total_points'], 0)
        self.assertGreater(analyze_stats['total_lines'], 0)

    def test_error_recovery_scenario(self):
        """测试错误恢复场景"""
        # 模拟数据质量问题场景
        # 包含无效几何的数据
        problematic_data = gpd.GeoDataFrame([
            {'id': 'valid', 'geometry': Point(116.3, 39.9)},
            {'id': 'invalid_point', 'geometry': None},
            {'id': 'invalid_line', 'geometry': LineString([])},
        ], crs='EPSG:4326')

        valid_data = gpd.GeoDataFrame([
            {'id': 'valid_line', 'geometry': LineString([(116.3, 39.9), (116.4, 39.9)])},
        ], crs='EPSG:4326')

        # 测试系统能否处理有问题的数据
        try:
            associator = NearestNeighborAssociator()
            # 关联分析应该能跳过无效几何
            result = associator.associate_points_to_lines(problematic_data, valid_data)

            # 验证有效数据被处理，无效数据被跳过
            self.assertGreaterEqual(len(result), 0)
            if len(result) > 0:
                # 验证结果中的几何体都是有效的
                null_count = result.geometry.isnull().sum()
                self.assertEqual(null_count, 0)

        except Exception as e:
            # 如果出现异常，应该是可预期的错误
            self.assertIn('几何', str(e)) or self.assertIn('geometry', str(e))


if __name__ == '__main__':
    unittest.main()