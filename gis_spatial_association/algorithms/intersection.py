"""
线-线相交检测算法模块

实现高效的线段相交检测分析，处理583条横断面线与54条纵断面线的相交关系。
支持一对多关系的智能解决，选择中点距离最近的关联。

Author: CCPM Auto Development System
"""

import logging
import time
from typing import Dict, List, Tuple, Optional, Union, Set
import numpy as np
import geopandas as gpd
from shapely.geometry import LineString, Point, MultiLineString
from shapely.strtree import STRtree
from shapely.ops import nearest_points

logger = logging.getLogger(__name__)


class LineIntersectionDetector:
    """线-线相交检测算法

    检测横断面线与纵断面线的相交关系，处理一对多关系，
    选择中点距离最近的关联，支持复杂几何类型。

    Attributes:
        intersection_tolerance: 相交容差
        use_spatial_index: 是否使用空间索引优化
        spatial_tree: STRtree空间索引
        intersection_results: 相交检测结果
    """

    def __init__(self,
                 intersection_tolerance: float = 1e-6,
                 use_spatial_index: bool = True):
        """初始化线-线相交检测算法

        Args:
            intersection_tolerance: 相交容差，用于处理浮点精度问题
            use_spatial_index: 是否使用空间索引优化查询
        """
        self.intersection_tolerance = intersection_tolerance
        self.use_spatial_index = use_spatial_index
        self.spatial_tree: Optional[STRtree] = None

        # 存储检测结果的详细信息
        self.intersection_results: List[Dict] = []
        self.resolved_associations: List[Dict] = []

        # 统计信息
        self.stats = {
            'total_h_lines': 0,
            'total_v_lines': 0,
            'raw_intersections': 0,
            'resolved_associations': 0,
            'processing_time': 0.0,
            'avg_intersections_per_h_line': 0.0
        }

    def _build_spatial_index(self, h_lines_gdf: gpd.GeoDataFrame) -> STRtree:
        """构建横断面线的空间索引

        Args:
            h_lines_gdf: 横断面线GeoDataFrame

        Returns:
            STRtree空间索引对象
        """
        logger.info(f"开始构建横断面线空间索引，要素数量: {len(h_lines_gdf)}")
        start_time = time.time()

        try:
            # 过滤有效几何体
            valid_geometries = []
            valid_indices = []

            for idx, geometry in enumerate(h_lines_gdf.geometry):
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

    def _calculate_line_midpoint(self, line: LineString) -> Point:
        """计算线段中点

        Args:
            line: 线段几何对象

        Returns:
            线段中点
        """
        try:
            return line.interpolate(0.5, normalized=True)
        except Exception as e:
            logger.error(f"计算线段中点失败: {str(e)}")
            # 使用边界框中心作为后备
            bounds = line.bounds
            return Point((bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2)

    def _find_intersections_brute_force(self,
                                       v_line: LineString,
                                       h_lines_gdf: gpd.GeoDataFrame) -> List[Dict]:
        """使用暴力搜索查找与纵断面的所有相交

        Args:
            v_line: 纵断面线几何对象
            h_lines_gdf: 横断面线GeoDataFrame

        Returns:
            相交结果列表
        """
        intersections = []

        for h_idx, h_row in h_lines_gdf.iterrows():
            h_line = h_row.geometry
            if h_line is None or h_line.is_empty:
                continue

            try:
                # 计算相交
                intersection_result = v_line.intersection(h_line)

                if intersection_result.is_empty:
                    continue

                # 处理不同类型的相交结果
                intersection_points = self._process_intersection_geometry(
                    intersection_result, v_line, h_line
                )

                for intersection_point in intersection_points:
                    # 计算横断面中点
                    h_midpoint = self._calculate_line_midpoint(h_line)

                    # 计算交点到横断面中点的距离
                    distance = intersection_point.distance(h_midpoint)

                    intersections.append({
                        'h_line_id': h_row.name if hasattr(h_row, 'name') else h_idx,
                        'h_line_idx': h_idx,
                        'v_line_id': v_line.name if hasattr(v_line, 'name') else 'unknown',
                        'v_line_geometry': v_line,
                        'h_line_geometry': h_line,
                        'intersection_point': intersection_point,
                        'intersection_type': intersection_result.geom_type,
                        'distance_to_midpoint': distance,
                        'intersection_length': self._calculate_intersection_length(
                            intersection_result, v_line, h_line
                        )
                    })

            except Exception as e:
                logger.error(f"处理相交时发生错误: {str(e)}")
                continue

        return intersections

    def _find_intersections_indexed(self,
                                   v_line: LineString,
                                   h_lines_gdf: gpd.GeoDataFrame) -> List[Dict]:
        """使用空间索引查找与纵断面的所有相交

        Args:
            v_line: 纵断面线几何对象
            h_lines_gdf: 横断面线GeoDataFrame

        Returns:
            相交结果列表
        """
        if self.spatial_tree is None:
            return self._find_intersections_brute_force(v_line, h_lines_gdf)

        intersections = []

        try:
            # 使用空间索引查询可能相交的横断面
            candidate_geometries = self.spatial_tree.query(v_line, predicate='intersects')

            for candidate_geom in candidate_geometries:
                # 找到对应的横断面记录
                h_idx = None
                for idx, h_row in h_lines_gdf.iterrows():
                    if h_row.geometry.equals(candidate_geom):
                        h_idx = idx
                        h_line = candidate_geom
                        break

                if h_idx is None:
                    continue

                try:
                    # 计算相交
                    intersection_result = v_line.intersection(h_line)

                    if intersection_result.is_empty:
                        continue

                    # 处理相交几何
                    intersection_points = self._process_intersection_geometry(
                        intersection_result, v_line, h_line
                    )

                    for intersection_point in intersection_points:
                        # 计算横断面中点
                        h_midpoint = self._calculate_line_midpoint(h_line)

                        # 计算交点到横断面中点的距离
                        distance = intersection_point.distance(h_midpoint)

                        intersections.append({
                            'h_line_id': h_lines_gdf.iloc[h_idx].name,
                            'h_line_idx': h_idx,
                            'v_line_id': v_line.name if hasattr(v_line, 'name') else 'unknown',
                            'v_line_geometry': v_line,
                            'h_line_geometry': h_line,
                            'intersection_point': intersection_point,
                            'intersection_type': intersection_result.geom_type,
                            'distance_to_midpoint': distance,
                            'intersection_length': self._calculate_intersection_length(
                                intersection_result, v_line, h_line
                            )
                        })

                except Exception as e:
                    logger.error(f"处理具体相交时发生错误: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"空间索引查询失败: {str(e)}")
            # 回退到暴力搜索
            return self._find_intersections_brute_force(v_line, h_lines_gdf)

        return intersections

    def _process_intersection_geometry(self,
                                      intersection_result,
                                      v_line: LineString,
                                      h_line: LineString) -> List[Point]:
        """处理相交几何体，提取交点

        Args:
            intersection_result: 相交结果几何体
            v_line: 纵断面线
            h_line: 横断面线

        Returns:
            交点列表
        """
        intersection_points = []

        try:
            if intersection_result.geom_type == 'Point':
                intersection_points.append(intersection_result)

            elif intersection_result.geom_type == 'MultiPoint':
                intersection_points.extend(list(intersection_result.geoms))

            elif intersection_result.geom_type == 'LineString':
                # 相交为线段，取中点作为交点
                midpoint = intersection_result.interpolate(0.5, normalized=True)
                intersection_points.append(midpoint)

            elif intersection_result.geom_type == 'MultiLineString':
                # 相交为多条线段，取每条线段的中点
                for line_geom in intersection_result.geoms:
                    midpoint = line_geom.interpolate(0.5, normalized=True)
                    intersection_points.append(midpoint)

            elif intersection_result.geom_type == 'GeometryCollection':
                # 处理几何集合
                for geom in intersection_result.geoms:
                    if geom.geom_type == 'Point':
                        intersection_points.append(geom)
                    elif geom.geom_type == 'LineString':
                        midpoint = geom.interpolate(0.5, normalized=True)
                        intersection_points.append(midpoint)

        except Exception as e:
            logger.error(f"处理相交几何体时发生错误: {str(e)}")

        # 过滤重复点（在容差范围内）
        filtered_points = self._filter_duplicate_points(intersection_points)

        return filtered_points

    def _filter_duplicate_points(self, points: List[Point]) -> List[Point]:
        """过滤重复点（在容差范围内）

        Args:
            points: 点列表

        Returns:
            过滤后的点列表
        """
        if not points:
            return []

        filtered_points = [points[0]]

        for point in points[1:]:
            is_duplicate = False
            for existing_point in filtered_points:
                if point.distance(existing_point) < self.intersection_tolerance:
                    is_duplicate = True
                    break

            if not is_duplicate:
                filtered_points.append(point)

        return filtered_points

    def _calculate_intersection_length(self,
                                      intersection_result,
                                      v_line: LineString,
                                      h_line: LineString) -> float:
        """计算相交长度

        Args:
            intersection_result: 相交结果
            v_line: 纵断面线
            h_line: 横断面线

        Returns:
            相交长度
        """
        try:
            if intersection_result.geom_type in ['LineString', 'MultiLineString']:
                return intersection_result.length
            else:
                return 0.0
        except Exception:
            return 0.0

    def find_intersections(self,
                          h_lines_gdf: gpd.GeoDataFrame,
                          v_lines_gdf: gpd.GeoDataFrame,
                          progress_callback: Optional[callable] = None) -> List[Dict]:
        """检测横断面线与纵断面线的所有交点

        Args:
            h_lines_gdf: 横断面线GeoDataFrame
            v_lines_gdf: 纵断面线GeoDataFrame
            progress_callback: 进度回调函数

        Returns:
            原始相交结果列表
        """
        logger.info(f"开始线-线相交检测，横断面: {len(h_lines_gdf)}, 纵断面: {len(v_lines_gdf)}")
        start_time = time.time()

        # 更新统计信息
        self.stats['total_h_lines'] = len(h_lines_gdf)
        self.stats['total_v_lines'] = len(v_lines_gdf)

        # 构建空间索引
        if self.use_spatial_index:
            self._build_spatial_index(h_lines_gdf)

        # 查找所有相交
        all_intersections = []
        total_v_lines = len(v_lines_gdf)

        for i, v_row in v_lines_gdf.iterrows():
            v_line = v_row.geometry
            if v_line is None or v_line.is_empty:
                continue

            # 查找该纵断面与所有横断面的相交
            if self.use_spatial_index:
                intersections = self._find_intersections_indexed(v_line, h_lines_gdf)
            else:
                intersections = self._find_intersections_brute_force(v_line, h_lines_gdf)

            all_intersections.extend(intersections)

            # 进度回调
            if progress_callback:
                progress = (i + 1) / total_v_lines * 100
                progress_callback(progress, i + 1, total_v_lines)

            logger.debug(f"纵断面 {i + 1}/{total_v_lines} 完成，发现 {len(intersections)} 个相交")

        # 保存原始结果
        self.intersection_results = all_intersections
        self.stats['raw_intersections'] = len(all_intersections)

        processing_time = time.time() - start_time
        self.stats['processing_time'] = processing_time

        logger.info(f"线-线相交检测完成，原始相交数: {len(all_intersections)}, 耗时: {processing_time:.2f}秒")

        return all_intersections

    def _resolve_multiple_intersections(self, intersections: List[Dict]) -> List[Dict]:
        """解决一对多相交问题，选择最优关联

        Args:
            intersections: 原始相交结果列表

        Returns:
            解决后的关联结果列表
        """
        logger.info(f"开始解决一对多相交问题，原始相交数: {len(intersections)}")

        # 按横断面分组
        h_line_groups = {}
        for intersection in intersections:
            h_id = intersection['h_line_id']
            if h_id not in h_line_groups:
                h_line_groups[h_id] = []
            h_line_groups[h_id].append(intersection)

        # 为每个横断面选择最近的纵断面
        resolved_associations = []
        h_lines_with_multiple = 0

        for h_id, group in h_line_groups.items():
            if len(group) > 1:
                h_lines_with_multiple += 1
                logger.debug(f"横断面 {h_id} 有 {len(group)} 个相交，选择最优解")

            # 选择距离中点最近的交点
            best_intersection = min(group, key=lambda x: x['distance_to_midpoint'])
            best_intersection['resolution_method'] = 'nearest_to_midpoint'
            best_intersection['total_candidates'] = len(group)

            resolved_associations.append(best_intersection)

        logger.info(f"一对多问题解决完成，处理 {h_lines_with_multiple} 个多相交横断面，"
                   f"最终关联数: {len(resolved_associations)}")

        return resolved_associations

    def resolve_intersections(self,
                            intersections: Optional[List[Dict]] = None) -> List[Dict]:
        """解决相交冲突，生成最终关联结果

        Args:
            intersections: 原始相交结果，如果为None则使用上次的结果

        Returns:
            解决后的关联结果列表
        """
        if intersections is None:
            intersections = self.intersection_results

        if not intersections:
            logger.warning("没有相交结果需要解决")
            return []

        self.resolved_associations = self._resolve_multiple_intersections(intersections)
        self.stats['resolved_associations'] = len(self.resolved_associations)

        # 计算平均每个横断面的相交数
        if self.stats['total_h_lines'] > 0:
            self.stats['avg_intersections_per_h_line'] = \
                len(intersections) / self.stats['total_h_lines']

        return self.resolved_associations

    def build_result_gdf(self,
                        associations: Optional[List[Dict]] = None,
                        h_lines_gdf: Optional[gpd.GeoDataFrame] = None,
                        v_lines_gdf: Optional[gpd.GeoDataFrame] = None) -> gpd.GeoDataFrame:
        """构建结果GeoDataFrame

        Args:
            associations: 关联结果列表
            h_lines_gdf: 横断面线数据
            v_lines_gdf: 纵断面线数据

        Returns:
            结果GeoDataFrame
        """
        if associations is None:
            associations = self.resolved_associations

        if not associations:
            logger.warning("没有关联结果")
            return gpd.GeoDataFrame()

        result_records = []

        for assoc in associations:
            record = {
                'h_line_id': assoc['h_line_id'],
                'v_line_id': assoc['v_line_id'],
                'intersection_point': assoc['intersection_point'],
                'distance_to_midpoint': assoc['distance_to_midpoint'],
                'intersection_type': assoc.get('intersection_type', 'unknown'),
                'intersection_length': assoc.get('intersection_length', 0.0),
                'resolution_method': assoc.get('resolution_method', 'unknown'),
                'total_candidates': assoc.get('total_candidates', 1),
                'geometry': assoc['intersection_point']  # 使用交点作为几何体
            }

            # 如果提供了原始数据，合并属性
            if h_lines_gdf is not None:
                h_line_data = h_lines_gdf[h_lines_gdf.name == assoc['h_line_id']]
                if len(h_line_data) > 0:
                    h_attrs = h_line_data.iloc[0].to_dict()
                    h_attrs = {f'h_{k}': v for k, v in h_attrs.items()}
                    record.update(h_attrs)

            if v_lines_gdf is not None:
                # 对于纵断面，我们需要通过几何匹配
                v_geom = assoc['v_line_geometry']
                for _, v_row in v_lines_gdf.iterrows():
                    if v_row.geometry.equals(v_geom):
                        v_attrs = v_row.to_dict()
                        v_attrs = {f'v_{k}': v for k, v in v_attrs.items()}
                        record.update(v_attrs)
                        break

            result_records.append(record)

        # 创建GeoDataFrame
        crs = None
        if h_lines_gdf is not None:
            crs = h_lines_gdf.crs
        elif v_lines_gdf is not None:
            crs = v_lines_gdf.crs

        result_gdf = gpd.GeoDataFrame(result_records, crs=crs)

        return result_gdf

    def get_detection_statistics(self) -> Dict:
        """获取检测统计信息

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
            'duplicate_h_lines': 0,
            'null_v_lines': 0
        }

        if len(result_gdf) == 0:
            return validation_stats

        # 检查空几何
        validation_stats['null_geometries'] = result_gdf.geometry.isnull().sum()

        # 检查无效距离
        if 'distance_to_midpoint' in result_gdf.columns:
            invalid_distances = result_gdf['distance_to_midpoint'].isnull() | \
                               (result_gdf['distance_to_midpoint'] < 0)
            validation_stats['invalid_distances'] = invalid_distances.sum()

        # 检查重复横断面
        if 'h_line_id' in result_gdf.columns:
            duplicate_h_lines = result_gdf['h_line_id'].duplicated().sum()
            validation_stats['duplicate_h_lines'] = duplicate_h_lines

        # 检查空纵断面
        if 'v_line_id' in result_gdf.columns:
            null_v_lines = result_gdf['v_line_id'].isnull().sum()
            validation_stats['null_v_lines'] = null_v_lines

        return validation_stats


def create_detector(config: Optional[Dict] = None) -> LineIntersectionDetector:
    """工厂函数：创建相交检测器实例

    Args:
        config: 配置字典

    Returns:
        LineIntersectionDetector实例
    """
    if config is None:
        config = {}

    return LineIntersectionDetector(
        intersection_tolerance=config.get('intersection_tolerance', 1e-6),
        use_spatial_index=config.get('use_spatial_index', True)
    )