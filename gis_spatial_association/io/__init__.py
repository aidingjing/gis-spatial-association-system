"""
GIS空间关联系统 - 输入输出模块

该模块提供完整的数据导出、报告生成、可视化和结果评估功能。
支持多种GIS格式的数据导出、生成专业的分析报告、
创建丰富的可视化内容，并对处理结果进行质量评估。

主要功能:
- 多格式数据导出 (Shapefile、GeoJSON、CSV、KML、Excel)
- 统计报告生成 (HTML、PDF、Markdown、Excel)
- 数据可视化 (地图、图表、网络图、仪表板)
- 结果质量评估和验证

作者: GIS空间关联系统开发团队
版本: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "GIS空间关联系统开发团队"

# 导入主要类和函数
from .exporters.result_exporter import ResultExporter
from .exporters.shapefile import ShapefileExporter
from .exporters.geojson import GeoJSONExporter
from .exporters.csv import CSVExporter
from .exporters.excel import ExcelExporter
from .exporters.kml import KMLExporter

from .reports.generator import ReportGenerator
from .reports.templates import ReportTemplateManager
from .reports.quality import QualityReportGenerator

from .visualizer.data_visualizer import DataVisualizer
from .visualizer.maps import MapVisualizer
from .visualizer.charts import ChartVisualizer
from .visualizer.network import NetworkVisualizer
from .visualizer.dashboard import DashboardGenerator

from .assessment.validator import ResultValidator
from .assessment.scorer import QualityScorer
from .assessment.analyzer import ResultAnalyzer

__all__ = [
    # 导出器
    'ResultExporter',
    'ShapefileExporter',
    'GeoJSONExporter',
    'CSVExporter',
    'ExcelExporter',
    'KMLExporter',

    # 报告生成器
    'ReportGenerator',
    'ReportTemplateManager',
    'QualityReportGenerator',

    # 可视化器
    'DataVisualizer',
    'MapVisualizer',
    'ChartVisualizer',
    'NetworkVisualizer',
    'DashboardGenerator',

    # 评估器
    'ResultValidator',
    'QualityScorer',
    'ResultAnalyzer'
]

# 模块级别的便捷函数
def export_analysis_results(results, export_config):
    """
    导出分析结果的便捷函数

    Args:
        results: 分析结果字典
        export_config: 导出配置字典

    Returns:
        list: 导出的文件路径列表
    """
    exporter = ResultExporter()
    return exporter.export_results(results, export_config)

def generate_analysis_report(results, output_dir, report_format='html'):
    """
    生成分析报告的便捷函数

    Args:
        results: 分析结果字典
        output_dir: 输出目录
        report_format: 报告格式 ('html', 'pdf', 'markdown', 'excel')

    Returns:
        str: 报告文件路径
    """
    generator = ReportGenerator()
    return generator.generate_report(results, output_dir, report_format)

def create_visualization_dashboard(results, output_dir):
    """
    创建可视化仪表板的便捷函数

    Args:
        results: 分析结果字典
        output_dir: 输出目录

    Returns:
        str: 仪表板文件路径
    """
    visualizer = DataVisualizer()
    return visualizer.create_visualization_dashboard(results, output_dir)

def assess_result_quality(results):
    """
    评估结果质量的便捷函数

    Args:
        results: 分析结果字典

    Returns:
        dict: 质量评估结果
    """
    validator = ResultValidator()
    scorer = QualityScorer()
    analyzer = ResultAnalyzer()

    validation_results = validator.validate_results(results)
    quality_scores = scorer.calculate_quality_scores(validation_results)
    analysis_summary = analyzer.analyze_results(results, validation_results, quality_scores)

    return {
        'validation': validation_results,
        'scores': quality_scores,
        'analysis': analysis_summary
    }