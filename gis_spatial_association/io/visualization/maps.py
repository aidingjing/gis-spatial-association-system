"""
地图可视化模块

提供丰富的GIS数据地图可视化功能，支持交互式地图、专题制图、
热力图等多种地图展示方式。

特点:
- 交互式地图生成 (Folium)
- 多种底图支持
- 专题制图功能
- 热力图和密度图
- 自定义样式配置
- 多格式输出支持

作者: GIS空间关联系统开发团队
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import pandas as pd
import geopandas as gpd

try:
    import folium
    from folium import plugins
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    import seaborn as sns
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False
    logger = logging.getLogger(__name__).warning("folium库未安装，交互式地图功能不可用")

logger = logging.getLogger(__name__)


class MapVisualizer:
    """
    地图可视化器

    生成各种类型的地图可视化，包括交互式地图和静态地图。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化地图可视化器

        Args:
            config: 可视化配置
        """
        self.config = config or {}

        # 默认配置
        self.default_config = {
            'default_zoom': 10,
            'tile_layer': 'OpenStreetMap',
            'color_scheme': 'viridis',
            'popup_enabled': True,
            'tooltip_enabled': True,
            'cluster_markers': False,
            'heat_map_radius': 15,
            'figure_size': (12, 8),
            'dpi': 300,
            'save_formats': ['html', 'png']
        }

        # 合并配置
        self.config = {**self.default_config, **self.config}

        # 颜色映射
        self.color_schemes = {
            'viridis': plt.cm.viridis,
            'plasma': plt.cm.plasma,
            'inferno': plt.cm.inferno,
            'magma': plt.cm.magma,
            'blues': plt.cm.Blues,
            'reds': plt.cm.Reds,
            'greens': plt.cm.Greens,
            'coolwarm': plt.cm.coolwarm,
            'rainbow': plt.cm.rainbow
        }

        # 底图选项
        self.tile_layers = {
            'OpenStreetMap': 'OpenStreetMap',
            'CartoDB Positron': 'CartoDB positron',
            'CartoDB Dark': 'CartoDB dark_matter',
            'Stamen Terrain': 'Stamen Terrain',
            'Stamen Toner': 'Stamen Toner',
            'Stamen Watercolor': 'Stamen Watercolor'
        }

    def create_spatial_map(self,
                          gdf: gpd.GeoDataFrame,
                          layer_name: str,
                          output_dir: Path) -> Optional[Dict[str, Any]]:
        """
        创建空间分布地图

        Args:
            gdf: GeoDataFrame
            layer_name: 图层名称
            output_dir: 输出目录

        Returns:
            Optional[Dict[str, Any]]: 地图信息
        """
        try:
            if not FOLIUM_AVAILABLE:
                logger.warning("folium库未安装，无法创建交互式地图")
                return None

            if gdf.empty:
                logger.warning(f"数据集 {layer_name} 为空，跳过地图创建")
                return None

            # 确保使用WGS84坐标系
            if gdf.crs != 'EPSG:4326':
                gdf_wgs84 = gdf.to_crs('EPSG:4326')
            else:
                gdf_wgs84 = gdf

            # 计算地图中心点和边界
            bounds = gdf_wgs84.total_bounds
            center_lat = (bounds[1] + bounds[3]) / 2
            center_lon = (bounds[0] + bounds[2]) / 2

            # 创建Folium地图
            m = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=self._calculate_zoom_level(bounds),
                tiles=self.config['tile_layer']
            )

            # 根据几何类型添加数据
            geom_type = gdf_wgs84.geometry.geom_type.iloc[0]

            if geom_type == 'Point':
                self._add_point_layer(m, gdf_wgs84, layer_name)
            elif geom_type in ['LineString', 'MultiLineString']:
                self._add_line_layer(m, gdf_wgs84, layer_name)
            elif geom_type in ['Polygon', 'MultiPolygon']:
                self._add_polygon_layer(m, gdf_wgs84, layer_name)

            # 添加图层控制
            folium.LayerControl().add_to(m)

            # 添加全屏控件
            plugins.Fullscreen().add_to(m)

            # 添加鼠标坐标显示
            plugins.MousePosition().add_to(m)

            # 添加测量工具
            plugins.MeasureControl().add_to(m)

            # 保存地图
            map_file = output_dir / f"{layer_name}_spatial_map.html"
            m.save(str(map_file))

            # 创建缩略图
            thumbnail_file = self._create_map_thumbnail(m, output_dir / f"{layer_name}_spatial_map.png")

            map_info = {
                'type': 'spatial_map',
                'title': f'{layer_name} 空间分布图',
                'description': f'显示 {layer_name} 的空间分布情况',
                'file_path': str(map_file),
                'thumbnail_path': str(thumbnail_file) if thumbnail_file else None,
                'format': 'html',
                'data_source': layer_name,
                'geometry_type': geom_type,
                'feature_count': len(gdf_wgs84),
                'bounds': bounds.tolist(),
                'center': [center_lat, center_lon]
            }

            logger.info(f"✅ 空间分布图创建成功: {map_file}")
            return map_info

        except Exception as e:
            logger.error(f"创建空间分布图失败: {str(e)}")
            return None

    def create_thematic_map(self,
                           gdf: gpd.GeoDataFrame,
                           layer_name: str,
                           output_dir: Path) -> Optional[Dict[str, Any]]:
        """
        创建专题地图

        Args:
            gdf: GeoDataFrame
            layer_name: 图层名称
            output_dir: 输出目录

        Returns:
            Optional[Dict[str, Any]]: 地图信息
        """
        try:
            if not FOLIUM_AVAILABLE:
                logger.warning("folium库未安装，无法创建专题地图")
                return None

            if gdf.empty:
                return None

            # 查找合适的数值字段
            numeric_columns = gdf.select_dtypes(include=['number']).columns
            if len(numeric_columns) == 0:
                logger.warning(f"数据集 {layer_name} 没有合适的数值字段用于专题制图")
                return None

            # 选择第一个数值字段（可以改进为自动选择最佳字段）
            value_column = numeric_columns[0]

            # 确保使用WGS84坐标系
            if gdf.crs != 'EPSG:4326':
                gdf_wgs84 = gdf.to_crs('EPSG:4326')
            else:
                gdf_wgs84 = gdf

            # 计算地图中心点
            bounds = gdf_wgs84.total_bounds
            center_lat = (bounds[1] + bounds[3]) / 2
            center_lon = (bounds[0] + bounds[2]) / 2

            # 创建Folium地图
            m = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=self._calculate_zoom_level(bounds),
                tiles=self.config['tile_layer']
            )

            # 创建颜色映射
            colormap = self._create_colormap(gdf_wgs84[value_column], value_column)

            # 添加专题图层
            geom_type = gdf_wgs84.geometry.geom_type.iloc[0]

            if geom_type == 'Point':
                self._add_thematic_point_layer(m, gdf_wgs84, layer_name, value_column, colormap)
            elif geom_type in ['Polygon', 'MultiPolygon']:
                self._add_thematic_polygon_layer(m, gdf_wgs84, layer_name, value_column, colormap)

            # 添加颜色图例
            colormap.add_to(m)

            # 保存地图
            map_file = output_dir / f"{layer_name}_thematic_map.html"
            m.save(str(map_file))

            # 创建缩略图
            thumbnail_file = self._create_map_thumbnail(m, output_dir / f"{layer_name}_thematic_map.png")

            map_info = {
                'type': 'thematic_map',
                'title': f'{layer_name} 专题图 ({value_column})',
                'description': f'基于 {value_column} 字段的专题制图',
                'file_path': str(map_file),
                'thumbnail_path': str(thumbnail_file) if thumbnail_file else None,
                'format': 'html',
                'data_source': layer_name,
                'value_column': value_column,
                'value_range': [float(gdf_wgs84[value_column].min()), float(gdf_wgs84[value_column].max())],
                'feature_count': len(gdf_wgs84)
            }

            logger.info(f"✅ 专题地图创建成功: {map_file}")
            return map_info

        except Exception as e:
            logger.error(f"创建专题地图失败: {str(e)}")
            return None

    def create_heatmap(self,
                      gdf: gpd.GeoDataFrame,
                      layer_name: str,
                      output_dir: Path) -> Optional[Dict[str, Any]]:
        """
        创建热力图

        Args:
            gdf: GeoDataFrame
            layer_name: 图层名称
            output_dir: 输出目录

        Returns:
            Optional[Dict[str, Any]]: 地图信息
        """
        try:
            if not FOLIUM_AVAILABLE:
                logger.warning("folium库未安装，无法创建热力图")
                return None

            if gdf.empty:
                return None

            # 确保是点数据
            geom_type = gdf.geometry.geom_type.iloc[0]
            if geom_type != 'Point':
                logger.warning(f"热力图仅支持点数据，当前几何类型: {geom_type}")
                return None

            # 确保使用WGS84坐标系
            if gdf.crs != 'EPSG:4326':
                gdf_wgs84 = gdf.to_crs('EPSG:4326')
            else:
                gdf_wgs84 = gdf

            # 计算地图中心点
            bounds = gdf_wgs84.total_bounds
            center_lat = (bounds[1] + bounds[3]) / 2
            center_lon = (bounds[0] + bounds[2]) / 2

            # 创建Folium地图
            m = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=self._calculate_zoom_level(bounds),
                tiles=self.config['tile_layer']
            )

            # 准备热力图数据
            heat_data = []
            for idx, row in gdf_wgs84.iterrows():
                heat_data.append([row.geometry.y, row.geometry.x])

            # 添加热力图层
            heat_map = plugins.HeatMap(
                heat_data,
                radius=self.config['heat_map_radius'],
                blur=15,
                gradient={0.4: 'blue', 0.65: 'lime', 1: 'red'}
            )
            heat_map.add_to(m)

            # 保存地图
            map_file = output_dir / f"{layer_name}_heatmap.html"
            m.save(str(map_file))

            # 创建缩略图
            thumbnail_file = self._create_map_thumbnail(m, output_dir / f"{layer_name}_heatmap.png")

            map_info = {
                'type': 'heatmap',
                'title': f'{layer_name} 热力图',
                'description': f'{layer_name} 的密度分布热力图',
                'file_path': str(map_file),
                'thumbnail_path': str(thumbnail_file) if thumbnail_file else None,
                'format': 'html',
                'data_source': layer_name,
                'point_count': len(gdf_wgs84),
                'radius': self.config['heat_map_radius']
            }

            logger.info(f"✅ 热力图创建成功: {map_file}")
            return map_info

        except Exception as e:
            logger.error(f"创建热力图失败: {str(e)}")
            return None

    def _add_point_layer(self, m: folium.Map, gdf: gpd.GeoDataFrame, layer_name: str):
        """
        添加点图层到地图

        Args:
            m: Folium地图对象
            gdf: GeoDataFrame
            layer_name: 图层名称
        """
        # 检查是否需要聚合点
        if self.config['cluster_markers'] and len(gdf) > 100:
            # 创建聚合标记
            feature_group = folium.FeatureGroup(name=f"{layer_name} (聚合)")

            for idx, row in gdf.iterrows():
                popup_text = self._create_popup_text(row, layer_name)
                tooltip_text = self._create_tooltip_text(row, layer_name)

                folium.CircleMarker(
                    location=[row.geometry.y, row.geometry.x],
                    radius=5,
                    popup=folium.Popup(popup_text, max_width=300) if self.config['popup_enabled'] else None,
                    tooltip=tooltip_text if self.config['tooltip_enabled'] else None,
                    color='blue',
                    fill=True,
                    fillColor='lightblue',
                    fillOpacity=0.7
                ).add_to(feature_group)

            # 添加聚合插件
            marker_cluster = plugins.MarkerCluster().add_to(feature_group)
            m.add_child(feature_group)
        else:
            # 创建普通点图层
            feature_group = folium.FeatureGroup(name=layer_name)

            for idx, row in gdf.iterrows():
                popup_text = self._create_popup_text(row, layer_name)
                tooltip_text = self._create_tooltip_text(row, layer_name)

                folium.CircleMarker(
                    location=[row.geometry.y, row.geometry.x],
                    radius=5,
                    popup=folium.Popup(popup_text, max_width=300) if self.config['popup_enabled'] else None,
                    tooltip=tooltip_text if self.config['tooltip_enabled'] else None,
                    color='blue',
                    fill=True,
                    fillColor='lightblue',
                    fillOpacity=0.7
                ).add_to(feature_group)

            m.add_child(feature_group)

    def _add_line_layer(self, m: folium.Map, gdf: gpd.GeoDataFrame, layer_name: str):
        """
        添加线图层到地图

        Args:
            m: Folium地图对象
            gdf: GeoDataFrame
            layer_name: 图层名称
        """
        feature_group = folium.FeatureGroup(name=layer_name)

        for idx, row in gdf.iterrows():
            popup_text = self._create_popup_text(row, layer_name)
            tooltip_text = self._create_tooltip_text(row, layer_name)

            # 获取线坐标
            if hasattr(row.geometry, 'coords'):
                coords = list(row.geometry.coords)
                locations = [[coord[1], coord[0]] for coord in coords]  # 转换为[lat, lon]

                folium.PolyLine(
                    locations=locations,
                    popup=folium.Popup(popup_text, max_width=300) if self.config['popup_enabled'] else None,
                    tooltip=tooltip_text if self.config['tooltip_enabled'] else None,
                    color='blue',
                    weight=3,
                    opacity=0.8
                ).add_to(feature_group)

        m.add_child(feature_group)

    def _add_polygon_layer(self, m: folium.Map, gdf: gpd.GeoDataFrame, layer_name: str):
        """
        添加面图层到地图

        Args:
            m: Folium地图对象
            gdf: GeoDataFrame
            layer_name: 图层名称
        """
        feature_group = folium.FeatureGroup(name=layer_name)

        for idx, row in gdf.iterrows():
            popup_text = self._create_popup_text(row, layer_name)
            tooltip_text = self._create_tooltip_text(row, layer_name)

            # 获取面坐标
            if hasattr(row.geometry, 'exterior'):
                coords = list(row.geometry.exterior.coords)
                locations = [[coord[1], coord[0]] for coord in coords]

                folium.Polygon(
                    locations=locations,
                    popup=folium.Popup(popup_text, max_width=300) if self.config['popup_enabled'] else None,
                    tooltip=tooltip_text if self.config['tooltip_enabled'] else None,
                    color='blue',
                    fill=True,
                    fillColor='lightblue',
                    fillOpacity=0.5,
                    weight=2
                ).add_to(feature_group)

        m.add_child(feature_group)

    def _add_thematic_point_layer(self, m: folium.Map, gdf: gpd.GeoDataFrame, layer_name: str,
                                 value_column: str, colormap):
        """
        添加专题点图层

        Args:
            m: Folium地图对象
            gdf: GeoDataFrame
            layer_name: 图层名称
            value_column: 数值字段名
            colormap: 颜色映射
        """
        feature_group = folium.FeatureGroup(name=f"{layer_name} ({value_column})")

        values = gdf[value_column]
        min_val, max_val = values.min(), values.max()

        for idx, row in gdf.iterrows():
            value = row[value_column]
            color = colormap(value)

            popup_text = self._create_popup_text(row, layer_name)
            popup_text += f"<br><b>{value_column}:</b> {value}"

            folium.CircleMarker(
                location=[row.geometry.y, row.geometry.x],
                radius=8,
                popup=folium.Popup(popup_text, max_width=300) if self.config['popup_enabled'] else None,
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.7,
                weight=2
            ).add_to(feature_group)

        m.add_child(feature_group)

    def _add_thematic_polygon_layer(self, m: folium.Map, gdf: gpd.GeoDataFrame, layer_name: str,
                                   value_column: str, colormap):
        """
        添加专题面图层

        Args:
            m: Folium地图对象
            gdf: GeoDataFrame
            layer_name: 图层名称
            value_column: 数值字段名
            colormap: 颜色映射
        """
        feature_group = folium.FeatureGroup(name=f"{layer_name} ({value_column})")

        for idx, row in gdf.iterrows():
            value = row[value_column]
            color = colormap(value)

            popup_text = self._create_popup_text(row, layer_name)
            popup_text += f"<br><b>{value_column}:</b> {value}"

            # 获取面坐标
            if hasattr(row.geometry, 'exterior'):
                coords = list(row.geometry.exterior.coords)
                locations = [[coord[1], coord[0]] for coord in coords]

                folium.Polygon(
                    locations=locations,
                    popup=folium.Popup(popup_text, max_width=300) if self.config['popup_enabled'] else None,
                    color=color,
                    fill=True,
                    fillColor=color,
                    fillOpacity=0.7,
                    weight=2
                ).add_to(feature_group)

        m.add_child(feature_group)

    def _create_colormap(self, values: pd.Series, column_name: str):
        """
        创建颜色映射

        Args:
            values: 数值序列
            column_name: 字段名

        Returns:
            folium.ColorMap: 颜色映射对象
        """
        min_val, max_val = values.min(), values.max()
        color_scheme = self.config['color_scheme']

        return folium.LinearColormap(
            colors=self._get_color_list(color_scheme),
            vmin=min_val,
            vmax=max_val,
            caption=column_name
        )

    def _get_color_list(self, scheme: str) -> List[str]:
        """
        获取颜色列表

        Args:
            scheme: 颜色方案名称

        Returns:
            List[str]: 颜色列表
        """
        # 简化的颜色映射
        color_maps = {
            'viridis': ['#440154', '#31688e', '#35b779', '#fde725'],
            'plasma': ['#0d0887', '#7e03a8', '#cc4778', '#f89540', '#f0f921'],
            'blues': ['#08519c', '#3182bd', '#6baed6', '#bdd7e7'],
            'reds': ['#a50f15', '#de2d26', '#fb6a4a', '#fcbba1'],
            'greens': ['#00441b', '#238b45', '#74c476', '#c7e9c0'],
            'coolwarm': ['#b2182b', '#fddbc7', '#f7f7f7', '#d1e5f0', '#2166ac']
        }

        return color_maps.get(scheme, color_maps['viridis'])

    def _create_popup_text(self, row: pd.Series, layer_name: str) -> str:
        """
        创建弹出窗口文本

        Args:
            row: 数据行
            layer_name: 图层名称

        Returns:
            str: 弹出窗口HTML文本
        """
        popup_parts = [f"<b>{layer_name}</b><br>"]

        for col in row.index:
            if col != 'geometry' and pd.notna(row[col]):
                popup_parts.append(f"<b>{col}:</b> {row[col]}<br>")

        return "".join(popup_parts)

    def _create_tooltip_text(self, row: pd.Series, layer_name: str) -> str:
        """
        创建工具提示文本

        Args:
            row: 数据行
            layer_name: 图层名称

        Returns:
            str: 工具提示文本
        """
        # 简化的工具提示，只显示主要信息
        if 'name' in row.index and pd.notna(row['name']):
            return f"{layer_name}: {row['name']}"
        elif 'id' in row.index and pd.notna(row['id']):
            return f"{layer_name}: ID {row['id']}"
        else:
            return layer_name

    def _calculate_zoom_level(self, bounds: List[float]) -> int:
        """
        根据边界计算合适的缩放级别

        Args:
            bounds: 边界坐标 [min_x, min_y, max_x, max_y]

        Returns:
            int: 缩放级别
        """
        try:
            # 计算地理范围
            width = abs(bounds[2] - bounds[0])  # 经度范围
            height = abs(bounds[3] - bounds[1])  # 纬度范围

            # 根据范围估算缩放级别
            if width > 10 or height > 10:
                return 6
            elif width > 1 or height > 1:
                return 8
            elif width > 0.1 or height > 0.1:
                return 10
            elif width > 0.01 or height > 0.01:
                return 12
            else:
                return 14
        except Exception:
            return self.config['default_zoom']

    def _create_map_thumbnail(self, m: folium.Map, output_path: Path) -> Optional[Path]:
        """
        创建地图缩略图

        Args:
            m: Folium地图对象
            output_path: 输出路径

        Returns:
            Optional[Path]: 缩略图路径
        """
        try:
            # 注意：这需要额外的依赖如 selenium 或 chromedriver
            # 这里提供一个简化的实现，实际使用时可能需要更复杂的设置
            logger.info(f"缩略图功能需要额外配置，跳过生成: {output_path}")
            return None
        except Exception as e:
            logger.warning(f"创建地图缩略图失败: {str(e)}")
            return None

    def create_custom_map(self,
                         data: gpd.GeoDataFrame,
                         options: Dict[str, Any],
                         output_path: str = None) -> Optional[str]:
        """
        创建自定义地图

        Args:
            data: GeoDataFrame
            options: 自定义选项
            output_path: 输出路径

        Returns:
            Optional[str]: 地图文件路径
        """
        try:
            if not FOLIUM_AVAILABLE:
                return None

            # 应用自定义配置
            custom_config = {**self.config, **options}

            # 创建地图
            gdf = data
            if gdf.crs != 'EPSG:4326':
                gdf = gdf.to_crs('EPSG:4326')

            bounds = gdf.total_bounds
            center_lat = (bounds[1] + bounds[3]) / 2
            center_lon = (bounds[0] + bounds[2]) / 2

            m = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=options.get('zoom_start', self._calculate_zoom_level(bounds)),
                tiles=options.get('tiles', custom_config['tile_layer'])
            )

            # 根据选项添加数据
            if options.get('heatmap', False):
                self._add_custom_heatmap(m, gdf, options)
            else:
                self._add_custom_data_layer(m, gdf, options)

            # 保存地图
            if not output_path:
                output_path = f"custom_map_{options.get('name', 'map')}.html"

            m.save(output_path)
            return output_path

        except Exception as e:
            logger.error(f"创建自定义地图失败: {str(e)}")
            return None

    def _add_custom_heatmap(self, m: folium.Map, gdf: gpd.GeoDataFrame, options: Dict[str, Any]):
        """添加自定义热力图"""
        heat_data = []
        for idx, row in gdf.iterrows():
            weight = options.get('weight_field')
            if weight and weight in row:
                heat_data.append([row.geometry.y, row.geometry.x, row[weight]])
            else:
                heat_data.append([row.geometry.y, row.geometry.x])

        plugins.HeatMap(
            heat_data,
            radius=options.get('radius', self.config['heat_map_radius']),
            blur=options.get('blur', 15)
        ).add_to(m)

    def _add_custom_data_layer(self, m: folium.Map, gdf: gpd.GeoDataFrame, options: Dict[str, Any]):
        """添加自定义数据图层"""
        for idx, row in gdf.iterrows():
            # 根据选项设置样式
            color = options.get('color', 'blue')
            radius = options.get('radius', 5)

            folium.CircleMarker(
                location=[row.geometry.y, row.geometry.x],
                radius=radius,
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.7
            ).add_to(m)

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """
        更新配置

        Args:
            new_config: 新配置
        """
        self.config.update(new_config)