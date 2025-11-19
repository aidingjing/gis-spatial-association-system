"""
GIS空间关联分析算法模块

包含核心空间分析算法实现：
- association: 点-线最近邻关联算法
- intersection: 线-线相交检测算法
- containment: 线-面包含判断算法
- transformation: 坐标系转换处理
"""

from .association import NearestNeighborAssociator
from .intersection import LineIntersectionDetector
from .containment import PolygonContainmentAnalyzer
from .transformation import CoordinateTransformer

__all__ = [
    'NearestNeighborAssociator',
    'LineIntersectionDetector',
    'PolygonContainmentAnalyzer',
    'CoordinateTransformer'
]