"""
Shapefile格式导出器

支持将GeoDataFrame导出为ESRI Shapefile格式，包含字段名处理、
数据类型转换、投影文件创建等功能。

特点:
- 自动处理字段名长度限制（10字符）
- 数据类型自动转换以符合Shapefile规范
- 创建.prj投影文件
- 支持UTF-8编码
- 处理大数据集的分块导出

作者: GIS空间关联系统开发团队
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon

logger = logging.getLogger(__name__)


class ShapefileExporter:
    """
    Shapefile格式导出器

    将GeoDataFrame导出为ESRI Shapefile格式，处理Shapefile的
    各种限制和要求。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化Shapefile导出器

        Args:
            config: 导出配置
        """
        self.config = config or {}

        # Shapefile默认配置
        self.default_config = {
            'encoding': 'utf-8',
            'field_name_strategy': 'truncate',  # 'truncate', 'prefix', 'hash'
            'auto_convert_types': True,
            'create_projection_file': True,
            'handle_large_datasets': True,
            'max_field_length': 10,
            'max_string_length': 254,
            'batch_size': 50000,  # 大数据集分批大小
            'validate_geometry': True,
            'fix_invalid_geometry': True
        }

        # 合并配置
        self.config = {**self.default_config, **self.config}

        # 支持的数据类型
        self.supported_data_types = ['GeoDataFrame']

        # 文件扩展名
        self.file_extension = '.shp'

        # 描述
        self.description = 'ESRI Shapefile格式导出器'

        # 字段名冲突计数器
        self.field_name_counters = {}

    def export(self,
              dataset_data: gpd.GeoDataFrame,
              dataset_name: str,
              output_dir: str) -> Optional[str]:
        """
        导出GeoDataFrame到Shapefile格式

        Args:
            dataset_data: 要导出的GeoDataFrame
            dataset_name: 数据集名称
            output_dir: 输出目录

        Returns:
            Optional[str]: 导出文件路径，失败返回None
        """
        try:
            logger.info(f"开始导出 {dataset_name} 到Shapefile格式...")

            # 验证输入数据
            if not isinstance(dataset_data, gpd.GeoDataFrame):
                raise ValueError("Shapefile导出需要GeoDataFrame数据")

            if dataset_data.empty:
                logger.warning(f"数据集 {dataset_name} 为空，跳过导出")
                return None

            # 验证几何数据
            if self.config['validate_geometry']:
                validation_result = self._validate_geometry(dataset_data)
                if not validation_result['valid']:
                    raise ValueError(f"几何数据验证失败: {validation_result['errors']}")

                if validation_result['invalid_count'] > 0 and self.config['fix_invalid_geometry']:
                    dataset_data = self._fix_invalid_geometry(dataset_data)

            # 准备数据
            prepared_gdf = self._prepare_shapefile_data(dataset_data)

            # 生成输出文件路径
            base_name = self._sanitize_filename(dataset_name)
            output_path = Path(output_dir) / f"{base_name}.shp"

            # 检查文件是否已存在
            if output_path.exists():
                if self.config.get('overwrite', True):
                    # 删除现有文件
                    self._remove_shapefile_files(output_path)
                else:
                    raise FileExistsError(f"Shapefile文件已存在: {output_path}")

            # 处理大数据集
            if self.config['handle_large_datasets'] and len(prepared_gdf) > self.config['batch_size']:
                return self._export_large_dataset(prepared_gdf, output_path)

            # 导出数据
            prepared_gdf.to_file(
                output_path,
                driver='ESRI Shapefile',
                encoding=self.config['encoding']
            )

            # 创建投影文件
            if self.config['create_projection_file']:
                self._create_projection_file(prepared_gdf, output_path)

            # 验证导出结果
            if not self._validate_export(output_path):
                raise RuntimeError("Shapefile导出验证失败")

            logger.info(f"✅ Shapefile导出成功: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"❌ Shapefile导出失败: {str(e)}")
            return None

    def get_output_path(self, dataset_name: str, output_dir: Path) -> Optional[Path]:
        """获取输出文件路径"""
        base_name = self._sanitize_filename(dataset_name)
        return output_dir / f"{base_name}.shp"

    def _prepare_shapefile_data(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        准备Shapefile数据

        Args:
            gdf: 原始GeoDataFrame

        Returns:
            gpd.GeoDataFrame: 准备好的GeoDataFrame
        """
        # 创建副本以避免修改原始数据
        prepared_gdf = gdf.copy()

        # 重置索引（Shapefile可能不支持复杂的索引）
        prepared_gdf = prepared_gdf.reset_index(drop=True)

        # 处理字段名
        prepared_gdf = self._process_field_names(prepared_gdf)

        # 转换数据类型
        if self.config['auto_convert_types']:
            prepared_gdf = self._convert_data_types(prepared_gdf)

        # 处理空值
        prepared_gdf = self._handle_null_values(prepared_gdf)

        return prepared_gdf

    def _process_field_names(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        处理字段名以符合Shapefile规范

        Args:
            gdf: GeoDataFrame

        Returns:
            gpd.GeoDataFrame: 处理字段名后的GeoDataFrame
        """
        max_length = self.config['max_field_length']
        strategy = self.config['field_name_strategy']

        column_mapping = {}
        self.field_name_counters.clear()

        for col in gdf.columns:
            if col == 'geometry':
                continue

            # 根据策略处理字段名
            new_name = self._process_single_field_name(col, max_length, strategy)

            # 确保新名称唯一
            final_name = self._ensure_unique_field_name(new_name, column_mapping)

            if final_name != col:
                column_mapping[col] = final_name

        if column_mapping:
            logger.info(f"重命名字段: {column_mapping}")
            gdf = gdf.rename(columns=column_mapping)

        return gdf

    def _process_single_field_name(self, field_name: str, max_length: int, strategy: str) -> str:
        """处理单个字段名"""
        # 清理字段名：移除特殊字符，只保留字母、数字和下划线
        clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', field_name)

        # 确保以字母开头
        if clean_name and not clean_name[0].isalpha():
            clean_name = 'f_' + clean_name

        # 处理长度限制
        if len(clean_name) <= max_length:
            return clean_name

        if strategy == 'truncate':
            return clean_name[:max_length]
        elif strategy == 'prefix':
            # 保留前缀和后缀
            prefix_len = max_length // 2
            suffix_len = max_length - prefix_len - 1
            return clean_name[:prefix_len] + '_' + clean_name[-suffix_len:]
        elif strategy == 'hash':
            # 使用哈希值
            import hashlib
            hash_obj = hashlib.md5(clean_name.encode())
            return clean_name[:max_length-8] + hash_obj.hexdigest()[:8]
        else:
            return clean_name[:max_length]

    def _ensure_unique_field_name(self, proposed_name: str, existing_mapping: Dict[str, str]) -> str:
        """确保字段名唯一"""
        if proposed_name not in existing_mapping.values():
            return proposed_name

        # 添加数字后缀
        counter = 1
        while True:
            candidate_name = f"{proposed_name[:8]}{counter:02d}"
            if candidate_name not in existing_mapping.values():
                return candidate_name
            counter += 1

    def _convert_data_types(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        转换数据类型以符合Shapefile规范

        Args:
            gdf: GeoDataFrame

        Returns:
            gpd.GeoDataFrame: 数据类型转换后的GeoDataFrame
        """
        for col in gdf.columns:
            if col == 'geometry':
                continue

            # 处理整数类型
            if gdf[col].dtype == 'int64':
                # 转换为int32以节省空间
                try:
                    gdf[col] = gdf[col].astype('int32')
                except OverflowError:
                    # 如果值太大，转换为字符串
                    gdf[col] = gdf[col].astype(str)
                    logger.warning(f"字段 {col} 的整数值过大，已转换为字符串")

            elif gdf[col].dtype == 'int32':
                # 已经是合适的类型
                pass

            # 处理浮点数类型
            elif gdf[col].dtype == 'float64':
                # 转换为float32
                gdf[col] = gdf[col].astype('float32')

            elif gdf[col].dtype == 'float32':
                # 已经是合适的类型
                pass

            # 处理字符串类型
            elif gdf[col].dtype == 'object':
                # 转换为字符串并限制长度
                max_length = self.config['max_string_length']
                gdf[col] = gdf[col].astype(str).str.slice(0, max_length)

            # 处理布尔类型
            elif gdf[col].dtype == 'bool':
                # 转换为字符串
                gdf[col] = gdf[col].astype(str)

            # 处理日期时间类型
            elif pd.api.types.is_datetime64_any_dtype(gdf[col]):
                # 转换为字符串格式
                gdf[col] = gdf[col].dt.strftime('%Y-%m-%d %H:%M:%S')

        return gdf

    def _handle_null_values(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        处理空值

        Args:
            gdf: GeoDataFrame

        Returns:
            gpd.GeoDataFrame: 处理空值后的GeoDataFrame
        """
        for col in gdf.columns:
            if col == 'geometry':
                continue

            # 根据数据类型填充空值
            if pd.api.types.is_numeric_dtype(gdf[col]):
                # 数值类型填充0
                gdf[col] = gdf[col].fillna(0)
            else:
                # 其他类型填充空字符串
                gdf[col] = gdf[col].fillna('')

        return gdf

    def _validate_geometry(self, gdf: gpd.GeoDataFrame) -> Dict[str, Any]:
        """
        验证几何数据

        Args:
            gdf: GeoDataFrame

        Returns:
            Dict[str, Any]: 验证结果
        """
        validation_result = {
            'valid': True,
            'errors': [],
            'invalid_count': 0,
            'valid_count': 0
        }

        # 检查几何列是否存在
        if 'geometry' not in gdf.columns:
            validation_result['valid'] = False
            validation_result['errors'].append("缺少geometry列")
            return validation_result

        # 检查空几何
        null_geometries = gdf['geometry'].isnull().sum()
        if null_geometries > 0:
            validation_result['errors'].append(f"发现 {null_geometries} 个空几何")
            validation_result['valid'] = False

        # 检查无效几何
        invalid_geometries = not gdf['geometry'].is_valid.sum()
        if invalid_geometries > 0:
            validation_result['invalid_count'] = invalid_geometries
            logger.warning(f"发现 {invalid_geometries} 个无效几何")

        validation_result['valid_count'] = len(gdf) - invalid_geometries

        return validation_result

    def _fix_invalid_geometry(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        修复无效几何

        Args:
            gdf: GeoDataFrame

        Returns:
            gpd.GeoDataFrame: 修复后的GeoDataFrame
        """
        logger.info("尝试修复无效几何...")

        # 使用缓冲区方法修复几何
        fixed_geometries = gdf['geometry'].buffer(0)

        # 检查修复结果
        still_invalid = not fixed_geometries.is_valid.sum()

        if still_invalid == 0:
            gdf['geometry'] = fixed_geometries
            logger.info("✅ 所有无效几何已修复")
        else:
            logger.warning(f"仍有 {still_invalid} 个几何无法修复")

        return gdf

    def _export_large_dataset(self, gdf: gpd.GeoDataFrame, output_path: Path) -> Optional[str]:
        """
        分批导出大数据集

        Args:
            gdf: GeoDataFrame
            output_path: 输出路径

        Returns:
            Optional[str]: 导出文件路径
        """
        batch_size = self.config['batch_size']
        total_rows = len(gdf)
        num_batches = (total_rows + batch_size - 1) // batch_size

        logger.info(f"大数据集分批导出，共 {num_batches} 批，每批 {batch_size} 条记录")

        try:
            # 创建第一个批次
            first_batch = gdf.iloc[:batch_size]
            first_batch.to_file(
                output_path,
                driver='ESRI Shapefile',
                encoding=self.config['encoding']
            )

            # 追加其他批次
            for i in range(1, num_batches):
                start_idx = i * batch_size
                end_idx = min((i + 1) * batch_size, total_rows)
                batch = gdf.iloc[start_idx:end_idx]

                batch.to_file(
                    output_path,
                    driver='ESRI Shapefile',
                    encoding=self.config['encoding'],
                    mode='a'  # 追加模式
                )

                logger.info(f"  已导出第 {i+1}/{num_batches} 批")

            logger.info(f"✅ 大数据集分批导出完成: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"大数据集分批导出失败: {str(e)}")
            return None

    def _create_projection_file(self, gdf: gpd.GeoDataFrame, shp_path: Path) -> None:
        """
        创建.prj投影文件

        Args:
            gdf: GeoDataFrame
            shp_path: Shapefile文件路径
        """
        try:
            if gdf.crs is not None:
                prj_path = shp_path.with_suffix('.prj')
                with open(prj_path, 'w', encoding='utf-8') as f:
                    f.write(gdf.crs.to_wkt())
                logger.debug(f"已创建投影文件: {prj_path}")
            else:
                logger.warning("数据没有坐标参考系统，跳过投影文件创建")

        except Exception as e:
            logger.error(f"创建投影文件失败: {str(e)}")

    def _remove_shapefile_files(self, shp_path: Path) -> None:
        """
        删除Shapefile相关文件

        Args:
            shp_path: Shapefile文件路径
        """
        shapefile_extensions = ['.shp', '.shx', '.dbf', '.prj', '.cpg', '.sbx', '.sbn']

        for ext in shapefile_extensions:
            file_path = shp_path.with_suffix(ext)
            if file_path.exists():
                file_path.unlink()

    def _validate_export(self, shp_path: Path) -> bool:
        """
        验证导出结果

        Args:
            shp_path: Shapefile文件路径

        Returns:
            bool: 验证是否通过
        """
        try:
            # 检查必要文件是否存在
            required_files = [
                shp_path,  # .shp
                shp_path.with_suffix('.shx'),  # .shx
                shp_path.with_suffix('.dbf')   # .dbf
            ]

            for file_path in required_files:
                if not file_path.exists():
                    logger.error(f"缺少必要文件: {file_path}")
                    return False

            # 尝试读取导出的文件
            try:
                test_gdf = gpd.read_file(shp_path)
                logger.info(f"导出验证成功，包含 {len(test_gdf)} 条记录")
                return True

            except Exception as e:
                logger.error(f"无法读取导出的Shapefile: {str(e)}")
                return False

        except Exception as e:
            logger.error(f"导出验证过程中发生错误: {str(e)}")
            return False

    def _sanitize_filename(self, filename: str) -> str:
        """
        清理文件名，移除非法字符

        Args:
            filename: 原始文件名

        Returns:
            str: 清理后的文件名
        """
        # 移除或替换非法字符
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # 移除开头和结尾的空格和点
        sanitized = sanitized.strip(' .')

        # 确保文件名不为空
        if not sanitized:
            sanitized = 'exported_data'

        return sanitized