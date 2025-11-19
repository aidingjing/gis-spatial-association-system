"""
结果数据导出框架

提供统一的导出接口，支持多种格式的同时导出，包含批量处理、
格式验证、错误处理等功能。

作者: GIS空间关联系统开发团队
"""

import os
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import pandas as pd
import geopandas as gpd

from .shapefile import ShapefileExporter
from .geojson import GeoJSONExporter
from .csv import CSVExporter
from .excel import ExcelExporter
from .kml import KMLExporter
from .geopackage import GeoPackageExporter

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ResultExporter:
    """
    结果数据导出框架

    提供统一的多格式数据导出功能，支持批量处理、格式转换、
    错误处理和进度跟踪。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化结果导出器

        Args:
            config: 导出器配置字典
        """
        self.config = config or {}

        # 初始化各种格式的导出器
        self.exporters = {
            'shapefile': ShapefileExporter(self.config.get('shapefile', {})),
            'geojson': GeoJSONExporter(self.config.get('geojson', {})),
            'csv': CSVExporter(self.config.get('csv', {})),
            'excel': ExcelExporter(self.config.get('excel', {})),
            'kml': KMLExporter(self.config.get('kml', {})),
            'geopackage': GeoPackageExporter(self.config.get('geopackage', {}))
        }

        # 支持的格式列表
        self.supported_formats = list(self.exporters.keys())

        # 默认导出配置
        self.default_export_config = {
            'formats': ['shapefile', 'geojson', 'csv'],
            'output_directory': './output',
            'create_subdirectories': True,
            'include_metadata': True,
            'compression': None,  # 'zip', 'tar', 'gzip'
            'overwrite': False,
            'validate_before_export': True,
            'generate_report': True,
            'batch_size': None,  # None表示不分批处理
            'progress_callback': None
        }

    def export_results(self,
                      results: Dict[str, Union[gpd.GeoDataFrame, pd.DataFrame, Dict]],
                      export_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        导出处理结果到多种格式

        Args:
            results: 分析结果字典
            export_config: 导出配置

        Returns:
            Dict[str, Any]: 导出结果信息
        """
        # 合并配置
        config = {**self.default_export_config, **(export_config or {})}

        logger.info("开始导出分析结果...")
        start_time = time.time()

        # 创建输出目录
        output_dir = Path(config['output_directory'])
        output_dir.mkdir(parents=True, exist_ok=True)

        # 初始化导出结果
        export_results = {
            'success': True,
            'exported_files': [],
            'failed_exports': [],
            'skipped_datasets': [],
            'summary': {},
            'errors': [],
            'warnings': [],
            'export_time': None
        }

        try:
            # 验证结果数据
            if config['validate_before_export']:
                validation_result = self._validate_export_data(results)
                if not validation_result['valid']:
                    export_results['success'] = False
                    export_results['errors'].extend(validation_result['errors'])
                    return export_results

                export_results['warnings'].extend(validation_result['warnings'])

            # 处理每个数据集
            for dataset_name, dataset_data in results.items():
                if not self._should_export_dataset(dataset_name, dataset_data, config):
                    export_results['skipped_datasets'].append(dataset_name)
                    continue

                try:
                    dataset_result = self._export_dataset(
                        dataset_name, dataset_data, config, output_dir
                    )

                    export_results['exported_files'].extend(dataset_result['files'])
                    export_results['summary'][dataset_name] = dataset_result['summary']

                    logger.info(f"✅ 成功导出数据集: {dataset_name}")

                except Exception as e:
                    error_msg = f"导出数据集 {dataset_name} 失败: {str(e)}"
                    logger.error(error_msg)
                    export_results['failed_exports'].append({
                        'dataset': dataset_name,
                        'error': str(e)
                    })
                    export_results['errors'].append(error_msg)

            # 生成导出报告
            if config.get('generate_report', True):
                report_result = self._generate_export_report(export_results, output_dir)
                if report_result:
                    export_results['report_file'] = report_result

            # 压缩导出文件
            if config.get('compression'):
                compression_result = self._compress_exports(
                    export_results['exported_files'], config['compression'], output_dir
                )
                if compression_result:
                    export_results['compressed_file'] = compression_result

            # 计算导出时间
            export_results['export_time'] = time.time() - start_time

            logger.info(f"导出完成，耗时: {export_results['export_time']:.2f}秒")

        except Exception as e:
            export_results['success'] = False
            export_results['errors'].append(f"导出过程中发生严重错误: {str(e)}")
            logger.error(f"导出过程中发生严重错误: {str(e)}")

        return export_results

    def _export_dataset(self,
                       dataset_name: str,
                       dataset_data: Union[gpd.GeoDataFrame, pd.DataFrame, Dict],
                       config: Dict[str, Any],
                       output_dir: Path) -> Dict[str, Any]:
        """
        导出单个数据集到多种格式

        Args:
            dataset_name: 数据集名称
            dataset_data: 数据集数据
            config: 导出配置
            output_dir: 输出目录

        Returns:
            Dict[str, Any]: 数据集导出结果
        """
        formats = config['formats']
        dataset_result = {
            'files': [],
            'summary': {
                'dataset_name': dataset_name,
                'formats_exported': [],
                'formats_failed': [],
                'total_files': 0,
                'total_size': 0
            }
        }

        # 创建数据集专用目录
        if config.get('create_subdirectories', True):
            dataset_dir = output_dir / dataset_name
            dataset_dir.mkdir(exist_ok=True)
        else:
            dataset_dir = output_dir

        # 分批处理大数据集
        if config.get('batch_size') and hasattr(dataset_data, '__len__'):
            if len(dataset_data) > config['batch_size']:
                dataset_data = self._process_large_dataset(dataset_data, config['batch_size'])

        # 导出到每种格式
        for format_name in formats:
            if format_name not in self.exporters:
                warning = f"不支持的导出格式: {format_name}"
                logger.warning(warning)
                continue

            try:
                exporter = self.exporters[format_name]

                # 检查是否覆盖现有文件
                if not config.get('overwrite', False):
                    existing_file = exporter.get_output_path(dataset_name, dataset_dir)
                    if existing_file and existing_file.exists():
                        warning = f"文件已存在，跳过导出: {existing_file}"
                        logger.warning(warning)
                        continue

                # 执行导出
                exported_file = exporter.export(dataset_data, dataset_name, str(dataset_dir))

                if exported_file:
                    dataset_result['files'].append(exported_file)
                    dataset_result['summary']['formats_exported'].append(format_name)

                    # 计算文件大小
                    file_size = os.path.getsize(exported_file) if os.path.exists(exported_file) else 0
                    dataset_result['summary']['total_size'] += file_size

                    logger.info(f"  ✅ 导出 {format_name} 格式: {exported_file}")
                else:
                    dataset_result['summary']['formats_failed'].append(format_name)

            except Exception as e:
                error_msg = f"导出 {format_name} 格式失败: {str(e)}"
                logger.error(f"  ❌ {error_msg}")
                dataset_result['summary']['formats_failed'].append(format_name)
                dataset_result['summary'].setdefault('errors', []).append(error_msg)

        # 更新统计信息
        dataset_result['summary']['total_files'] = len(dataset_result['files'])

        return dataset_result

    def _validate_export_data(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证导出数据

        Args:
            results: 分析结果字典

        Returns:
            Dict[str, Any]: 验证结果
        """
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }

        if not results:
            validation_result['valid'] = False
            validation_result['errors'].append("没有可导出的数据")
            return validation_result

        # 检查每个数据集
        for dataset_name, dataset_data in results.items():
            if not self._is_valid_dataset(dataset_data):
                validation_result['valid'] = False
                validation_result['errors'].append(
                    f"数据集 {dataset_name} 不是有效的GeoDataFrame或DataFrame"
                )
            elif self._is_empty_dataset(dataset_data):
                validation_result['warnings'].append(
                    f"数据集 {dataset_name} 为空，将跳过导出"
                )

        return validation_result

    def _is_valid_dataset(self, dataset_data: Any) -> bool:
        """检查数据集是否有效"""
        return isinstance(dataset_data, (gpd.GeoDataFrame, pd.DataFrame))

    def _is_empty_dataset(self, dataset_data: Any) -> bool:
        """检查数据集是否为空"""
        if hasattr(dataset_data, 'empty'):
            return dataset_data.empty
        return False

    def _should_export_dataset(self,
                             dataset_name: str,
                             dataset_data: Any,
                             config: Dict[str, Any]) -> bool:
        """判断是否应该导出数据集"""
        # 检查是否在排除列表中
        exclude_datasets = config.get('exclude_datasets', [])
        if dataset_name in exclude_datasets:
            return False

        # 检查是否在包含列表中（如果指定了）
        include_datasets = config.get('include_datasets')
        if include_datasets and dataset_name not in include_datasets:
            return False

        # 检查数据集是否为空
        if self._is_empty_dataset(dataset_data):
            logger.warning(f"跳过空数据集: {dataset_name}")
            return False

        return True

    def _process_large_dataset(self,
                              dataset_data: Union[gpd.GeoDataFrame, pd.DataFrame],
                              batch_size: int) -> Union[gpd.GeoDataFrame, pd.DataFrame]:
        """处理大数据集，这里可以根据需要进行分块等优化"""
        # 对于大数据集，可以考虑分块处理
        logger.info(f"处理大数据集，批量大小: {batch_size}")
        return dataset_data

    def _generate_export_report(self,
                               export_results: Dict[str, Any],
                               output_dir: Path) -> Optional[str]:
        """生成导出报告"""
        try:
            report_path = output_dir / 'export_report.txt'

            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("GIS空间关联系统 - 数据导出报告\n")
                f.write("=" * 50 + "\n\n")

                f.write(f"导出时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"导出状态: {'成功' if export_results['success'] else '失败'}\n")
                f.write(f"总耗时: {export_results.get('export_time', 0):.2f}秒\n\n")

                f.write(f"导出文件数量: {len(export_results['exported_files'])}\n")
                f.write(f"失败导出数量: {len(export_results['failed_exports'])}\n")
                f.write(f"跳过数据集数量: {len(export_results['skipped_datasets'])}\n\n")

                if export_results['exported_files']:
                    f.write("成功导出的文件:\n")
                    for file_path in export_results['exported_files']:
                        f.write(f"  - {file_path}\n")
                    f.write("\n")

                if export_results['failed_exports']:
                    f.write("失败的导出:\n")
                    for failed in export_results['failed_exports']:
                        f.write(f"  - {failed['dataset']}: {failed['error']}\n")
                    f.write("\n")

                if export_results['warnings']:
                    f.write("警告信息:\n")
                    for warning in export_results['warnings']:
                        f.write(f"  - {warning}\n")
                    f.write("\n")

                if export_results['errors']:
                    f.write("错误信息:\n")
                    for error in export_results['errors']:
                        f.write(f"  - {error}\n")

            logger.info(f"导出报告已生成: {report_path}")
            return str(report_path)

        except Exception as e:
            logger.error(f"生成导出报告失败: {str(e)}")
            return None

    def _compress_exports(self,
                         exported_files: List[str],
                         compression_type: str,
                         output_dir: Path) -> Optional[str]:
        """压缩导出文件"""
        try:
            import zipfile
            import tarfile

            timestamp = time.strftime('%Y%m%d_%H%M%S')

            if compression_type == 'zip':
                archive_path = output_dir / f'gis_exports_{timestamp}.zip'
                with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for file_path in exported_files:
                        if os.path.exists(file_path):
                            zf.write(file_path, os.path.basename(file_path))

            elif compression_type == 'tar':
                archive_path = output_dir / f'gis_exports_{timestamp}.tar.gz'
                with tarfile.open(archive_path, 'w:gz') as tf:
                    for file_path in exported_files:
                        if os.path.exists(file_path):
                            tf.add(file_path, arcname=os.path.basename(file_path))

            else:
                logger.warning(f"不支持的压缩类型: {compression_type}")
                return None

            logger.info(f"导出文件已压缩: {archive_path}")
            return str(archive_path)

        except Exception as e:
            logger.error(f"压缩文件失败: {str(e)}")
            return None

    def get_supported_formats(self) -> List[str]:
        """获取支持的导出格式列表"""
        return self.supported_formats.copy()

    def add_custom_exporter(self,
                           format_name: str,
                           exporter_class: type) -> None:
        """
        添加自定义导出器

        Args:
            format_name: 格式名称
            exporter_class: 导出器类
        """
        self.exporters[format_name] = exporter_class(self.config.get(format_name, {}))
        self.supported_formats.append(format_name)
        logger.info(f"已添加自定义导出器: {format_name}")

    def remove_exporter(self, format_name: str) -> None:
        """
        移除导出器

        Args:
            format_name: 格式名称
        """
        if format_name in self.exporters:
            del self.exporters[format_name]
            self.supported_formats.remove(format_name)
            logger.info(f"已移除导出器: {format_name}")

    def get_exporter_info(self, format_name: str) -> Optional[Dict[str, Any]]:
        """
        获取导出器信息

        Args:
            format_name: 格式名称

        Returns:
            Optional[Dict[str, Any]]: 导出器信息
        """
        if format_name in self.exporters:
            exporter = self.exporters[format_name]
            return {
                'format_name': format_name,
                'class_name': exporter.__class__.__name__,
                'supported_data_types': getattr(exporter, 'supported_data_types', []),
                'file_extension': getattr(exporter, 'file_extension', None),
                'description': getattr(exporter, 'description', '')
            }
        return None