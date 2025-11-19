"""
结果验证器

提供对分析结果的全面验证功能，确保结果的正确性和可靠性。

特点:
- 结果数据完整性验证
- 逻辑一致性检查
- 空间关系验证
- 属性数据验证
- 性能指标验证

作者: GIS空间关联系统开发团队
"""

import logging
from typing import Dict, Any, List, Optional, Union, Tuple
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon

logger = logging.getLogger(__name__)


class ResultValidator:
    """
    结果验证器

    对GIS空间关联分析的结果进行全面验证。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化结果验证器

        Args:
            config: 验证配置
        """
        self.config = config or {}

        # 默认配置
        self.default_config = {
            'validate_geometry': True,
            'validate_attributes': True,
            'validate_spatial_relations': True,
            'validate_associations': True,
            'validate_performance': True,
            'strict_mode': False,
            'tolerance': 1e-6
        }

        # 合并配置
        self.config = {**self.default_config, **self.config}

    def validate_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证分析结果

        Args:
            results: 分析结果数据

        Returns:
            Dict[str, Any]: 验证结果
        """
        try:
            logger.info("开始结果验证...")

            validation_result = {
                'overall_valid': True,
                'validation_score': 100,
                'validations': {},
                'errors': [],
                'warnings': [],
                'summary': {}
            }

            # 验证各种结果组件
            for component_name, component_data in results.items():
                if isinstance(component_data, (gpd.GeoDataFrame, pd.DataFrame)):
                    # 验证数据集
                    dataset_validation = self._validate_dataset(component_name, component_data)
                    validation_result['validations'][component_name] = dataset_validation

                    # 收集错误和警告
                    validation_result['errors'].extend(dataset_validation.get('errors', []))
                    validation_result['warnings'].extend(dataset_validation.get('warnings', []))

                elif component_name == 'associations' and isinstance(component_data, list):
                    # 验证关联关系
                    association_validation = self._validate_associations(component_data)
                    validation_result['validations']['associations'] = association_validation

                    validation_result['errors'].extend(association_validation.get('errors', []))
                    validation_result['warnings'].extend(association_validation.get('warnings', []))

                elif component_name == 'performance_metrics' and isinstance(component_data, dict):
                    # 验证性能指标
                    performance_validation = self._validate_performance_metrics(component_data)
                    validation_result['validations']['performance'] = performance_validation

            # 计算总体验证分数
            validation_result['validation_score'] = self._calculate_validation_score(
                validation_result['validations']
            )

            # 确定总体有效性
            validation_result['overall_valid'] = (
                validation_result['validation_score'] >= 70 and
                len(validation_result['errors']) == 0
            )

            # 生成验证摘要
            validation_result['summary'] = self._generate_validation_summary(validation_result)

            logger.info(f"结果验证完成，验证分数: {validation_result['validation_score']:.1f}")
            return validation_result

        except Exception as e:
            logger.error(f"结果验证失败: {str(e)}")
            return {
                'overall_valid': False,
                'validation_score': 0,
                'validations': {},
                'errors': [{'type': 'validation_error', 'description': str(e)}],
                'warnings': [],
                'summary': {'status': 'failed', 'error': str(e)}
            }

    def _validate_dataset(self, name: str, data: Union[gpd.GeoDataFrame, pd.DataFrame]) -> Dict[str, Any]:
        """
        验证单个数据集

        Args:
            name: 数据集名称
            data: 数据集数据

        Returns:
            Dict[str, Any]: 验证结果
        """
        validation = {
            'valid': True,
            'score': 100,
            'errors': [],
            'warnings': [],
            'checks': {}
        }

        try:
            # 基础检查
            basic_checks = self._perform_basic_checks(data)
            validation['checks']['basic'] = basic_checks
            validation['warnings'].extend(basic_checks.get('warnings', []))

            if basic_checks.get('critical_issues'):
                validation['valid'] = False
                validation['errors'].extend(basic_checks['critical_issues'])

            # 几何验证（如果是GeoDataFrame）
            if isinstance(data, gpd.GeoDataFrame) and self.config['validate_geometry']:
                geometry_checks = self._validate_geometry(data)
                validation['checks']['geometry'] = geometry_checks
                validation['warnings'].extend(geometry_checks.get('warnings', []))

                if geometry_checks.get('critical_issues'):
                    validation['valid'] = False
                    validation['errors'].extend(geometry_checks['critical_issues'])

            # 属性验证
            if self.config['validate_attributes']:
                attribute_checks = self._validate_attributes(data)
                validation['checks']['attributes'] = attribute_checks
                validation['warnings'].extend(attribute_checks.get('warnings', []))

                if attribute_checks.get('critical_issues'):
                    validation['valid'] = False
                    validation['errors'].extend(attribute_checks['critical_issues'])

            # 计算验证分数
            validation['score'] = self._calculate_dataset_score(validation['checks'])

        except Exception as e:
            validation['valid'] = False
            validation['errors'].append({
                'type': 'dataset_validation_error',
                'dataset': name,
                'description': str(e)
            })

        return validation

    def _perform_basic_checks(self, data: Union[gpd.GeoDataFrame, pd.DataFrame]) -> Dict[str, Any]:
        """
        执行基础检查

        Args:
            data: 数据集

        Returns:
            Dict[str, Any]: 检查结果
        """
        checks = {
            'warnings': [],
            'critical_issues': []
        }

        # 检查是否为空
        if data.empty:
            checks['critical_issues'].append({
                'type': 'empty_dataset',
                'description': '数据集为空'
            })
            return checks

        # 检查列数
        if len(data.columns) == 0:
            checks['critical_issues'].append({
                'type': 'no_columns',
                'description': '数据集没有列'
            })

        # 检查重复行
        duplicate_rows = data.duplicated().sum()
        if duplicate_rows > 0:
            checks['warnings'].append({
                'type': 'duplicate_rows',
                'count': duplicate_rows,
                'description': f'发现 {duplicate_rows} 行重复数据'
            })

        # 检查数据类型一致性
        for col in data.columns:
            if col != 'geometry':
                # 检查混合数据类型
                unique_types = set(type(val).__name__ for val in data[col].dropna())
                if len(unique_types) > 2:  # 允许两种类型（如int和float）
                    checks['warnings'].append({
                        'type': 'mixed_data_types',
                        'column': col,
                        'types': list(unique_types),
                        'description': f'列 {col} 包含混合数据类型'
                    })

        return checks

    def _validate_geometry(self, gdf: gpd.GeoDataFrame) -> Dict[str, Any]:
        """
        验证几何数据

        Args:
            gdf: GeoDataFrame

        Returns:
            Dict[str, Any]: 验证结果
        """
        checks = {
            'warnings': [],
            'critical_issues': []
        }

        try:
            # 检查几何列
            if 'geometry' not in gdf.columns:
                checks['critical_issues'].append({
                    'type': 'missing_geometry_column',
                    'description': '缺少几何列'
                })
                return checks

            # 检查空几何
            null_geometries = gdf.geometry.isnull().sum()
            if null_geometries > 0:
                checks['warnings'].append({
                    'type': 'null_geometries',
                    'count': null_geometries,
                    'description': f'发现 {null_geometries} 个空几何'
                })

            # 检查无效几何
            invalid_geometries = not gdf.geometry.is_valid.sum()
            if invalid_geometries > 0:
                severity = 'critical' if invalid_geometries > len(gdf) * 0.5 else 'warning'
                issue = {
                    'type': 'invalid_geometries',
                    'count': invalid_geometries,
                    'description': f'发现 {invalid_geometries} 个无效几何'
                }

                if severity == 'critical':
                    checks['critical_issues'].append(issue)
                else:
                    checks['warnings'].append(issue)

            # 检查坐标系统
            if gdf.crs is None:
                checks['warnings'].append({
                    'type': 'missing_crs',
                    'description': '数据缺少坐标参考系统'
                })

            # 检查几何类型一致性
            geom_types = gdf.geometry.geom_type.value_counts()
            if len(geom_types) > 3:
                checks['warnings'].append({
                    'type': 'geometry_type_diversity',
                    'diversity': len(geom_types),
                    'description': f'几何类型过多 ({len(geom_types)} 种)'
                })

        except Exception as e:
            checks['critical_issues'].append({
                'type': 'geometry_validation_error',
                'description': f'几何验证过程中发生错误: {str(e)}'
            })

        return checks

    def _validate_attributes(self, data: Union[gpd.GeoDataFrame, pd.DataFrame]) -> Dict[str, Any]:
        """
        验证属性数据

        Args:
            data: 数据集

        Returns:
            Dict[str, Any]: 验证结果
        """
        checks = {
            'warnings': [],
            'critical_issues': []
        }

        try:
            # 检查缺失值
            missing_data = data.isnull().sum()
            for col, missing_count in missing_data.items():
                if col != 'geometry' and missing_count > 0:
                    missing_ratio = missing_count / len(data)
                    if missing_ratio > 0.5:
                        checks['critical_issues'].append({
                            'type': 'high_missing_rate',
                            'column': col,
                            'ratio': missing_ratio,
                            'description': f'列 {col} 缺失率过高: {missing_ratio:.1%}'
                        })
                    elif missing_ratio > 0.1:
                        checks['warnings'].append({
                            'type': 'moderate_missing_rate',
                            'column': col,
                            'ratio': missing_ratio,
                            'description': f'列 {col} 存在缺失值: {missing_ratio:.1%}'
                        })

            # 检查数值范围
            numeric_columns = data.select_dtypes(include=['number']).columns
            for col in numeric_columns:
                if col in data.columns:
                    # 检查异常值
                    Q1 = data[col].quantile(0.25)
                    Q3 = data[col].quantile(0.75)
                    IQR = Q3 - Q1
                    lower_bound = Q1 - 1.5 * IQR
                    upper_bound = Q3 + 1.5 * IQR

                    outliers = data[(data[col] < lower_bound) | (data[col] > upper_bound)]
                    outlier_ratio = len(outliers) / len(data)

                    if outlier_ratio > 0.1:
                        checks['warnings'].append({
                            'type': 'high_outlier_ratio',
                            'column': col,
                            'ratio': outlier_ratio,
                            'count': len(outliers),
                            'description': f'列 {col} 包含较多异常值: {len(outliers)} 个 ({outlier_ratio:.1%})'
                        })

        except Exception as e:
            checks['critical_issues'].append({
                'type': 'attribute_validation_error',
                'description': f'属性验证过程中发生错误: {str(e)}'
            })

        return checks

    def _validate_associations(self, associations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        验证关联关系

        Args:
            associations: 关联关系列表

        Returns:
            Dict[str, Any]: 验证结果
        """
        validation = {
            'valid': True,
            'score': 100,
            'errors': [],
            'warnings': [],
            'checks': {}
        }

        try:
            if not associations:
                validation['warnings'].append({
                    'type': 'no_associations',
                    'description': '没有找到关联关系'
                })
                return validation

            # 基础检查
            required_fields = ['source', 'target']
            for i, assoc in enumerate(associations):
                missing_fields = [field for field in required_fields if field not in assoc]
                if missing_fields:
                    validation['errors'].append({
                        'type': 'missing_required_fields',
                        'index': i,
                        'missing_fields': missing_fields,
                        'description': f'关联关系 {i} 缺少必要字段: {missing_fields}'
                    })

            # 检查关联质量
            if 'quality_score' in associations[0]:
                quality_scores = [assoc.get('quality_score', 0) for assoc in associations]
                avg_quality = sum(quality_scores) / len(quality_scores)

                if avg_quality < 0.5:
                    validation['warnings'].append({
                        'type': 'low_association_quality',
                        'average_score': avg_quality,
                        'description': f'关联关系质量较低，平均分: {avg_quality:.2f}'
                    })

            # 检查重复关联
            association_pairs = set()
            duplicates = []
            for i, assoc in enumerate(associations):
                pair = tuple(sorted([assoc.get('source'), assoc.get('target')]))
                if pair in association_pairs:
                    duplicates.append(i)
                else:
                    association_pairs.add(pair)

            if duplicates:
                validation['warnings'].append({
                    'type': 'duplicate_associations',
                    'indices': duplicates,
                    'description': f'发现 {len(duplicates)} 个重复的关联关系'
                })

            validation['checks']['basic'] = {'association_count': len(associations)}
            validation['score'] = 100 - (len(validation['warnings']) * 5) - (len(validation['errors']) * 20)

        except Exception as e:
            validation['valid'] = False
            validation['errors'].append({
                'type': 'association_validation_error',
                'description': f'关联验证过程中发生错误: {str(e)}'
            })

        return validation

    def _validate_performance_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证性能指标

        Args:
            metrics: 性能指标

        Returns:
            Dict[str, Any]: 验证结果
        """
        validation = {
            'valid': True,
            'warnings': [],
            'checks': {}
        }

        try:
            # 检查必要的性能指标
            required_metrics = ['processing_time', 'memory_usage']
            missing_metrics = [metric for metric in required_metrics if metric not in metrics]

            if missing_metrics:
                validation['warnings'].append({
                    'type': 'missing_performance_metrics',
                    'missing_metrics': missing_metrics,
                    'description': f'缺少性能指标: {missing_metrics}'
                })

            # 检查性能指标合理性
            if 'processing_time' in metrics:
                processing_time = metrics['processing_time']
                if processing_time > 3600:  # 超过1小时
                    validation['warnings'].append({
                        'type': 'long_processing_time',
                        'time': processing_time,
                        'description': f'处理时间较长: {processing_time:.1f} 秒'
                    })

            if 'memory_usage' in metrics:
                memory_usage = metrics['memory_usage']
                if memory_usage > 1024**3:  # 超过1GB
                    validation['warnings'].append({
                        'type': 'high_memory_usage',
                        'usage': memory_usage,
                        'description': f'内存使用量较高: {memory_usage / 1024**2:.1f} MB'
                    })

            validation['checks']['performance'] = metrics

        except Exception as e:
            validation['warnings'].append({
                'type': 'performance_validation_error',
                'description': f'性能指标验证过程中发生错误: {str(e)}'
            })

        return validation

    def _calculate_dataset_score(self, checks: Dict[str, Any]) -> float:
        """
        计算数据集验证分数

        Args:
            checks: 检查结果

        Returns:
            float: 验证分数
        """
        score = 100.0

        # 根据问题严重程度扣分
        for check_type, check_result in checks.items():
            if isinstance(check_result, dict):
                errors = check_result.get('errors', [])
                warnings = check_result.get('warnings', [])

                score -= len(errors) * 20  # 严重错误扣20分
                score -= len(warnings) * 5  # 警告扣5分

        return max(0, score)

    def _calculate_validation_score(self, validations: Dict[str, Any]) -> float:
        """
        计算总体验证分数

        Args:
            validations: 验证结果

        Returns:
            float: 总体验证分数
        """
        if not validations:
            return 100.0

        scores = []
        for component, validation in validations.items():
            if isinstance(validation, dict) and 'score' in validation:
                scores.append(validation['score'])

        if not scores:
            return 100.0

        return sum(scores) / len(scores)

    def _generate_validation_summary(self, validation_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成验证摘要

        Args:
            validation_result: 验证结果

        Returns:
            Dict[str, Any]: 摘要信息
        """
        return {
            'total_components': len(validation_result['validations']),
            'overall_valid': validation_result['overall_valid'],
            'validation_score': validation_result['validation_score'],
            'total_errors': len(validation_result['errors']),
            'total_warnings': len(validation_result['warnings']),
            'validation_level': self._get_validation_level(validation_result['validation_score']),
            'recommended_actions': self._generate_recommendations(validation_result)
        }

    def _get_validation_level(self, score: float) -> str:
        """
        获取验证等级

        Args:
            score: 验证分数

        Returns:
            str: 验证等级
        """
        if score >= 95:
            return '优秀'
        elif score >= 85:
            return '良好'
        elif score >= 70:
            return '合格'
        elif score >= 50:
            return '需要改进'
        else:
            return '不合格'

    def _generate_recommendations(self, validation_result: Dict[str, Any]) -> List[str]:
        """
        生成改进建议

        Args:
            validation_result: 验证结果

        Returns:
            List[str]: 建议列表
        """
        recommendations = []

        # 基于错误生成建议
        error_types = [error.get('type', 'unknown') for error in validation_result['errors']]
        warning_types = [warning.get('type', 'unknown') for warning in validation_result['warnings']]

        if 'invalid_geometries' in error_types:
            recommendations.append("修复无效的几何数据，使用缓冲区方法或重新数字化")

        if 'high_missing_rate' in error_types:
            recommendations.append("处理缺失值过多的字段，考虑删除或补充数据")

        if 'duplicate_rows' in warning_types:
            recommendations.append("清理重复的数据记录")

        if 'missing_crs' in warning_types:
            recommendations.append("为数据定义合适的坐标参考系统")

        if validation_result['validation_score'] < 70:
            recommendations.append("整体验证分数较低，建议进行全面的数据质量改进")

        if not validation_result['overall_valid']:
            recommendations.append("存在严重问题，需要在继续分析前解决")

        if not recommendations:
            recommendations.append("验证通过，数据质量良好")

        return recommendations