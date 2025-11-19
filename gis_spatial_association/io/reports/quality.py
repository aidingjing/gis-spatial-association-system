"""
数据质量评估和报告生成模块

提供全面的数据质量评估功能，包含几何验证、属性检查、
完整性分析等，并生成专业的质量评估报告。

特点:
- 几何数据质量评估
- 属性数据完整性检查
- 坐标系统验证
- 数据一致性分析
- 质量评分体系
- 改进建议生成

作者: GIS空间关联系统开发团队
"""

import logging
from typing import Dict, Any, List, Optional, Union, Tuple
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon
from shapely.validation import make_valid

logger = logging.getLogger(__name__)


class DataQualityAssessor:
    """
    数据质量评估器

    对GIS数据进行全面的质量评估，包括几何、属性、完整性等方面。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化数据质量评估器

        Args:
            config: 评估配置
        """
        self.config = config or {}

        # 默认配置
        self.default_config = {
            'geometry_validation': True,
            'attribute_completeness': True,
            'coordinate_system_validation': True,
            'duplicate_detection': True,
            'outlier_detection': True,
            'quality_weights': {
                'completeness': 0.3,
                'validity': 0.3,
                'consistency': 0.2,
                'accuracy': 0.2
            },
            'severity_levels': {
                'critical': 0,
                'high': 25,
                'medium': 50,
                'low': 75
            }
        }

        # 合并配置
        self.config = {**self.default_config, **self.config}

    def assess_quality(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估整体数据质量

        Args:
            results: 分析结果数据

        Returns:
            Dict[str, Any]: 质量评估结果
        """
        try:
            logger.info("开始数据质量评估...")

            assessment_result = {
                'overall_score': 0,
                'quality_level': 'unknown',
                'dataset_assessments': {},
                'issues': [],
                'recommendations': [],
                'quality_metrics': {},
                'summary': {}
            }

            # 评估每个数据集
            for dataset_name, dataset_data in results.items():
                if isinstance(dataset_data, (gpd.GeoDataFrame, pd.DataFrame)):
                    dataset_assessment = self._assess_dataset_quality(dataset_name, dataset_data)
                    assessment_result['dataset_assessments'][dataset_name] = dataset_assessment

                    # 收集所有问题
                    assessment_result['issues'].extend(dataset_assessment.get('issues', []))

            # 计算整体评分
            assessment_result['overall_score'] = self._calculate_overall_score(
                assessment_result['dataset_assessments']
            )

            # 确定质量等级
            assessment_result['quality_level'] = self._determine_quality_level(assessment_result['overall_score'])

            # 生成质量指标
            assessment_result['quality_metrics'] = self._generate_quality_metrics(assessment_result)

            # 生成建议
            assessment_result['recommendations'] = self._generate_quality_recommendations(assessment_result)

            # 生成摘要
            assessment_result['summary'] = self._generate_quality_summary(assessment_result)

            logger.info(f"质量评估完成，总体评分: {assessment_result['overall_score']:.1f}")
            return assessment_result

        except Exception as e:
            logger.error(f"数据质量评估失败: {str(e)}")
            return {
                'overall_score': 0,
                'quality_level': 'failed',
                'dataset_assessments': {},
                'issues': [{'type': 'error', 'description': str(e)}],
                'recommendations': [],
                'quality_metrics': {},
                'summary': {'status': 'failed', 'error': str(e)}
            }

    def _assess_dataset_quality(self, name: str, data: Union[gpd.GeoDataFrame, pd.DataFrame]) -> Dict[str, Any]:
        """
        评估单个数据集的质量

        Args:
            name: 数据集名称
            data: 数据集数据

        Returns:
            Dict[str, Any]: 数据集质量评估结果
        """
        assessment = {
            'dataset_name': name,
            'overall_score': 0,
            'completeness_score': 0,
            'validity_score': 0,
            'consistency_score': 0,
            'accuracy_score': 0,
            'issues': [],
            'metrics': {}
        }

        try:
            # 完整性评估
            completeness_result = self._assess_completeness(data)
            assessment['completeness_score'] = completeness_result['score']
            assessment['issues'].extend(completeness_result['issues'])
            assessment['metrics']['completeness'] = completeness_result['metrics']

            # 有效性评估（几何数据）
            if isinstance(data, gpd.GeoDataFrame):
                validity_result = self._assess_geometry_validity(data)
                assessment['validity_score'] = validity_result['score']
                assessment['issues'].extend(validity_result['issues'])
                assessment['metrics']['validity'] = validity_result['metrics']

                # 坐标系统评估
                crs_result = self._assess_coordinate_system(data)
                assessment['issues'].extend(crs_result['issues'])
                assessment['metrics']['coordinate_system'] = crs_result['metrics']

            # 一致性评估
            consistency_result = self._assess_consistency(data)
            assessment['consistency_score'] = consistency_result['score']
            assessment['issues'].extend(consistency_result['issues'])
            assessment['metrics']['consistency'] = consistency_result['metrics']

            # 准确性评估
            accuracy_result = self._assess_accuracy(data)
            assessment['accuracy_score'] = accuracy_result['score']
            assessment['issues'].extend(accuracy_result['issues'])
            assessment['metrics']['accuracy'] = accuracy_result['metrics']

            # 计算总体评分
            weights = self.config['quality_weights']
            assessment['overall_score'] = (
                assessment['completeness_score'] * weights['completeness'] +
                assessment['validity_score'] * weights['validity'] +
                assessment['consistency_score'] * weights['consistency'] +
                assessment['accuracy_score'] * weights['accuracy']
            )

        except Exception as e:
            logger.error(f"评估数据集 {name} 质量失败: {str(e)}")
            assessment['issues'].append({
                'type': 'error',
                'severity': 'critical',
                'description': f"质量评估过程中发生错误: {str(e)}"
            })

        return assessment

    def _assess_completeness(self, data: Union[gpd.GeoDataFrame, pd.DataFrame]) -> Dict[str, Any]:
        """
        评估数据完整性

        Args:
            data: 数据集

        Returns:
            Dict[str, Any]: 完整性评估结果
        """
        result = {
            'score': 0,
            'issues': [],
            'metrics': {}
        }

        try:
            total_cells = len(data) * len(data.columns)
            missing_cells = data.isnull().sum().sum()
            complete_cells = total_cells - missing_cells

            # 计算完整性评分
            if total_cells > 0:
                completeness_ratio = complete_cells / total_cells
                result['score'] = completeness_ratio * 100
            else:
                completeness_ratio = 0
                result['score'] = 0

            # 收集完整性指标
            result['metrics'] = {
                'total_records': len(data),
                'total_columns': len(data.columns),
                'total_cells': total_cells,
                'missing_cells': missing_cells,
                'complete_cells': complete_cells,
                'completeness_ratio': completeness_ratio,
                'missing_by_column': data.isnull().sum().to_dict()
            }

            # 检查完整性问题
            missing_ratio_by_column = (data.isnull().sum() / len(data)).to_dict()

            for col, missing_ratio in missing_ratio_by_column.items():
                if missing_ratio > 0.5:  # 超过50%缺失
                    result['issues'].append({
                        'type': 'high_missing_rate',
                        'severity': 'high',
                        'column': col,
                        'missing_ratio': missing_ratio,
                        'description': f"字段 {col} 缺失率过高: {missing_ratio:.1%}"
                    })
                elif missing_ratio > 0.1:  # 超过10%缺失
                    result['issues'].append({
                        'type': 'moderate_missing_rate',
                        'severity': 'medium',
                        'column': col,
                        'missing_ratio': missing_ratio,
                        'description': f"字段 {col} 存在缺失值: {missing_ratio:.1%}"
                    })

            # 检查空数据集
            if len(data) == 0:
                result['issues'].append({
                    'type': 'empty_dataset',
                    'severity': 'critical',
                    'description': '数据集为空'
                })

        except Exception as e:
            logger.error(f"完整性评估失败: {str(e)}")
            result['issues'].append({
                'type': 'assessment_error',
                'severity': 'critical',
                'description': f"完整性评估失败: {str(e)}"
            })

        return result

    def _assess_geometry_validity(self, gdf: gpd.GeoDataFrame) -> Dict[str, Any]:
        """
        评估几何数据有效性

        Args:
            gdf: GeoDataFrame

        Returns:
            Dict[str, Any]: 几何有效性评估结果
        """
        result = {
            'score': 0,
            'issues': [],
            'metrics': {}
        }

        try:
            # 检查几何有效性
            valid_geometries = gdf.geometry.is_valid.sum()
            total_geometries = len(gdf)
            invalid_geometries = total_geometries - valid_geometries

            # 检查空几何
            null_geometries = gdf.geometry.isnull().sum()

            # 检查几何类型一致性
            geom_types = gdf.geometry.geom_type.value_counts()

            # 计算几何有效性评分
            if total_geometries > 0:
                validity_ratio = valid_geometries / total_geometries
                result['score'] = validity_ratio * 100
            else:
                validity_ratio = 0
                result['score'] = 0

            # 收集几何指标
            result['metrics'] = {
                'total_geometries': total_geometries,
                'valid_geometries': valid_geometries,
                'invalid_geometries': invalid_geometries,
                'null_geometries': null_geometries,
                'validity_ratio': validity_ratio,
                'geometry_types': geom_types.to_dict(),
                'geometry_type_diversity': len(geom_types)
            }

            # 检查几何问题
            if invalid_geometries > 0:
                invalid_ratio = invalid_geometries / total_geometries
                severity = 'critical' if invalid_ratio > 0.5 else 'high' if invalid_ratio > 0.1 else 'medium'

                result['issues'].append({
                    'type': 'invalid_geometry',
                    'severity': severity,
                    'count': invalid_geometries,
                    'ratio': invalid_ratio,
                    'description': f"发现 {invalid_geometries} 个无效几何 ({invalid_ratio:.1%})"
                })

            if null_geometries > 0:
                null_ratio = null_geometries / total_geometries
                severity = 'critical' if null_ratio > 0.5 else 'high' if null_ratio > 0.1 else 'medium'

                result['issues'].append({
                    'type': 'null_geometry',
                    'severity': severity,
                    'count': null_geometries,
                    'ratio': null_ratio,
                    'description': f"发现 {null_geometries} 个空几何 ({null_ratio:.1%})"
                })

            # 检查几何类型混乱
            if len(geom_types) > 3:
                result['issues'].append({
                    'type': 'geometry_type_diversity',
                    'severity': 'medium',
                    'diversity': len(geom_types),
                    'description': f"几何类型过多 ({len(geom_types)} 种)，可能影响分析一致性"
                })

        except Exception as e:
            logger.error(f"几何有效性评估失败: {str(e)}")
            result['issues'].append({
                'type': 'assessment_error',
                'severity': 'critical',
                'description': f"几何有效性评估失败: {str(e)}"
            })

        return result

    def _assess_coordinate_system(self, gdf: gpd.GeoDataFrame) -> Dict[str, Any]:
        """
        评估坐标系统

        Args:
            gdf: GeoDataFrame

        Returns:
            Dict[str, Any]: 坐标系统评估结果
        """
        result = {
            'score': 100,  # 默认满分
            'issues': [],
            'metrics': {}
        }

        try:
            # 检查坐标系统
            crs = gdf.crs

            if crs is None:
                result['score'] = 0
                result['issues'].append({
                    'type': 'missing_crs',
                    'severity': 'critical',
                    'description': '数据缺少坐标参考系统'
                })
                result['metrics'] = {
                    'has_crs': False,
                    'crs_info': None,
                    'is_geographic': False,
                    'is_projected': False
                }
            else:
                # 分析坐标系统
                is_geographic = crs.is_geographic
                is_projected = not is_geographic

                result['metrics'] = {
                    'has_crs': True,
                    'crs_info': str(crs),
                    'is_geographic': is_geographic,
                    'is_projected': is_projected,
                    'epsg_code': crs.to_epsg() if hasattr(crs, 'to_epsg') else None
                }

                # 检查坐标范围合理性（对于地理坐标系）
                if is_geographic:
                    bounds = gdf.total_bounds
                    if len(bounds) == 4:
                        min_x, min_y, max_x, max_y = bounds

                        # 检查坐标范围是否在合理范围内
                        if not (-180 <= min_x <= 180 and -180 <= max_x <= 180):
                            result['score'] = 50
                            result['issues'].append({
                                'type': 'invalid_longitude_range',
                                'severity': 'high',
                                'range': (min_x, max_x),
                                'description': f"经度范围异常: [{min_x:.3f}, {max_x:.3f}]"
                            })

                        if not (-90 <= min_y <= 90 and -90 <= max_y <= 90):
                            result['score'] = 50
                            result['issues'].append({
                                'type': 'invalid_latitude_range',
                                'severity': 'high',
                                'range': (min_y, max_y),
                                'description': f"纬度范围异常: [{min_y:.3f}, {max_y:.3f}]"
                            })

        except Exception as e:
            logger.error(f"坐标系统评估失败: {str(e)}")
            result['score'] = 0
            result['issues'].append({
                'type': 'assessment_error',
                'severity': 'critical',
                'description': f"坐标系统评估失败: {str(e)}"
            })

        return result

    def _assess_consistency(self, data: Union[gpd.GeoDataFrame, pd.DataFrame]) -> Dict[str, Any]:
        """
        评估数据一致性

        Args:
            data: 数据集

        Returns:
            Dict[str, Any]: 一致性评估结果
        """
        result = {
            'score': 100,  # 默认满分
            'issues': [],
            'metrics': {}
        }

        try:
            consistency_issues = []

            # 检查重复记录
            duplicate_rows = data.duplicated().sum()
            if duplicate_rows > 0:
                duplicate_ratio = duplicate_rows / len(data)
                consistency_issues.append({
                    'type': 'duplicate_records',
                    'severity': 'medium',
                    'count': duplicate_rows,
                    'ratio': duplicate_ratio,
                    'description': f"发现 {duplicate_rows} 条重复记录 ({duplicate_ratio:.1%})"
                })

            # 检查数据类型不一致
            for col in data.columns:
                if col != 'geometry' and data[col].dtype == 'object':
                    # 检查字符串和数值混合
                    numeric_values = pd.to_numeric(data[col], errors='coerce')
                    if not numeric_values.isna().all() and not numeric_values.isna().sum() == len(data):
                        # 有部分可以转换为数值，部分不能，说明类型不一致
                        mixed_type_count = data[col].apply(lambda x: isinstance(x, str)).sum()
                        if mixed_type_count > 0 and mixed_type_count < len(data):
                            consistency_issues.append({
                                'type': 'inconsistent_data_type',
                                'severity': 'low',
                                'column': col,
                                'description': f"字段 {col} 包含混合数据类型"
                            })

            # 检查几何一致性（如果是GeoDataFrame）
            if isinstance(data, gpd.GeoDataFrame):
                # 检查几何精度一致性
                if len(data) > 1:
                    # 计算几何精度（基于坐标小数位数）
                    precision_scores = []
                    for geom in data.geometry:
                        if geom is not None and not geom.is_empty:
                            precision = self._calculate_geometry_precision(geom)
                            precision_scores.append(precision)

                    if precision_scores:
                        precision_variance = pd.Series(precision_scores).var()
                        if precision_variance > 1:  # 精度差异过大
                            consistency_issues.append({
                                'type': 'inconsistent_geometry_precision',
                                'severity': 'low',
                                'variance': precision_variance,
                                'description': f"几何精度不一致，方差: {precision_variance:.2f}"
                            })

            # 计算一致性评分
            total_issues = len(consistency_issues)
            if total_issues == 0:
                result['score'] = 100
            elif total_issues <= 2:
                result['score'] = 85
            elif total_issues <= 5:
                result['score'] = 70
            else:
                result['score'] = 50

            result['issues'] = consistency_issues
            result['metrics'] = {
                'duplicate_records': duplicate_rows,
                'consistency_issues_count': total_issues,
                'issue_types': list(set(issue['type'] for issue in consistency_issues))
            }

        except Exception as e:
            logger.error(f"一致性评估失败: {str(e)}")
            result['score'] = 0
            result['issues'].append({
                'type': 'assessment_error',
                'severity': 'critical',
                'description': f"一致性评估失败: {str(e)}"
            })

        return result

    def _assess_accuracy(self, data: Union[gpd.GeoDataFrame, pd.DataFrame]) -> Dict[str, Any]:
        """
        评估数据准确性

        Args:
            data: 数据集

        Returns:
            Dict[str, Any]: 准确性评估结果
        """
        result = {
            'score': 100,  # 默认满分
            'issues': [],
            'metrics': {}
        }

        try:
            accuracy_issues = []

            # 检查数值异常值
            numeric_columns = data.select_dtypes(include=['number']).columns
            for col in numeric_columns:
                if col in data.columns:
                    # 使用IQR方法检测异常值
                    Q1 = data[col].quantile(0.25)
                    Q3 = data[col].quantile(0.75)
                    IQR = Q3 - Q1
                    lower_bound = Q1 - 1.5 * IQR
                    upper_bound = Q3 + 1.5 * IQR

                    outliers = data[(data[col] < lower_bound) | (data[col] > upper_bound)]
                    outlier_count = len(outliers)

                    if outlier_count > 0:
                        outlier_ratio = outlier_count / len(data)
                        if outlier_ratio > 0.1:  # 超过10%的异常值
                            accuracy_issues.append({
                                'type': 'high_outlier_ratio',
                                'severity': 'medium',
                                'column': col,
                                'count': outlier_count,
                                'ratio': outlier_ratio,
                                'description': f"字段 {col} 包含较多异常值: {outlier_count} 个 ({outlier_ratio:.1%})"
                            })

            # 检查地理准确性（如果是GeoDataFrame）
            if isinstance(data, gpd.GeoDataFrame):
                # 检查坐标精度
                bounds = data.total_bounds
                if len(bounds) == 4:
                    min_x, min_y, max_x, max_y = bounds

                    # 检查坐标范围是否过小（可能精度问题）
                    if (max_x - min_x) < 0.001 or (max_y - min_y) < 0.001:
                        accuracy_issues.append({
                            'type': 'suspected_coordinate_precision',
                            'severity': 'low',
                            'bounds': bounds.tolist(),
                            'description': "坐标范围过小，可能存在精度问题"
                        })

            # 检查文本字段的异常值
            text_columns = data.select_dtypes(include=['object']).columns
            for col in text_columns:
                if col != 'geometry':
                    # 检查异常长的字符串
                    str_lengths = data[col].astype(str).str.len()
                    max_length = str_lengths.max()
                    mean_length = str_lengths.mean()

                    if max_length > mean_length * 10:  # 最大长度是平均长度的10倍以上
                        accuracy_issues.append({
                            'type': 'suspicious_text_length',
                            'severity': 'low',
                            'column': col,
                            'max_length': max_length,
                            'mean_length': mean_length,
                            'description': f"字段 {col} 存在异常长的文本"
                        })

            # 计算准确性评分
            total_issues = len(accuracy_issues)
            if total_issues == 0:
                result['score'] = 100
            elif total_issues <= 3:
                result['score'] = 90
            elif total_issues <= 6:
                result['score'] = 75
            else:
                result['score'] = 60

            result['issues'] = accuracy_issues
            result['metrics'] = {
                'accuracy_issues_count': total_issues,
                'numeric_columns_analyzed': len(numeric_columns),
                'text_columns_analyzed': len([col for col in text_columns if col != 'geometry']),
                'issue_types': list(set(issue['type'] for issue in accuracy_issues))
            }

        except Exception as e:
            logger.error(f"准确性评估失败: {str(e)}")
            result['score'] = 0
            result['issues'].append({
                'type': 'assessment_error',
                'severity': 'critical',
                'description': f"准确性评估失败: {str(e)}"
            })

        return result

    def _calculate_geometry_precision(self, geom) -> float:
        """
        计算几何精度

        Args:
            geom: 几何对象

        Returns:
            float: 精度值
        """
        try:
            if geom.geom_type == 'Point':
                # 计算坐标的小数位数
                x, y = geom.x, geom.y
                precision_x = len(str(x).split('.')[-1]) if '.' in str(x) else 0
                precision_y = len(str(y).split('.')[-1]) if '.' in str(y) else 0
                return min(precision_x, precision_y)
            else:
                # 对于其他几何类型，计算坐标的平均小数位数
                coords = list(geom.coords)
                precisions = []
                for x, y in coords:
                    precision_x = len(str(x).split('.')[-1]) if '.' in str(x) else 0
                    precision_y = len(str(y).split('.')[-1]) if '.' in str(y) else 0
                    precisions.append(min(precision_x, precision_y))
                return sum(precisions) / len(precisions) if precisions else 0
        except Exception:
            return 0

    def _calculate_overall_score(self, dataset_assessments: Dict[str, Any]) -> float:
        """
        计算整体质量评分

        Args:
            dataset_assessments: 数据集评估结果

        Returns:
            float: 整体评分
        """
        if not dataset_assessments:
            return 0

        total_score = 0
        total_weight = 0

        for dataset_name, assessment in dataset_assessments.items():
            score = assessment.get('overall_score', 0)
            # 使用记录数作为权重
            weight = 1  # 简化起见，使用相同权重
            total_score += score * weight
            total_weight += weight

        return total_score / total_weight if total_weight > 0 else 0

    def _determine_quality_level(self, score: float) -> str:
        """
        确定质量等级

        Args:
            score: 质量评分

        Returns:
            str: 质量等级
        """
        if score >= 90:
            return '优秀'
        elif score >= 80:
            return '良好'
        elif score >= 70:
            return '中等'
        elif score >= 60:
            return '及格'
        else:
            return '需要改进'

    def _generate_quality_metrics(self, assessment_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成质量指标

        Args:
            assessment_result: 评估结果

        Returns:
            Dict[str, Any]: 质量指标
        """
        metrics = {
            'overall_score': assessment_result['overall_score'],
            'quality_level': assessment_result['quality_level'],
            'total_issues': len(assessment_result['issues']),
            'critical_issues': len([i for i in assessment_result['issues'] if i.get('severity') == 'critical']),
            'high_issues': len([i for i in assessment_result['issues'] if i.get('severity') == 'high']),
            'medium_issues': len([i for i in assessment_result['issues'] if i.get('severity') == 'medium']),
            'low_issues': len([i for i in assessment_result['issues'] if i.get('severity') == 'low']),
            'issue_types': list(set(issue.get('type', 'unknown') for issue in assessment_result['issues'])),
            'datasets_assessed': len(assessment_result['dataset_assessments'])
        }

        # 计算各维度平均分
        if assessment_result['dataset_assessments']:
            completeness_scores = [d.get('completeness_score', 0) for d in assessment_result['dataset_assessments'].values()]
            validity_scores = [d.get('validity_score', 0) for d in assessment_result['dataset_assessments'].values()]
            consistency_scores = [d.get('consistency_score', 0) for d in assessment_result['dataset_assessments'].values()]
            accuracy_scores = [d.get('accuracy_score', 0) for d in assessment_result['dataset_assessments'].values()]

            metrics.update({
                'avg_completeness_score': sum(completeness_scores) / len(completeness_scores),
                'avg_validity_score': sum(validity_scores) / len(validity_scores),
                'avg_consistency_score': sum(consistency_scores) / len(consistency_scores),
                'avg_accuracy_score': sum(accuracy_scores) / len(accuracy_scores)
            })

        return metrics

    def _generate_quality_recommendations(self, assessment_result: Dict[str, Any]) -> List[str]:
        """
        生成质量改进建议

        Args:
            assessment_result: 评估结果

        Returns:
            List[str]: 建议列表
        """
        recommendations = []

        # 基于问题类型的建议
        issue_types = [issue.get('type', 'unknown') for issue in assessment_result['issues']]
        issue_type_counts = pd.Series(issue_types).value_counts().to_dict()

        if 'high_missing_rate' in issue_type_counts:
            recommendations.append("建议检查并补充缺失数据过多的字段，或考虑删除相关字段")

        if 'invalid_geometry' in issue_type_counts:
            recommendations.append("建议修复无效的几何数据，可使用缓冲区方法或重新数字化")

        if 'missing_crs' in issue_type_counts:
            recommendations.append("建议为数据定义合适的坐标参考系统")

        if 'duplicate_records' in issue_type_counts:
            recommendations.append("建议清理重复的数据记录")

        if 'high_outlier_ratio' in issue_type_counts:
            recommendations.append("建议检查并处理数值异常值，确认其合理性")

        if 'inconsistent_data_type' in issue_type_counts:
            recommendations.append("建议统一字段的数据类型，确保数据一致性")

        # 基于总体评分的建议
        overall_score = assessment_result['overall_score']
        if overall_score < 60:
            recommendations.append("数据质量较差，建议进行全面的数据清洗和质量改进")
        elif overall_score < 80:
            recommendations.append("数据质量中等，建议针对性解决主要质量问题")
        elif overall_score < 90:
            recommendations.append("数据质量良好，建议进一步优化细节问题")

        # 如果没有问题
        if not assessment_result['issues']:
            recommendations.append("数据质量优秀，可以用于后续分析")

        return recommendations

    def _generate_quality_summary(self, assessment_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成质量评估摘要

        Args:
            assessment_result: 评估结果

        Returns:
            Dict[str, Any]: 摘要信息
        """
        return {
            'total_datasets': len(assessment_result['dataset_assessments']),
            'overall_quality_level': assessment_result['quality_level'],
            'overall_score': assessment_result['overall_score'],
            'total_issues_found': len(assessment_result['issues']),
            'critical_problems_count': len([i for i in assessment_result['issues'] if i.get('severity') == 'critical']),
            'needs_immediate_attention': len([i for i in assessment_result['issues'] if i.get('severity') in ['critical', 'high']]) > 0,
            'assessment_status': 'completed' if assessment_result['overall_score'] > 0 else 'failed'
        }


class QualityReportGenerator:
    """
    质量报告生成器

    生成专业的数据质量评估报告。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化质量报告生成器

        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.data_assessor = DataQualityAssessor(config)

    def assess_quality(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估数据质量

        Args:
            results: 分析结果

        Returns:
            Dict[str, Any]: 质量评估结果
        """
        return self.data_assessor.assess_quality(results)