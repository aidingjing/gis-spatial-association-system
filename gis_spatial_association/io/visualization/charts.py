"""
统计图表可视化模块

提供丰富的统计图表生成功能，支持多种图表类型和自定义样式。

特点:
- 多种图表类型支持
- 自动化图表生成
- 自定义样式配置
- 批量图表处理
- 多格式输出

作者: GIS空间关联系统开发团队
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import seaborn as sns

logger = logging.getLogger(__name__)


class ChartVisualizer:
    """
    统计图表可视化器

    生成各种类型的统计图表。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.setup_style()

    def setup_style(self):
        """设置图表样式"""
        plt.style.use(self.config.get('chart_style', 'seaborn-v0_8'))
        sns.set_palette("husl")

    def create_dataset_overview_chart(self, results: Dict[str, Any], output_dir: Path) -> Optional[Dict[str, Any]]:
        """创建数据集概览图表"""
        try:
            # 统计数据集信息
            dataset_info = []
            for name, data in results.items():
                if isinstance(data, (gpd.GeoDataFrame, pd.DataFrame)):
                    dataset_info.append({
                        'name': name,
                        'records': len(data),
                        'type': 'GeoDataFrame' if isinstance(data, gpd.GeoDataFrame) else 'DataFrame'
                    })

            if not dataset_info:
                return None

            # 创建图表
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

            # 数据集大小对比图
            names = [d['name'] for d in dataset_info]
            sizes = [d['records'] for d in dataset_info]

            bars = ax1.bar(names, sizes, color='skyblue', alpha=0.7)
            ax1.set_title('数据集大小分布', fontsize=14, fontweight='bold')
            ax1.set_xlabel('数据集名称')
            ax1.set_ylabel('记录数')
            plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')

            # 添加数值标签
            for bar, size in zip(bars, sizes):
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height,
                        f'{size:,}',
                        ha='center', va='bottom')

            # 数据类型分布饼图
            type_counts = pd.Series([d['type'] for d in dataset_info]).value_counts()
            colors = ['lightcoral', 'lightskyblue']
            ax2.pie(type_counts.values, labels=type_counts.index, autopct='%1.1f%%',
                   colors=colors[:len(type_counts)], startangle=90)
            ax2.set_title('数据类型分布', fontsize=14, fontweight='bold')

            plt.tight_layout()

            # 保存图表
            chart_file = output_dir / 'dataset_overview.png'
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            plt.close()

            return {
                'type': 'overview_chart',
                'title': '数据集概览',
                'file_path': str(chart_file),
                'format': 'png'
            }

        except Exception as e:
            logger.error(f"创建数据集概览图表失败: {str(e)}")
            return None

    def create_attribute_distribution_charts(self, data: Union[gpd.GeoDataFrame, pd.DataFrame],
                                           dataset_name: str, output_dir: Path) -> List[Dict[str, Any]]:
        """创建属性分布图表"""
        charts = []

        try:
            if data.empty:
                return charts

            # 数值字段分布
            numeric_columns = data.select_dtypes(include=['number']).columns[:3]  # 限制数量

            for col in numeric_columns:
                chart = self._create_distribution_chart(data, col, dataset_name, output_dir)
                if chart:
                    charts.append(chart)

            # 分类字段分布
            categorical_columns = data.select_dtypes(include=['object', 'category']).columns[:2]

            for col in categorical_columns:
                if col != 'geometry':
                    chart = self._create_categorical_chart(data, col, dataset_name, output_dir)
                    if chart:
                        charts.append(chart)

        except Exception as e:
            logger.error(f"创建属性分布图表失败: {str(e)}")

        return charts

    def _create_distribution_chart(self, data: Union[gpd.GeoDataFrame, pd.DataFrame],
                                  column: str, dataset_name: str, output_dir: Path) -> Optional[Dict[str, Any]]:
        """创建数值分布图表"""
        try:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

            # 直方图
            data[column].hist(bins=30, ax=ax1, alpha=0.7, color='skyblue')
            ax1.set_title(f'{column} 分布直方图')
            ax1.set_xlabel(column)
            ax1.set_ylabel('频数')

            # 箱线图
            data[column].plot(kind='box', ax=ax2)
            ax2.set_title(f'{column} 箱线图')
            ax2.set_ylabel(column)

            plt.tight_layout()

            chart_file = output_dir / f'{dataset_name}_{column}_distribution.png'
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            plt.close()

            return {
                'type': 'distribution_chart',
                'title': f'{dataset_name} - {column} 分布',
                'file_path': str(chart_file),
                'format': 'png'
            }

        except Exception as e:
            logger.error(f"创建分布图表失败 {column}: {str(e)}")
            return None

    def _create_categorical_chart(self, data: Union[gpd.GeoDataFrame, pd.DataFrame],
                                 column: str, dataset_name: str, output_dir: Path) -> Optional[Dict[str, Any]]:
        """创建分类字段图表"""
        try:
            value_counts = data[column].value_counts().head(10)  # 限制显示前10个

            if len(value_counts) == 0:
                return None

            fig, ax = plt.subplots(figsize=(10, 6))

            value_counts.plot(kind='bar', ax=ax, color='lightcoral', alpha=0.7)
            ax.set_title(f'{column} 分布')
            ax.set_xlabel(column)
            ax.set_ylabel('计数')
            plt.xticks(rotation=45, ha='right')

            plt.tight_layout()

            chart_file = output_dir / f'{dataset_name}_{column}_categorical.png'
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            plt.close()

            return {
                'type': 'categorical_chart',
                'title': f'{dataset_name} - {column} 分布',
                'file_path': str(chart_file),
                'format': 'png'
            }

        except Exception as e:
            logger.error(f"创建分类图表失败 {column}: {str(e)}")
            return None

    def create_custom_chart(self, data: Union[gpd.GeoDataFrame, pd.DataFrame],
                           options: Dict[str, Any], output_path: str = None) -> Optional[str]:
        """创建自定义图表"""
        try:
            chart_type = options.get('type', 'bar')
            x_column = options.get('x_column')
            y_column = options.get('y_column')

            if not x_column or x_column not in data.columns:
                return None

            fig, ax = plt.subplots(figsize=self.config.get('figure_size', (12, 8)))

            if chart_type == 'bar':
                if y_column and y_column in data.columns:
                    data.plot(kind='bar', x=x_column, y=y_column, ax=ax)
                else:
                    data[x_column].value_counts().plot(kind='bar', ax=ax)
            elif chart_type == 'line':
                data.plot(kind='line', x=x_column, y=y_column, ax=ax)
            elif chart_type == 'scatter':
                if y_column and y_column in data.columns:
                    data.plot(kind='scatter', x=x_column, y=y_column, ax=ax)

            ax.set_title(options.get('title', '自定义图表'))
            plt.tight_layout()

            if not output_path:
                output_path = f"custom_chart.{options.get('format', 'png')}"

            plt.savefig(output_path, dpi=self.config.get('dpi', 300), bbox_inches='tight')
            plt.close()

            return output_path

        except Exception as e:
            logger.error(f"创建自定义图表失败: {str(e)}")
            return None

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """更新配置"""
        self.config.update(new_config)
        self.setup_style()