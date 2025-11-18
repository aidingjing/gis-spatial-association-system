"""
几何数据验证模块

提供全面的几何数据质量检查功能，包括：
- 几何有效性检查（自相交、无效几何、空几何）
- 多种几何类型验证（Point, LineString, Polygon, Multi*）
- 几何精度控制和修复建议
- 几何统计和质量报告

Author: CCPM Auto Development System
"""

import logging
import numpy as np
import geopandas as gpd
from typing import Dict, List, Tuple, Optional, Union, Set
from shapely.geometry import (
    Point, LineString, Polygon, MultiPoint, MultiLineString, MultiPolygon,
    GeometryCollection, shape, mapping
)
from shapely.validation import make_valid
from shapely.ops import unary_union, linemerge, polygonize_full
from shapely import affinity, wkt, wkb

logger = logging.getLogger(__name__)


class GeometryValidationError:
    """几何验证错误类"""

    def __init__(self, error_type: str, message: str, geometry_id: Optional[Union[int, str]] = None):
        self.error_type = error_type
        self.message = message
        self.geometry_id = geometry_id
        self.severity = self._determine_severity(error_type)

    def _determine_severity(self, error_type: str) -> str:
        """根据错误类型确定严重程度"""
        high_severity = {'invalid_geometry', 'self_intersection', 'empty_geometry'}
        medium_severity = {'degenerate', 'duplicate_points', 'invalid_ring'}

        if error_type in high_severity:
            return 'high'
        elif error_type in medium_severity:
            return 'medium'
        else:
            return 'low'

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'error_type': self.error_type,
            'message': self.message,
            'geometry_id': self.geometry_id,
            'severity': self.severity
        }


class GeometryValidator:
    """几何数据验证器

    支持检测和修复各种几何数据问题，包括：
    - 无效几何（自相交、无效环等）
    - 空几何和退化几何
    - 重复点和冗余顶点
    - 精度问题

    验证目标数据：
    - 20,385个横断面点的几何有效性
    - 583条横断面线的几何正确性
    - 2,706个纵断面点的几何完整性
    - 80个防治对象面的几何合理性
    """

    def __init__(self,
                 tolerance: float = 1e-8,
                 allow_empty: bool = False,
                 check_precision: bool = True):
        """初始化几何验证器

        Args:
            tolerance: 几何容差，用于精度控制
            allow_empty: 是否允许空几何
            check_precision: 是否检查几何精度问题
        """
        self.tolerance = tolerance
        self.allow_empty = allow_empty
        self.check_precision = check_precision
        self.errors: List[GeometryValidationError] = []
        self.statistics: Dict = {}

    def validate_geodataframe(self, gdf: gpd.GeoDataFrame) -> Dict:
        """验证GeoDataFrame中的所有几何对象

        Args:
            gdf: 要验证的GeoDataFrame

        Returns:
            包含验证结果的字典
        """
        self.errors = []
        self.statistics = self._initialize_statistics()

        logger.info(f"开始验证 {len(gdf)} 个几何对象")

        for idx, row in gdf.iterrows():
            geometry = row.geometry
            geom_id = getattr(row, 'id', idx)

            self._validate_single_geometry(geometry, geom_id)

        # 计算统计信息
        self._calculate_statistics(gdf)

        return self._generate_validation_report()

    def _validate_single_geometry(self, geometry, geom_id: Union[int, str]):
        """验证单个几何对象"""
        if geometry is None:
            self.errors.append(GeometryValidationError(
                'null_geometry', f'几何对象为空', geom_id
            ))
            return

        if geometry.is_empty:
            if not self.allow_empty:
                self.errors.append(GeometryValidationError(
                    'empty_geometry', f'几何对象为空', geom_id
                ))
            return

        # 检查几何有效性
        if not geometry.is_valid:
            self.errors.append(GeometryValidationError(
                'invalid_geometry', f'几何对象无效: {self._get_validity_reason(geometry)}', geom_id
            ))

        # 根据几何类型进行特定验证
        if geometry.geom_type == 'Point':
            self._validate_point(geometry, geom_id)
        elif geometry.geom_type == 'LineString':
            self._validate_linestring(geometry, geom_id)
        elif geometry.geom_type == 'Polygon':
            self._validate_polygon(geometry, geom_id)
        elif geometry.geom_type.startswith('Multi'):
            self._validate_multigeometry(geometry, geom_id)
        elif geometry.geom_type == 'GeometryCollection':
            self._validate_geometry_collection(geometry, geom_id)

        # 精度检查
        if self.check_precision:
            self._check_geometry_precision(geometry, geom_id)

    def _validate_point(self, point: Point, geom_id: Union[int, str]):
        """验证点几何"""
        # 检查坐标是否为有限值
        if not (np.isfinite(point.x) and np.isfinite(point.y)):
            self.errors.append(GeometryValidationError(
                'invalid_coordinates', f'点坐标包含非有限值: ({point.x}, {point.y})', geom_id
            ))

        # 检查是否在合理地理范围内
        if not self._is_reasonable_coordinate(point.x, point.y):
            self.errors.append(GeometryValidationError(
                'out_of_bounds', f'点坐标超出合理范围: ({point.x}, {point.y})', geom_id
            ))

    def _validate_linestring(self, linestring: LineString, geom_id: Union[int, str]):
        """验证线几何"""
        coords = list(linestring.coords)

        # 检查点数
        if len(coords) < 2:
            self.errors.append(GeometryValidationError(
                'degenerate', f'线几何点数不足，只有 {len(coords)} 个点', geom_id
            ))
            return

        # 检查重复点
        duplicate_count = self._count_duplicate_points(coords)
        if duplicate_count > len(coords) * 0.1:  # 超过10%的点重复
            self.errors.append(GeometryValidationError(
                'duplicate_points', f'线几何包含过多重复点: {duplicate_count}/{len(coords)}', geom_id
            ))

        # 检查自相交
        if linestring.is_closed and len(coords) > 3:
            # 对于闭合线，检查是否为有效多边形
            try:
                polygon = Polygon(coords)
                if not polygon.is_valid:
                    self.errors.append(GeometryValidationError(
                        'self_intersection', f'闭合线几何存在自相交', geom_id
                    ))
            except:
                pass

    def _validate_polygon(self, polygon: Polygon, geom_id: Union[int, str]):
        """验证面几何"""
        # 检查外环
        exterior_coords = list(polygon.exterior.coords)
        if len(exterior_coords) < 4:
            self.errors.append(GeometryValidationError(
                'invalid_ring', f'多边形外环点数不足: {len(exterior_coords)}', geom_id
            ))

        # 检查内环
        for i, interior in enumerate(polygon.interiors):
            interior_coords = list(interior.coords)
            if len(interior_coords) < 4:
                self.errors.append(GeometryValidationError(
                    'invalid_ring', f'多边形内环 {i} 点数不足: {len(interior_coords)}', geom_id
                ))

        # 检查面积
        if polygon.area < self.tolerance:
            self.errors.append(GeometryValidationError(
                'degenerate', f'多边形面积过小: {polygon.area}', geom_id
            ))

        # 检查自相交
        if not polygon.exterior.is_ccw:  # 外环应该是逆时针
            self.errors.append(GeometryValidationError(
                'invalid_orientation', f'多边形外环方向错误', geom_id
            ))

    def _validate_multigeometry(self, multigeometry, geom_id: Union[int, str]):
        """验证多重几何"""
        if len(multigeometry.geoms) == 0:
            self.errors.append(GeometryValidationError(
                'empty_multi', f'多重几何不包含任何几何对象', geom_id
            ))
            return

        # 验证每个子几何
        for i, geom in enumerate(multigeometry.geoms):
            self._validate_single_geometry(geom, f"{geom_id}_{i}")

    def _validate_geometry_collection(self, collection: GeometryCollection, geom_id: Union[int, str]):
        """验证几何集合"""
        if len(collection.geoms) == 0:
            self.errors.append(GeometryValidationError(
                'empty_collection', f'几何集合不包含任何几何对象', geom_id
            ))
            return

        # 验证每个几何对象
        for i, geom in enumerate(collection.geoms):
            self._validate_single_geometry(geom, f"{geom_id}_{i}")

    def _check_geometry_precision(self, geometry, geom_id: Union[int, str]):
        """检查几何精度问题"""
        try:
            if hasattr(geometry, 'coords') and geometry.geom_type not in ['MultiPoint', 'MultiLineString', 'MultiPolygon']:
                coords = list(geometry.coords)
            elif hasattr(geometry, 'geoms'):
                # 对于多重几何，检查所有子几何
                for geom in geometry.geoms:
                    self._check_geometry_precision(geom, geom_id)
                return
            else:
                return
        except NotImplementedError:
            # 某些复杂几何可能不支持直接访问坐标
            return

        # 检查坐标精度
        for i, (x, y) in enumerate(coords):
            if abs(x) < self.tolerance:
                self.errors.append(GeometryValidationError(
                    'precision_issue', f'坐标 x 精度过低: {x} (点 {i})', geom_id
                ))
            if abs(y) < self.tolerance:
                self.errors.append(GeometryValidationError(
                    'precision_issue', f'坐标 y 精度过低: {y} (点 {i})', geom_id
                ))

    def _is_reasonable_coordinate(self, x: float, y: float) -> bool:
        """检查坐标是否在合理地理范围内"""
        # 中国大陆大致范围：经度73°-135°，纬度18°-54°
        # 给出一些余量
        return 50 <= x <= 150 and 10 <= y <= 60

    def _count_duplicate_points(self, coords: List[Tuple]) -> int:
        """计算重复点数量"""
        unique_coords = set()
        duplicate_count = 0

        for coord in coords:
            rounded_coord = (round(coord[0], 8), round(coord[1], 8))
            if rounded_coord in unique_coords:
                duplicate_count += 1
            else:
                unique_coords.add(rounded_coord)

        return duplicate_count

    def _get_validity_reason(self, geometry) -> str:
        """获取几何无效的原因"""
        try:
            # 尝试解释无效原因
            if hasattr(geometry, 'explain_validity'):
                return geometry.explain_validity()
            else:
                # 使用Shapely 2.0+的方法
                return geometry.is_valid_reason if hasattr(geometry, 'is_valid_reason') else "未知原因"
        except:
            return "无法确定无效原因"

    def _initialize_statistics(self) -> Dict:
        """初始化统计信息"""
        return {
            'total_geometries': 0,
            'valid_geometries': 0,
            'invalid_geometries': 0,
            'empty_geometries': 0,
            'geometry_types': {},
            'error_types': {},
            'severity_counts': {'high': 0, 'medium': 0, 'low': 0}
        }

    def _calculate_statistics(self, gdf: gpd.GeoDataFrame):
        """计算统计信息"""
        self.statistics['total_geometries'] = len(gdf)

        # 统计几何类型
        for geom in gdf.geometry:
            if geom is None:
                continue

            if geom.is_empty:
                self.statistics['empty_geometries'] += 1

            if geom.is_valid:
                self.statistics['valid_geometries'] += 1
            else:
                self.statistics['invalid_geometries'] += 1

            geom_type = geom.geom_type
            self.statistics['geometry_types'][geom_type] = \
                self.statistics['geometry_types'].get(geom_type, 0) + 1

        # 统计错误类型
        for error in self.errors:
            error_type = error.error_type
            self.statistics['error_types'][error_type] = \
                self.statistics['error_types'].get(error_type, 0) + 1
            self.statistics['severity_counts'][error.severity] += 1

    def _generate_validation_report(self) -> Dict:
        """生成验证报告"""
        valid_ratio = self.statistics['valid_geometries'] / max(1, self.statistics['total_geometries'])

        return {
            'summary': {
                'total_geometries': self.statistics['total_geometries'],
                'valid_geometries': self.statistics['valid_geometries'],
                'invalid_geometries': self.statistics['invalid_geometries'],
                'empty_geometries': self.statistics['empty_geometries'],
                'validity_ratio': valid_ratio,
                'total_errors': len(self.errors)
            },
            'geometry_types': self.statistics['geometry_types'],
            'error_types': self.statistics['error_types'],
            'severity_distribution': self.statistics['severity_counts'],
            'errors': [error.to_dict() for error in self.errors],
            'quality_score': self._calculate_quality_score()
        }

    def _calculate_quality_score(self) -> float:
        """计算质量分数 (0-100)"""
        if self.statistics['total_geometries'] == 0:
            return 0.0

        # 基础分数：有效性比例
        base_score = (self.statistics['valid_geometries'] /
                     self.statistics['total_geometries']) * 100

        # 错误惩罚
        high_penalty = self.statistics['severity_counts']['high'] * 10
        medium_penalty = self.statistics['severity_counts']['medium'] * 5
        low_penalty = self.statistics['severity_counts']['low'] * 2

        total_penalty = high_penalty + medium_penalty + low_penalty
        penalty_per_geom = total_penalty / max(1, self.statistics['total_geometries'])

        # 最终分数
        final_score = max(0, base_score - penalty_per_geom * 10)
        return round(final_score, 2)

    def get_repair_suggestions(self) -> List[Dict]:
        """获取修复建议"""
        suggestions = []

        error_type_suggestions = {
            'invalid_geometry': {
                'action': 'make_valid',
                'description': '使用 make_valid() 函数修复无效几何',
                'auto_fixable': True
            },
            'self_intersection': {
                'action': 'fix_intersection',
                'description': '使用几何修复工具处理自相交问题',
                'auto_fixable': False
            },
            'empty_geometry': {
                'action': 'remove_or_ignore',
                'description': '删除或忽略空几何对象',
                'auto_fixable': True
            },
            'duplicate_points': {
                'action': 'simplify',
                'description': '使用简化算法去除重复点',
                'auto_fixable': True
            },
            'precision_issue': {
                'action': 'snap_to_grid',
                'description': '使用网格对齐解决精度问题',
                'auto_fixable': True
            },
            'out_of_bounds': {
                'action': 'manual_review',
                'description': '需要手动检查坐标是否正确',
                'auto_fixable': False
            }
        }

        for error in self.errors:
            if error.error_type in error_type_suggestions:
                suggestion = error_type_suggestions[error.error_type].copy()
                suggestion['geometry_id'] = error.geometry_id
                suggestion['error_message'] = error.message
                suggestions.append(suggestion)

        return suggestions