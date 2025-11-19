"""
GeoPackage格式导出器

支持将GeoDataFrame导出为GeoPackage格式，包含多图层支持、
空间索引、元数据等功能。

特点:
- 多图层支持
- 空间索引优化
- 元数据管理
- 坐标系统保持
- 压缩存储
- 标准兼容

作者: GIS空间关联系统开发团队
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import pandas as pd
import geopandas as gpd

logger = logging.getLogger(__name__)


class GeoPackageExporter:
    """
    GeoPackage格式导出器

    将GeoDataFrame导出为OGC GeoPackage格式，支持现代GIS标准。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化GeoPackage导出器

        Args:
            config: 导出配置
        """
        self.config = config or {}

        # GeoPackage默认配置
        self.default_config = {
            'encoding': 'utf-8',
            'spatial_index': True,
            'layer_prefix': '',
            'append_to_existing': False,
            'overwrite_layer': False,
            'create_metadata': True,
            'description': '',
            'dataset_crs': None,  # None表示保持原CRS
            'geometry_type': 'auto',  # 'auto', 'POINT', 'LINESTRING', 'POLYGON', etc.
            'validate_geometries': True,
            'fix_invalid_geometries': True,
            'optimize_for_size': True,
            'compression': 'DEFLATE'  # 'NONE', 'DEFLATE'
        }

        # 合并配置
        self.config = {**self.default_config, **self.config}

        # 支持的数据类型
        self.supported_data_types = ['GeoDataFrame']

        # 文件扩展名
        self.file_extension = '.gpkg'

        # 描述
        self.description = 'GeoPackage格式导出器'

    def export(self,
              dataset_data: Union[gpd.GeoDataFrame, Dict[str, gpd.GeoDataFrame]],
              dataset_name: str,
              output_dir: str) -> Optional[str]:
        """
        导出数据到GeoPackage格式

        Args:
            dataset_data: 要导出的GeoDataFrame或数据字典
            dataset_name: 数据集名称
            output_dir: 输出目录

        Returns:
            Optional[str]: 导出文件路径，失败返回None
        """
        try:
            logger.info(f"开始导出 {dataset_name} 到GeoPackage格式...")

            # 处理输入数据
            if isinstance(dataset_data, dict):
                # 多个图层
                data_dict = dataset_data
            else:
                # 单个图层
                data_dict = {dataset_name: dataset_data}

            # 验证输入数据
            for name, gdf in data_dict.items():
                if not isinstance(gdf, gpd.GeoDataFrame):
                    raise ValueError(f"图层 {name} 不是GeoDataFrame数据")
                if gdf.empty:
                    logger.warning(f"图层 {name} 为空，跳过导出")
                    continue

            # 生成输出文件路径
            base_name = self._sanitize_filename(dataset_name)
            output_path = Path(output_dir) / f"{base_name}.gpkg"

            # 检查文件是否已存在
            if output_path.exists():
                if self.config.get('overwrite', True):
                    output_path.unlink()
                elif not self.config['append_to_existing']:
                    raise FileExistsError(f"GeoPackage文件已存在: {output_path}")

            # 创建GeoPackage文件
            return self._create_geopackage(data_dict, base_name, output_path)

        except Exception as e:
            logger.error(f"❌ GeoPackage导出失败: {str(e)}")
            return None

    def get_output_path(self, dataset_name: str, output_dir: Path) -> Optional[Path]:
        """获取输出文件路径"""
        base_name = self._sanitize_filename(dataset_name)
        return output_dir / f"{base_name}.gpkg"

    def _create_geopackage(self, data_dict: Dict[str, gpd.GeoDataFrame],
                          base_name: str, output_path: Path) -> Optional[str]:
        """
        创建GeoPackage文件

        Args:
            data_dict: 数据字典
            base_name: 基础名称
            output_path: 输出路径

        Returns:
            Optional[str]: 导出文件路径
        """
        try:
            # 处理每个图层
            for layer_name, gdf in data_dict.items():
                if gdf.empty:
                    continue

                # 准备数据
                prepared_gdf = self._prepare_geopackage_data(gdf, layer_name)

                # 生成图层名称
                gpkg_layer_name = self._generate_layer_name(layer_name)

                # 构建导出参数
                export_params = {
                    'driver': 'GPKG',
                    'layer': gpkg_layer_name,
                    'encoding': self.config['encoding']
                }

                # 添加空间索引
                if self.config['spatial_index']:
                    export_params['SPATIAL_INDEX'] = 'YES'

                # 坐标系统处理
                if self.config['dataset_crs']:
                    prepared_gdf = prepared_gdf.to_crs(self.config['dataset_crs'])

                # 几何类型设置
                if self.config['geometry_type'] != 'auto':
                    export_params['GEOMETRY_TYPE'] = self.config['geometry_type']

                # 确定写入模式
                if output_path.exists() and self.config['append_to_existing']:
                    export_params['mode'] = 'a'  # 追加模式
                else:
                    export_params['mode'] = 'w'  # 写入模式

                # 导出数据
                prepared_gdf.to_file(output_path, **export_params)

                logger.info(f"✅ 图层 {layer_name} 导出成功")

            # 添加元数据
            if self.config['create_metadata']:
                self._add_metadata(output_path, base_name, data_dict)

            logger.info(f"✅ GeoPackage导出成功: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"创建GeoPackage文件失败: {str(e)}")
            return None

    def _prepare_geopackage_data(self, gdf: gpd.GeoDataFrame, layer_name: str) -> gpd.GeoDataFrame:
        """
        准备GeoPackage数据

        Args:
            gdf: 原始GeoDataFrame
            layer_name: 图层名称

        Returns:
            gpd.GeoDataFrame: 准备好的GeoDataFrame
        """
        # 创建副本
        prepared_gdf = gdf.copy()

        # 重置索引
        prepared_gdf = prepared_gdf.reset_index(drop=True)

        # 验证几何
        if self.config['validate_geometries']:
            validation_result = self._validate_geometries(prepared_gdf)
            if not validation_result['valid']:
                if self.config['fix_invalid_geometries']:
                    prepared_gdf = self._fix_invalid_geometries(prepared_gdf)
                else:
                    logger.warning(f"图层 {layer_name} 包含无效几何")

        # 清理属性数据
        prepared_gdf = self._clean_attribute_data(prepared_gdf)

        # 处理大数据集优化
        if self.config['optimize_for_size']:
            prepared_gdf = self._optimize_for_size(prepared_gdf)

        return prepared_gdf

    def _validate_geometries(self, gdf: gpd.GeoDataFrame) -> Dict[str, Any]:
        """
        验证几何数据

        Args:
            gdf: GeoDataFrame

        Returns:
            Dict[str, Any]: 验证结果
        """
        validation_result = {
            'valid': True,
            'invalid_count': 0,
            'errors': []
        }

        # 检查几何有效性
        invalid_geoms = not gdf.geometry.is_valid
        invalid_count = invalid_geoms.sum()

        if invalid_count > 0:
            validation_result['invalid_count'] = invalid_count
            validation_result['valid'] = False
            validation_result['errors'].append(f"发现 {invalid_count} 个无效几何")

        # 检查空几何
        null_geoms = gdf.geometry.isnull()
        null_count = null_geoms.sum()

        if null_count > 0:
            validation_result['errors'].append(f"发现 {null_count} 个空几何")

        return validation_result

    def _fix_invalid_geometries(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        修复无效几何

        Args:
            gdf: GeoDataFrame

        Returns:
            gpd.GeoDataFrame: 修复后的GeoDataFrame
        """
        logger.info("尝试修复无效几何...")

        # 使用缓冲区方法修复
        fixed_geometries = gdf.geometry.buffer(0)

        # 检查修复结果
        still_invalid = not fixed_geometries.is_valid.sum()

        if still_invalid == 0:
            gdf.geometry = fixed_geometries
            logger.info("✅ 所有无效几何已修复")
        else:
            logger.warning(f"仍有 {still_invalid} 个几何无法修复")

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

            # 处理空值
            if gdf[col].isna().any():
                if pd.api.types.is_numeric_dtype(gdf[col]):
                    gdf[col] = gdf[col].fillna(0)
                else:
                    gdf[col] = gdf[col].fillna('')

            # 处理日期时间
            if pd.api.types.is_datetime64_any_dtype(gdf[col]):
                # GeoPackage支持日期时间类型
                pass

            # 处理复杂数据类型
            elif gdf[col].dtype == 'object':
                # 检查是否包含复杂数据
                for idx, value in gdf[col].items():
                    if isinstance(value, (list, dict, tuple)):
                        # 转换为JSON字符串
                        gdf.at[idx, col] = str(value)

        return gdf

    def _optimize_for_size(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        优化数据以减小文件大小

        Args:
            gdf: GeoDataFrame

        Returns:
            gpd.GeoDataFrame: 优化后的GeoDataFrame
        """
        # 优化数值类型
        for col in gdf.columns:
            if col == 'geometry':
                continue

            if pd.api.types.is_numeric_dtype(gdf[col]):
                # 尝试使用更小的数据类型
                if gdf[col].dtype == 'int64':
                    # 检查是否可以使用int32
                    min_val = gdf[col].min()
                    max_val = gdf[col].max()
                    if min_val >= -2147483648 and max_val <= 2147483647:
                        gdf[col] = gdf[col].astype('int32')

                elif gdf[col].dtype == 'float64':
                    # 转换为float32
                    gdf[col] = gdf[col].astype('float32')

        # 简化几何
        if len(gdf) > 10000:  # 大数据集才进行几何简化
            tolerance = 0.00001
            gdf.geometry = gdf.geometry.simplify(tolerance, preserve_topology=True)

        return gdf

    def _generate_layer_name(self, original_name: str) -> str:
        """
        生成符合GeoPackage规范的图层名称

        Args:
            original_name: 原始名称

        Returns:
            str: 图层名称
        """
        # 添加前缀
        layer_name = f"{self.config['layer_prefix']}{original_name}"

        # GeoPackage图层名称限制
        # 最大长度：32字符
        # 只能包含字母、数字和下划线
        import re

        # 清理名称
        layer_name = re.sub(r'[^a-zA-Z0-9_]', '_', layer_name)

        # 限制长度
        if len(layer_name) > 32:
            layer_name = layer_name[:32]

        # 确保以字母开头
        if layer_name and not layer_name[0].isalpha():
            layer_name = 'l_' + layer_name[:31]

        return layer_name or 'layer'

    def _add_metadata(self, gpkg_path: Path, dataset_name: str, data_dict: Dict[str, gpd.GeoDataFrame]):
        """
        添加元数据到GeoPackage

        Args:
            gpkg_path: GeoPackage文件路径
            dataset_name: 数据集名称
            data_dict: 数据字典
        """
        try:
            import sqlite3

            # 连接到GeoPackage数据库
            conn = sqlite3.connect(str(gpkg_path))
            cursor = conn.cursor()

            # 添加数据集元数据
            description = self.config.get('description', f'GIS空间关联分析数据集: {dataset_name}')

            cursor.execute("""
                INSERT OR REPLACE INTO gpkg_contents (
                    table_name, data_type, identifier, description,
                    last_change, min_x, min_y, max_x, max_y, srs_id
                ) VALUES (?, 'features', ?, ?, datetime('now'), NULL, NULL, NULL, NULL, NULL)
            """, (dataset_name, description))

            # 添加扩展信息
            cursor.execute("""
                INSERT OR REPLACE INTO gpkg_extensions (
                    table_name, column_name, extension_name, definition, scope
                ) VALUES (?, NULL, 'gpkg_metadata', 'GeoPackage Metadata', 'read-write')
            """, (dataset_name,))

            conn.commit()
            conn.close()

            logger.info("✅ 元数据添加成功")

        except Exception as e:
            logger.warning(f"添加元数据失败: {str(e)}")

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

    def get_geopackage_info(self, gpkg_path: Path) -> Dict[str, Any]:
        """
        获取GeoPackage文件信息

        Args:
            gpkg_path: GeoPackage文件路径

        Returns:
            Dict[str, Any]: 文件信息
        """
        try:
            import sqlite3

            info = {
                'file_path': str(gpkg_path),
                'file_size': gpkg_path.stat().st_size if gpkg_path.exists() else 0,
                'layers': [],
                'metadata': {}
            }

            if not gpkg_path.exists():
                return info

            # 连接到GeoPackage数据库
            conn = sqlite3.connect(str(gpkg_path))
            cursor = conn.cursor()

            # 获取图层信息
            cursor.execute("""
                SELECT table_name, identifier, description, srs_id
                FROM gpkg_contents
                WHERE data_type = 'features'
            """)

            layers = cursor.fetchall()
            for layer in layers:
                layer_info = {
                    'name': layer[0],
                    'identifier': layer[1],
                    'description': layer[2],
                    'srs_id': layer[3]
                }

                # 获取要素数量
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {layer[0]}")
                    count = cursor.fetchone()[0]
                    layer_info['feature_count'] = count
                except:
                    layer_info['feature_count'] = 0

                info['layers'].append(layer_info)

            conn.close()
            return info

        except Exception as e:
            logger.error(f"获取GeoPackage信息失败: {str(e)}")
            return info