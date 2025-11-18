"""
CSV格式导出器

支持将GeoDataFrame和DataFrame导出为CSV格式，包含几何信息
的转换、属性字段处理、编码设置等功能。

特点:
- 自动处理几何信息（坐标、WKT等）
- 支持多种编码格式
- 灵活的分隔符配置
- 大数据集分块导出
- 空值处理策略
- 数据类型优化

作者: GIS空间关联系统开发团队
"""

import os
import csv
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon
from shapely import wkt

logger = logging.getLogger(__name__)


class CSVExporter:
    """
    CSV格式导出器

    将GeoDataFrame或DataFrame导出为CSV格式，支持几何信息的
    多种表示方式。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化CSV导出器

        Args:
            config: 导出配置
        """
        self.config = config or {}

        # CSV默认配置
        self.default_config = {
            'encoding': 'utf-8-sig',  # 支持BOM以便Excel正确显示中文
            'separator': ',',
            'decimal': '.',
            'geometry_representation': 'auto',  # 'auto', 'coordinates', 'wkt', 'wkb', 'none'
            'include_geometry_type': True,
            'include_area': False,
            'include_length': False,
            'coordinate_precision': 6,
            'null_value': '',
            'date_format': '%Y-%m-%d %H:%M:%S',
            'batch_size': 100000,  # 大数据集分块大小
            'quote_character': '"',
            'escape_character': '\\',
            'line_terminator': '\n'
        }

        # 合并配置
        self.config = {**self.default_config, **self.config}

        # 支持的数据类型
        self.supported_data_types = ['GeoDataFrame', 'DataFrame']

        # 文件扩展名
        self.file_extension = '.csv'

        # 描述
        self.description = 'CSV格式导出器'

    def export(self,
              dataset_data: Union[gpd.GeoDataFrame, pd.DataFrame],
              dataset_name: str,
              output_dir: str) -> Optional[str]:
        """
        导出数据到CSV格式

        Args:
            dataset_data: 要导出的GeoDataFrame或DataFrame
            dataset_name: 数据集名称
            output_dir: 输出目录

        Returns:
            Optional[str]: 导出文件路径，失败返回None
        """
        try:
            logger.info(f"开始导出 {dataset_name} 到CSV格式...")

            # 验证输入数据
            if not isinstance(dataset_data, (gpd.GeoDataFrame, pd.DataFrame)):
                raise ValueError("CSV导出需要GeoDataFrame或DataFrame数据")

            if dataset_data.empty:
                logger.warning(f"数据集 {dataset_name} 为空，跳过导出")
                return None

            # 准备数据
            prepared_df = self._prepare_csv_data(dataset_data)

            # 生成输出文件路径
            base_name = self._sanitize_filename(dataset_name)
            output_path = Path(output_dir) / f"{base_name}.csv"

            # 检查文件是否已存在
            if output_path.exists():
                if self.config.get('overwrite', True):
                    output_path.unlink()
                else:
                    raise FileExistsError(f"CSV文件已存在: {output_path}")

            # 导出数据
            if len(prepared_df) > self.config['batch_size']:
                return self._export_large_dataset(prepared_df, output_path)
            else:
                return self._export_single_file(prepared_df, output_path)

        except Exception as e:
            logger.error(f"❌ CSV导出失败: {str(e)}")
            return None

    def get_output_path(self, dataset_name: str, output_dir: Path) -> Optional[Path]:
        """获取输出文件路径"""
        base_name = self._sanitize_filename(dataset_name)
        return output_dir / f"{base_name}.csv"

    def _prepare_csv_data(self, df: Union[gpd.GeoDataFrame, pd.DataFrame]) -> pd.DataFrame:
        """
        准备CSV数据

        Args:
            df: 原始DataFrame或GeoDataFrame

        Returns:
            pd.DataFrame: 准备好的DataFrame
        """
        # 创建副本以避免修改原始数据
        prepared_df = df.copy()

        # 重置索引
        prepared_df = prepared_df.reset_index(drop=True)

        # 处理几何信息
        if isinstance(df, gpd.GeoDataFrame):
            prepared_df = self._process_geometry_columns(prepared_df)

        # 清理属性数据
        prepared_df = self._clean_attribute_data(prepared_df)

        return prepared_df

    def _process_geometry_columns(self, gdf: gpd.GeoDataFrame) -> pd.DataFrame:
        """
        处理几何列

        Args:
            gdf: GeoDataFrame

        Returns:
            pd.DataFrame: 处理后的DataFrame
        """
        # 移除原始几何列
        df = gdf.drop('geometry', axis=1)

        # 根据配置处理几何信息
        geometry_representation = self.config['geometry_representation']

        if geometry_representation == 'none':
            # 不包含几何信息
            pass
        elif geometry_representation == 'auto':
            # 自动选择最佳表示方式
            df = self._auto_geometry_representation(gdf, df)
        elif geometry_representation == 'coordinates':
            # 添加坐标信息
            df = self._add_coordinate_columns(gdf, df)
        elif geometry_representation == 'wkt':
            # 添加WKT表示
            df = self._add_wkt_column(gdf, df)
        elif geometry_representation == 'wkb':
            # 添加WKB表示
            df = self._add_wkb_column(gdf, df)

        # 添加几何类型
        if self.config['include_geometry_type']:
            df['geometry_type'] = gdf.geometry.geom_type

        # 添加面积和长度信息
        if self.config['include_area']:
            df['geometry_area'] = gdf.geometry.area

        if self.config['include_length']:
            df['geometry_length'] = gdf.geometry.length

        return df

    def _auto_geometry_representation(self, gdf: gpd.GeoDataFrame, df: pd.DataFrame) -> pd.DataFrame:
        """
        自动选择几何信息表示方式

        Args:
            gdf: GeoDataFrame
            df: DataFrame

        Returns:
            pd.DataFrame: 处理后的DataFrame
        """
        # 获取主要几何类型
        geom_type = gdf.geometry.geom_type.iloc[0] if len(gdf) > 0 else None

        if geom_type == 'Point':
            # 点类型使用坐标
            df = self._add_coordinate_columns(gdf, df)
        elif geom_type in ['LineString', 'MultiLineString']:
            # 线类型使用WKT
            df = self._add_wkt_column(gdf, df)
        elif geom_type in ['Polygon', 'MultiPolygon']:
            # 面类型使用WKT
            df = self._add_wkt_column(gdf, df)
        else:
            # 其他类型使用WKT
            df = self._add_wkt_column(gdf, df)

        return df

    def _add_coordinate_columns(self, gdf: gpd.GeoDataFrame, df: pd.DataFrame) -> pd.DataFrame:
        """
        添加坐标列（适用于点几何）

        Args:
            gdf: GeoDataFrame
            df: DataFrame

        Returns:
            pd.DataFrame: 添加坐标列的DataFrame
        """
        # 确保使用WGS84坐标系
        if gdf.crs != 'EPSG:4326' and gdf.crs is not None:
            gdf_wgs84 = gdf.to_crs('EPSG:4326')
        else:
            gdf_wgs84 = gdf

        # 添加坐标列
        precision = self.config['coordinate_precision']

        df['longitude'] = gdf_wgs84.geometry.x.round(precision)
        df['latitude'] = gdf_wgs84.geometry.y.round(precision)

        # 如果有Z坐标，也添加
        if gdf_wgs84.geometry.has_z.any():
            df['elevation'] = gdf_wgs84.geometry.z.round(precision)

        return df

    def _add_wkt_column(self, gdf: gpd.GeoDataFrame, df: pd.DataFrame) -> pd.DataFrame:
        """
        添加WKT列

        Args:
            gdf: GeoDataFrame
            df: DataFrame

        Returns:
            pd.DataFrame: 添加WKT列的DataFrame
        """
        df['geometry_wkt'] = gdf.geometry.to_wkt()
        return df

    def _add_wkb_column(self, gdf: gpd.GeoDataFrame, df: pd.DataFrame) -> pd.DataFrame:
        """
        添加WKB列

        Args:
            gdf: GeoDataFrame
            df: DataFrame

        Returns:
            pd.DataFrame: 添加WKB列的DataFrame
        """
        df['geometry_wkb'] = gdf.geometry.to_wkb()
        return df

    def _clean_attribute_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        清理属性数据

        Args:
            df: DataFrame

        Returns:
            pd.DataFrame: 清理后的DataFrame
        """
        for col in df.columns:
            # 处理空值
            null_value = self.config['null_value']
            df[col] = df[col].fillna(null_value)

            # 处理日期时间
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.strftime(self.config['date_format'])

            # 处理复杂数据类型
            elif df[col].dtype == 'object':
                # 检查是否包含复杂数据
                for idx, value in df[col].items():
                    if isinstance(value, (list, dict, tuple)):
                        # 转换为JSON字符串
                        df.at[idx, col] = self._convert_to_json_string(value)
                    elif pd.isna(value):
                        df.at[idx, col] = null_value

        return df

    def _convert_to_json_string(self, value) -> str:
        """
        将复杂值转换为JSON字符串

        Args:
            value: 要转换的值

        Returns:
            str: JSON字符串
        """
        import json
        try:
            return json.dumps(value, ensure_ascii=False, separators=(',', ':'))
        except Exception:
            return str(value)

    def _export_single_file(self, df: pd.DataFrame, output_path: Path) -> Optional[str]:
        """
        导出单个CSV文件

        Args:
            df: DataFrame
            output_path: 输出路径

        Returns:
            Optional[str]: 导出文件路径
        """
        try:
            # 构建CSV参数
            csv_params = {
                'sep': self.config['separator'],
                'encoding': self.config['encoding'],
                'index': False,
                'quoting': csv.QUOTE_NONNUMERIC if self.config['quote_character'] == '"' else csv.QUOTE_MINIMAL,
                'quotechar': self.config['quote_character'],
                'line_terminator': self.config['line_terminator'],
                'na_rep': self.config['null_value']
            }

            # 添加小数分隔符
            if self.config['decimal'] != '.':
                # pandas没有直接支持小数分隔符的参数，需要在导出后处理
                csv_params['float_format'] = lambda x: str(x).replace('.', self.config['decimal'])

            # 导出文件
            df.to_csv(output_path, **csv_params)

            # 如果需要处理小数分隔符，重新写入文件
            if self.config['decimal'] != '.':
                self._fix_decimal_separator(output_path)

            logger.info(f"✅ CSV导出成功: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"单个文件导出失败: {str(e)}")
            return None

    def _export_large_dataset(self, df: pd.DataFrame, output_path: Path) -> Optional[str]:
        """
        分块导出大数据集

        Args:
            df: DataFrame
            output_path: 输出路径

        Returns:
            Optional[str]: 导出文件路径
        """
        try:
            batch_size = self.config['batch_size']
            total_rows = len(df)
            num_batches = (total_rows + batch_size - 1) // batch_size

            logger.info(f"大数据集分块导出，共 {num_batches} 批，每批 {batch_size} 条记录")

            # 首先写入头部
            with open(output_path, 'w', encoding=self.config['encoding'], newline='') as f:
                writer = csv.writer(f,
                                  delimiter=self.config['separator'],
                                  quotechar=self.config['quote_character'],
                                  lineterminator=self.config['line_terminator'])

                # 写入列名
                writer.writerow(df.columns)

            # 分块写入数据
            for i in range(num_batches):
                start_idx = i * batch_size
                end_idx = min((i + 1) * batch_size, total_rows)
                batch_df = df.iloc[start_idx:end_idx]

                # 追加到文件
                batch_df.to_csv(output_path,
                              mode='a',
                              header=False,
                              sep=self.config['separator'],
                              encoding=self.config['encoding'],
                              index=False,
                              quotechar=self.config['quote_character'],
                              lineterminator=self.config['line_terminator'],
                              na_rep=self.config['null_value'])

                logger.info(f"  已导出第 {i+1}/{num_batches} 批")

            logger.info(f"✅ 大数据集分块导出完成: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"大数据集分块导出失败: {str(e)}")
            return None

    def _fix_decimal_separator(self, file_path: Path) -> None:
        """
        修复小数分隔符

        Args:
            file_path: 文件路径
        """
        try:
            with open(file_path, 'r', encoding=self.config['encoding']) as f:
                content = f.read()

            # 替换小数点
            content = content.replace('.', self.config['decimal'])

            with open(file_path, 'w', encoding=self.config['encoding']) as f:
                f.write(content)

        except Exception as e:
            logger.warning(f"修复小数分隔符失败: {str(e)}")

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

    def get_csv_info(self, file_path: Path) -> Dict[str, Any]:
        """
        获取CSV文件信息

        Args:
            file_path: CSV文件路径

        Returns:
            Dict[str, Any]: 文件信息
        """
        try:
            # 快速获取文件信息
            info = {
                'file_path': str(file_path),
                'file_size': file_path.stat().st_size,
                'row_count': 0,
                'column_count': 0,
                'columns': [],
                'encoding': self.config['encoding'],
                'separator': self.config['separator']
            }

            # 读取文件头部获取列信息
            with open(file_path, 'r', encoding=self.config['encoding']) as f:
                reader = csv.reader(f, delimiter=self.config['separator'])
                headers = next(reader)
                info['column_count'] = len(headers)
                info['columns'] = headers

                # 计算行数（近似）
                for i, line in enumerate(f):
                    pass
                info['row_count'] = i + 1 if i > 0 else 0

            return info

        except Exception as e:
            logger.error(f"获取CSV文件信息失败: {str(e)}")
            return {}