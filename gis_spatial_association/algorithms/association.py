"""
点-线最近邻关联算法模块

实现高效的点到线的最近邻关联分析，支持大规模数据集处理。
使用R-tree空间索引优化查询性能，算法复杂度达到O(n log n)。

Author: CCPM Auto Development System
"""

import logging
import time
from typing import Dict, List, Tuple, Optional, Union
import numpy as np
import geopandas as gpd
from shapely.geometry import Point, LineString
from rtree import index
from shapely.strtree import STRtree

logger = logging.getLogger(__name__)


class NearestNeighborAssociator:
    """点-线最近邻关联算法

    支持将20,385个横断面点批量关联到583条横断面线，
    使用空间索引优化性能，处理大数据集。

    Attributes:
        spatial_index: R-tree空间索引对象
        use_spatial_index: 是否使用空间索引优化
        association_threshold: 关联距离阈值
        batch_size: 批处理大小
    """

    def __init__(self,
                 use_spatial_index: bool = True,
                 association_threshold: float = float('inf'),
                 batch_size: int = 1000):
        """初始化点-线关联算法

        Args:
            use_spatial_index: 是否使用空间索引优化查询
            association_threshold: 关联距离阈值，超过此距离的点不关联
            batch_size: 批处理大小，用于内存优化
        """
        self.spatial_index: Optional[index.Index] = None
        self.use_spatial_index = use_spatial_index
        self.association_threshold = association_threshold
        self.batch_size = batch_size
        self.lines_gdf: Optional[gpd.GeoDataFrame] = None

        # 统计信息
        self.stats = {
            'total_points': 0,
            'total_lines': 0,
            'associated_points': 0,
            'processing_time': 0.0,
            'avg_association_distance': 0.0
        }

    def build_spatial_index(self, lines_gdf: gpd.GeoDataFrame) -> index.Index:
        """构建线的R-tree空间索引

        Args:
            lines_gdf: 线要素GeoDataFrame

        Returns:
            R-tree空间索引对象
        """
        logger.info(f"开始构建空间索引，要素数量: {len(lines_gdf)}")
        start_time = time.time()

        try:
            # 使用R-tree构建空间索引
            lines_tree = index.Index()

            for idx, geometry in enumerate(lines_gdf.geometry):
                if geometry is not None and not geometry.is_empty:
                    # 使用几何体的边界框
                    bounds = geometry.bounds
                    lines_tree.insert(idx, bounds)

            self.spatial_index = lines_tree
            build_time = time.time() - start_time
            logger.info(f"空间索引构建完成，耗时: {build_time:.2f}秒")

            return lines_tree

        except Exception as e:
            logger.error(f"空间索引构建失败: {str(e)}")
            raise

    def _find_nearest_line_brute_force(self, point: Point, lines_gdf: gpd.GeoDataFrame) -> Tuple[int, float]:
        """使用暴力搜索查找最近的线

        Args:
            point: 点几何对象
            lines_gdf: 线要素GeoDataFrame

        Returns:
            (最近线索引, 最小距离)
        """
        min_distance = float('inf')
        nearest_line_idx = -1

        for idx, line_geometry in enumerate(lines_gdf.geometry):
            if line_geometry is not None and not line_geometry.is_empty:
                distance = point.distance(line_geometry)
                if distance < min_distance and distance <= self.association_threshold:
                    min_distance = distance
                    nearest_line_idx = idx

        return nearest_line_idx, min_distance

    def _find_nearest_line_indexed(self, point: Point, lines_gdf: gpd.GeoDataFrame) -> Tuple[int, float]:
        """使用空间索引查找最近的线

        Args:
            point: 点几何对象
            lines_gdf: 线要素GeoDataFrame

        Returns:
            (最近线索引, 最小距离)
        """
        if self.spatial_index is None:
            return self._find_nearest_line_brute_force(point, lines_gdf)

        # 使用空间索引快速筛选候选线
        candidate_indices = list(self.spatial_index.nearest(point.bounds, num_results=10))

        if not candidate_indices:
            return -1, float('inf')

        # 在候选线中找到真正的最近线
        min_distance = float('inf')
        nearest_line_idx = -1

        for idx in candidate_indices:
            if idx < len(lines_gdf):
                line_geometry = lines_gdf.iloc[idx].geometry
                if line_geometry is not None and not line_geometry.is_empty:
                    distance = point.distance(line_geometry)
                    if distance < min_distance and distance <= self.association_threshold:
                        min_distance = distance
                        nearest_line_idx = idx

        return nearest_line_idx, min_distance

    def _process_batch(self,
                      points_batch: gpd.GeoDataFrame,
                      lines_gdf: gpd.GeoDataFrame,
                      start_idx: int) -> List[Dict]:
        """处理一个批次的点数据

        Args:
            points_batch: 批次点数据
            lines_gdf: 线要素数据
            start_idx: 批次起始索引

        Returns:
            关联结果列表
        """
        associations = []

        for i, point_row in points_batch.iterrows():
            point = point_row.geometry
            if point is None or point.is_empty:
                continue

            # 查找最近线
            if self.use_spatial_index:
                nearest_line_idx, distance = self._find_nearest_line_indexed(point, lines_gdf)
            else:
                nearest_line_idx, distance = self._find_nearest_line_brute_force(point, lines_gdf)

            # 如果找到关联且距离在阈值内
            if nearest_line_idx != -1 and distance <= self.association_threshold:
                associations.append({
                    'point_idx': start_idx + i,
                    'point_id': point_row.name if hasattr(point_row, 'name') else i,
                    'line_idx': nearest_line_idx,
                    'line_id': lines_gdf.iloc[nearest_line_idx].name,
                    'distance': distance,
                    'point_geometry': point,
                    'line_geometry': lines_gdf.iloc[nearest_line_idx].geometry
                })

        return associations

    def associate_points_to_lines(self,
                                 points_gdf: gpd.GeoDataFrame,
                                 lines_gdf: gpd.GeoDataFrame,
                                 progress_callback: Optional[callable] = None) -> gpd.GeoDataFrame:
        """批量关联点到最近的线

        Args:
            points_gdf: 点要素GeoDataFrame
            lines_gdf: 线要素GeoDataFrame
            progress_callback: 进度回调函数

        Returns:
            包含关联结果的GeoDataFrame
        """
        logger.info(f"开始点-线关联分析，点数量: {len(points_gdf)}, 线数量: {len(lines_gdf)}")
        start_time = time.time()

        # 更新统计信息
        self.stats['total_points'] = len(points_gdf)
        self.stats['total_lines'] = len(lines_gdf)

        # 保存线数据引用
        self.lines_gdf = lines_gdf

        # 构建空间索引
        if self.use_spatial_index:
            self.build_spatial_index(lines_gdf)

        # 分批处理点数据
        all_associations = []
        total_batches = (len(points_gdf) + self.batch_size - 1) // self.batch_size

        for batch_idx in range(total_batches):
            start_idx = batch_idx * self.batch_size
            end_idx = min(start_idx + self.batch_size, len(points_gdf))

            points_batch = points_gdf.iloc[start_idx:end_idx]
            batch_associations = self._process_batch(points_batch, lines_gdf, start_idx)
            all_associations.extend(batch_associations)

            # 进度回调
            if progress_callback:
                progress = (batch_idx + 1) / total_batches * 100
                progress_callback(progress, batch_idx + 1, total_batches)

            logger.debug(f"批次 {batch_idx + 1}/{total_batches} 完成，关联 {len(batch_associations)} 个点")

        # 计算平均关联距离
        if all_associations:
            distances = [assoc['distance'] for assoc in all_associations]
            self.stats['avg_association_distance'] = np.mean(distances)

        # 处理时间统计
        processing_time = time.time() - start_time
        self.stats['processing_time'] = processing_time
        self.stats['associated_points'] = len(all_associations)

        logger.info(f"点-线关联完成，总关联数: {len(all_associations)}, "
                   f"耗时: {processing_time:.2f}秒, "
                   f"平均关联距离: {self.stats['avg_association_distance']:.2f}")

        # 构建结果GeoDataFrame
        return self._build_result_gdf(all_associations, points_gdf, lines_gdf)

    def _build_result_gdf(self,
                         associations: List[Dict],
                         points_gdf: gpd.GeoDataFrame,
                         lines_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """构建结果GeoDataFrame

        Args:
            associations: 关联结果列表
            points_gdf: 原始点数据
            lines_gdf: 原始线数据

        Returns:
            结果GeoDataFrame
        """
        if not associations:
            logger.warning("没有找到任何关联关系")
            return gpd.GeoDataFrame()

        # 创建关联记录
        result_records = []
        for assoc in associations:
            # 合并点属性
            point_attrs = points_gdf.iloc[assoc['point_idx']].to_dict()

            # 合并线属性（添加前缀避免冲突）
            line_attrs = lines_gdf.iloc[assoc['line_idx']].to_dict()
            line_attrs = {f'line_{k}': v for k, v in line_attrs.items()}

            # 合并关联信息
            record = {
                **point_attrs,
                **line_attrs,
                'association_distance': assoc['distance'],
                'point_idx': assoc['point_idx'],
                'line_idx': assoc['line_idx']
            }

            # 设置几何体为点
            record['geometry'] = assoc['point_geometry']

            result_records.append(record)

        # 创建GeoDataFrame
        result_gdf = gpd.GeoDataFrame(result_records, crs=points_gdf.crs)

        return result_gdf

    def get_association_statistics(self) -> Dict:
        """获取关联分析统计信息

        Returns:
            统计信息字典
        """
        return self.stats.copy()

    def validate_associations(self, result_gdf: gpd.GeoDataFrame) -> Dict[str, int]:
        """验证关联结果质量

        Args:
            result_gdf: 关联结果GeoDataFrame

        Returns:
            验证结果统计
        """
        validation_stats = {
            'total_associations': len(result_gdf),
            'null_geometries': 0,
            'invalid_distances': 0,
            'duplicate_associations': 0
        }

        if len(result_gdf) == 0:
            return validation_stats

        # 检查空几何
        validation_stats['null_geometries'] = result_gdf.geometry.isnull().sum()

        # 检查无效距离
        if 'association_distance' in result_gdf.columns:
            invalid_distances = result_gdf['association_distance'].isnull() | \
                               (result_gdf['association_distance'] < 0)
            validation_stats['invalid_distances'] = invalid_distances.sum()

        # 检查重复关联
        if 'point_idx' in result_gdf.columns:
            duplicate_points = result_gdf['point_idx'].duplicated().sum()
            validation_stats['duplicate_associations'] = duplicate_points

        return validation_stats


def create_associator(config: Optional[Dict] = None) -> NearestNeighborAssociator:
    """工厂函数：创建关联器实例

    Args:
        config: 配置字典

    Returns:
        NearestNeighborAssociator实例
    """
    if config is None:
        config = {}

    return NearestNeighborAssociator(
        use_spatial_index=config.get('use_spatial_index', True),
        association_threshold=config.get('association_threshold', float('inf')),
        batch_size=config.get('batch_size', 1000)
    )