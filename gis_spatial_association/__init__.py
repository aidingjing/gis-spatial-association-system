"""
GIS空间关联分析系统

提供高效的地理空间要素关联分析功能，包括：
- 点-线最近邻关联分析
- 线-线相交检测分析
- 线-面包含判断分析
- 坐标系转换处理

技术栈：Python + GeoPandas + Shapely + Rtree
"""

__version__ = "1.0.0"
__author__ = "CCPM Auto Development System"

from .algorithms.association import NearestNeighborAssociator
from .algorithms.intersection import LineIntersectionDetector
from .algorithms.containment import PolygonContainmentAnalyzer
from .algorithms.transformation import CoordinateTransformer

__all__ = [
    'NearestNeighborAssociator',
    'LineIntersectionDetector',
    'PolygonContainmentAnalyzer',
    'CoordinateTransformer'
]