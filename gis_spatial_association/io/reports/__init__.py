"""
统计报告生成模块

提供多种格式的分析报告生成功能，包含HTML、PDF、Markdown、Excel等格式。
支持模板定制、图表集成、数据质量评估等功能。

支持的报告格式:
- HTML - 交互式网页报告
- PDF - 专业PDF报告
- Markdown - 文档格式报告
- Excel - 数据分析报告

主要功能:
- 报告模板管理
- 数据统计分析
- 图表生成集成
- 质量评估报告
- 自定义样式支持

作者: GIS空间关联系统开发团队
"""

__version__ = "1.0.0"

from .generator import ReportGenerator
from .templates import ReportTemplateManager, HTMLTemplateEngine, PDFTemplateEngine
from .quality import QualityReportGenerator, DataQualityAssessor

__all__ = [
    'ReportGenerator',
    'ReportTemplateManager',
    'HTMLTemplateEngine',
    'PDFTemplateEngine',
    'QualityReportGenerator',
    'DataQualityAssessor'
]