"""
GeoJSON格式导出器

支持将GeoDataFrame导出为GeoJSON格式，包含坐标系统转换、
精度控制、压缩等功能。

特点:
- 自动转换为WGS84坐标系（GeoJSON标准）
- 支持几何精度控制
- JSON格式优化和美化
- 压缩输出选项
- 属性数据类型保持

作者: GIS空间关联系统开发团队
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union
import pandas as pd
import geopandas as gpd

logger = logging.getLogger(__name__)


class GeoJSONExporter:
    """
    GeoJSON格式导出器

    将GeoDataFrame导出为GeoJSON格式，符合RFC 7946标准。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化GeoJSON导出器

        Args:
            config: 导出配置
        """
        self.config = config or {}

        # GeoJSON默认配置
        self.default_config = {
            'encoding': 'utf-8',
            'force_wgs84': True,  # 强制转换为WGS84
            'precision': None,  # 坐标精度，None表示不限制
            'indent': 2,  # JSON缩进，None表示压缩
            'separate_files': False,  # 是否为不同几何类型创建单独文件
            'include_bbox': False,  # 是否包含边界框
            'include_crs': False,  # 是否包含坐标参考系统
            'optimize_json': True,  # 是否优化JSON输出
            'handle_large_geometries': True,  # 是否处理大几何对象
            'max_feature_count': None,  # 最大要素数量限制
            'pretty_print': True  # 是否美化输出
        }

        # 合并配置
        self.config = {**self.default_config, **self.config}

        # 支持的数据类型
        self.supported_data_types = ['GeoDataFrame']

        # 文件扩展名
        self.file_extension = '.geojson'

        # 描述
        self.description = 'GeoJSON格式导出器'

    def export(self,
              dataset_data: gpd.GeoDataFrame,
              dataset_name: str,
              output_dir: str) -> Optional[str]:
        """
        导出GeoDataFrame到GeoJSON格式

        Args:
            dataset_data: 要导出的GeoDataFrame
            dataset_name: 数据集名称
            output_dir: 输出目录

        Returns:
            Optional[str]: 导出文件路径，失败返回None
        """
        try:
            logger.info(f"开始导出 {dataset_name} 到GeoJSON格式...")

            # 验证输入数据
            if not isinstance(dataset_data, gpd.GeoDataFrame):
                raise ValueError("GeoJSON导出需要GeoDataFrame数据")

            if dataset_data.empty:
                logger.warning(f"数据集 {dataset_name} 为空，跳过导出")
                return None

            # 准备数据
            prepared_gdf = self._prepare_geojson_data(dataset_data)

            # 生成输出文件路径
            base_name = self._sanitize_filename(dataset_name)
            output_path = Path(output_dir) / f"{base_name}.geojson"

            # 检查文件是否已存在
            if output_path.exists():
                if self.config.get('overwrite', True):
                    output_path.unlink()
                else:
                    raise FileExistsError(f"GeoJSON文件已存在: {output_path}")

            # 导出数据
            if self.config['separate_files']:
                exported_files = self._export_separate_files(prepared_gdf, base_name, output_dir)
                return exported_files[0] if exported_files else None
            else:
                return self._export_single_file(prepared_gdf, output_path)

        except Exception as e:
            logger.error(f"❌ GeoJSON导出失败: {str(e)}")
            return None

    def get_output_path(self, dataset_name: str, output_dir: Path) -> Optional[Path]:
        """获取输出文件路径"""
        base_name = self._sanitize_filename(dataset_name)
        return output_dir / f"{base_name}.geojson"

    def _prepare_geojson_data(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        准备GeoJSON数据

        Args:
            gdf: 原始GeoDataFrame

        Returns:
            gpd.GeoDataFrame: 准备好的GeoDataFrame
        """
        # 创建副本以避免修改原始数据
        prepared_gdf = gdf.copy()

        # 重置索引
        prepared_gdf = prepared_gdf.reset_index(drop=True)

        # 坐标系统转换
        if self.config['force_wgs84']:
            prepared_gdf = self._convert_to_wgs84(prepared_gdf)

        # 处理大几何对象
        if self.config['handle_large_geometries']:
            prepared_gdf = self._handle_large_geometries(prepared_gdf)

        # 处理要素数量限制
        if self.config['max_feature_count']:
            max_count = self.config['max_feature_count']
            if len(prepared_gdf) > max_count:
                prepared_gdf = prepared_gdf.head(max_count)
                logger.warning(f"数据集被截断到 {max_count} 个要素")

        # 清理属性数据
        prepared_gdf = self._clean_attribute_data(prepared_gdf)

        return prepared_gdf

    def _convert_to_wgs84(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        转换坐标系统到WGS84

        Args:
            gdf: GeoDataFrame

        Returns:
            gpd.GeoDataFrame: 转换后的GeoDataFrame
        """
        if gdf.crs is None:
            logger.warning("数据没有坐标参考系统，假设为WGS84")
            # 创建WGS84坐标系
            gdf.crs = 'EPSG:4326'
        elif gdf.crs != 'EPSG:4326':
            logger.info(f"将坐标系从 {gdf.crs} 转换为 WGS84")
            gdf = gdf.to_crs('EPSG:4326')

        return gdf

    def _handle_large_geometries(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        处理大几何对象

        Args:
            gdf: GeoDataFrame

        Returns:
            gpd.GeoDataFrame: 处理后的GeoDataFrame
        """
        # 简化几何对象以减少文件大小
        tolerance = 0.00001  # 简化容差

        for idx, row in gdf.iterrows():
            geom = row.geometry

            # 检查几何复杂度
            if hasattr(geom, 'geom_type'):
                if geom.geom_type in ['Polygon', 'MultiPolygon']:
                    # 计算顶点数量
                    if hasattr(geom, 'exterior'):
                        num_vertices = len(geom.exterior.coords)
                    elif hasattr(geom, 'geoms'):
                        num_vertices = sum(len(part.exterior.coords) for part in geom.geoms)
                    else:
                        num_vertices = 0

                    # 如果顶点数量过多，进行简化
                    if num_vertices > 1000:
                        simplified_geom = geom.simplify(tolerance, preserve_topology=True)
                        gdf.at[idx, 'geometry'] = simplified_geom
                        logger.debug(f"简化几何对象，顶点数: {num_vertices} -> {len(simplified_geom.exterior.coords) if hasattr(simplified_geom, 'exterior') else 0}")

        return gdf

    def _clean_attribute_data(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        清理属性数据

        Args:
            gdf: GeoDataFrame

        Returns:
            gpd.GeoDataFrame: 清理后的GeoDataFrame
        """
        for col in gdf.columns:
            if col == 'geometry':
                continue

            # 处理NaN值
            if gdf[col].isna().any():
                if pd.api.types.is_numeric_dtype(gdf[col]):
                    gdf[col] = gdf[col].fillna(0)
                else:
                    gdf[col] = gdf[col].fillna('')

            # 处理数据类型
            if pd.api.types.is_datetime64_any_dtype(gdf[col]):
                # 将日期时间转换为ISO格式字符串
                gdf[col] = gdf[col].dt.strftime('%Y-%m-%dT%H:%M:%SZ')

            # 处理复杂对象
            elif gdf[col].dtype == 'object':
                # 检查是否为复杂对象（列表、字典等）
                for idx, value in gdf[col].items():
                    if isinstance(value, (list, dict, tuple)):
                        # 转换为JSON字符串
                        gdf.at[idx, col] = json.dumps(value, ensure_ascii=False)

        return gdf

    def _export_single_file(self, gdf: gpd.GeoDataFrame, output_path: Path) -> Optional[str]:
        """
        导出单个GeoJSON文件

        Args:
            gdf: GeoDataFrame
            output_path: 输出路径

        Returns:
            Optional[str]: 导出文件路径
        """
        try:
            # 构建GeoJSON参数
            geojson_params = {
                'driver': 'GeoJSON',
                'encoding': self.config['encoding']
            }

            # 添加精度控制
            if self.config['precision'] is not None:
                geojson_params['precision'] = self.config['precision']

            # 导出文件
            gdf.to_file(output_path, **geojson_params)

            # 优化JSON输出
            if self.config['optimize_json'] or self.config['pretty_print']:
                self._optimize_json_output(output_path)

            logger.info(f"✅ GeoJSON导出成功: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"单个文件导出失败: {str(e)}")
            return None

    def _export_separate_files(self, gdf: gpd.GeoDataFrame, base_name: str, output_dir: str) -> List[str]:
        """
        按几何类型导出单独的文件

        Args:
            gdf: GeoDataFrame
            base_name: 基础文件名
            output_dir: 输出目录

        Returns:
            List[str]: 导出文件路径列表
        """
        exported_files = []

        # 按几何类型分组
        geometry_types = gdf.geometry.geom_type.unique()

        for geom_type in geometry_types:
            if geom_type is None:
                continue

            # 筛选特定几何类型的数据
            type_gdf = gdf[gdf.geometry.geom_type == geom_type].copy()

            if type_gdf.empty:
                continue

            # 生成文件名
            type_name = geom_type.lower().replace(' ', '_')
            filename = f"{base_name}_{type_name}.geojson"
            output_path = Path(output_dir) / filename

            try:
                # 导出该几何类型的文件
                geojson_params = {
                    'driver': 'GeoJSON',
                    'encoding': self.config['encoding']
                }

                if self.config['precision'] is not None:
                    geojson_params['precision'] = self.config['precision']

                type_gdf.to_file(output_path, **geojson_params)

                # 优化JSON输出
                if self.config['optimize_json'] or self.config['pretty_print']:
                    self._optimize_json_output(output_path)

                exported_files.append(str(output_path))
                logger.info(f"✅ {geom_type} 类型导出成功: {output_path}")

            except Exception as e:
                logger.error(f"{geom_type} 类型导出失败: {str(e)}")

        return exported_files

    def _optimize_json_output(self, file_path: Path) -> None:
        """
        优化JSON输出格式

        Args:
            file_path: 文件路径
        """
        try:
            # 读取原始JSON
            with open(file_path, 'r', encoding='utf-8') as f:
                geojson_data = json.load(f)

            # 添加额外信息
            if self.config['include_bbox']:
                if 'features' in geojson_data and geojson_data['features']:
                    # 计算边界框
                    coords = []
                    for feature in geojson_data['features']:
                        if 'geometry' in feature and feature['geometry']:
                            self._extract_coordinates(feature['geometry'], coords)

                    if coords:
                        lons = [coord[0] for coord in coords]
                        lats = [coord[1] for coord in coords]
                        bbox = [min(lons), min(lats), max(lons), max(lats)]
                        geojson_data['bbox'] = bbox

            # 写入优化后的JSON
            indent = self.config['indent'] if self.config['pretty_print'] else None
            ensure_ascii = False

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(geojson_data, f, indent=indent, ensure_ascii=ensure_ascii, separators=(',', ': ') if indent else (',', ':'))

        except Exception as e:
            logger.warning(f"JSON输出优化失败: {str(e)}")

    def _extract_coordinates(self, geometry, coords_list):
        """
        递归提取几何坐标

        Args:
            geometry: 几何对象
            coords_list: 坐标列表
        """
        if isinstance(geometry, dict):
            if 'coordinates' in geometry:
                coords = geometry['coordinates']
                self._add_coords_recursive(coords, coords_list)
            elif 'geometries' in geometry:
                for geom in geometry['geometries']:
                    self._extract_coordinates(geom, coords_list)

    def _add_coords_recursive(self, coords, coords_list):
        """
        递归添加坐标到列表

        Args:
            coords: 坐标数据
            coords_list: 坐标列表
        """
        if isinstance(coords, (list, tuple)):
            if len(coords) == 2 and all(isinstance(c, (int, float)) for c in coords):
                coords_list.append(coords)
            else:
                for coord in coords:
                    self._add_coords_recursive(coord, coords_list)

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