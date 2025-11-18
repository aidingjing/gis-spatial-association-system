"""
线-面包含判断算法模块

实现高效的线与面相交关系分析，检测横断面与80个防治对象面的相交关系。
支持级联关联传递和复杂几何类型处理。

Author: CCPM Auto Development System
"""

import logging
import time
from typing import Dict, List, Tuple, Optional, Union, Set
import numpy as np
import geopandas as gpd
from shapely.geometry import LineString, Polygon, MultiPolygon, Point
from shapely.strtree import STRtree
from shapely.ops import split, unary_union

logger = logging.getLogger(__name__)


class PolygonContainmentAnalyzer:
    """线-面包含判断算法

    检测横断面与防治对象面的相交关系，实现级联关联传递，
    支持复杂几何类型，包括多边形、多部件多边形等。

    Attributes:
        intersection_types: 支持的相交类型
        use_spatial_index: 是否使用空间索引优化
        spatial_tree: STRtree空间索引
        cascade_associations: 级联关联结果
    """

    def __init__(self,
                 use_spatial_index: bool = True,
                 cascade_enabled: bool = True):
        """初始化线-面包含判断算法

        Args:
            use_spatial_index: 是否使用空间索引优化查询
            cascade_enabled: 是否启用级联关联传递
        """
        self.use_spatial_index = use_spatial_index
        self.cascade_enabled = cascade_enabled
        self.spatial_tree: Optional[STRtree] = None

        # 支持的相交类型
        self.intersection_types = {
            'contains': '面完全包含线',
            'within': '线完全在面内',
            'intersects': '线与面相交',
            'touches': '线与面相切',
            'crosses': '线穿过面'
        }

        # 存储分析结果
        self.containment_results: List[Dict] = []
        self.cascade_associations: Dict[str, List[str]] = {}

        # 统计信息
        self.stats = {
            'total_lines': 0,
            'total_polygons': 0,
            'total_intersections': 0,
            'cascade_chains': 0,
            'processing_time': 0.0,
            'intersection_type_counts': {itype: 0 for itype in self.intersection_types}
        }

    def _build_spatial_index(self, polygons_gdf: gpd.GeoDataFrame) -> STRtree:
        """构建面的空间索引

        Args:
            polygons_gdf: 面要素GeoDataFrame

        Returns:
            STRtree空间索引对象
        """
        logger.info(f"开始构建面要素空间索引，要素数量: {len(polygons_gdf)}")
        start_time = time.time()

        try:
            # 过滤有效几何体
            valid_geometries = []
            valid_indices = []

            for idx, geometry in enumerate(polygons_gdf.geometry):
                if geometry is not None and not geometry.is_empty:
                    valid_geometries.append(geometry)
                    valid_indices.append(idx)

            # 构建STRtree空间索引
            if valid_geometries:
                self.spatial_tree = STRtree(valid_geometries)
                build_time = time.time() - start_time
                logger.info(f"空间索引构建完成，有效要素: {len(valid_geometries)}, 耗时: {build_time:.2f}秒")
                return self.spatial_tree
            else:
                logger.warning("没有有效的几何体用于构建空间索引")
                return None

        except Exception as e:
            logger.error(f"空间索引构建失败: {str(e)}")
            raise

    def _determine_intersection_type(self,
                                    line: LineString,
                                    polygon: Polygon) -> str:
        """确定线与面的相交类型

        Args:
            line: 线几何对象
            polygon: 面几何对象

        Returns:
            相交类型字符串
        """
        try:
            # 按优先级检查相交类型
            if polygon.contains(line):
                return 'contains'
            elif line.within(polygon):
                return 'within'
            elif line.crosses(polygon):
                return 'crosses'
            elif line.touches(polygon):
                return 'touches'
            elif line.intersects(polygon):
                return 'intersects'
            else:
                return 'none'

        except Exception as e:
            logger.error(f"判断相交类型时发生错误: {str(e)}")
            return 'unknown'

    def _calculate_intersection_metrics(self,
                                       line: LineString,
                                       polygon: Polygon,
                                       intersection_type: str) -> Dict:
        """计算相交度量指标

        Args:
            line: 线几何对象
            polygon: 面几何对象
            intersection_type: 相交类型

        Returns:
            度量指标字典
        """
        metrics = {
            'intersection_type': intersection_type,
            'line_length': 0.0,
            'intersection_length': 0.0,
            'inside_length': 0.0,
            'outside_length': 0.0,
            'intersection_ratio': 0.0,
            'num_intersection_points': 0
        }

        try:
            # 基本长度
            metrics['line_length'] = line.length

            # 计算相交长度
            if line.intersects(polygon):
                intersection = line.intersection(polygon)
                if intersection.geom_type == 'LineString':
                    metrics['intersection_length'] = intersection.length
                elif intersection.geom_type == 'MultiLineString':
                    metrics['intersection_length'] = sum(line.length for line in intersection.geoms)

            # 计算线在面内的长度
            if line.within(polygon):
                metrics['inside_length'] = line.length
            else:
                # 计算线在面内的部分
                try:
                    clipped_line = line.intersection(polygon)
                    if clipped_line.geom_type == 'LineString':
                        metrics['inside_length'] = clipped_line.length
                    elif clipped_line.geom_type == 'MultiLineString':
                        metrics['inside_length'] = sum(line.length for line in clipped_line.geoms)
                except Exception:
                    metrics['inside_length'] = 0.0

            # 计算线在面外的长度
            metrics['outside_length'] = metrics['line_length'] - metrics['inside_length']

            # 计算相交比例
            if metrics['line_length'] > 0:
                metrics['intersection_ratio'] = metrics['inside_length'] / metrics['line_length']

            # 计算交点数量
            boundary = polygon.boundary
            intersection_points = line.intersection(boundary)
            if intersection_points.geom_type == 'Point':
                metrics['num_intersection_points'] = 1
            elif intersection_points.geom_type == 'MultiPoint':
                metrics['num_intersection_points'] = len(intersection_points.geoms)

        except Exception as e:
            logger.error(f"计算相交度量指标时发生错误: {str(e)}")

        return metrics

    def _find_polygon_intersections_brute_force(self,
                                               line: LineString,
                                               polygons_gdf: gpd.GeoDataFrame,
                                               line_idx: int,
                                               line_id: str) -> List[Dict]:
        """使用暴力搜索查找与线的所有面相交

        Args:
            line: 线几何对象
            polygons_gdf: 面要素GeoDataFrame
            line_idx: 线索引
            line_id: 线ID

        Returns:
            相交结果列表
        """
        intersections = []

        for poly_idx, poly_row in polygons_gdf.iterrows():
            polygon = poly_row.geometry
            if polygon is None or polygon.is_empty:
                continue

            try:
                # 检查是否相交
                if not line.intersects(polygon):
                    continue

                # 确定相交类型
                intersection_type = self._determine_intersection_type(line, polygon)

                if intersection_type == 'none':
                    continue

                # 计算度量指标
                metrics = self._calculate_intersection_metrics(line, polygon, intersection_type)

                intersections.append({
                    'line_id': line_id,
                    'line_idx': line_idx,
                    'line_geometry': line,
                    'polygon_id': poly_row.name if hasattr(poly_row, 'name') else poly_idx,
                    'polygon_idx': poly_idx,
                    'polygon_geometry': polygon,
                    **metrics
                })

            except Exception as e:
                logger.error(f"处理线面相交时发生错误: {str(e)}")
                continue

        return intersections

    def _find_polygon_intersections_indexed(self,
                                           line: LineString,
                                           polygons_gdf: gpd.GeoDataFrame,
                                           line_idx: int,
                                           line_id: str) -> List[Dict]:
        """使用空间索引查找与线的所有面相交

        Args:
            line: 线几何对象
            polygons_gdf: 面要素GeoDataFrame
            line_idx: 线索引
            line_id: 线ID

        Returns:
            相交结果列表
        """
        if self.spatial_tree is None:
            return self._find_polygon_intersections_brute_force(
                line, polygons_gdf, line_idx, line_id
            )

        intersections = []

        try:
            # 使用空间索引查询可能相交的面
            candidate_geometries = self.spatial_tree.query(line, predicate='intersects')

            for candidate_geom in candidate_geometries:
                # 找到对应的面记录
                poly_idx = None
                for idx, poly_row in polygons_gdf.iterrows():
                    if poly_row.geometry.equals(candidate_geom):
                        poly_idx = idx
                        polygon = candidate_geom
                        break

                if poly_idx is None:
                    continue

                try:
                    # 确定相交类型
                    intersection_type = self._determine_intersection_type(line, polygon)

                    if intersection_type == 'none':
                        continue

                    # 计算度量指标
                    metrics = self._calculate_intersection_metrics(line, polygon, intersection_type)

                    intersections.append({
                        'line_id': line_id,
                        'line_idx': line_idx,
                        'line_geometry': line,
                        'polygon_id': polygons_gdf.iloc[poly_idx].name,
                        'polygon_idx': poly_idx,
                        'polygon_geometry': polygon,
                        **metrics
                    })

                except Exception as e:
                    logger.error(f"处理具体线面相交时发生错误: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"空间索引查询失败: {str(e)}")
            # 回退到暴力搜索
            return self._find_polygon_intersections_brute_force(
                line, polygons_gdf, line_idx, line_id
            )

        return intersections

    def find_intersections(self,
                          lines_gdf: gpd.GeoDataFrame,
                          polygons_gdf: gpd.GeoDataFrame,
                          progress_callback: Optional[callable] = None) -> List[Dict]:
        """检测线与面的所有相交关系

        Args:
            lines_gdf: 线要素GeoDataFrame
            polygons_gdf: 面要素GeoDataFrame
            progress_callback: 进度回调函数

        Returns:
            相交结果列表
        """
        logger.info(f"开始线-面相交检测，线数量: {len(lines_gdf)}, 面数量: {len(polygons_gdf)}")
        start_time = time.time()

        # 更新统计信息
        self.stats['total_lines'] = len(lines_gdf)
        self.stats['total_polygons'] = len(polygons_gdf)

        # 构建空间索引
        if self.use_spatial_index:
            self._build_spatial_index(polygons_gdf)

        # 查找所有相交
        all_intersections = []
        total_lines = len(lines_gdf)

        for i, line_row in lines_gdf.iterrows():
            line = line_row.geometry
            if line is None or line.is_empty:
                continue

            line_id = line_row.name if hasattr(line_row, 'name') else i

            # 查找该线与所有面的相交
            if self.use_spatial_index:
                intersections = self._find_polygon_intersections_indexed(
                    line, polygons_gdf, i, line_id
                )
            else:
                intersections = self._find_polygon_intersections_brute_force(
                    line, polygons_gdf, i, line_id
                )

            all_intersections.extend(intersections)

            # 进度回调
            if progress_callback:
                progress = (i + 1) / total_lines * 100
                progress_callback(progress, i + 1, total_lines)

            logger.debug(f"线 {i + 1}/{total_lines} 完成，发现 {len(intersections)} 个相交")

        # 保存结果
        self.containment_results = all_intersections
        self.stats['total_intersections'] = len(all_intersections)

        # 统计相交类型
        for intersection in all_intersections:
            intersection_type = intersection.get('intersection_type', 'unknown')
            if intersection_type in self.stats['intersection_type_counts']:
                self.stats['intersection_type_counts'][intersection_type] += 1

        processing_time = time.time() - start_time
        self.stats['processing_time'] = processing_time

        logger.info(f"线-面相交检测完成，总相交数: {len(all_intersections)}, 耗时: {processing_time:.2f}秒")

        return all_intersections

    def _build_cascade_associations(self, intersections: List[Dict]) -> Dict[str, List[str]]:
        """构建级联关联关系

        Args:
            intersections: 相交结果列表

        Returns:
            级联关联字典 {line_id: [polygon_id1, polygon_id2, ...]}
        """
        logger.info("开始构建级联关联关系")

        cascade_dict = {}

        # 按线分组
        line_groups = {}
        for intersection in intersections:
            line_id = intersection['line_id']
            if line_id not in line_groups:
                line_groups[line_id] = []
            line_groups[line_id].append(intersection)

        # 为每条线构建级联关系
        for line_id, line_intersections in line_groups.items():
            # 按相交比例排序，优先选择包含关系
            sorted_intersections = sorted(
                line_intersections,
                key=lambda x: (
                    x['intersection_type'] == 'contains',
                    x['intersection_type'] == 'within',
                    x['intersection_ratio']
                ),
                reverse=True
            )

            # 构建级联关系
            polygon_ids = []
            for intersection in sorted_intersections:
                polygon_id = intersection['polygon_id']
                if polygon_id not in polygon_ids:  # 避免重复
                    polygon_ids.append(polygon_id)

            if polygon_ids:
                cascade_dict[line_id] = polygon_ids

        self.stats['cascade_chains'] = len(cascade_dict)
        logger.info(f"级联关联构建完成，涉及 {len(cascade_dict)} 条线")

        return cascade_dict

    def build_cascade_associations(self,
                                  intersections: Optional[List[Dict]] = None) -> Dict[str, List[str]]:
        """构建级联关联传递关系

        Args:
            intersections: 相交结果列表，如果为None则使用上次的结果

        Returns:
            级联关联字典
        """
        if not self.cascade_enabled:
            logger.info("级联关联功能已禁用")
            return {}

        if intersections is None:
            intersections = self.containment_results

        if not intersections:
            logger.warning("没有相交结果用于构建级联关联")
            return {}

        self.cascade_associations = self._build_cascade_associations(intersections)
        return self.cascade_associations

    def build_result_gdf(self,
                        intersections: Optional[List[Dict]] = None,
                        lines_gdf: Optional[gpd.GeoDataFrame] = None,
                        polygons_gdf: Optional[gpd.GeoDataFrame] = None) -> gpd.GeoDataFrame:
        """构建结果GeoDataFrame

        Args:
            intersections: 相交结果列表
            lines_gdf: 原始线数据
            polygons_gdf: 原始面数据

        Returns:
            结果GeoDataFrame
        """
        if intersections is None:
            intersections = self.containment_results

        if not intersections:
            logger.warning("没有相交结果")
            return gpd.GeoDataFrame()

        result_records = []

        for intersection in intersections:
            record = {
                'line_id': intersection['line_id'],
                'polygon_id': intersection['polygon_id'],
                'intersection_type': intersection['intersection_type'],
                'line_length': intersection['line_length'],
                'intersection_length': intersection['intersection_length'],
                'inside_length': intersection['inside_length'],
                'outside_length': intersection['outside_length'],
                'intersection_ratio': intersection['intersection_ratio'],
                'num_intersection_points': intersection['num_intersection_points'],
                'geometry': intersection['line_geometry']  # 使用线作为几何体
            }

            # 如果提供了原始数据，合并属性
            if lines_gdf is not None:
                line_data = lines_gdf[lines_gdf.name == intersection['line_id']]
                if len(line_data) > 0:
                    line_attrs = line_data.iloc[0].to_dict()
                    line_attrs = {f'line_{k}': v for k, v in line_attrs.items()}
                    record.update(line_attrs)

            if polygons_gdf is not None:
                # 对于面，我们需要通过几何匹配
                poly_geom = intersection['polygon_geometry']
                for _, poly_row in polygons_gdf.iterrows():
                    if poly_row.geometry.equals(poly_geom):
                        poly_attrs = poly_row.to_dict()
                        poly_attrs = {f'polygon_{k}': v for k, v in poly_attrs.items()}
                        record.update(poly_attrs)
                        break

            result_records.append(record)

        # 创建GeoDataFrame
        crs = None
        if lines_gdf is not None:
            crs = lines_gdf.crs
        elif polygons_gdf is not None:
            crs = polygons_gdf.crs

        result_gdf = gpd.GeoDataFrame(result_records, crs=crs)

        return result_gdf

    def get_analysis_statistics(self) -> Dict:
        """获取分析统计信息

        Returns:
            统计信息字典
        """
        return self.stats.copy()

    def validate_results(self, result_gdf: gpd.GeoDataFrame) -> Dict[str, int]:
        """验证分析结果质量

        Args:
            result_gdf: 结果GeoDataFrame

        Returns:
            验证结果统计
        """
        validation_stats = {
            'total_records': len(result_gdf),
            'null_geometries': 0,
            'invalid_ratios': 0,
            'negative_lengths': 0,
            'null_types': 0
        }

        if len(result_gdf) == 0:
            return validation_stats

        # 检查空几何
        validation_stats['null_geometries'] = result_gdf.geometry.isnull().sum()

        # 检查无效比例
        if 'intersection_ratio' in result_gdf.columns:
            invalid_ratios = result_gdf['intersection_ratio'].isnull() | \
                           (result_gdf['intersection_ratio'] < 0) | \
                           (result_gdf['intersection_ratio'] > 1)
            validation_stats['invalid_ratios'] = invalid_ratios.sum()

        # 检查负长度
        length_columns = ['line_length', 'intersection_length', 'inside_length', 'outside_length']
        for col in length_columns:
            if col in result_gdf.columns:
                negative_lengths = result_gdf[col] < 0
                validation_stats['negative_lengths'] += negative_lengths.sum()

        # 检查空类型
        if 'intersection_type' in result_gdf.columns:
            null_types = result_gdf['intersection_type'].isnull()
            validation_stats['null_types'] = null_types.sum()

        return validation_stats


def create_analyzer(config: Optional[Dict] = None) -> PolygonContainmentAnalyzer:
    """工厂函数：创建面包含分析器实例

    Args:
        config: 配置字典

    Returns:
        PolygonContainmentAnalyzer实例
    """
    if config is None:
        config = {}

    return PolygonContainmentAnalyzer(
        use_spatial_index=config.get('use_spatial_index', True),
        cascade_enabled=config.get('cascade_enabled', True)
    )