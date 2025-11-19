"""
KML格式导出器

支持将GeoDataFrame导出为KML格式，包含样式设置、
图标定义、时序数据等功能。

特点:
- 自动样式和图标设置
- 描述信息生成
- 时间戳支持
- 图层组织
- 弹出窗口自定义
- 性能优化

作者: GIS空间关联系统开发团队
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon
from datetime import datetime

try:
    import simplekml
    SIMPLEKML_AVAILABLE = True
except ImportError:
    SIMPLEKML_AVAILABLE = False
    logger = logging.getLogger(__name__).warning("simplekml未安装，KML导出功能不可用")

logger = logging.getLogger(__name__)


class KMLExporter:
    """
    KML格式导出器

    将GeoDataFrame导出为Google Earth KML格式，支持丰富的
    可视化设置。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化KML导出器

        Args:
            config: 导出配置
        """
        self.config = config or {}

        # KML默认配置
        self.default_config = {
            'name_field': 'name',
            'description_field': 'description',
            'style_by_attribute': None,
            'default_color': 'ff0000ff',  # AABBGGRR (alpha, blue, green, red)
            'default_icon': 'http://maps.google.com/mapfiles/kml/pushpin/ylw-pushpin.png',
            'line_width': 2,
            'polygon_opacity': 0.7,
            'include_timestamps': False,
            'timestamp_field': None,
            'altitude_mode': 'clampToGround',  # 'clampToGround', 'relativeToGround', 'absolute'
            'extrude': False,
            'tessellate': False,
            'generate_styles': True,
            'create_folders': False,
            'folder_attribute': None
        }

        # 合并配置
        self.config = {**self.default_config, **self.config}

        # 支持的数据类型
        self.supported_data_types = ['GeoDataFrame']

        # 文件扩展名
        self.file_extension = '.kml'

        # 描述
        self.description = 'KML格式导出器'

    def export(self,
              dataset_data: gpd.GeoDataFrame,
              dataset_name: str,
              output_dir: str) -> Optional[str]:
        """
        导出GeoDataFrame到KML格式

        Args:
            dataset_data: 要导出的GeoDataFrame
            dataset_name: 数据集名称
            output_dir: 输出目录

        Returns:
            Optional[str]: 导出文件路径，失败返回None
        """
        try:
            logger.info(f"开始导出 {dataset_name} 到KML格式...")

            # 检查simplekml可用性
            if not SIMPLEKML_AVAILABLE:
                raise ImportError("需要安装simplekml库: pip install simplekml")

            # 验证输入数据
            if not isinstance(dataset_data, gpd.GeoDataFrame):
                raise ValueError("KML导出需要GeoDataFrame数据")

            if dataset_data.empty:
                logger.warning(f"数据集 {dataset_name} 为空，跳过导出")
                return None

            # 准备数据
            prepared_gdf = self._prepare_kml_data(dataset_data)

            # 生成输出文件路径
            base_name = self._sanitize_filename(dataset_name)
            output_path = Path(output_dir) / f"{base_name}.kml"

            # 检查文件是否已存在
            if output_path.exists():
                if self.config.get('overwrite', True):
                    output_path.unlink()
                else:
                    raise FileExistsError(f"KML文件已存在: {output_path}")

            # 创建KML文档
            return self._create_kml_document(prepared_gdf, base_name, output_path)

        except Exception as e:
            logger.error(f"❌ KML导出失败: {str(e)}")
            return None

    def get_output_path(self, dataset_name: str, output_dir: Path) -> Optional[Path]:
        """获取输出文件路径"""
        base_name = self._sanitize_filename(dataset_name)
        return output_dir / f"{base_name}.kml"

    def _prepare_kml_data(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        准备KML数据

        Args:
            gdf: 原始GeoDataFrame

        Returns:
            gpd.GeoDataFrame: 准备好的GeoDataFrame
        """
        # 创建副本
        prepared_gdf = gdf.copy()

        # 确保使用WGS84坐标系
        if prepared_gdf.crs != 'EPSG:4326':
            if prepared_gdf.crs is not None:
                prepared_gdf = prepared_gdf.to_crs('EPSG:4326')
            else:
                logger.warning("数据没有坐标参考系统，假设为WGS84")
                prepared_gdf.crs = 'EPSG:4326'

        # 重置索引
        prepared_gdf = prepared_gdf.reset_index(drop=True)

        # 添加缺失的名称和描述字段
        if self.config['name_field'] not in prepared_gdf.columns:
            prepared_gdf[self.config['name_field']] = [
                f"Feature {i+1}" for i in range(len(prepared_gdf))
            ]

        if self.config['description_field'] not in prepared_gdf.columns:
            prepared_gdf[self.config['description_field']] = self._generate_descriptions(prepared_gdf)

        return prepared_gdf

    def _generate_descriptions(self, gdf: gpd.GeoDataFrame) -> List[str]:
        """
        生成要素描述

        Args:
            gdf: GeoDataFrame

        Returns:
            List[str]: 描述列表
        """
        descriptions = []

        for idx, row in gdf.iterrows():
            desc_parts = []

            # 添加几何类型
            geom_type = row.geometry.geom_type
            desc_parts.append(f"<b>几何类型:</b> {geom_type}")

            # 添加属性信息
            for col in gdf.columns:
                if col not in ['geometry', self.config['name_field'], self.config['description_field']]:
                    value = row[col]
                    if pd.notna(value):
                        desc_parts.append(f"<b>{col}:</b> {value}")

            # 添加几何属性
            if geom_type == 'Point':
                desc_parts.append(f"<b>坐标:</b> {row.geometry.x:.6f}, {row.geometry.y:.6f}")
            elif geom_type in ['Polygon', 'MultiPolygon']:
                desc_parts.append(f"<b>面积:</b> {row.geometry.area:.2f}")
            elif geom_type in ['LineString', 'MultiLineString']:
                desc_parts.append(f"<b>长度:</b> {row.geometry.length:.2f}")

            descriptions.append("<br>".join(desc_parts))

        return descriptions

    def _create_kml_document(self, gdf: gpd.GeoDataFrame, document_name: str, output_path: Path) -> Optional[str]:
        """
        创建KML文档

        Args:
            gdf: GeoDataFrame
            document_name: 文档名称
            output_path: 输出路径

        Returns:
            Optional[str]: 导出文件路径
        """
        try:
            # 创建KML对象
            kml = simplekml.Kml()
            kml.document.name = document_name

            # 生成样式
            styles = self._generate_styles(kml, gdf) if self.config['generate_styles'] else {}

            # 创建文件夹
            if self.config['create_folders'] and self.config['folder_attribute']:
                folders = self._create_folders(kml, gdf)
            else:
                folders = {None: kml.document}

            # 添加要素
            for idx, row in gdf.iterrows():
                self._add_feature_to_kml(kml, row, styles, folders)

            # 保存KML文件
            kml.save(str(output_path))

            logger.info(f"✅ KML导出成功: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"创建KML文档失败: {str(e)}")
            return None

    def _generate_styles(self, kml, gdf: gpd.GeoDataFrame) -> Dict[str, Any]:
        """
        生成KML样式

        Args:
            kml: KML对象
            gdf: GeoDataFrame

        Returns:
            Dict[str, Any]: 样式字典
        """
        styles = {}

        style_by_attribute = self.config['style_by_attribute']

        if style_by_attribute and style_by_attribute in gdf.columns:
            # 根据属性值生成不同样式
            unique_values = gdf[style_by_attribute].unique()
            colors = self._generate_colors(len(unique_values))

            for i, value in enumerate(unique_values):
                style_name = f"style_{i}"
                color = colors[i]

                style = kml.newstyle(name=style_name)

                # 根据几何类型设置样式
                geom_type = gdf.geometry.geom_type.iloc[0]

                if geom_type == 'Point':
                    icon_style = style.iconstyle
                    icon_style.color = color
                    icon_style.icon.href = self.config['default_icon']
                    icon_style.scale = 1.0

                elif geom_type in ['LineString', 'MultiLineString']:
                    linestyle = style.linestyle
                    linestyle.color = color
                    linestyle.width = self.config['line_width']

                elif geom_type in ['Polygon', 'MultiPolygon']:
                    polystyle = style.polystyle
                    polystyle.color = self._add_alpha(color, self.config['polygon_opacity'])
                    polystyle.fill = 1
                    polystyle.outline = 1

                    linestyle = style.linestyle
                    linestyle.color = color
                    linestyle.width = self.config['line_width']

                styles[value] = style_name
        else:
            # 使用默认样式
            styles['default'] = 'default_style'

        return styles

    def _generate_colors(self, count: int) -> List[str]:
        """
        生成颜色列表

        Args:
            count: 颜色数量

        Returns:
            List[str]: 颜色列表
        """
        colors = []

        # 预定义的颜色列表
        base_colors = [
            'ff0000ff',  # 红色
            'ff00ff00',  # 绿色
            'ff0000ff',  # 蓝色
            'ff00ffff',  # 青色
            'ffff00ff',  # 品红色
            'ff00aaff',  # 橙色
            'ffffaa00',  # 紫色
        ]

        for i in range(count):
            colors.append(base_colors[i % len(base_colors)])

        return colors

    def _add_alpha(self, color: str, opacity: float) -> str:
        """
        添加透明度到颜色

        Args:
            color: 原始颜色
            opacity: 透明度 (0-1)

        Returns:
            str: 带透明度的颜色
        """
        alpha = int(opacity * 255)
        return f"{alpha:02x}{color[2:]}"

    def _create_folders(self, kml, gdf: gpd.GeoDataFrame) -> Dict[str, Any]:
        """
        创建文件夹组织

        Args:
            kml: KML对象
            gdf: GeoDataFrame

        Returns:
            Dict[str, Any]: 文件夹字典
        """
        folders = {}
        folder_attribute = self.config['folder_attribute']

        if folder_attribute and folder_attribute in gdf.columns:
            unique_values = gdf[folder_attribute].unique()

            for value in unique_values:
                folder_name = str(value)
                folder = kml.newfolder(name=folder_name)
                folders[value] = folder

        return folders

    def _add_feature_to_kml(self, kml, row, styles: Dict[str, Any], folders: Dict[str, Any]):
        """
        添加要素到KML

        Args:
            kml: KML对象
            row: 要素行数据
            styles: 样式字典
            folders: 文件夹字典
        """
        geom = row.geometry
        name = str(row[self.config['name_field']])
        description = str(row[self.config['description_field']])

        # 确定文件夹
        folder_key = None
        if self.config['folder_attribute'] and self.config['folder_attribute'] in row:
            folder_key = row[self.config['folder_attribute']]

        folder = folders.get(folder_key, folders.get(None, kml.document))

        # 确定样式
        style_name = None
        if self.config['style_by_attribute'] and self.config['style_by_attribute'] in row:
            style_name = styles.get(row[self.config['style_by_attribute']], 'default_style')
        else:
            style_name = styles.get('default', None)

        # 根据几何类型添加要素
        if geom.geom_type == 'Point':
            point = folder.newpoint(name=name, description=description)
            point.coords = [(geom.x, geom.y)]

            if style_name:
                point.style = style_name

            # 设置高度模式
            if self.config['altitude_mode'] != 'clampToGround':
                point.altitudemode = self.config['altitude_mode']

        elif geom.geom_type == 'LineString':
            line = folder.newlinestring(name=name, description=description)
            line.coords = list(geom.coords)

            if style_name:
                line.style = style_name

            line.extrude = self.config['extrude']
            line.tessellate = self.config['tessellate']
            line.altitudemode = self.config['altitude_mode']

        elif geom.geom_type == 'Polygon':
            polygon = folder.newpolygon(name=name, description=description)

            # 外环坐标
            exterior_coords = list(geom.exterior.coords)
            polygon.outerboundaryis = exterior_coords

            # 内环坐标（如果有）
            if hasattr(geom, 'interiors'):
                for interior in geom.interiors:
                    polygon.innerboundaryis = list(interior.coords)

            if style_name:
                polygon.style = style_name

            polygon.extrude = self.config['extrude']
            polygon.tessellate = self.config['tessellate']
            polygon.altitudemode = self.config['altitude_mode']

        # 添加时间戳
        if self.config['include_timestamps'] and self.config['timestamp_field'] and self.config['timestamp_field'] in row:
            timestamp = row[self.config['timestamp_field']]
            if pd.notna(timestamp):
                if hasattr(point, 'timestamp'):
                    point.timestamp.when = timestamp

    def _sanitize_filename(self, filename: str) -> str:
        """
        清理文件名，移除非法字符

        Args:
            filename: 原始文件名

        Returns:
            str: 清理后的文件名
        """
        import re
        # 移除或替换非法字符
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # 移除开头和结尾的空格和点
        sanitized = sanitized.strip(' .')

        # 确保文件名不为空
        if not sanitized:
            sanitized = 'exported_data'

        return sanitized