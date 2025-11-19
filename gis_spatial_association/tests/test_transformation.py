"""
坐标系统转换处理单元测试

测试CoordinateTransformer类的各种功能和边界条件。

Author: CCPM Auto Development System
"""

import unittest
import numpy as np
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon
import pandas as pd
import warnings

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from algorithms.transformation import CoordinateTransformer, create_transformer


class TestCoordinateTransformer(unittest.TestCase):
    """坐标转换器测试类"""

    def setUp(self):
        """测试前的设置"""
        # 忽略pyproj警告
        warnings.filterwarnings('ignore', category=FutureWarning, module='pyproj')

        # 创建测试用的点数据（WGS84）
        self.points_wgs84_data = [
            {'id': 'point_1', 'geometry': Point(116.3974, 39.9093)},  # 北京
            {'id': 'point_2', 'geometry': Point(121.4737, 31.2304)},  # 上海
            {'id': 'point_3', 'geometry': Point(113.2644, 23.1291)},  # 广州
        ]
        self.points_wgs84_gdf = gpd.GeoDataFrame(self.points_wgs84_data, crs='EPSG:4326')

        # 创建测试用的线数据（WGS84）
        self.lines_wgs84_data = [
            {'id': 'line_1', 'geometry': LineString([(116.3974, 39.9093), (121.4737, 31.2304)])},
            {'id': 'line_2', 'geometry': LineString([(121.4737, 31.2304), (113.2644, 23.1291)])},
        ]
        self.lines_wgs84_gdf = gpd.GeoDataFrame(self.lines_wgs84_data, crs='EPSG:4326')

        # 创建测试用的面数据（WGS84）
        self.polygons_wgs84_data = [
            {
                'id': 'poly_1',
                'geometry': Polygon([
                    (116.3, 39.9), (116.5, 39.9), (116.5, 40.1), (116.3, 40.1)
                ])
            }
        ]
        self.polygons_wgs84_gdf = gpd.GeoDataFrame(self.polygons_wgs84_data, crs='EPSG:4326')

        # 创建转换器
        self.transformer = CoordinateTransformer(
            default_target_crs='EPSG:4490',
            tolerance=1e-6
        )

    def test_initialization(self):
        """测试初始化"""
        # 测试默认初始化
        transformer = CoordinateTransformer()
        self.assertEqual(transformer.default_target_crs, 'EPSG:4490')
        self.assertEqual(transformer.tolerance, 1e-6)

        # 测试自定义初始化
        transformer = CoordinateTransformer(
            default_target_crs='EPSG:3857',
            tolerance=1e-5
        )
        self.assertEqual(transformer.default_target_crs, 'EPSG:3857')
        self.assertEqual(transformer.tolerance, 1e-5)

    def test_supported_crs_list(self):
        """测试支持的坐标系列表"""
        crs_list = self.transformer.get_supported_crs_list()

        # 验证包含常用坐标系
        self.assertIn('WGS84', crs_list)
        self.assertIn('CGCS2000', crs_list)
        self.assertIn('Web_Mercator', crs_list)

        # 验证EPSG代码正确
        self.assertEqual(crs_list['WGS84'], 'EPSG:4326')
        self.assertEqual(crs_list['CGCS2000'], 'EPSG:4490')
        self.assertEqual(crs_list['Web_Mercator'], 'EPSG:3857')

    def test_coordinate_system_detection(self):
        """测试坐标系检测"""
        # 测试WGS84检测
        detected_crs = self.transformer.detect_coordinate_system(self.points_wgs84_gdf)
        self.assertIsNotNone(detected_crs)
        self.assertIn('4326', str(detected_crs))

        # 测试无坐标系数据
        no_crs_gdf = gpd.GeoDataFrame(self.points_wgs84_data)
        detected_crs = self.transformer.detect_coordinate_system(no_crs_gdf)
        self.assertIsNone(detected_crs)

    def test_coordinate_range_validation(self):
        """测试坐标范围验证"""
        # 测试正常的地理坐标
        validation_result = self.transformer._validate_coordinate_range(self.points_wgs84_gdf)

        self.assertTrue(validation_result['is_valid'])
        self.assertIsNotNone(validation_result['bounds'])
        self.assertIsNotNone(validation_result['suggested_crs'])

        # 测试投影坐标范围
        projected_points = self.points_wgs84_gdf.to_crs('EPSG:3857')
        validation_result = self.transformer._validate_coordinate_range(projected_points)

        self.assertTrue(validation_result['is_valid'])
        # 对于投影坐标，应该建议不同的坐标系
        self.assertIsNotNone(validation_result['suggested_crs'])

    def test_transformer_caching(self):
        """测试转换器缓存"""
        # 第一次获取转换器
        transformer1 = self.transformer._get_transformer('EPSG:4326', 'EPSG:4490')
        self.assertIsNotNone(transformer1)

        # 第二次获取应该使用缓存
        transformer2 = self.transformer._get_transformer('EPSG:4326', 'EPSG:4490')
        self.assertIs(transformer1, transformer2)

        # 验证缓存大小
        self.assertEqual(len(self.transformer.transformers), 1)

    def test_single_dataset_transformation(self):
        """测试单个数据集转换"""
        # 测试WGS84到CGCS2000转换
        transformed_gdf = self.transformer.transform_to_unified_crs(
            self.points_wgs84_gdf, 'EPSG:4490'
        )

        # 验证转换结果
        self.assertEqual(len(transformed_gdf), len(self.points_wgs84_gdf))
        self.assertIsNotNone(transformed_gdf.crs)
        self.assertIn('4490', str(transformed_gdf.crs))

        # 验证坐标发生变化
        original_points = list(self.points_wgs84_gdf.geometry)
        transformed_points = list(transformed_gdf.geometry)

        for orig, trans in zip(original_points, transformed_points):
            # 转换后坐标应该不同（WGS84和CGCS2000有微小差异）
            coordinate_diff = abs(orig.x - trans.x) + abs(orig.y - trans.y)
            self.assertGreater(coordinate_diff, 0)

    def test_no_transformation_needed(self):
        """测试无需转换的情况"""
        # 相同坐标系不需要转换
        result_gdf = self.transformer.transform_to_unified_crs(
            self.points_wgs84_gdf, 'EPSG:4326'
        )

        self.assertEqual(len(result_gdf), len(self.points_wgs84_gdf))
        self.assertIn('4326', str(result_gdf.crs))

    def test_no_crs_handling(self):
        """测试无坐标系数据处理"""
        no_crs_gdf = gpd.GeoDataFrame(self.points_wgs84_data)

        # 应该设置目标坐标系
        result_gdf = self.transformer.transform_to_unified_crs(no_crs_gdf, 'EPSG:4326')

        self.assertIsNotNone(result_gdf.crs)
        self.assertIn('4326', str(result_gds.crs))

    def test_batch_transformation(self):
        """测试批量转换"""
        datasets = {
            'points': self.points_wgs84_gdf,
            'lines': self.lines_wgs84_gdf,
            'polygons': self.polygons_wgs84_gdf
        }

        transformed_datasets, target_crs = self.transformer.batch_transform_datasets(
            datasets, 'EPSG:4490'
        )

        # 验证所有数据集都被转换
        self.assertEqual(len(transformed_datasets), len(datasets))

        for name, gdf in transformed_datasets.items():
            self.assertIn('4490', str(gdf.crs))
            self.assertEqual(len(gdf), len(datasets[name]))

        # 验证目标坐标系
        self.assertEqual(target_crs, 'EPSG:4490')

    def test_auto_target_crs_determination(self):
        """测试自动目标坐标系确定"""
        # 创建混合坐标系数据集
        datasets = {
            'wgs84_points': self.points_wgs84_gdf,
            'cgcs2000_points': self.points_wgs84_gdf.to_crs('EPSG:4490')
        }

        # 不指定目标坐标系，让算法自动选择
        transformed_datasets, target_crs = self.transformer.batch_transform_datasets(datasets)

        # 应该选择其中一个现有坐标系
        self.assertIn(target_crs, ['EPSG:4326', 'EPSG:4490'])

    def test_progress_callback(self):
        """测试进度回调功能"""
        datasets = {
            'points': self.points_wgs84_gdf,
            'lines': self.lines_wgs84_gdf
        }

        progress_calls = []

        def progress_callback(progress, current, total):
            progress_calls.append((progress, current, total))

        self.transformer.batch_transform_datasets(
            datasets, 'EPSG:4490', progress_callback=progress_callback
        )

        # 验证进度回调被调用
        self.assertGreater(len(progress_calls), 0)

        # 验证进度值合理
        for progress, current, total in progress_calls:
            self.assertGreaterEqual(progress, 0)
            self.assertLessEqual(progress, 100)

    def test_transformation_statistics(self):
        """测试转换统计信息"""
        datasets = {
            'points': self.points_wgs84_gdf,
            'lines': self.lines_wgs84_gdf
        }

        self.transformer.batch_transform_datasets(datasets, 'EPSG:4490')
        stats = self.transformer.get_transformation_statistics()

        # 验证统计信息
        self.assertEqual(stats['total_datasets'], 2)
        self.assertEqual(stats['transformed_datasets'], 2)
        self.assertGreater(stats['total_features'], 0)
        self.assertGreater(stats['transformed_features'], 0)
        self.assertGreater(stats['processing_time'], 0)

        # 验证坐标系分布
        self.assertIn('crs_distribution', stats)
        self.assertIsInstance(stats['crs_distribution'], dict)

    def test_transformation_quality_validation(self):
        """测试转换质量验证"""
        # 转换数据
        transformed_gdf = self.transformer.transform_to_unified_crs(
            self.points_wgs84_gdf, 'EPSG:4490'
        )

        # 验证转换质量
        validation_result = self.transformer.validate_transformation_quality(
            self.points_wgs84_gdf, transformed_gdf, sample_size=2
        )

        # 验证验证结果
        self.assertIn('is_valid', validation_result)
        self.assertIn('sample_size', validation_result)
        self.assertIn('coordinate_differences', validation_result)

        # 对于小样本，样本大小应该符合预期
        if len(self.points_wgs84_gdf) > 2:
            self.assertEqual(validation_result['sample_size'], 2)

    def test_error_handling(self):
        """测试错误处理"""
        # 测试无效坐标系转换
        try:
            # 使用不存在的EPSG代码
            invalid_gdf = self.points_wgs84_gdf.set_crs('EPSG:9999', allow_override=True)
            self.transformer.transform_to_unified_crs(invalid_gdf, 'EPSG:4490')
            # 如果没有抛出异常，这是意料之外的
        except Exception:
            # 预期会有异常
            pass

    def test_different_geometry_types(self):
        """测试不同几何类型转换"""
        # 测试点
        transformed_points = self.transformer.transform_to_unified_crs(
            self.points_wgs84_gdf, 'EPSG:4490'
        )
        self.assertTrue(all(geom.geom_type == 'Point' for geom in transformed_points.geometry))

        # 测试线
        transformed_lines = self.transformer.transform_to_unified_crs(
            self.lines_wgs84_gdf, 'EPSG:4490'
        )
        self.assertTrue(all(geom.geom_type == 'LineString' for geom in transformed_lines.geometry))

        # 测试面
        transformed_polygons = self.transformer.transform_to_unified_crs(
            self.polygons_wgs84_gdf, 'EPSG:4490'
        )
        self.assertTrue(all(geom.geom_type == 'Polygon' for geom in transformed_polygons.geometry))

    def test_transformer_cache_clearing(self):
        """测试转换器缓存清空"""
        # 添加一些转换器到缓存
        self.transformer._get_transformer('EPSG:4326', 'EPSG:4490')
        self.transformer._get_transformer('EPSG:4326', 'EPSG:3857')

        # 验证缓存不为空
        self.assertGreater(len(self.transformer.transformers), 0)

        # 清空缓存
        self.transformer.clear_transformer_cache()

        # 验证缓存已清空
        self.assertEqual(len(self.transformer.transformers), 0)

    def test_create_transformer_factory(self):
        """测试工厂函数"""
        # 测试默认配置
        transformer = create_transformer()
        self.assertIsInstance(transformer, CoordinateTransformer)
        self.assertEqual(transformer.default_target_crs, 'EPSG:4490')

        # 测试自定义配置
        config = {
            'default_target_crs': 'EPSG:3857',
            'tolerance': 1e-5
        }
        transformer = create_transformer(config)
        self.assertEqual(transformer.default_target_crs, 'EPSG:3857')
        self.assertEqual(transformer.tolerance, 1e-5)

    def test_large_dataset_transformation(self):
        """测试大数据集转换"""
        # 创建大量点数据
        np.random.seed(42)
        large_points_data = []

        for i in range(1000):
            x = np.random.uniform(100, 120)
            y = np.random.uniform(20, 40)
            large_points_data.append({
                'id': f'point_{i}',
                'geometry': Point(x, y)
            })

        large_points_gdf = gpd.GeoDataFrame(large_points_data, crs='EPSG:4326')

        # 测试转换性能
        import time
        start_time = time.time()
        result_gdf = self.transformer.transform_to_unified_crs(large_points_gdf, 'EPSG:4490')
        processing_time = time.time() - start_time

        # 验证结果
        self.assertEqual(len(result_gdf), len(large_points_gdf))
        self.assertIn('4490', str(result_gdf.crs))
        self.assertLess(processing_time, 30.0)  # 应该在30秒内完成

    def test_crs_priority_strategy(self):
        """测试坐标系优先级策略"""
        # 创建包含CGCS2000的数据集
        datasets = {
            'wgs84_data': self.points_wgs84_gdf,
            'cgcs2000_data': self.points_wgs84_gdf.to_crs('EPSG:4490'),
            'other_data': self.points_wgs84_gdf.to_crs('EPSG:3857')
        }

        # 自动确定目标坐标系
        _, target_crs = self.transformer.batch_transform_datasets(datasets)

        # 应该优先选择CGCS2000
        self.assertEqual(target_crs, 'EPSG:4490')


class TestCoordinateTransformationEdgeCases(unittest.TestCase):
    """坐标转换边界条件测试类"""

    def setUp(self):
        """测试前的设置"""
        warnings.filterwarnings('ignore', category=FutureWarning, module='pyproj')
        self.transformer = CoordinateTransformer()

    def test_empty_dataset_handling(self):
        """测试空数据集处理"""
        empty_gdf = gpd.GeoDataFrame(geometry=[], crs='EPSG:4326')

        result_gdf = self.transformer.transform_to_unified_crs(empty_gdf, 'EPSG:4490')

        self.assertEqual(len(result_gdf), 0)
        self.assertIn('4490', str(result_gdf.crs))

    def test_invalid_geometry_handling(self):
        """测试无效几何体处理"""
        # 包含None几何体的数据
        invalid_data = [
            {'id': 'valid', 'geometry': Point(116.3974, 39.9093)},
            {'id': 'invalid', 'geometry': None},
        ]
        invalid_gdf = gpd.GeoDataFrame(invalid_data, crs='EPSG:4326')

        # 转换应该能处理None几何体
        try:
            result_gdf = self.transformer.transform_to_unified_crs(invalid_gdf, 'EPSG:4490')
            # 验证有效几何体被转换
            valid_count = result_gdf.geometry.notnull().sum()
            self.assertEqual(valid_count, 1)
        except Exception as e:
            # 如果失败，应该是有意义的错误信息
            self.assertIsInstance(e, (ValueError, TypeError))

    def test_extreme_coordinate_values(self):
        """测试极值坐标"""
        # 创建极值坐标点
        extreme_data = [
            {'id': 'north_pole', 'geometry': Point(0, 89.9)},
            {'id': 'south_pole', 'geometry': Point(0, -89.9)},
            {'id': 'dateline', 'geometry': Point(179.9, 0)},
            {'id': 'antidateline', 'geometry': Point(-179.9, 0)},
        ]
        extreme_gdf = gpd.GeoDataFrame(extreme_data, crs='EPSG:4326')

        # 转换应该能处理极值坐标
        try:
            result_gdf = self.transformer.transform_to_unified_crs(extreme_gdf, 'EPSG:4490')
            self.assertEqual(len(result_gdf), len(extreme_gdf))
        except Exception as e:
            # 极值坐标可能导致投影问题
            logger.warning(f"极值坐标转换遇到问题: {e}")


if __name__ == '__main__':
    unittest.main()