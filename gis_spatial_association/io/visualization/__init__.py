"""
数据可视化模块

提供丰富的GIS数据可视化功能，包含地图可视化、统计图表、
网络图、仪表板等多种可视化方式。

主要功能:
- 交互式地图可视化 (Folium)
- 统计图表生成 (Matplotlib/Seaborn)
- 网络关系图 (NetworkX)
- 数据仪表板
- 自定义样式配置
- 多格式输出

支持的图表类型:
- 散点图、柱状图、折线图
- 热力图、密度图
- 空间分布图
- 关系网络图
- 时间序列图

作者: GIS空间关联系统开发团队
"""

__version__ = "1.0.0"

from .data_visualizer import DataVisualizer
from .maps import MapVisualizer
from .charts import ChartVisualizer
from .network import NetworkVisualizer
from .dashboard import DashboardGenerator

__all__ = [
    'DataVisualizer',
    'MapVisualizer',
    'ChartVisualizer',
    'NetworkVisualizer',
    'DashboardGenerator'
]