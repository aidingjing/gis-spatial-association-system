"""
报告生成器

提供统一的分析报告生成接口，支持多种格式和模板。
集成数据处理、统计分析、图表生成等功能。

特点:
- 多格式报告支持 (HTML, PDF, Markdown, Excel)
- 模板系统支持
- 自动数据统计分析
- 图表和可视化集成
- 自定义样式配置
- 增量报告生成

作者: GIS空间关联系统开发团队
"""

import os
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import pandas as pd
import geopandas as gpd
from datetime import datetime

from .templates import ReportTemplateManager, HTMLTemplateEngine
from .quality import QualityReportGenerator, DataQualityAssessor

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    报告生成器

    生成完整的GIS空间关联分析报告，支持多种格式和自定义模板。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化报告生成器

        Args:
            config: 报告配置
        """
        self.config = config or {}

        # 默认配置
        self.default_config = {
            'output_formats': ['html'],
            'template_engine': 'default',
            'include_charts': True,
            'include_quality_assessment': True,
            'include_processing_log': True,
            'language': 'zh-CN',
            'date_format': '%Y-%m-%d %H:%M:%S',
            'decimal_places': 2,
            'chart_style': 'seaborn',
            'color_scheme': 'default',
            'company_logo': None,
            'report_title': 'GIS空间关联分析报告',
            'author': 'GIS空间关联系统',
            'version': '1.0.0',
            'output_directory': './reports'
        }

        # 合并配置
        self.config = {**self.default_config, **self.config}

        # 初始化组件
        self.template_manager = ReportTemplateManager(self.config)
        self.quality_generator = QualityReportGenerator(self.config)
        self.data_assessor = DataQualityAssessor(self.config)

        # 支持的输出格式
        self.supported_formats = ['html', 'pdf', 'markdown', 'excel']

    def generate_report(self,
                       results: Dict[str, Any],
                       output_dir: str,
                       report_formats: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        生成分析报告

        Args:
            results: 分析结果数据
            output_dir: 输出目录
            report_formats: 报告格式列表

        Returns:
            Dict[str, Any]: 生成结果
        """
        try:
            logger.info("开始生成分析报告...")

            # 确定输出格式
            formats = report_formats or self.config['output_formats']
            valid_formats = [fmt for fmt in formats if fmt in self.supported_formats]

            if not valid_formats:
                raise ValueError(f"没有有效的报告格式。支持格式: {self.supported_formats}")

            # 创建输出目录
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            # 收集报告数据
            report_data = self._collect_report_data(results)

            # 初始化生成结果
            generation_results = {
                'success': True,
                'generated_files': [],
                'failed_formats': [],
                'report_data': report_data,
                'generation_time': None,
                'errors': [],
                'warnings': []
            }

            start_time = time.time()

            # 生成不同格式的报告
            for format_type in valid_formats:
                try:
                    file_path = self._generate_format_report(
                        format_type, report_data, output_path
                    )
                    if file_path:
                        generation_results['generated_files'].append(file_path)
                        logger.info(f"✅ {format_type.upper()} 报告生成成功: {file_path}")
                    else:
                        generation_results['failed_formats'].append(format_type)

                except Exception as e:
                    error_msg = f"{format_type.upper()} 报告生成失败: {str(e)}"
                    logger.error(error_msg)
                    generation_results['failed_formats'].append(format_type)
                    generation_results['errors'].append(error_msg)

            # 计算生成时间
            generation_results['generation_time'] = time.time() - start_time

            logger.info(f"报告生成完成，耗时: {generation_results['generation_time']:.2f}秒")
            return generation_results

        except Exception as e:
            logger.error(f"❌ 报告生成失败: {str(e)}")
            return {
                'success': False,
                'generated_files': [],
                'failed_formats': formats or [],
                'report_data': None,
                'generation_time': None,
                'errors': [str(e)],
                'warnings': []
            }

    def _collect_report_data(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        收集报告数据

        Args:
            results: 分析结果

        Returns:
            Dict[str, Any]: 报告数据
        """
        report_data = {
            'metadata': self._generate_metadata(),
            'datasets': {},
            'statistics': {},
            'associations': {},
            'quality_assessment': {},
            'processing_log': [],
            'charts': {},
            'summary': {}
        }

        # 收集数据集信息
        for dataset_name, dataset_data in results.items():
            if isinstance(dataset_data, (gpd.GeoDataFrame, pd.DataFrame)):
                report_data['datasets'][dataset_name] = self._analyze_dataset(dataset_name, dataset_data)

        # 收集关联分析结果
        if 'associations' in results:
            report_data['associations'] = self._analyze_associations(results['associations'])

        # 生成统计信息
        report_data['statistics'] = self._generate_statistics(results)

        # 质量评估
        if self.config['include_quality_assessment']:
            report_data['quality_assessment'] = self.quality_generator.assess_quality(results)

        # 生成汇总信息
        report_data['summary'] = self._generate_summary(report_data)

        return report_data

    def _generate_metadata(self) -> Dict[str, Any]:
        """
        生成报告元数据

        Returns:
            Dict[str, Any]: 元数据
        """
        return {
            'title': self.config['report_title'],
            'author': self.config['author'],
            'version': self.config['version'],
            'generation_time': datetime.now().strftime(self.config['date_format']),
            'language': self.config['language'],
            'description': 'GIS空间关联分析系统自动生成的分析报告'
        }

    def _analyze_dataset(self, name: str, data: Union[gpd.GeoDataFrame, pd.DataFrame]) -> Dict[str, Any]:
        """
        分析单个数据集

        Args:
            name: 数据集名称
            data: 数据集数据

        Returns:
            Dict[str, Any]: 分析结果
        """
        analysis = {
            'name': name,
            'type': 'geodataframe' if isinstance(data, gpd.GeoDataFrame) else 'dataframe',
            'record_count': len(data),
            'column_count': len(data.columns),
            'columns': list(data.columns),
            'memory_usage': data.memory_usage(deep=True).sum(),
            'numeric_columns': [],
            'categorical_columns': [],
            'date_columns': [],
            'null_values': {},
            'data_types': {}
        }

        if isinstance(data, gpd.GeoDataFrame):
            # 几何信息
            analysis.update({
                'geometry_type': data.geometry.geom_type.iloc[0] if len(data) > 0 else None,
                'geometry_types': data.geometry.geom_type.value_counts().to_dict() if len(data) > 0 else {},
                'coordinate_system': str(data.crs) if data.crs else None,
                'bounds': data.total_bounds.tolist() if len(data) > 0 else None,
                'area_stats': self._calculate_area_statistics(data) if hasattr(data.geometry, 'area') else {},
                'length_stats': self._calculate_length_statistics(data) if hasattr(data.geometry, 'length') else {}
            })

        # 分析列类型
        for col in data.columns:
            if col == 'geometry':
                continue

            analysis['data_types'][col] = str(data[col].dtype)

            if pd.api.types.is_numeric_dtype(data[col]):
                analysis['numeric_columns'].append(col)
                # 计算统计信息
                analysis[f'{col}_stats'] = data[col].describe().to_dict()
            elif pd.api.types.is_categorical_dtype(data[col]):
                analysis['categorical_columns'].append(col)
                # 分类统计
                analysis[f'{col}_value_counts'] = data[col].value_counts().to_dict()
            elif pd.api.types.is_datetime64_any_dtype(data[col]):
                analysis['date_columns'].append(col)
                # 日期范围
                analysis[f'{col}_date_range'] = {
                    'min': data[col].min().strftime(self.config['date_format']) if pd.notna(data[col].min()) else None,
                    'max': data[col].max().strftime(self.config['date_format']) if pd.notna(data[col].max()) else None
                }

            # 空值统计
            null_count = data[col].isna().sum()
            if null_count > 0:
                analysis['null_values'][col] = {
                    'count': null_count,
                    'percentage': (null_count / len(data)) * 100
                }

        return analysis

    def _calculate_area_statistics(self, gdf: gpd.GeoDataFrame) -> Dict[str, Any]:
        """
        计算面积统计

        Args:
            gdf: GeoDataFrame

        Returns:
            Dict[str, Any]: 面积统计
        """
        try:
            areas = gdf.geometry.area
            return {
                'total': areas.sum(),
                'mean': areas.mean(),
                'median': areas.median(),
                'min': areas.min(),
                'max': areas.max(),
                'std': areas.std()
            }
        except Exception:
            return {}

    def _calculate_length_statistics(self, gdf: gpd.GeoDataFrame) -> Dict[str, Any]:
        """
        计算长度统计

        Args:
            gdf: GeoDataFrame

        Returns:
            Dict[str, Any]: 长度统计
        """
        try:
            lengths = gdf.geometry.length
            return {
                'total': lengths.sum(),
                'mean': lengths.mean(),
                'median': lengths.median(),
                'min': lengths.min(),
                'max': lengths.max(),
                'std': lengths.std()
            }
        except Exception:
            return {}

    def _analyze_associations(self, associations: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析关联关系

        Args:
            associations: 关联数据

        Returns:
            Dict[str, Any]: 关联分析结果
        """
        analysis = {
            'total_associations': len(associations) if isinstance(associations, list) else 0,
            'association_types': {},
            'quality_scores': [],
            'spatial_relationships': {},
            'summary_statistics': {}
        }

        if isinstance(associations, list) and associations:
            # 分析关联类型
            association_types = [assoc.get('type', 'unknown') for assoc in associations]
            type_counts = pd.Series(association_types).value_counts().to_dict()
            analysis['association_types'] = type_counts

            # 质量评分
            quality_scores = [assoc.get('quality_score', 0) for assoc in associations if 'quality_score' in assoc]
            if quality_scores:
                analysis['quality_scores'] = {
                    'mean': sum(quality_scores) / len(quality_scores),
                    'min': min(quality_scores),
                    'max': max(quality_scores),
                    'count': len(quality_scores)
                }

            # 空间关系统计
            spatial_rels = [assoc.get('spatial_relation', 'unknown') for assoc in associations if 'spatial_relation' in assoc]
            if spatial_rels:
                rel_counts = pd.Series(spatial_rels).value_counts().to_dict()
                analysis['spatial_relationships'] = rel_counts

        return analysis

    def _generate_statistics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成统计信息

        Args:
            results: 分析结果

        Returns:
            Dict[str, Any]: 统计信息
        """
        stats = {
            'total_datasets': 0,
            'total_records': 0,
            'total_geometries': 0,
            'data_volume': 0,
            'processing_time': 0,
            'memory_usage': 0
        }

        # 统计数据集信息
        for dataset_name, dataset_data in results.items():
            if isinstance(dataset_data, (gpd.GeoDataFrame, pd.DataFrame)):
                stats['total_datasets'] += 1
                stats['total_records'] += len(dataset_data)

                if isinstance(dataset_data, gpd.GeoDataFrame):
                    stats['total_geometries'] += len(dataset_data)

                # 计算数据内存使用
                stats['memory_usage'] += dataset_data.memory_usage(deep=True).sum()

        # 数据体积估算（字节）
        stats['data_volume'] = stats['memory_usage']

        return stats

    def _generate_summary(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成报告摘要

        Args:
            report_data: 报告数据

        Returns:
            Dict[str, Any]: 摘要信息
        """
        summary = {
            'key_findings': [],
            'data_overview': {},
            'quality_overview': {},
            'recommendations': []
        }

        # 数据概览
        datasets = report_data.get('datasets', {})
        summary['data_overview'] = {
            'total_datasets': len(datasets),
            'total_records': sum(d['record_count'] for d in datasets.values()),
            'geometry_types': list(set(d.get('geometry_type') for d in datasets.values() if d.get('geometry_type')))
        }

        # 质量概览
        quality = report_data.get('quality_assessment', {})
        if quality:
            overall_score = quality.get('overall_score', 0)
            summary['quality_overview'] = {
                'overall_score': overall_score,
                'quality_level': self._get_quality_level(overall_score),
                'issues_found': len(quality.get('issues', []))
            }

        # 生成关键发现
        summary['key_findings'] = self._generate_key_findings(report_data)

        # 生成建议
        summary['recommendations'] = self._generate_recommendations(report_data)

        return summary

    def _get_quality_level(self, score: float) -> str:
        """
        根据评分获取质量等级

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

    def _generate_key_findings(self, report_data: Dict[str, Any]) -> List[str]:
        """
        生成关键发现

        Args:
            report_data: 报告数据

        Returns:
            List[str]: 关键发现列表
        """
        findings = []

        datasets = report_data.get('datasets', {})
        stats = report_data.get('statistics', {})

        # 数据集规模发现
        if stats['total_records'] > 100000:
            findings.append(f"处理了大规模数据集，包含 {stats['total_records']:,} 条记录")
        elif stats['total_records'] > 10000:
            findings.append(f"处理了中等规模数据集，包含 {stats['total_records']:,} 条记录")

        # 几何类型发现
        geometry_types = set()
        for dataset_info in datasets.values():
            geom_type = dataset_info.get('geometry_type')
            if geom_type:
                geometry_types.add(geom_type)

        if len(geometry_types) > 1:
            findings.append(f"分析包含多种几何类型: {', '.join(geometry_types)}")

        # 关联分析发现
        associations = report_data.get('associations', {})
        if associations.get('total_associations', 0) > 0:
            findings.append(f"发现了 {associations['total_associations']} 个空间关联关系")

        # 质量发现
        quality = report_data.get('quality_assessment', {})
        overall_score = quality.get('overall_score', 0)
        if overall_score >= 90:
            findings.append("数据质量优秀，无需额外处理")
        elif overall_score < 70:
            findings.append("数据质量需要改进，建议进行数据清洗")

        return findings

    def _generate_recommendations(self, report_data: Dict[str, Any]) -> List[str]:
        """
        生成改进建议

        Args:
            report_data: 报告数据

        Returns:
            List[str]: 建议列表
        """
        recommendations = []

        # 基于数据质量生成建议
        quality = report_data.get('quality_assessment', {})
        issues = quality.get('issues', [])

        for issue in issues:
            if 'missing' in issue.lower():
                recommendations.append("建议检查并补充缺失的数据")
            elif 'invalid' in issue.lower():
                recommendations.append("建议修复无效的几何数据")
            elif 'duplicate' in issue.lower():
                recommendations.append("建议清理重复的数据记录")

        # 基于数据量生成建议
        stats = report_data.get('statistics', {})
        if stats['memory_usage'] > 1024 * 1024 * 100:  # 100MB
            recommendations.append("数据量较大，建议使用空间索引优化查询性能")

        return recommendations

    def _generate_format_report(self, format_type: str, report_data: Dict[str, Any], output_path: Path) -> Optional[str]:
        """
        生成特定格式的报告

        Args:
            format_type: 报告格式
            report_data: 报告数据
            output_path: 输出路径

        Returns:
            Optional[str]: 生成的文件路径
        """
        try:
            if format_type == 'html':
                return self.template_manager.generate_html_report(report_data, output_path)
            elif format_type == 'pdf':
                return self.template_manager.generate_pdf_report(report_data, output_path)
            elif format_type == 'markdown':
                return self.template_manager.generate_markdown_report(report_data, output_path)
            elif format_type == 'excel':
                return self.template_manager.generate_excel_report(report_data, output_path)
            else:
                raise ValueError(f"不支持的报告格式: {format_type}")

        except Exception as e:
            logger.error(f"生成 {format_type} 报告失败: {str(e)}")
            return None

    def get_supported_formats(self) -> List[str]:
        """获取支持的报告格式"""
        return self.supported_formats.copy()

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """
        更新配置

        Args:
            new_config: 新配置
        """
        self.config.update(new_config)
        self.template_manager.update_config(new_config)

    def add_template(self, template_type: str, template_path: str) -> None:
        """
        添加自定义模板

        Args:
            template_type: 模板类型
            template_path: 模板路径
        """
        self.template_manager.add_custom_template(template_type, template_path)