"""
结果质量评估和验证模块

提供全面的结果数据质量评估功能，包含结果验证、质量评分、
异常分析等。

主要功能:
- 结果准确性验证
- 空间关联质量评分
- 异常检测和分析
- 结果对比验证
- 质量改进建议

作者: GIS空间关联系统开发团队
"""

__version__ = "1.0.0"

from .validator import ResultValidator
from .scorer import QualityScorer
from .analyzer import ResultAnalyzer

__all__ = [
    'ResultValidator',
    'QualityScorer',
    'ResultAnalyzer'
]