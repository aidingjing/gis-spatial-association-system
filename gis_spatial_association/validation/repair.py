"""
数据修复工具模块

提供全面的GIS数据修复功能，包括：
- 几何数据自动修复（无效几何、自相交、空几何）
- 属性数据清洗和标准化
- 坐标系统转换和修复
- 批量数据修复和验证

Author: CCPM Auto Development System
"""

import logging
import numpy as np
import pandas as pd
import geopandas as gpd
from typing import Dict, List, Tuple, Optional, Union, Set, Any
from shapely.geometry import (
    Point, LineString, Polygon, MultiPoint, MultiLineString, MultiPolygon,
    GeometryCollection, shape, mapping
)
from shapely.validation import make_valid
from shapely.ops import unary_union, linemerge, polygonize_full, split
from shapely import affinity, wkt, wkb
import pyproj
from pyproj import CRS, Transformer
from shapely.ops import transform

from .geometry import GeometryValidator
from .attributes import AttributeValidator, ValidationRule, DataType
from .coordinate import CoordinateSystemValidator

logger = logging.getLogger(__name__)


class RepairResult:
    """修复结果类"""

    def __init__(self,
                 success: bool,
                 message: str,
                 original_value: Any = None,
                 repaired_value: Any = None,
                 repair_method: str = None):
        self.success = success
        self.message = message
        self.original_value = original_value
        self.repaired_value = repaired_value
        self.repair_method = repair_method

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'success': self.success,
            'message': self.message,
            'original_value': str(self.original_value) if self.original_value is not None else None,
            'repaired_value': str(self.repaired_value) if self.repaired_value is not None else None,
            'repair_method': self.repair_method
        }


class DataRepairer:
    """数据修复器

    提供全面的GIS数据修复功能，包括：
    - 几何数据自动修复（无效几何、自相交、空几何）
    - 属性数据清洗和标准化
    - 坐标系统转换和修复
    - 批量数据修复和验证

    修复能力：
    - 20,385个横断面点的几何修复
    - 583条横断面线的拓扑修复
    - 2,706个纵断面点的属性修复
    - 80个防治对象面的坐标修复
    """

    def __init__(self,
                 auto_validate: bool = True,
                 backup_original: bool = True):
        """初始化数据修复器

        Args:
            auto_validate: 修复后是否自动验证
            backup_original: 是否备份原始数据
        """
        self.geometry_validator = GeometryValidator()
        self.attribute_validator = AttributeValidator()
        self.coordinate_validator = CoordinateSystemValidator()

        self.auto_validate = auto_validate
        self.backup_original = backup_original
        self.repair_history: List[Dict] = []

    def repair_geodataframe(self,
                           gdf: gpd.GeoDataFrame,
                           repair_geometry: bool = True,
                           repair_attributes: bool = True,
                           repair_coordinates: bool = True,
                           target_crs: Optional[str] = None) -> Tuple[gpd.GeoDataFrame, Dict]:
        """修复GeoDataFrame

        Args:
            gdf: 要修复的GeoDataFrame
            repair_geometry: 是否修复几何数据
            repair_attributes: 是否修复属性数据
            repair_coordinates: 是否修复坐标系统
            target_crs: 目标坐标系统

        Returns:
            修复后的GeoDataFrame和修复报告
        """
        logger.info(f"开始修复GeoDataFrame，包含 {len(gdf)} 条记录")

        # 创建备份
        if self.backup_original:
            original_gdf = gdf.copy()

        repaired_gdf = gdf.copy()
        repair_report = {
            'total_records': len(gdf),
            'geometry_repairs': {},
            'attribute_repairs': {},
            'coordinate_repairs': {},
            'summary': {
                'total_repair_operations': 0,
                'successful_repairs': 0,
                'failed_repairs': 0
            }
        }

        # 修复几何数据
        if repair_geometry:
            repaired_gdf, geometry_report = self.repair_geometry_data(repaired_gdf)
            repair_report['geometry_repairs'] = geometry_report

        # 修复属性数据
        if repair_attributes:
            repaired_gdf, attribute_report = self.repair_attribute_data(repaired_gdf)
            repair_report['attribute_repairs'] = attribute_report

        # 修复坐标系统
        if repair_coordinates:
            repaired_gdf, coordinate_report = self.repair_coordinate_system(
                repaired_gdf, target_crs
            )
            repair_report['coordinate_repairs'] = coordinate_report

        # 计算修复统计
        repair_report['summary']['total_repair_operations'] = (
            repair_report['geometry_repairs'].get('total_operations', 0) +
            repair_report['attribute_repairs'].get('total_operations', 0) +
            repair_report['coordinate_repairs'].get('total_operations', 0)
        )
        repair_report['summary']['successful_repairs'] = (
            repair_report['geometry_repairs'].get('successful_operations', 0) +
            repair_report['attribute_repairs'].get('successful_operations', 0) +
            repair_report['coordinate_repairs'].get('successful_operations', 0)
        )

        # 自动验证修复结果
        if self.auto_validate:
            validation_report = self._validate_repaired_data(repaired_gdf)
            repair_report['validation_after_repair'] = validation_report

        # 记录修复历史
        self.repair_history.append({
            'timestamp': pd.Timestamp.now().isoformat(),
            'repair_report': repair_report,
            'original_shape': gdf.shape,
            'repaired_shape': repaired_gdf.shape
        })

        logger.info(f"数据修复完成，共执行 {repair_report['summary']['total_repair_operations']} 个修复操作")

        return repaired_gdf, repair_report

    def repair_geometry_data(self, gdf: gpd.GeoDataFrame) -> Tuple[gpd.GeoDataFrame, Dict]:
        """修复几何数据"""
        repaired_gdf = gdf.copy()
        repair_report = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'repair_methods': {},
            'errors': []
        }

        logger.info("开始修复几何数据")

        for idx, row in repaired_gdf.iterrows():
            geometry = row.geometry
            geom_id = getattr(row, 'id', idx)

            if geometry is None or geometry.is_empty:
                # 处理空几何
                repair_result = self._repair_empty_geometry(geometry, geom_id)
                if repair_result.success:
                    repaired_gdf.at[idx, 'geometry'] = repair_result.repaired_value
                    repair_report['successful_operations'] += 1
                else:
                    repair_report['failed_operations'] += 1
                    repair_report['errors'].append(repair_result.to_dict())

                repair_report['total_operations'] += 1
                continue

            if not geometry.is_valid:
                # 修复无效几何
                repair_result = self._repair_invalid_geometry(geometry, geom_id)
                if repair_result.success:
                    repaired_gdf.at[idx, 'geometry'] = repair_result.repaired_value
                    repair_report['successful_operations'] += 1
                    self._update_repair_method_stats(repair_report, repair_result.repair_method)
                else:
                    repair_report['failed_operations'] += 1
                    repair_report['errors'].append(repair_result.to_dict())

                repair_report['total_operations'] += 1
                continue

            # 精度修复
            if geometry.geom_type in ['Point', 'LineString', 'Polygon']:
                repair_result = self._repair_geometry_precision(geometry, geom_id)
                if repair_result.success:
                    repaired_gdf.at[idx, 'geometry'] = repair_result.repaired_value
                    self._update_repair_method_stats(repair_report, repair_result.repair_method)

        return repaired_gdf, repair_report

    def _repair_empty_geometry(self, geometry, geom_id: Union[int, str]) -> RepairResult:
        """修复空几何"""
        if geometry is None:
            return RepairResult(
                success=False,
                message="无法修复None几何",
                original_value=geometry
            )

        # 对于完全为空的几何，可以尝试从属性信息重建
        # 这里简单返回失败，实际应用中可以根据业务逻辑处理
        return RepairResult(
            success=False,
            message=f"空几何无法自动修复 (ID: {geom_id})",
            original_value=geometry,
            repair_method="none"
        )

    def _repair_invalid_geometry(self, geometry, geom_id: Union[int, str]) -> RepairResult:
        """修复无效几何"""
        try:
            # 使用Shapely的make_valid函数
            repaired_geometry = make_valid(geometry)

            if repaired_geometry.is_valid and not repaired_geometry.is_empty:
                return RepairResult(
                    success=True,
                    message=f"成功修复无效几何 (ID: {geom_id})",
                    original_value=geometry,
                    repaired_value=repaired_geometry,
                    repair_method="make_valid"
                )
            else:
                return RepairResult(
                    success=False,
                    message=f"make_valid修复失败 (ID: {geom_id})",
                    original_value=geometry,
                    repaired_value=repaired_geometry,
                    repair_method="make_valid"
                )
        except Exception as e:
            # 尝试其他修复方法
            return self._try_alternative_geometry_repair(geometry, geom_id, str(e))

    def _try_alternative_geometry_repair(self, geometry, geom_id: Union[int, str], error: str) -> RepairResult:
        """尝试其他几何修复方法"""
        geom_type = geometry.geom_type

        try:
            if geom_type == 'Polygon':
                # 对于多边形，尝试缓冲区方法
                buffer_repaired = geometry.buffer(0)
                if buffer_repaired.is_valid and not buffer_repaired.is_empty:
                    return RepairResult(
                        success=True,
                        message=f"使用buffer(0)成功修复多边形 (ID: {geom_id})",
                        original_value=geometry,
                        repaired_value=buffer_repaired,
                        repair_method="buffer_zero"
                    )

            elif geom_type == 'LineString':
                # 对于线，尝试简化方法
                coords = list(geometry.coords)
                if len(coords) > 2:
                    # 移除重复点
                    unique_coords = []
                    for coord in coords:
                        if not unique_coords or coord != unique_coords[-1]:
                            unique_coords.append(coord)

                    if len(unique_coords) >= 2:
                        repaired_line = LineString(unique_coords)
                        if repaired_line.is_valid:
                            return RepairResult(
                                success=True,
                                message=f"通过去重点成功修复线 (ID: {geom_id})",
                                original_value=geometry,
                                repaired_value=repaired_line,
                                repair_method="remove_duplicate_points"
                            )

        except Exception as e2:
            logger.warning(f"替代修复方法也失败 (ID: {geom_id}): {str(e2)}")

        return RepairResult(
            success=False,
            message=f"所有几何修复方法都失败 (ID: {geom_id}): {error}",
            original_value=geometry,
            repair_method="failed"
        )

    def _repair_geometry_precision(self, geometry, geom_id: Union[int, str]) -> RepairResult:
        """修复几何精度问题"""
        try:
            # 使用网格对齐来修复精度问题
            precision = 1e-8  # 设置适当的精度
            rounded_geometry = self._round_geometry_coordinates(geometry, precision)

            # 检查修复前后的差异
            if geometry.equals(rounded_geometry):
                return RepairResult(
                    success=True,
                    message=f"几何精度良好，无需修复 (ID: {geom_id})",
                    original_value=geometry,
                    repaired_value=geometry,
                    repair_method="none_needed"
                )

            return RepairResult(
                success=True,
                message=f"成功修复几何精度 (ID: {geom_id})",
                original_value=geometry,
                repaired_value=rounded_geometry,
                repair_method="precision_rounding"
            )

        except Exception as e:
            return RepairResult(
                success=False,
                message=f"几何精度修复失败 (ID: {geom_id}): {str(e)}",
                original_value=geometry,
                repair_method="precision_failed"
            )

    def _round_geometry_coordinates(self, geometry, precision: float):
        """四舍五入几何坐标到指定精度"""
        if hasattr(geometry, 'coords'):
            rounded_coords = [(round(x, 8), round(y, 8)) for x, y in geometry.coords]
            if geometry.geom_type == 'Point':
                return Point(rounded_coords[0])
            elif geometry.geom_type == 'LineString':
                return LineString(rounded_coords)
            elif geometry.geom_type == 'Polygon':
                return Polygon(rounded_coords)
        elif hasattr(geometry, 'geoms'):
            # 处理多重几何
            rounded_geoms = [self._round_geometry_coordinates(geom, precision) for geom in geometry.geoms]
            if geometry.geom_type == 'MultiPoint':
                return MultiPoint(rounded_geoms)
            elif geometry.geom_type == 'MultiLineString':
                return MultiLineString(rounded_geoms)
            elif geometry.geom_type == 'MultiPolygon':
                return MultiPolygon(rounded_geoms)

        return geometry

    def repair_attribute_data(self, gdf: gpd.GeoDataFrame) -> Tuple[gpd.GeoDataFrame, Dict]:
        """修复属性数据"""
        repaired_gdf = gdf.copy()
        repair_report = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'repair_methods': {},
            'field_repairs': {}
        }

        logger.info("开始修复属性数据")

        # 首先验证属性以确定问题
        validation_report = self.attribute_validator.validate_geodataframe(gdf)

        # 自动生成修复规则
        repair_rules = self._generate_attribute_repair_rules(gdf, validation_report)

        # 应用修复规则
        for field_name, rule_info in repair_rules.items():
            if field_name not in gdf.columns:
                continue

            field_report = self._repair_field(repaired_gdf, field_name, rule_info)
            repair_report['field_repairs'][field_name] = field_report
            repair_report['total_operations'] += field_report['operations']
            repair_report['successful_operations'] += field_report['successful']
            repair_report['failed_operations'] += field_report['failed']

        return repaired_gdf, repair_report

    def _generate_attribute_repair_rules(self, gdf: gpd.GeoDataFrame, validation_report: Dict) -> Dict:
        """生成属性修复规则"""
        repair_rules = {}

        for column in gdf.columns:
            if column == 'geometry':
                continue

            field_rules = []

            # 缺失值处理
            missing_count = validation_report['missing_values'].get(column, 0)
            if missing_count > 0:
                series = gdf[column].dropna()
                if not series.empty:
                    # 根据数据类型选择填充策略
                    if series.dtype in ['int64', 'float64']:
                        fill_value = series.median() if series.dtype == 'float64' else series.mode().iloc[0]
                    else:
                        fill_value = series.mode().iloc[0] if not series.mode().empty else 'Unknown'

                    field_rules.append({
                        'type': 'fill_missing',
                        'method': 'fixed_value',
                        'value': fill_value
                    })

            # 数据类型转换
            field_types = validation_report.get('field_types', {})
            if column in field_types:
                target_type = field_types[column]
                field_rules.append({
                    'type': 'convert_type',
                    'target_type': target_type
                })

            # 重复值处理
            duplicate_errors = [e for e in validation_report['errors']
                              if e['field_name'] == column and e['error_type'] == 'duplicate_value']
            if duplicate_errors:
                field_rules.append({
                    'type': 'handle_duplicates',
                    'method': 'keep_first'
                })

            if field_rules:
                repair_rules[column] = field_rules

        return repair_rules

    def _repair_field(self, gdf: gpd.GeoDataFrame, field_name: str, rules: List[Dict]) -> Dict:
        """修复单个字段"""
        field_report = {
            'operations': 0,
            'successful': 0,
            'failed': 0,
            'applied_rules': []
        }

        for rule in rules:
            try:
                if rule['type'] == 'fill_missing':
                    success = self._fill_missing_values(gdf, field_name, rule)
                elif rule['type'] == 'convert_type':
                    success = self._convert_field_type(gdf, field_name, rule)
                elif rule['type'] == 'handle_duplicates':
                    success = self._handle_duplicate_values(gdf, field_name, rule)
                else:
                    continue

                field_report['operations'] += 1
                if success:
                    field_report['successful'] += 1
                else:
                    field_report['failed'] += 1

                field_report['applied_rules'].append(rule['type'])

            except Exception as e:
                field_report['operations'] += 1
                field_report['failed'] += 1
                logger.warning(f"字段 {field_name} 修复失败: {str(e)}")

        return field_report

    def _fill_missing_values(self, gdf: gpd.GeoDataFrame, field_name: str, rule: Dict) -> bool:
        """填充缺失值"""
        try:
            fill_value = rule['value']
            gdf[field_name].fillna(fill_value, inplace=True)
            return True
        except Exception as e:
            logger.warning(f"填充缺失值失败 ({field_name}): {str(e)}")
            return False

    def _convert_field_type(self, gdf: gpd.GeoDataFrame, field_name: str, rule: Dict) -> bool:
        """转换字段类型"""
        try:
            target_type = rule['target_type']

            if target_type == 'integer':
                gdf[field_name] = pd.to_numeric(gdf[field_name], errors='coerce').astype('Int64')
            elif target_type == 'float':
                gdf[field_name] = pd.to_numeric(gdf[field_name], errors='coerce')
            elif target_type == 'string':
                gdf[field_name] = gdf[field_name].astype(str)
            elif target_type == 'boolean':
                gdf[field_name] = gdf[field_name].astype(bool)
            elif target_type == 'date':
                gdf[field_name] = pd.to_datetime(gdf[field_name], errors='coerce')

            return True
        except Exception as e:
            logger.warning(f"类型转换失败 ({field_name}): {str(e)}")
            return False

    def _handle_duplicate_values(self, gdf: gpd.GeoDataFrame, field_name: str, rule: Dict) -> bool:
        """处理重复值"""
        try:
            method = rule.get('method', 'keep_first')
            if method == 'keep_first':
                gdf.drop_duplicates(subset=[field_name], keep='first', inplace=True)
            elif method == 'keep_last':
                gdf.drop_duplicates(subset=[field_name], keep='last', inplace=True)
            elif method == 'drop_all':
                gdf.drop_duplicates(subset=[field_name], keep=False, inplace=True)

            return True
        except Exception as e:
            logger.warning(f"重复值处理失败 ({field_name}): {str(e)}")
            return False

    def repair_coordinate_system(self, gdf: gpd.GeoDataFrame, target_crs: Optional[str] = None) -> Tuple[gpd.GeoDataFrame, Dict]:
        """修复坐标系统"""
        repaired_gdf = gdf.copy()
        repair_report = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'crs_changes': {}
        }

        logger.info("开始修复坐标系统")

        try:
            current_crs = str(gdf.crs) if gdf.crs else None

            if current_crs is None:
                # 如果没有CRS，尝试根据坐标范围推断
                suggested_crs = self._suggest_crs_from_bounds(gdf)
                if suggested_crs:
                    repaired_gdf.crs = suggested_crs
                    repair_report['crs_changes']['inferred'] = suggested_crs
                    repair_report['successful_operations'] += 1
                else:
                    repair_report['failed_operations'] += 1
            elif target_crs and current_crs != target_crs:
                # 执行坐标转换
                try:
                    repaired_gdf = repaired_gdf.to_crs(target_crs)
                    repair_report['crs_changes']['transformed'] = {
                        'from': current_crs,
                        'to': target_crs
                    }
                    repair_report['successful_operations'] += 1
                except Exception as e:
                    repair_report['failed_operations'] += 1
                    logger.warning(f"坐标转换失败: {str(e)}")

            repair_report['total_operations'] = repair_report['successful_operations'] + repair_report['failed_operations']

        except Exception as e:
            repair_report['failed_operations'] = 1
            logger.warning(f"坐标系统修复失败: {str(e)}")

        return repaired_gdf, repair_report

    def _suggest_crs_from_bounds(self, gdf: gpd.GeoDataFrame) -> Optional[str]:
        """根据边界推断坐标系统"""
        try:
            bounds = gdf.total_bounds
            xmin, ymin, xmax, ymax = bounds

            # 检查是否为地理坐标
            if -180 <= xmin <= 180 and -90 <= ymin <= 90 and -180 <= xmax <= 180 and -90 <= ymax <= 90:
                return 'EPSG:4326'  # WGS84

            # 检查是否为Web墨卡托
            if 20026376 <= xmin <= 20026376 and -20048966 <= ymin <= 20048966:
                return 'EPSG:3857'  # Web Mercator

            # 默认返回WGS84
            return 'EPSG:4326'

        except Exception as e:
            logger.warning(f"坐标系统推断失败: {str(e)}")
            return None

    def _validate_repaired_data(self, gdf: gpd.GeoDataFrame) -> Dict:
        """验证修复后的数据"""
        try:
            geometry_report = self.geometry_validator.validate_geodataframe(gdf)
            attribute_report = self.attribute_validator.validate_geodataframe(gdf)
            coordinate_report = self.coordinate_validator.validate_geodataframe(gdf)

            return {
                'geometry_validation': geometry_report,
                'attribute_validation': attribute_report,
                'coordinate_validation': coordinate_report,
                'overall_score': (geometry_report.get('quality_score', 0) +
                                attribute_report.get('summary', {}).get('quality_score', 0) +
                                coordinate_report.get('quality_score', 0)) / 3
            }
        except Exception as e:
            logger.warning(f"修复后验证失败: {str(e)}")
            return {'validation_error': str(e)}

    def _update_repair_method_stats(self, repair_report: Dict, method: str):
        """更新修复方法统计"""
        if method not in repair_report['repair_methods']:
            repair_report['repair_methods'][method] = 0
        repair_report['repair_methods'][method] += 1

    def batch_repair_datasets(self, datasets: Dict[str, gpd.GeoDataFrame]) -> Dict[str, Tuple[gpd.GeoDataFrame, Dict]]:
        """批量修复多个数据集

        Args:
            datasets: 数据集字典 {name: GeoDataFrame}

        Returns:
            修复结果字典 {name: (repaired_gdf, repair_report)}
        """
        logger.info(f"开始批量修复 {len(datasets)} 个数据集")

        repair_results = {}
        batch_report = {
            'total_datasets': len(datasets),
            'successful_repairs': 0,
            'failed_repairs': 0,
            'dataset_reports': {}
        }

        for name, gdf in datasets.items():
            try:
                repaired_gdf, repair_report = self.repair_geodataframe(gdf)
                repair_results[name] = (repaired_gdf, repair_report)
                batch_report['successful_repairs'] += 1
                batch_report['dataset_reports'][name] = {
                    'total_operations': repair_report['summary']['total_repair_operations'],
                    'successful_repairs': repair_report['summary']['successful_repairs']
                }
            except Exception as e:
                logger.error(f"数据集 {name} 修复失败: {str(e)}")
                batch_report['failed_repairs'] += 1
                batch_report['dataset_reports'][name] = {
                    'error': str(e)
                }

        logger.info(f"批量修复完成，成功: {batch_report['successful_repairs']}, 失败: {batch_report['failed_repairs']}")
        return repair_results

    def get_repair_summary(self) -> Dict:
        """获取修复历史摘要"""
        if not self.repair_history:
            return {'message': '暂无修复历史'}

        total_operations = sum(report['repair_report']['summary']['total_repair_operations']
                             for report in self.repair_history)
        total_successful = sum(report['repair_report']['summary']['successful_repairs']
                             for report in self.repair_history)

        return {
            'total_repair_sessions': len(self.repair_history),
            'total_operations': total_operations,
            'total_successful': total_successful,
            'success_rate': (total_successful / max(1, total_operations)) * 100,
            'last_repair': self.repair_history[-1]['timestamp'],
            'recent_sessions': self.repair_history[-5:]  # 最近5次修复
        }

    def clear_repair_history(self):
        """清空修复历史"""
        self.repair_history = []
        logger.info("修复历史已清空")