"""
数据可视化主模块

提供统一的数据可视化接口，集成地图可视化、统计图表、
网络图等多种可视化方式。

特点:
- 多种可视化方式集成
- 自动化图表生成
- 交互式地图支持
- 自定义样式配置
- 批量可视化处理
- 多格式输出支持

作者: GIS空间关联系统开发团队
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import pandas as pd
import geopandas as gpd
from datetime import datetime

from .maps import MapVisualizer
from .charts import ChartVisualizer
from .network import NetworkVisualizer
from .dashboard import DashboardGenerator

logger = logging.getLogger(__name__)


class DataVisualizer:
    """
    数据可视化器

    提供全面的数据可视化功能，支持空间数据、统计数据和关系数据的可视化。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化数据可视化器

        Args:
            config: 可视化配置
        """
        self.config = config or {}

        # 默认配置
        self.default_config = {
            'output_formats': ['html', 'png'],
            'style_theme': 'default',
            'color_scheme': 'viridis',
            'figure_size': (12, 8),
            'dpi': 300,
            'interactive_maps': True,
            'auto_spatial_analysis': True,
            'chart_style': 'seaborn-v0_8',
            'map_tiles': 'OpenStreetMap',
            'language': 'zh-CN',
            'output_directory': './visualizations'
        }

        # 合并配置
        self.config = {**self.default_config, **self.config}

        # 初始化可视化组件
        self.map_visualizer = MapVisualizer(self.config)
        self.chart_visualizer = ChartVisualizer(self.config)
        self.network_visualizer = NetworkVisualizer(self.config)
        self.dashboard_generator = DashboardGenerator(self.config)

        # 支持的输出格式
        self.supported_formats = ['html', 'png', 'jpg', 'svg', 'pdf']

    def create_visualization_dashboard(self,
                                      results: Dict[str, Any],
                                      output_dir: str,
                                      dashboard_title: Optional[str] = None) -> Optional[str]:
        """
        创建完整的可视化仪表板

        Args:
            results: 分析结果数据
            output_dir: 输出目录
            dashboard_title: 仪表板标题

        Returns:
            Optional[str]: 仪表板文件路径
        """
        try:
            logger.info("开始创建可视化仪表板...")

            # 创建输出目录
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            # 初始化仪表板数据
            dashboard_data = {
                'title': dashboard_title or 'GIS空间关联分析可视化仪表板',
                'generation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'maps': [],
                'charts': [],
                'networks': [],
                'summary': {},
                'metadata': {}
            }

            # 生成各种可视化
            # 1. 地图可视化
            map_visualizations = self._create_map_visualizations(results, output_path)
            dashboard_data['maps'] = map_visualizations

            # 2. 统计图表
            chart_visualizations = self._create_chart_visualizations(results, output_path)
            dashboard_data['charts'] = chart_visualizations

            # 3. 网络关系图
            network_visualizations = self._create_network_visualizations(results, output_path)
            dashboard_data['networks'] = network_visualizations

            # 4. 生成汇总信息
            dashboard_data['summary'] = self._generate_visualization_summary(dashboard_data)

            # 5. 生成元数据
            dashboard_data['metadata'] = self._generate_visualization_metadata(results)

            # 生成HTML仪表板
            dashboard_file = self.dashboard_generator.generate_dashboard(dashboard_data, output_path)

            if dashboard_file:
                logger.info(f"✅ 可视化仪表板创建成功: {dashboard_file}")
                return dashboard_file
            else:
                logger.error("可视化仪表板创建失败")
                return None

        except Exception as e:
            logger.error(f"❌ 创建可视化仪表板失败: {str(e)}")
            return None

    def create_individual_visualizations(self,
                                        results: Dict[str, Any],
                                        output_dir: str,
                                        visualization_types: Optional[List[str]] = None) -> Dict[str, List[str]]:
        """
        创建单独的可视化文件

        Args:
            results: 分析结果数据
            output_dir: 输出目录
            visualization_types: 可视化类型列表

        Returns:
            Dict[str, List[str]]: 生成的文件路径
        """
        try:
            logger.info("开始创建单独的可视化文件...")

            # 确定可视化类型
            viz_types = visualization_types or ['maps', 'charts', 'networks']
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            generated_files = {
                'maps': [],
                'charts': [],
                'networks': []
            }

            # 创建地图可视化
            if 'maps' in viz_types:
                map_files = self._create_map_visualizations(results, output_path)
                generated_files['maps'] = [viz['file_path'] for viz in map_files if viz.get('file_path')]

            # 创建统计图表
            if 'charts' in viz_types:
                chart_files = self._create_chart_visualizations(results, output_path)
                generated_files['charts'] = [viz['file_path'] for viz in chart_files if viz.get('file_path')]

            # 创建网络关系图
            if 'networks' in viz_types:
                network_files = self._create_network_visualizations(results, output_path)
                generated_files['networks'] = [viz['file_path'] for viz in network_files if viz.get('file_path')]

            total_files = sum(len(files) for files in generated_files.values())
            logger.info(f"✅ 单独可视化文件创建完成，共 {total_files} 个文件")

            return generated_files

        except Exception as e:
            logger.error(f"❌ 创建单独可视化文件失败: {str(e)}")
            return {'maps': [], 'charts': [], 'networks': []}

    def _create_map_visualizations(self, results: Dict[str, Any], output_path: Path) -> List[Dict[str, Any]]:
        """
        创建地图可视化

        Args:
            results: 分析结果
            output_path: 输出路径

        Returns:
            List[Dict[str, Any]]: 地图可视化列表
        """
        maps = []

        for dataset_name, dataset_data in results.items():
            if isinstance(dataset_data, gpd.GeoDataFrame) and not dataset_data.empty:
                try:
                    # 创建基础地图
                    map_viz = self.map_visualizer.create_spatial_map(
                        dataset_data,
                        dataset_name,
                        output_path
                    )

                    if map_viz:
                        maps.append(map_viz)

                    # 创建专题地图（如果适用）
                    if self._should_create_thematic_map(dataset_data):
                        thematic_map = self.map_visualizer.create_thematic_map(
                            dataset_data,
                            dataset_name,
                            output_path
                        )
                        if thematic_map:
                            maps.append(thematic_map)

                    # 创建热力图（如果数据适合）
                    if self._should_create_heatmap(dataset_data):
                        heatmap = self.map_visualizer.create_heatmap(
                            dataset_data,
                            dataset_name,
                            output_path
                        )
                        if heatmap:
                            maps.append(heatmap)

                except Exception as e:
                    logger.warning(f"创建地图可视化失败 {dataset_name}: {str(e)}")

        return maps

    def _create_chart_visualizations(self, results: Dict[str, Any], output_path: Path) -> List[Dict[str, Any]]:
        """
        创建统计图表可视化

        Args:
            results: 分析结果
            output_path: 输出路径

        Returns:
            List[Dict[str, Any]]: 图表可视化列表
        """
        charts = []

        try:
            # 数据集概览图表
            overview_chart = self.chart_visualizer.create_dataset_overview_chart(results, output_path)
            if overview_chart:
                charts.append(overview_chart)

            # 属性分布图表
            for dataset_name, dataset_data in results.items():
                if isinstance(dataset_data, (gpd.GeoDataFrame, pd.DataFrame)) and not dataset_data.empty:
                    attribute_charts = self.chart_visualizer.create_attribute_distribution_charts(
                        dataset_data, dataset_name, output_path
                    )
                    charts.extend(attribute_charts)

            # 关联分析图表
            if 'associations' in results:
                association_charts = self.chart_visualizer.create_association_analysis_charts(
                    results['associations'], output_path
                )
                charts.extend(association_charts)

            # 质量评估图表
            if 'quality_assessment' in results:
                quality_chart = self.chart_visualizer.create_quality_assessment_chart(
                    results['quality_assessment'], output_path
                )
                if quality_chart:
                    charts.append(quality_chart)

        except Exception as e:
            logger.warning(f"创建统计图表失败: {str(e)}")

        return charts

    def _create_network_visualizations(self, results: Dict[str, Any], output_path: Path) -> List[Dict[str, Any]]:
        """
        创建网络关系可视化

        Args:
            results: 分析结果
            output_path: 输出路径

        Returns:
            List[Dict[str, Any]]: 网络可视化列表
        """
        networks = []

        try:
            # 关联关系网络图
            if 'associations' in results:
                association_network = self.network_visualizer.create_association_network(
                    results['associations'], output_path
                )
                if association_network:
                    networks.append(association_network)

            # 空间拓扑网络图
            spatial_network = self.network_visualizer.create_spatial_topology_network(
                results, output_path
            )
            if spatial_network:
                networks.append(spatial_network)

        except Exception as e:
            logger.warning(f"创建网络可视化失败: {str(e)}")

        return networks

    def _should_create_thematic_map(self, gdf: gpd.GeoDataFrame) -> bool:
        """
        判断是否应该创建专题地图

        Args:
            gdf: GeoDataFrame

        Returns:
            bool: 是否应该创建
        """
        # 检查是否有合适的数值字段用于专题制图
        numeric_columns = gdf.select_dtypes(include=['number']).columns
        return len(numeric_columns) > 0 and len(gdf) > 1

    def _should_create_heatmap(self, gdf: gpd.GeoDataFrame) -> bool:
        """
        判断是否应该创建热力图

        Args:
            gdf: GeoDataFrame

        Returns:
            bool: 是否应该创建
        """
        # 对于点数据且数量适中时创建热力图
        return (gdf.geometry.geom_type.iloc[0] == 'Point' and
                10 < len(gdf) < 10000)

    def _generate_visualization_summary(self, dashboard_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成可视化汇总信息

        Args:
            dashboard_data: 仪表板数据

        Returns:
            Dict[str, Any]: 汇总信息
        """
        summary = {
            'total_visualizations': 0,
            'map_count': len(dashboard_data.get('maps', [])),
            'chart_count': len(dashboard_data.get('charts', [])),
            'network_count': len(dashboard_data.get('networks', [])),
            'visualization_types': [],
            'data_sources': set(),
            'file_formats': set()
        }

        # 统计各种信息
        for viz_type in ['maps', 'charts', 'networks']:
            for viz in dashboard_data.get(viz_type, []):
                summary['total_visualizations'] += 1
                summary['visualization_types'].append(viz.get('type', 'unknown'))
                summary['data_sources'].add(viz.get('data_source', 'unknown'))
                summary['file_formats'].add(viz.get('format', 'unknown'))

        # 转换set为list
        summary['data_sources'] = list(summary['data_sources'])
        summary['file_formats'] = list(summary['file_formats'])
        summary['visualization_types'] = list(set(summary['visualization_types']))

        return summary

    def _generate_visualization_metadata(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成可视化元数据

        Args:
            results: 分析结果

        Returns:
            Dict[str, Any]: 元数据
        """
        return {
            'total_datasets': len([k for k, v in results.items() if isinstance(v, (gpd.GeoDataFrame, pd.DataFrame))]),
            'has_geospatial_data': any(isinstance(v, gpd.GeoDataFrame) for v in results.values()),
            'has_association_data': 'associations' in results,
            'has_quality_data': 'quality_assessment' in results,
            'visualization_config': {
                'style_theme': self.config['style_theme'],
                'color_scheme': self.config['color_scheme'],
                'interactive_maps': self.config['interactive_maps'],
                'chart_style': self.config['chart_style']
            },
            'generated_by': 'GIS空间关联系统 - 数据可视化模块',
            'version': '1.0.0'
        }

    def create_custom_visualization(self,
                                   data: Union[gpd.GeoDataFrame, pd.DataFrame],
                                   viz_type: str,
                                   options: Optional[Dict[str, Any]] = None,
                                   output_path: str = None) -> Optional[str]:
        """
        创建自定义可视化

        Args:
            data: 输入数据
            viz_type: 可视化类型
            options: 可视化选项
            output_path: 输出路径

        Returns:
            Optional[str]: 生成的文件路径
        """
        try:
            options = options or {}

            if viz_type == 'map':
                return self.map_visualizer.create_custom_map(data, options, output_path)
            elif viz_type == 'chart':
                return self.chart_visualizer.create_custom_chart(data, options, output_path)
            elif viz_type == 'network':
                return self.network_visualizer.create_custom_network(data, options, output_path)
            else:
                raise ValueError(f"不支持的可视化类型: {viz_type}")

        except Exception as e:
            logger.error(f"创建自定义可视化失败: {str(e)}")
            return None

    def get_supported_visualization_types(self) -> Dict[str, List[str]]:
        """
        获取支持的可视化类型

        Returns:
            Dict[str, List[str]]: 支持的可视化类型
        """
        return {
            'maps': ['spatial', 'thematic', 'heatmap', 'choropleth', 'bubble'],
            'charts': ['bar', 'line', 'scatter', 'histogram', 'box', 'violin', 'heatmap', 'pair'],
            'networks': ['association', 'topology', 'hierarchical', 'force_directed']
        }

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """
        更新可视化配置

        Args:
            new_config: 新配置
        """
        self.config.update(new_config)

        # 更新各组件配置
        for component in [self.map_visualizer, self.chart_visualizer, self.network_visualizer, self.dashboard_generator]:
            if hasattr(component, 'update_config'):
                component.update_config(new_config)

    def export_visualization_config(self, file_path: str) -> None:
        """
        导出可视化配置

        Args:
            file_path: 配置文件路径
        """
        import json

        try:
            config_to_export = {
                'config': self.config,
                'supported_types': self.get_supported_visualization_types(),
                'supported_formats': self.supported_formats
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_to_export, f, indent=2, ensure_ascii=False)

            logger.info(f"可视化配置已导出: {file_path}")

        except Exception as e:
            logger.error(f"导出可视化配置失败: {str(e)}")

    def import_visualization_config(self, file_path: str) -> None:
        """
        导入可视化配置

        Args:
            file_path: 配置文件路径
        """
        import json

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)

            if 'config' in imported_config:
                self.update_config(imported_config['config'])
                logger.info(f"可视化配置已导入: {file_path}")
            else:
                logger.warning("配置文件格式不正确")

        except Exception as e:
            logger.error(f"导入可视化配置失败: {str(e)}")