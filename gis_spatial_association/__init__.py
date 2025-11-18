"""
GIS空间关联分析系统

提供高效的地理空间要素关联分析功能，包括：
- 点-线最近邻关联分析
- 线-线相交检测分析
- 线-面包含判断分析
- 坐标系转换处理
- 全面的数据质量验证和修复

技术栈：Python + GeoPandas + Shapely + Rtree + PyProj
"""

__version__ = "1.0.0"
__author__ = "CCPM Auto Development System"

# 可选依赖导入，优雅地处理缺失依赖
try:
    from .algorithms.association import NearestNeighborAssociator
    _HAS_ASSOCIATION = True
except ImportError as e:
    NearestNeighborAssociator = None
    _HAS_ASSOCIATION = False
    import logging
    logging.warning(f"关联分析模块不可用: {e}")

try:
    from .algorithms.intersection import LineIntersectionDetector
    _HAS_INTERSECTION = True
except ImportError as e:
    LineIntersectionDetector = None
    _HAS_INTERSECTION = False
    logging.warning(f"相交检测模块不可用: {e}")

try:
    from .algorithms.containment import PolygonContainmentAnalyzer
    _HAS_CONTAINMENT = True
except ImportError as e:
    PolygonContainmentAnalyzer = None
    _HAS_CONTAINMENT = False
    logging.warning(f"包含分析模块不可用: {e}")

try:
    from .algorithms.transformation import CoordinateTransformer
    _HAS_TRANSFORMATION = True
except ImportError as e:
    CoordinateTransformer = None
    _HAS_TRANSFORMATION = False
    logging.warning(f"坐标转换模块不可用: {e}")

# 数据验证模块导入
try:
    from .validation import (
        GeometryValidator, AttributeValidator, CoordinateSystemValidator,
        DataQualityScorer, DataRepairer
    )
    _HAS_VALIDATION = True
except ImportError as e:
    GeometryValidator = AttributeValidator = CoordinateSystemValidator = None
    DataQualityScorer = DataRepairer = None
    _HAS_VALIDATION = False
    logging.warning(f"数据验证模块不可用: {e}")

# 动态构建__all__列表
__all__ = []
if _HAS_ASSOCIATION:
    __all__.append('NearestNeighborAssociator')
if _HAS_INTERSECTION:
    __all__.append('LineIntersectionDetector')
if _HAS_CONTAINMENT:
    __all__.append('PolygonContainmentAnalyzer')
if _HAS_TRANSFORMATION:
    __all__.append('CoordinateTransformer')
if _HAS_VALIDATION:
    __all__.extend(['GeometryValidator', 'AttributeValidator', 'CoordinateSystemValidator',
                    'DataQualityScorer', 'DataRepairer'])