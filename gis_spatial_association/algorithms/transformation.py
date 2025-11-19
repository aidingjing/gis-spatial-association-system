"""
坐标系统转换处理模块

实现WGS84与CGCS2000坐标系之间的自动转换，支持批量数据集处理和转换精度验证。

Author: CCPM Auto Development System
"""

import logging
import time
from typing import Dict, List, Tuple, Optional, Union, Any
import warnings
import numpy as np
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon
import pyproj

logger = logging.getLogger(__name__)

# 忽略pyproj的FutureWarning
warnings.filterwarnings('ignore', category=FutureWarning, module='pyproj')


class CoordinateTransformer:
    """坐标系统转换处理

    支持WGS84与CGCS2000坐标系之间的自动转换，
    自动检测和统一坐标系，提供转换精度验证。

    Attributes:
        wgs84_crs: WGS84坐标系定义
        cgcs2000_crs: CGCS2000坐标系定义
        default_target_crs: 默认目标坐标系
        transformers: 坐标转换器缓存
        transformation_stats: 转换统计信息
    """

    # 常用坐标系定义
    SUPPORTED_CRS = {
        'WGS84': 'EPSG:4326',
        'CGCS2000': 'EPSG:4490',
        'Web_Mercator': 'EPSG:3857',
        'Beijing1954': 'EPSG:4214',
        'XiAn1980': 'EPSG:4610',
        'CGCS2000_3_Degree_GK_CM_117E': 'EPSG:4547',
        'CGCS2000_3_Degree_GK_CM_120E': 'EPSG:4550',
        'CGCS2000_3_Degree_GK_CM_123E': 'EPSG:4553'
    }

    def __init__(self,
                 default_target_crs: str = 'EPSG:4490',
                 tolerance: float = 1e-6):
        """初始化坐标转换器

        Args:
            default_target_crs: 默认目标坐标系
            tolerance: 坐标转换容差
        """
        self.wgs84_crs = 'EPSG:4326'
        self.cgcs2000_crs = 'EPSG:4490'
        self.default_target_crs = default_target_crs
        self.tolerance = tolerance

        # 转换器缓存
        self.transformers: Dict[Tuple[str, str], Any] = {}

        # 统计信息
        self.transformation_stats = {
            'total_datasets': 0,
            'transformed_datasets': 0,
            'total_features': 0,
            'transformed_features': 0,
            'transformation_errors': 0,
            'avg_transformation_time': 0.0,
            'crs_distribution': {},
            'transformation_chains': []
        }

    def _get_transformer(self, source_crs: str, target_crs: str) -> Any:
        """获取或创建坐标转换器

        Args:
            source_crs: 源坐标系
            target_crs: 目标坐标系

        Returns:
            pyproj转换器对象
        """
        transform_key = (source_crs, target_crs)

        if transform_key not in self.transformers:
            try:
                # 创建转换器
                transformer = pyproj.Transformer.from_crs(
                    source_crs, target_crs, always_xy=True
                )
                self.transformers[transform_key] = transformer
                logger.debug(f"创建坐标转换器: {source_crs} -> {target_crs}")

            except Exception as e:
                logger.error(f"创建坐标转换器失败 {source_crs} -> {target_crs}: {str(e)}")
                raise

        return self.transformers[transform_key]

    def detect_coordinate_system(self, gdf: gpd.GeoDataFrame) -> str:
        """检测数据集的坐标系

        Args:
            gdf: GeoDataFrame

        Returns:
            坐标系字符串
        """
        try:
            if gdf.crs is not None:
                crs_str = str(gdf.crs)
                logger.debug(f"检测到坐标系: {crs_str}")
                return crs_str
            else:
                logger.warning("数据集没有定义坐标系")
                return None

        except Exception as e:
            logger.error(f"检测坐标系时发生错误: {str(e)}")
            return None

    def _validate_coordinate_range(self, gdf: gpd.GeoDataFrame) -> Dict[str, Any]:
        """验证坐标范围，推断可能的坐标系

        Args:
            gdf: GeoDataFrame

        Returns:
            验证结果字典
        """
        validation_result = {
            'is_valid': True,
            'bounds': None,
            'suggested_crs': None,
            'warnings': []
        }

        try:
            # 获取边界框
            bounds = gdf.total_bounds
            validation_result['bounds'] = bounds

            min_x, min_y, max_x, max_y = bounds

            # 根据坐标范围推断坐标系
            # 经度范围: -180 到 180
            # 纬度范围: -90 到 90
            if -180 <= min_x <= 180 and -180 <= max_x <= 180 and \
               -90 <= min_y <= 90 and -90 <= max_y <= 90:
                validation_result['suggested_crs'] = 'EPSG:4326'  # WGS84
            else:
                # 可能是投影坐标系
                validation_result['suggested_crs'] = 'EPSG:4490'  # CGCS2000
                validation_result['warnings'].append(
                    "坐标范围超出地理坐标系范围，可能为投影坐标系"
                )

            # 检查坐标合理性
            if min_x == max_x or min_y == max_y:
                validation_result['is_valid'] = False
                validation_result['warnings'].append("坐标范围异常，可能数据有问题")

        except Exception as e:
            logger.error(f"验证坐标范围时发生错误: {str(e)}")
            validation_result['is_valid'] = False
            validation_result['warnings'].append(f"坐标验证失败: {str(e)}")

        return validation_result

    def transform_to_unified_crs(self,
                                gdf: gpd.GeoDataFrame,
                                target_crs: Optional[str] = None) -> gpd.GeoDataFrame:
        """转换GeoDataFrame到统一坐标系

        Args:
            gdf: 输入GeoDataFrame
            target_crs: 目标坐标系，如果为None则使用默认目标坐标系

        Returns:
            转换后的GeoDataFrame
        """
        if target_crs is None:
            target_crs = self.default_target_crs

        source_crs = self.detect_coordinate_system(gdf)

        # 检查是否需要转换
        if source_crs is None:
            logger.warning("源数据没有坐标系，假设为目标坐标系")
            gdf_crs = gdf.set_crs(target_crs)
            return gdf_crs

        if str(source_crs) == target_crs:
            logger.debug("坐标系相同，无需转换")
            return gdf.copy()

        # 执行坐标转换
        logger.info(f"转换坐标系: {source_crs} -> {target_crs}")
        start_time = time.time()

        try:
            transformed_gdf = gdf.to_crs(target_crs)
            transformation_time = time.time() - start_time
            logger.info(f"坐标转换完成，耗时: {transformation_time:.2f}秒")

            return transformed_gdf

        except Exception as e:
            logger.error(f"坐标转换失败: {str(e)}")
            raise

    def batch_transform_datasets(self,
                                datasets: Dict[str, gpd.GeoDataFrame],
                                target_crs: Optional[str] = None,
                                progress_callback: Optional[callable] = None) -> Tuple[Dict[str, gpd.GeoDataFrame], str]:
        """批量转换多个数据集到统一坐标系

        Args:
            datasets: 数据集字典 {name: GeoDataFrame}
            target_crs: 目标坐标系
            progress_callback: 进度回调函数

        Returns:
            (转换后的数据集字典, 使用的目标坐标系)
        """
        logger.info(f"开始批量转换 {len(datasets)} 个数据集")
        start_time = time.time()

        # 更新统计信息
        self.transformation_stats['total_datasets'] = len(datasets)
        self.transformation_stats['total_features'] = sum(len(gdf) for gdf in datasets.values())

        # 检测所有数据集的坐标系
        crs_analysis = {}
        crs_distribution = {}

        for name, gdf in datasets.items():
            detected_crs = self.detect_coordinate_system(gdf)
            crs_analysis[name] = detected_crs

            # 统计坐标系分布
            crs_key = detected_crs if detected_crs else 'None'
            crs_distribution[crs_key] = crs_distribution.get(crs_key, 0) + 1

        self.transformation_stats['crs_distribution'] = crs_distribution
        logger.info(f"检测到的坐标系分布: {crs_distribution}")

        # 确定目标坐标系
        if target_crs is None:
            target_crs = self._determine_target_crs(crs_analysis)
            logger.info(f"自动确定目标坐标系: {target_crs}")

        # 转换所有数据集
        transformed_datasets = {}
        total_datasets = len(datasets)
        transformed_count = 0
        transformed_features = 0

        for i, (name, gdf) in enumerate(datasets.items()):
            try:
                transformed_gdf = self.transform_to_unified_crs(gdf, target_crs)
                transformed_datasets[name] = transformed_gdf
                transformed_count += 1
                transformed_features += len(gdf)

                logger.debug(f"数据集 {name} 转换完成")

            except Exception as e:
                logger.error(f"转换数据集 {name} 失败: {str(e)}")
                self.transformation_stats['transformation_errors'] += 1
                # 保留原始数据，但记录错误
                transformed_datasets[name] = gdf

            # 进度回调
            if progress_callback:
                progress = (i + 1) / total_datasets * 100
                progress_callback(progress, i + 1, total_datasets)

        # 更新统计信息
        processing_time = time.time() - start_time
        self.transformation_stats['transformed_datasets'] = transformed_count
        self.transformation_stats['transformed_features'] = transformed_features
        self.transformation_stats['avg_transformation_time'] = processing_time / total_datasets

        # 记录转换链
        self.transformation_stats['transformation_chains'].append({
            'timestamp': time.time(),
            'datasets': list(datasets.keys()),
            'source_crs_list': list(crs_analysis.values()),
            'target_crs': target_crs,
            'success_count': transformed_count
        })

        logger.info(f"批量转换完成，成功转换 {transformed_count}/{total_datasets} 个数据集，"
                   f"耗时: {processing_time:.2f}秒")

        return transformed_datasets, target_crs

    def _determine_target_crs(self, crs_analysis: Dict[str, str]) -> str:
        """确定目标坐标系

        Args:
            crs_analysis: 坐标系分析结果 {dataset_name: crs_string}

        Returns:
            目标坐标系字符串
        """
        # 统计坐标系出现频率
        crs_count = {}
        for crs in crs_analysis.values():
            if crs is not None:
                crs_count[crs] = crs_count.get(crs, 0) + 1

        if not crs_count:
            logger.warning("所有数据集都没有坐标系，使用默认坐标系")
            return self.default_target_crs

        # 选择出现频率最高的坐标系
        most_common_crs = max(crs_count.items(), key=lambda x: x[1])[0]

        # 优先级策略
        # 1. 如果有CGCS2000，优先选择CGCS2000
        if 'EPSG:4490' in crs_count or any('4490' in str(crs) for crs in crs_count.keys()):
            return 'EPSG:4490'

        # 2. 如果有WGS84，选择WGS84
        if 'EPSG:4326' in crs_count or any('4326' in str(crs) for crs in crs_count.keys()):
            return 'EPSG:4326'

        # 3. 否则选择最常用的坐标系
        return str(most_common_crs)

    def validate_transformation_quality(self,
                                       original_gdf: gpd.GeoDataFrame,
                                       transformed_gdf: gpd.GeoDataFrame,
                                       sample_size: int = 100) -> Dict[str, Any]:
        """验证坐标转换质量

        Args:
            original_gdf: 原始GeoDataFrame
            transformed_gdf: 转换后的GeoDataFrame
            sample_size: 采样点数量

        Returns:
            验证结果字典
        """
        validation_result = {
            'is_valid': True,
            'sample_size': 0,
            'coordinate_differences': [],
            'max_difference': 0.0,
            'avg_difference': 0.0,
            'warnings': []
        }

        try:
            # 采样检查
            if len(original_gdf) > sample_size:
                sample_indices = np.random.choice(len(original_gdf), sample_size, replace=False)
                original_sample = original_gdf.iloc[sample_indices]
                transformed_sample = transformed_gdf.iloc[sample_indices]
            else:
                original_sample = original_gdf
                transformed_sample = transformed_gdf

            validation_result['sample_size'] = len(original_sample)

            # 计算坐标差异（通过反向转换检查）
            if original_gdf.crs != transformed_gdf.crs:
                # 创建反向转换器
                source_crs = str(original_gdf.crs)
                target_crs = str(transformed_gdf.crs)

                try:
                    back_transformer = self._get_transformer(target_crs, source_crs)
                    coordinate_differences = []

                    for orig_geom, trans_geom in zip(original_sample.geometry, transformed_sample.geometry):
                        if orig_geom is not None and trans_geom is not None:
                            # 反向转换
                            back_transformed_coords = back_transformer.transform(
                                trans_geom.x, trans_geom.y
                            )

                            # 计算差异
                            if hasattr(orig_geom, 'x') and hasattr(orig_geom, 'y'):
                                diff_x = abs(orig_geom.x - back_transformed_coords[0])
                                diff_y = abs(orig_geom.y - back_transformed_coords[1])
                                diff_total = np.sqrt(diff_x**2 + diff_y**2)
                                coordinate_differences.append(diff_total)

                    if coordinate_differences:
                        validation_result['coordinate_differences'] = coordinate_differences
                        validation_result['max_difference'] = max(coordinate_differences)
                        validation_result['avg_difference'] = np.mean(coordinate_differences)

                        # 检查转换精度
                        if validation_result['max_difference'] > self.tolerance:
                            validation_result['warnings'].append(
                                f"坐标转换精度超出容差: {validation_result['max_difference']:.8f}"
                            )

                except Exception as e:
                    validation_result['warnings'].append(f"反向转换验证失败: {str(e)}")

        except Exception as e:
            logger.error(f"验证转换质量时发生错误: {str(e)}")
            validation_result['is_valid'] = False
            validation_result['warnings'].append(f"转换质量验证失败: {str(e)}")

        return validation_result

    def get_transformation_statistics(self) -> Dict:
        """获取转换统计信息

        Returns:
            统计信息字典
        """
        return self.transformation_stats.copy()

    def get_supported_crs_list(self) -> Dict[str, str]:
        """获取支持的坐标系列表

        Returns:
            支持的坐标系字典 {名称: EPSG代码}
        """
        return self.SUPPORTED_CRS.copy()

    def clear_transformer_cache(self):
        """清空转换器缓存"""
        self.transformers.clear()
        logger.info("转换器缓存已清空")


def create_transformer(config: Optional[Dict] = None) -> CoordinateTransformer:
    """工厂函数：创建坐标转换器实例

    Args:
        config: 配置字典

    Returns:
        CoordinateTransformer实例
    """
    if config is None:
        config = {}

    return CoordinateTransformer(
        default_target_crs=config.get('default_target_crs', 'EPSG:4490'),
        tolerance=config.get('tolerance', 1e-6)
    )