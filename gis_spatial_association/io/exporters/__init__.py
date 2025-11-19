"""
数据导出模块

提供多种GIS数据格式的导出功能，支持主流的空间数据和非空间数据格式。
包含格式转换、字段处理、坐标系统转换等功能。

支持的导出格式:
- Shapefile (.shp) - ESRI Shapefile格式
- GeoJSON (.geojson) - JSON格式地理数据
- CSV (.csv) - 逗号分隔值格式
- Excel (.xlsx) - Microsoft Excel格式
- KML (.kml) - Google Earth KML格式
- GeoPackage (.gpkg) - OGC GeoPackage格式

作者: GIS空间关联系统开发团队
"""

__version__ = "1.0.0"

from .result_exporter import ResultExporter
from .shapefile import ShapefileExporter
from .geojson import GeoJSONExporter
from .csv import CSVExporter
from .excel import ExcelExporter
from .kml import KMLExporter
from .geopackage import GeoPackageExporter

__all__ = [
    'ResultExporter',
    'ShapefileExporter',
    'GeoJSONExporter',
    'CSVExporter',
    'ExcelExporter',
    'KMLExporter',
    'GeoPackageExporter'
]