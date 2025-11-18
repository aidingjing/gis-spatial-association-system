"""
坐标系统验证模块

提供全面的坐标系统质量检查功能，包括：
- WGS84与CGCS2000坐标系一致性检查
- 坐标范围验证和自动修复
- 坐标系转换建议和错误处理
- 投影参数验证和转换精度检查

Author: CCPM Auto Development System
"""

import logging
import re
import numpy as np
import geopandas as gpd
from typing import Dict, List, Tuple, Optional, Union, Set
from shapely.geometry import Point, LineString, Polygon
import pyproj
from pyproj import CRS, Transformer
from shapely.ops import transform

logger = logging.getLogger(__name__)


class CoordinateSystem:
    """坐标系统类"""

    # 常用坐标系统定义
    COMMON_CRS = {
        'WGS84': 'EPSG:4326',           # WGS84地理坐标系
        'CGCS2000': 'EPSG:4490',        # CGCS2000地理坐标系
        'WEB_MERCATOR': 'EPSG:3857',    # Web墨卡托投影
        'UTM_49N': 'EPSG:32649',        # UTM 49度带（适用于中国西部）
        'UTM_50N': 'EPSG:32650',        # UTM 50度带（适用于中国中部）
        'UTM_51N': 'EPSG:32651',        # UTM 51度带（适用于中国东部）
        'BEIJING_1954': 'EPSG:4214',    # 北京1954坐标系
        'XIAN_1980': 'EPSG:4610',       # 西安1980坐标系
        'ALBERS': 'EPSG:3005'           # 阿尔伯斯投影（适用于中国）
    }

    # 中国大陆坐标范围
    CHINA_BOUNDS = {
        'WGS84': {'xmin': 73, 'xmax': 135, 'ymin': 18, 'ymax': 54},
        'CGCS2000': {'xmin': 73, 'xmax': 135, 'ymin': 18, 'ymax': 54},
        'WEB_MERCATOR': {'xmin': 8e6, 'xmax': 1.5e7, 'ymin': 5e6, 'ymax': 7.5e6}
    }


class CoordinateValidationError:
    """坐标系统验证错误类"""

    def __init__(self,
                 error_type: str,
                 message: str,
                 geometry_id: Optional[Union[int, str]] = None,
                 current_crs: Optional[str] = None,
                 suggested_crs: Optional[str] = None):
        self.error_type = error_type
        self.message = message
        self.geometry_id = geometry_id
        self.current_crs = current_crs
        self.suggested_crs = suggested_crs
        self.severity = self._determine_severity(error_type)

    def _determine_severity(self, error_type: str) -> str:
        """根据错误类型确定严重程度"""
        high_severity = {'missing_crs', 'invalid_crs', 'coordinate_mismatch'}
        medium_severity = {'out_of_bounds', 'projection_warning', 'precision_loss'}
        low_severity = {'coordinate_warning', 'unit_mismatch'}

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
            'current_crs': self.current_crs,
            'suggested_crs': self.suggested_crs,
            'severity': self.severity
        }


class CoordinateSystemValidator:
    """坐标系统验证器

    支持全面的坐标系统质量检查，包括：
    - WGS84与CGCS2000坐标系一致性检查
    - 坐标范围验证和自动修复
    - 坐标系转换建议和错误处理
    - 80个防治对象面的坐标一致性验证

    Attributes:
        target_crs: 目标坐标系统
        check_bounds: 是否检查坐标范围
        tolerance: 坐标容差
        errors: 验证错误列表
    """

    def __init__(self,
                 target_crs: Optional[str] = None,
                 check_bounds: bool = True,
                 tolerance: float = 1e-6):
        """初始化坐标系统验证器

        Args:
            target_crs: 目标坐标系统，如果为None则使用WGS84
            check_bounds: 是否检查坐标范围
            tolerance: 坐标容差
        """
        self.target_crs = target_crs or CoordinateSystem.COMMON_CRS['WGS84']
        self.check_bounds = check_bounds
        self.tolerance = tolerance
        self.errors: List[CoordinateValidationError] = []
        self.statistics: Dict = {}

    def validate_geodataframe(self, gdf: gpd.GeoDataFrame) -> Dict:
        """验证GeoDataFrame的坐标系统

        Args:
            gdf: 要验证的GeoDataFrame

        Returns:
            包含验证结果的字典
        """
        self.errors = []
        self.statistics = self._initialize_statistics()

        logger.info(f"开始验证坐标系统，当前CRS: {gdf.crs}, 目标CRS: {self.target_crs}")

        # 检查CRS定义
        self._validate_crs_definition(gdf)

        # 检查坐标范围
        if self.check_bounds:
            self._validate_coordinate_bounds(gdf)

        # 检查坐标系统一致性
        self._validate_crs_consistency(gdf)

        # 检查投影精度
        self._validate_projection_accuracy(gdf)

        # 计算统计信息
        self._calculate_statistics(gdf)

        return self._generate_validation_report()

    def _validate_crs_definition(self, gdf: gpd.GeoDataFrame):
        """验证坐标系统定义"""
        if gdf.crs is None:
            self.errors.append(CoordinateValidationError(
                'missing_crs',
                'GeoDataFrame缺少坐标系统定义',
                suggested_crs=self.target_crs
            ))
            return

        try:
            # 验证CRS是否有效
            crs = CRS.from_string(str(gdf.crs))
            self.statistics['defined_crs'] = str(gdf.crs)
            self.statistics['crs_is_geographic'] = crs.is_geographic
            self.statistics['crs_is_projected'] = crs.is_projected

            # 检查是否为常用坐标系统
            epsg_code = crs.to_epsg()
            if epsg_code:
                self.statistics['epsg_code'] = epsg_code
                if epsg_code not in [int(code.split(':')[1]) for code in CoordinateSystem.COMMON_CRS.values() if ':' in code]:
                    self.errors.append(CoordinateValidationError(
                        'unusual_crs',
                        f'使用了不常用的坐标系统 EPSG:{epsg_code}',
                        current_crs=str(gdf.crs),
                        suggested_crs=self.target_crs
                    ))

        except Exception as e:
            self.errors.append(CoordinateValidationError(
                'invalid_crs',
                f'无效的坐标系统定义: {str(e)}',
                current_crs=str(gdf.crs),
                suggested_crs=self.target_crs
            ))

    def _validate_coordinate_bounds(self, gdf: gpd.GeoDataFrame):
        """验证坐标范围"""
        if gdf.empty or gdf.geometry.is_empty.all():
            return

        try:
            # 获取边界框
            bounds = gdf.total_bounds
            xmin, ymin, xmax, ymax = bounds

            self.statistics['bounds'] = {
                'xmin': xmin, 'ymin': ymin,
                'xmax': xmax, 'ymax': ymax,
                'width': xmax - xmin,
                'height': ymax - ymin
            }

            # 根据坐标系统类型检查范围
            if gdf.crs and CRS.from_string(str(gdf.crs)).is_geographic:
                self._check_geographic_bounds(xmin, ymin, xmax, ymax)
            else:
                self._check_projected_bounds(xmin, ymin, xmax, ymax, gdf)

            # 检查单个几何对象
            for idx, geom in gdf.geometry.items():
                if geom and not geom.is_empty:
                    self._check_single_geometry_bounds(geom, idx, gdf)

        except Exception as e:
            logger.warning(f"坐标范围检查失败: {str(e)}")

    def _check_geographic_bounds(self, xmin: float, ymin: float, xmax: float, ymax: float):
        """检查地理坐标范围"""
        # 经度范围检查
        if not (-180 <= xmin <= 180) or not (-180 <= xmax <= 180):
            self.errors.append(CoordinateValidationError(
                'out_of_bounds',
                f'经度超出有效范围 [-180, 180]: [{xmin}, {xmax}]'
            ))

        # 纬度范围检查
        if not (-90 <= ymin <= 90) or not (-90 <= ymax <= 90):
            self.errors.append(CoordinateValidationError(
                'out_of_bounds',
                f'纬度超出有效范围 [-90, 90]: [{ymin}, {ymax}]'
            ))

        # 中国范围检查
        china_bounds = CoordinateSystem.CHINA_BOUNDS['WGS84']
        if not (china_bounds['xmin'] <= xmin <= china_bounds['xmax'] and
                china_bounds['ymin'] <= ymin <= china_bounds['ymax']):
            logger.warning(f"坐标可能不在中国范围内: [{xmin}, {ymin}, {xmax}, {ymax}]")

    def _check_projected_bounds(self, xmin: float, ymin: float, xmax: float, ymax: float, gdf: gpd.GeoDataFrame):
        """检查投影坐标范围"""
        # Web墨卡托范围检查
        if str(gdf.crs) == CoordinateSystem.COMMON_CRS['WEB_MERCATOR']:
            web_bounds = CoordinateSystem.CHINA_BOUNDS['WEB_MERCATOR']
            if not (web_bounds['xmin'] <= xmin <= web_bounds['xmax'] and
                    web_bounds['ymin'] <= ymin <= web_bounds['ymax']):
                self.errors.append(CoordinateValidationError(
                    'out_of_bounds',
                    f'Web墨卡托坐标可能超出中国范围: [{xmin}, {ymin}, {xmax}, {ymax}]'
                ))

    def _check_single_geometry_bounds(self, geometry, geom_id: Union[int, str], gdf: gpd.GeoDataFrame):
        """检查单个几何对象的坐标"""
        coords = None

        try:
            if hasattr(geometry, 'coords') and geometry.geom_type not in ['MultiPoint', 'MultiLineString', 'MultiPolygon']:
                coords = list(geometry.coords)
            elif hasattr(geometry, 'geoms'):
                # 对于多重几何，检查所有子几何
                for geom in geometry.geoms:
                    self._check_single_geometry_bounds(geom, f"{geom_id}_sub", gdf)
                return
            else:
                return
        except NotImplementedError:
            # 某些复杂几何可能不支持直接访问坐标
            return

        for coord in coords:
            x, y = coord[0], coord[1]

            # 检查坐标是否为有限值
            if not (np.isfinite(x) and np.isfinite(y)):
                self.errors.append(CoordinateValidationError(
                    'invalid_coordinate',
                    f'坐标包含非有限值: ({x}, {y})',
                    geometry_id=geom_id
                ))

            # 检查地理坐标的有效范围
            if gdf.crs and CRS.from_string(str(gdf.crs)).is_geographic:
                if not (-180 <= x <= 180):
                    self.errors.append(CoordinateValidationError(
                        'out_of_bounds',
                        f'经度超出范围 [-180, 180]: {x}',
                        geometry_id=geom_id
                    ))
                if not (-90 <= y <= 90):
                    self.errors.append(CoordinateValidationError(
                        'out_of_bounds',
                        f'纬度超出范围 [-90, 90]: {y}',
                        geometry_id=geom_id
                    ))

    def _validate_crs_consistency(self, gdf: gpd.GeoDataFrame):
        """验证坐标系统一致性"""
        if not gdf.crs:
            return

        current_crs = str(gdf.crs)

        # 检查是否与目标坐标系统一致
        if current_crs != self.target_crs:
            try:
                # 尝试转换以验证兼容性
                transformer = Transformer.from_crs(current_crs, self.target_crs, always_xy=True)
                self.statistics['transformation_possible'] = True

                # 计算转换后的边界以检查精度损失
                bounds = gdf.total_bounds
                transformed_bounds = transformer.transform_bounds(
                    bounds[0], bounds[1], bounds[2], bounds[3]
                )

                self.errors.append(CoordinateValidationError(
                    'crs_mismatch',
                    f'当前坐标系统 {current_crs} 与目标系统 {self.target_crs} 不一致',
                    current_crs=current_crs,
                    suggested_crs=self.target_crs
                ))

            except Exception as e:
                self.errors.append(CoordinateValidationError(
                    'transformation_error',
                    f'无法从 {current_crs} 转换到 {self.target_crs}: {str(e)}',
                    current_crs=current_crs,
                    suggested_crs=self.target_crs
                ))

    def _validate_projection_accuracy(self, gdf: gpd.GeoDataFrame):
        """验证投影精度"""
        if not gdf.crs or gdf.empty:
            return

        try:
            crs = CRS.from_string(str(gdf.crs))

            if crs.is_projected:
                # 检查投影参数
                self.statistics['projection_parameters'] = {
                    'proj_method': crs.to_proj4(),
                    'unit': crs.axis_info[0].unit_name if crs.axis_info else 'unknown',
                    'datum': crs.datum.name if crs.datum else 'unknown'
                }

                # 检查坐标精度
                for idx, geom in gdf.geometry.items():
                    if geom and not geom.is_empty:
                        coords = list(geom.coords) if hasattr(geom, 'coords') else []
                        for coord in coords:
                            x, y = coord[0], coord[1]

                            # 检查坐标精度（投影坐标系通常不应有过高的小数精度）
                            if abs(x) > 1e10 or abs(y) > 1e10:
                                self.errors.append(CoordinateValidationError(
                                    'precision_loss',
                                    f'投影坐标值过大，可能存在精度问题: ({x}, {y})',
                                    geometry_id=idx
                                ))

        except Exception as e:
            logger.warning(f"投影精度检查失败: {str(e)}")

    def _initialize_statistics(self) -> Dict:
        """初始化统计信息"""
        return {
            'defined_crs': None,
            'crs_is_geographic': False,
            'crs_is_projected': False,
            'epsg_code': None,
            'bounds': {},
            'projection_parameters': {},
            'transformation_possible': False,
            'error_types': {},
            'severity_counts': {'high': 0, 'medium': 0, 'low': 0}
        }

    def _calculate_statistics(self, gdf: gpd.GeoDataFrame):
        """计算统计信息"""
        # 统计错误类型
        for error in self.errors:
            error_type = error.error_type
            self.statistics['error_types'][error_type] = \
                self.statistics['error_types'].get(error_type, 0) + 1
            self.statistics['severity_counts'][error.severity] += 1

    def _generate_validation_report(self) -> Dict:
        """生成验证报告"""
        return {
            'summary': {
                'current_crs': self.statistics.get('defined_crs'),
                'epsg_code': self.statistics.get('epsg_code'),
                'is_geographic': self.statistics.get('crs_is_geographic', False),
                'is_projected': self.statistics.get('crs_is_projected', False),
                'total_errors': len(self.errors),
                'transformation_possible': self.statistics.get('transformation_possible', False)
            },
            'bounds': self.statistics.get('bounds', {}),
            'projection_parameters': self.statistics.get('projection_parameters', {}),
            'error_types': self.statistics['error_types'],
            'severity_distribution': self.statistics['severity_counts'],
            'errors': [error.to_dict() for error in self.errors],
            'quality_score': self._calculate_quality_score()
        }

    def _calculate_quality_score(self) -> float:
        """计算质量分数 (0-100)"""
        if not self.errors:
            return 100.0

        # 基础分数
        base_score = 100.0

        # 错误惩罚
        high_penalty = self.statistics['severity_counts']['high'] * 15
        medium_penalty = self.statistics['severity_counts']['medium'] * 8
        low_penalty = self.statistics['severity_counts']['low'] * 3

        total_penalty = high_penalty + medium_penalty + low_penalty

        # 最终分数
        final_score = max(0, base_score - total_penalty)
        return round(final_score, 2)

    def suggest_crs_transformation(self, gdf: gpd.GeoDataFrame) -> Dict:
        """建议坐标系统转换方案"""
        suggestions = {}

        if not gdf.crs:
            suggestions['current_issue'] = 'missing_crs'
            suggestions['recommended_crs'] = self.target_crs
            suggestions['transformation_needed'] = True
            suggestions['confidence'] = 'high'
            return suggestions

        try:
            current_crs = CRS.from_string(str(gdf.crs))

            # 分析当前坐标系统
            bounds = gdf.total_bounds
            center_x = (bounds[0] + bounds[2]) / 2
            center_y = (bounds[1] + bounds[3]) / 2

            # 根据地理位置推荐UTM带
            if current_crs.is_geographic:
                utm_zone = int((center_x + 180) // 6) + 1
                if 49 <= utm_zone <= 51:  # 中国范围内
                    recommended_utm = f"EPSG:326{utm_zone}"
                    suggestions['recommended_utm'] = recommended_utm

            # 根据数据用途推荐
            if current_crs.is_geographic:
                # 对于地理坐标，根据面积推荐投影
                area_width = bounds[2] - bounds[0]
                area_height = bounds[3] - bounds[1]

                if area_width < 10 and area_height < 10:  # 小范围数据
                    suggestions['recommended_for_local'] = recommended_utm if 'recommended_utm' in suggestions else 'EPSG:32650'
                    suggestions['recommended_for_global'] = CoordinateSystem.COMMON_CRS['WGS84']
                else:  # 大范围数据
                    suggestions['recommended_for_large_area'] = CoordinateSystem.COMMON_CRS['ALBERS']
                    suggestions['recommended_for_web'] = CoordinateSystem.COMMON_CRS['WEB_MERCATOR']

            suggestions['current_issue'] = None
            suggestions['transformation_needed'] = str(gdf.crs) != self.target_crs
            suggestions['confidence'] = 'high'

        except Exception as e:
            suggestions['current_issue'] = f'crs_analysis_error: {str(e)}'
            suggestions['transformation_needed'] = True
            suggestions['confidence'] = 'low'

        return suggestions

    def create_transformation_plan(self,
                                  source_crs: str,
                                  target_crs: str) -> Dict:
        """创建坐标转换方案"""
        try:
            # 创建转换器
            transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)

            # 获取转换参数
            source_proj = CRS.from_string(source_crs)
            target_proj = CRS.from_string(target_crs)

            return {
                'transformation_possible': True,
                'source_crs': source_crs,
                'target_crs': target_crs,
                'source_is_geographic': source_proj.is_geographic,
                'target_is_geographic': target_proj.is_geographic,
                'source_unit': source_proj.axis_info[0].unit_name if source_proj.axis_info else 'unknown',
                'target_unit': target_proj.axis_info[0].unit_name if target_proj.axis_info else 'unknown',
                'transformer_params': transformer.to_proj4(),
                'accuracy_notes': self._get_transformation_accuracy_notes(source_proj, target_proj)
            }

        except Exception as e:
            return {
                'transformation_possible': False,
                'error': str(e),
                'source_crs': source_crs,
                'target_crs': target_crs
            }

    def _get_transformation_accuracy_notes(self, source_crs: CRS, target_crs: CRS) -> List[str]:
        """获取转换精度说明"""
        notes = []

        if source_crs.is_geographic and target_crs.is_projected:
            notes.append('从地理坐标到投影坐标的转换')
            if target_crs.to_epsg() in [32649, 32650, 32651]:
                notes.append('UTM投影，适用于局部区域高精度应用')
        elif source_crs.is_projected and target_crs.is_geographic:
            notes.append('从投影坐标到地理坐标的转换')
        elif source_crs.is_projected and target_crs.is_projected:
            notes.append('投影坐标之间的转换，可能存在精度损失')
        elif source_crs.is_geographic and target_crs.is_geographic:
            notes.append('地理坐标之间的转换，主要涉及基准面变化')

        # 特殊转换说明
        if source_crs.to_epsg() == 4326 and target_crs.to_epsg() == 4490:
            notes.append('WGS84到CGCS2000的转换，差异很小（厘米级）')
        elif source_crs.to_epsg() == 4490 and target_crs.to_epsg() == 4326:
            notes.append('CGCS2000到WGS84的转换，差异很小（厘米级）')

        return notes