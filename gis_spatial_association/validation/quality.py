"""
数据质量评分模块

提供综合的数据质量评估功能，包括：
- 综合质量评分算法 (A-F等级)
- 详细的质量报告和改进建议
- 批量数据质量评估
- 多维度质量指标分析

Author: CCPM Auto Development System
"""

import logging
import numpy as np
import pandas as pd
import geopandas as gpd
from typing import Dict, List, Tuple, Optional, Union, Any
from datetime import datetime
import json
from enum import Enum

from .geometry import GeometryValidator
from .attributes import AttributeValidator
from .coordinate import CoordinateSystemValidator

logger = logging.getLogger(__name__)


class QualityGrade(Enum):
    """质量等级枚举"""
    A = 'A'  # 优秀 (90-100分)
    B = 'B'  # 良好 (80-89分)
    C = 'C'  # 一般 (70-79分)
    D = 'D'  # 较差 (60-69分)
    F = 'F'  # 不合格 (0-59分)


class QualityDimension(Enum):
    """质量维度枚举"""
    COMPLETENESS = 'completeness'      # 完整性
    VALIDITY = 'validity'              # 有效性
    CONSISTENCY = 'consistency'        # 一致性
    ACCURACY = 'accuracy'              # 准确性
    PRECISION = 'precision'            # 精确性
    TIMELINESS = 'timeliness'          # 时效性


class QualityMetric:
    """质量指标类"""

    def __init__(self,
                 name: str,
                 dimension: QualityDimension,
                 weight: float = 1.0,
                 description: str = "",
                 threshold: Optional[Dict] = None):
        self.name = name
        self.dimension = dimension
        self.weight = weight
        self.description = description
        self.threshold = threshold or {'excellent': 95, 'good': 80, 'fair': 60, 'poor': 0}
        self.score = 0.0
        self.details = {}

    def calculate_score(self, value: float) -> float:
        """计算指标分数"""
        threshold = self.threshold

        if value >= threshold['excellent']:
            return 100
        elif value >= threshold['good']:
            return 80 + (value - threshold['good']) / (threshold['excellent'] - threshold['good']) * 20
        elif value >= threshold['fair']:
            return 60 + (value - threshold['fair']) / (threshold['good'] - threshold['fair']) * 20
        else:
            return max(0, value / threshold['fair'] * 60)


class DataQualityScorer:
    """数据质量评分器

    提供综合的数据质量评估，包括：
    - 多维度质量指标计算
    - A-F等级评分系统
    - 详细的质量报告和改进建议
    - 批量数据质量评估

    验证目标：
    - 20,385个横断面点的综合质量评分
    - 583条横断面线的几何正确性评分
    - 2,706个纵断面点的属性完整性评分
    - 80个防治对象面的坐标一致性评分
    - 综合数据质量评分≥90分
    """

    def __init__(self,
                 geometry_weight: float = 0.3,
                 attribute_weight: float = 0.4,
                 coordinate_weight: float = 0.2,
                 overall_weight: float = 0.1):
        """初始化数据质量评分器

        Args:
            geometry_weight: 几何质量权重
            attribute_weight: 属性质量权重
            coordinate_weight: 坐标系统质量权重
            overall_weight: 整体质量权重
        """
        self.geometry_validator = GeometryValidator()
        self.attribute_validator = AttributeValidator()
        self.coordinate_validator = CoordinateSystemValidator()

        self.weights = {
            'geometry': geometry_weight,
            'attribute': attribute_weight,
            'coordinate': coordinate_weight,
            'overall': overall_weight
        }

        self.metrics = self._initialize_metrics()
        self.quality_scores = {}
        self.quality_reports = {}

    def _initialize_metrics(self) -> Dict[str, List[QualityMetric]]:
        """初始化质量指标"""
        return {
            'geometry': [
                QualityMetric(
                    'validity_ratio', QualityDimension.VALIDITY, 0.4,
                    '有效几何对象比例'
                ),
                QualityMetric(
                    'completeness_ratio', QualityDimension.COMPLETENESS, 0.3,
                    '非空几何对象比例'
                ),
                QualityMetric(
                    'error_rate', QualityDimension.VALIDITY, 0.3,
                    '几何错误率（反向指标）'
                )
            ],
            'attributes': [
                QualityMetric(
                    'field_completeness', QualityDimension.COMPLETENESS, 0.4,
                    '字段完整性'
                ),
                QualityMetric(
                    'data_consistency', QualityDimension.CONSISTENCY, 0.3,
                    '数据一致性'
                ),
                QualityMetric(
                    'error_ratio', QualityDimension.VALIDITY, 0.3,
                    '属性错误率（反向指标）'
                )
            ],
            'coordinate': [
                QualityMetric(
                    'crs_validity', QualityDimension.VALIDITY, 0.5,
                    '坐标系统有效性'
                ),
                QualityMetric(
                    'bounds_validity', QualityDimension.ACCURACY, 0.3,
                    '坐标范围有效性'
                ),
                QualityMetric(
                    'consistency_ratio', QualityDimension.CONSISTENCY, 0.2,
                    '坐标一致性'
                )
            ],
            'overall': [
                QualityMetric(
                    'record_count', QualityDimension.COMPLETENESS, 0.2,
                    '记录数量充足性'
                ),
                QualityMetric(
                    'spatial_coverage', QualityDimension.ACCURACY, 0.3,
                    '空间覆盖合理性'
                ),
                QualityMetric(
                    'metadata_completeness', QualityDimension.COMPLETENESS, 0.2,
                    '元数据完整性'
                ),
                QualityMetric(
                    'data_freshness', QualityDimension.TIMELINESS, 0.3,
                    '数据时效性'
                )
            ]
        }

    def evaluate_geodataframe(self,
                            gdf: gpd.GeoDataFrame,
                            dataset_name: str = "default") -> Dict:
        """评估GeoDataFrame的数据质量

        Args:
            gdf: 要评估的GeoDataFrame
            dataset_name: 数据集名称

        Returns:
            包含质量评估结果的字典
        """
        logger.info(f"开始评估数据集 '{dataset_name}' 的质量，包含 {len(gdf)} 条记录")

        # 执行各项验证
        geometry_report = self.geometry_validator.validate_geodataframe(gdf)
        attribute_report = self.attribute_validator.validate_geodataframe(gdf)
        coordinate_report = self.coordinate_validator.validate_geodataframe(gdf)

        # 计算各维度质量分数
        geometry_score = self._calculate_geometry_score(geometry_report)
        attribute_score = self._calculate_attribute_score(attribute_report)
        coordinate_score = self._calculate_coordinate_score(coordinate_report)
        overall_score = self._calculate_overall_score(gdf, geometry_report, attribute_report, coordinate_report)

        # 计算综合质量分数
        total_score = (
            geometry_score * self.weights['geometry'] +
            attribute_score * self.weights['attribute'] +
            coordinate_score * self.weights['coordinate'] +
            overall_score * self.weights['overall']
        )

        # 确定质量等级
        quality_grade = self._determine_grade(total_score)

        # 生成质量报告
        quality_report = self._generate_quality_report(
            dataset_name, gdf,
            geometry_score, attribute_score, coordinate_score, overall_score,
            total_score, quality_grade,
            geometry_report, attribute_report, coordinate_report
        )

        # 保存结果
        self.quality_scores[dataset_name] = total_score
        self.quality_reports[dataset_name] = quality_report

        return quality_report

    def _calculate_geometry_score(self, report: Dict) -> float:
        """计算几何质量分数"""
        metrics = self.metrics['geometry']

        # 有效性比例
        validity_ratio = report['summary']['validity_ratio']
        metrics[0].score = metrics[0].calculate_score(validity_ratio * 100)
        metrics[0].details = {'validity_ratio': validity_ratio}

        # 完整性比例
        total_geoms = report['summary']['total_geometries']
        empty_geoms = report['summary']['empty_geometries']
        completeness_ratio = (total_geoms - empty_geoms) / max(1, total_geoms)
        metrics[1].score = metrics[1].calculate_score(completeness_ratio * 100)
        metrics[1].details = {'completeness_ratio': completeness_ratio}

        # 错误率（反向指标）
        total_errors = report['summary']['total_errors']
        error_rate = 1 - (total_errors / max(1, total_geoms))
        metrics[2].score = metrics[2].calculate_score(error_rate * 100)
        metrics[2].details = {'error_rate': 1 - error_rate, 'total_errors': total_errors}

        # 计算加权平均分
        weighted_score = sum(metric.score * metric.weight for metric in metrics) / sum(m.weight for m in metrics)
        return round(weighted_score, 2)

    def _calculate_attribute_score(self, report: Dict) -> float:
        """计算属性质量分数"""
        metrics = self.metrics['attributes']

        # 字段完整性
        avg_completeness = report['summary']['average_completeness']
        metrics[0].score = metrics[0].calculate_score(avg_completeness)
        metrics[0].details = {'average_completeness': avg_completeness}

        # 数据一致性（基于错误类型分布）
        severity_dist = report['severity_distribution']
        high_severity_ratio = severity_dist['high'] / max(1, report['summary']['total_records'])
        consistency_score = max(0, 100 - high_severity_ratio * 100)
        metrics[1].score = metrics[1].calculate_score(consistency_score)
        metrics[1].details = {'high_severity_ratio': high_severity_ratio}

        # 错误率（反向指标）
        total_errors = report['summary']['total_errors']
        total_records = report['summary']['total_records']
        error_ratio = 1 - (total_errors / max(1, total_records))
        metrics[2].score = metrics[2].calculate_score(error_ratio * 100)
        metrics[2].details = {'error_ratio': 1 - error_ratio, 'total_errors': total_errors}

        # 计算加权平均分
        weighted_score = sum(metric.score * metric.weight for metric in metrics) / sum(m.weight for m in metrics)
        return round(weighted_score, 2)

    def _calculate_coordinate_score(self, report: Dict) -> float:
        """计算坐标系统质量分数"""
        metrics = self.metrics['coordinate']

        # 坐标系统有效性
        crs_valid = 100 if report['summary']['current_crs'] else 0
        metrics[0].score = metrics[0].calculate_score(crs_valid)
        metrics[0].details = {'crs_defined': report['summary']['current_crs'] is not None}

        # 坐标范围有效性
        bounds_valid = 100 if not any(e['error_type'] == 'out_of_bounds' for e in report['errors']) else 60
        metrics[1].score = metrics[1].calculate_score(bounds_valid)
        metrics[1].details = {'bounds_valid': bounds_valid == 100}

        # 坐标一致性
        transformation_possible = 100 if report['summary']['transformation_possible'] else 70
        metrics[2].score = metrics[2].calculate_score(transformation_possible)
        metrics[2].details = {'transformation_possible': report['summary']['transformation_possible']}

        # 计算加权平均分
        weighted_score = sum(metric.score * metric.weight for metric in metrics) / sum(m.weight for m in metrics)
        return round(weighted_score, 2)

    def _calculate_overall_score(self,
                               gdf: gpd.GeoDataFrame,
                               geometry_report: Dict,
                               attribute_report: Dict,
                               coordinate_report: Dict) -> float:
        """计算整体质量分数"""
        metrics = self.metrics['overall']

        # 记录数量充足性
        record_count = len(gdf)
        # 根据几何类型设定合理记录数量阈值
        expected_count = self._get_expected_record_count(gdf)
        record_ratio = min(100, (record_count / max(1, expected_count)) * 100)
        metrics[0].score = metrics[0].calculate_score(record_ratio)
        metrics[0].details = {'record_count': record_count, 'expected_count': expected_count}

        # 空间覆盖合理性
        bounds_validity = 100 if coordinate_report['summary']['total_errors'] == 0 else 70
        metrics[1].score = metrics[1].calculate_score(bounds_validity)
        metrics[1].details = {'bounds_valid': bounds_validity == 100}

        # 元数据完整性（基于字段数量）
        non_geom_fields = len([col for col in gdf.columns if col != 'geometry'])
        metadata_score = min(100, (non_geom_fields / 5) * 100)  # 假设5个基本字段为满分
        metrics[2].score = metrics[2].calculate_score(metadata_score)
        metrics[2].details = {'non_geom_fields': non_geom_fields}

        # 数据时效性（默认给良好分数）
        timeliness_score = 80  # 可以根据实际数据时间戳计算
        metrics[3].score = metrics[3].calculate_score(timeliness_score)
        metrics[3].details = {'timeliness_assumed': timeliness_score}

        # 计算加权平均分
        weighted_score = sum(metric.score * metric.weight for metric in metrics) / sum(m.weight for m in metrics)
        return round(weighted_score, 2)

    def _get_expected_record_count(self, gdf: gpd.GeoDataFrame) -> int:
        """根据几何类型获取期望的记录数量"""
        if gdf.empty:
            return 100

        geom_type = gdf.geometry.iloc[0].geom_type if not gdf.geometry.iloc[0].is_empty else 'Unknown'

        # 根据项目数据设定期望数量
        expected_counts = {
            'Point': 20000,        # 横断面点和纵断面点的总和
            'LineString': 600,     # 横断面线
            'Polygon': 80,         # 防治对象面
            'MultiPoint': 20000,
            'MultiLineString': 600,
            'MultiPolygon': 80
        }

        return expected_counts.get(geom_type, 1000)

    def _determine_grade(self, score: float) -> QualityGrade:
        """根据分数确定质量等级"""
        if score >= 90:
            return QualityGrade.A
        elif score >= 80:
            return QualityGrade.B
        elif score >= 70:
            return QualityGrade.C
        elif score >= 60:
            return QualityGrade.D
        else:
            return QualityGrade.F

    def _generate_quality_report(self,
                               dataset_name: str,
                               gdf: gpd.GeoDataFrame,
                               geometry_score: float,
                               attribute_score: float,
                               coordinate_score: float,
                               overall_score: float,
                               total_score: float,
                               quality_grade: QualityGrade,
                               geometry_report: Dict,
                               attribute_report: Dict,
                               coordinate_report: Dict) -> Dict:
        """生成质量报告"""
        report = {
            'dataset_info': {
                'name': dataset_name,
                'record_count': len(gdf),
                'geometry_types': list(gdf.geometry.geom_type.value_counts().to_dict().keys()),
                'field_count': len(gdf.columns) - 1,  # 减去几何列
                'crs': str(gdf.crs),
                'evaluation_date': datetime.now().isoformat()
            },
            'quality_summary': {
                'total_score': total_score,
                'quality_grade': quality_grade.value,
                'geometry_score': geometry_score,
                'attribute_score': attribute_score,
                'coordinate_score': coordinate_score,
                'overall_score': overall_score
            },
            'dimension_scores': {
                'completeness': self._calculate_dimension_score(QualityDimension.COMPLETENESS),
                'validity': self._calculate_dimension_score(QualityDimension.VALIDITY),
                'consistency': self._calculate_dimension_score(QualityDimension.CONSISTENCY),
                'accuracy': self._calculate_dimension_score(QualityDimension.ACCURACY),
                'precision': self._calculate_dimension_score(QualityDimension.PRECISION),
                'timeliness': self._calculate_dimension_score(QualityDimension.TIMELINESS)
            },
            'detailed_metrics': self._get_detailed_metrics(),
            'improvement_recommendations': self._generate_improvement_recommendations(
                geometry_score, attribute_score, coordinate_score, overall_score,
                geometry_report, attribute_report, coordinate_report
            ),
            'quality_trend': {
                'target_score': 90,
                'current_gap': max(0, 90 - total_score),
                'improvement_priority': self._determine_improvement_priority(
                    geometry_score, attribute_score, coordinate_score
                )
            }
        }

        return report

    def _calculate_dimension_score(self, dimension: QualityDimension) -> float:
        """计算质量维度分数"""
        dimension_metrics = []
        for category_metrics in self.metrics.values():
            for metric in category_metrics:
                if metric.dimension == dimension:
                    dimension_metrics.append(metric.score)

        if not dimension_metrics:
            return 0.0

        return round(sum(dimension_metrics) / len(dimension_metrics), 2)

    def _get_detailed_metrics(self) -> Dict:
        """获取详细指标信息"""
        detailed = {}
        for category, metrics in self.metrics.items():
            detailed[category] = []
            for metric in metrics:
                detailed[category].append({
                    'name': metric.name,
                    'dimension': metric.dimension.value,
                    'weight': metric.weight,
                    'score': metric.score,
                    'description': metric.description,
                    'details': metric.details
                })
        return detailed

    def _generate_improvement_recommendations(self,
                                            geometry_score: float,
                                            attribute_score: float,
                                            coordinate_score: float,
                                            overall_score: float,
                                            geometry_report: Dict,
                                            attribute_report: Dict,
                                            coordinate_report: Dict) -> List[Dict]:
        """生成改进建议"""
        recommendations = []

        # 几何质量改进建议
        if geometry_score < 80:
            recommendations.append({
                'category': 'geometry',
                'priority': 'high' if geometry_score < 60 else 'medium',
                'description': f'几何质量分数较低 ({geometry_score})，建议进行几何修复',
                'actions': self._get_geometry_improvement_actions(geometry_report)
            })

        # 属性质量改进建议
        if attribute_score < 80:
            recommendations.append({
                'category': 'attributes',
                'priority': 'high' if attribute_score < 60 else 'medium',
                'description': f'属性质量分数较低 ({attribute_score})，建议进行数据清洗',
                'actions': self._get_attribute_improvement_actions(attribute_report)
            })

        # 坐标系统改进建议
        if coordinate_score < 80:
            recommendations.append({
                'category': 'coordinate',
                'priority': 'high' if coordinate_score < 60 else 'medium',
                'description': f'坐标系统质量分数较低 ({coordinate_score})，建议进行坐标系统修复',
                'actions': self._get_coordinate_improvement_actions(coordinate_report)
            })

        # 整体质量改进建议
        if overall_score < 80:
            recommendations.append({
                'category': 'overall',
                'priority': 'medium',
                'description': f'整体质量需要提升 ({overall_score})',
                'actions': [
                    '增加数据量以达到期望规模',
                    '完善元数据信息',
                    '建立数据质量监控机制'
                ]
            })

        return recommendations

    def _get_geometry_improvement_actions(self, report: Dict) -> List[str]:
        """获取几何改进措施"""
        actions = []

        error_types = report.get('error_types', {})
        if error_types.get('invalid_geometry', 0) > 0:
            actions.append('使用 make_valid() 函数修复无效几何')
        if error_types.get('empty_geometry', 0) > 0:
            actions.append('检查并处理空几何对象')
        if error_types.get('self_intersection', 0) > 0:
            actions.append('修复自相交几何对象')
        if error_types.get('precision_issue', 0) > 0:
            actions.append('调整几何精度和容差设置')

        if not actions:
            actions.append('几何质量良好，继续维护')

        return actions

    def _get_attribute_improvement_actions(self, report: Dict) -> List[str]:
        """获取属性改进措施"""
        actions = []

        missing_values = report.get('missing_values', {})
        high_missing_fields = [field for field, count in missing_values.items()
                             if count > 0]
        if high_missing_fields:
            actions.append(f'处理缺失值字段: {", ".join(high_missing_fields)}')

        error_types = report.get('error_types', {})
        if error_types.get('invalid_type', 0) > 0:
            actions.append('统一字段数据类型')
        if error_types.get('duplicate_value', 0) > 0:
            actions.append('处理重复值问题')

        field_completeness = report.get('field_completeness', {})
        low_completeness_fields = [field for field, completeness in field_completeness.items()
                                  if completeness < 90]
        if low_completeness_fields:
            actions.append(f'提升字段完整性: {", ".join(low_completeness_fields)}')

        if not actions:
            actions.append('属性质量良好，继续维护')

        return actions

    def _get_coordinate_improvement_actions(self, report: Dict) -> List[str]:
        """获取坐标系统改进措施"""
        actions = []

        if not report['summary']['current_crs']:
            actions.append('定义坐标参考系统')
        elif report['summary']['total_errors'] > 0:
            actions.append('修复坐标系统相关错误')

        if not report['summary']['transformation_possible']:
            actions.append('选择兼容的目标坐标系统')

        if any(e['error_type'] == 'out_of_bounds' for e in report['errors']):
            actions.append('检查坐标范围是否合理')

        if not actions:
            actions.append('坐标系统质量良好，继续维护')

        return actions

    def _determine_improvement_priority(self,
                                      geometry_score: float,
                                      attribute_score: float,
                                      coordinate_score: float) -> str:
        """确定改进优先级"""
        scores = {
            'geometry': geometry_score,
            'attributes': attribute_score,
            'coordinate': coordinate_score
        }

        # 找出最低分的维度
        lowest_category = min(scores, key=scores.get)
        lowest_score = scores[lowest_category]

        if lowest_score < 60:
            return f'{lowest_category} (急需改进)'
        elif lowest_score < 80:
            return f'{lowest_category} (建议改进)'
        else:
            return '整体质量良好'

    def batch_evaluate(self, datasets: Dict[str, gpd.GeoDataFrame]) -> Dict:
        """批量评估多个数据集

        Args:
            datasets: 数据集字典 {name: GeoDataFrame}

        Returns:
            批量评估报告
        """
        logger.info(f"开始批量评估 {len(datasets)} 个数据集")

        batch_report = {
            'summary': {
                'total_datasets': len(datasets),
                'evaluation_date': datetime.now().isoformat(),
                'average_score': 0,
                'grade_distribution': {grade.value: 0 for grade in QualityGrade}
            },
            'dataset_reports': {},
            'cross_dataset_analysis': {}
        }

        total_score = 0

        for name, gdf in datasets.items():
            report = self.evaluate_geodataframe(gdf, name)
            batch_report['dataset_reports'][name] = report
            total_score += report['quality_summary']['total_score']

            # 统计等级分布
            grade = report['quality_summary']['quality_grade']
            batch_report['summary']['grade_distribution'][grade] += 1

        # 计算平均分
        batch_report['summary']['average_score'] = round(total_score / len(datasets), 2)

        # 跨数据集分析
        batch_report['cross_dataset_analysis'] = self._cross_dataset_analysis(datasets)

        return batch_report

    def _cross_dataset_analysis(self, datasets: Dict[str, gpd.GeoDataFrame]) -> Dict:
        """跨数据集分析"""
        analysis = {
            'total_records': sum(len(gdf) for gdf in datasets.values()),
            'geometry_type_distribution': {},
            'crs_distribution': {},
            'field_overlap': set(),
            'quality_comparison': {}
        }

        # 统计几何类型分布
        all_geom_types = []
        for gdf in datasets.values():
            if not gdf.empty:
                geom_types = list(gdf.geometry.geom_type.value_counts().to_dict().keys())
                all_geom_types.extend(geom_types)

        from collections import Counter
        geom_counter = Counter(all_geom_types)
        analysis['geometry_type_distribution'] = dict(geom_counter)

        # 统计坐标系统分布
        crs_list = []
        for gdf in datasets.values():
            if gdf.crs:
                crs_list.append(str(gdf.crs))
        crs_counter = Counter(crs_list)
        analysis['crs_distribution'] = dict(crs_counter)

        # 分析字段重叠
        if datasets:
            common_fields = set(datasets.values().__iter__().__next__().columns)
            for gdf in list(datasets.values())[1:]:
                common_fields &= set(gdf.columns)
            analysis['field_overlap'] = list(common_fields - {'geometry'})

        # 质量对比
        for name, report in self.quality_reports.items():
            analysis['quality_comparison'][name] = report['quality_summary']['total_score']

        return analysis

    def export_quality_report(self,
                            dataset_name: str,
                            output_path: str,
                            format: str = 'json'):
        """导出质量报告

        Args:
            dataset_name: 数据集名称
            output_path: 输出路径
            format: 输出格式 ('json' 或 'csv')
        """
        if dataset_name not in self.quality_reports:
            raise ValueError(f"未找到数据集 '{dataset_name}' 的质量报告")

        report = self.quality_reports[dataset_name]

        if format.lower() == 'json':
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        elif format.lower() == 'csv':
            # 简化的CSV格式，主要导出摘要信息
            summary_data = {
                'dataset': dataset_name,
                'total_score': report['quality_summary']['total_score'],
                'quality_grade': report['quality_summary']['quality_grade'],
                'geometry_score': report['quality_summary']['geometry_score'],
                'attribute_score': report['quality_summary']['attribute_score'],
                'coordinate_score': report['quality_summary']['coordinate_score'],
                'record_count': report['dataset_info']['record_count']
            }

            df = pd.DataFrame([summary_data])
            df.to_csv(output_path, index=False, encoding='utf-8')
        else:
            raise ValueError(f"不支持的输出格式: {format}")

        logger.info(f"质量报告已导出到: {output_path}")