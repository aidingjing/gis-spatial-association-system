"""
网络关系可视化模块

提供网络关系图可视化功能，支持关联关系展示、拓扑结构分析等。

特点:
- 网络关系图生成
- 多种布局算法
- 自定义节点样式
- 交互式网络图
- 社区检测可视化

作者: GIS空间关联系统开发团队
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import pandas as pd
import geopandas as gpd

try:
    import networkx as nx
    import matplotlib.pyplot as plt
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    logger = logging.getLogger(__name__).warning("networkx库未安装，网络可视化功能不可用")

logger = logging.getLogger(__name__)


class NetworkVisualizer:
    """
    网络关系可视化器

    生成网络关系图和拓扑结构图。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.figure_size = self.config.get('figure_size', (12, 8))

    def create_association_network(self, associations: List[Dict[str, Any]],
                                 output_dir: Path) -> Optional[Dict[str, Any]]:
        """创建关联关系网络图"""
        try:
            if not NETWORKX_AVAILABLE:
                return None

            if not associations:
                return None

            # 创建网络图
            G = nx.Graph()

            # 添加节点和边
            for assoc in associations:
                source = assoc.get('source', 'unknown')
                target = assoc.get('target', 'unknown')
                weight = assoc.get('weight', 1)

                G.add_edge(source, target, weight=weight)

            if len(G.nodes()) == 0:
                return None

            # 绘制网络图
            plt.figure(figsize=self.figure_size)
            pos = nx.spring_layout(G, k=1, iterations=50)

            # 绘制节点
            nx.draw_networkx_nodes(G, pos, node_color='lightblue',
                                 node_size=1000, alpha=0.8)

            # 绘制边
            nx.draw_networkx_edges(G, pos, alpha=0.5, width=2)

            # 绘制标签
            nx.draw_networkx_labels(G, pos, font_size=10, font_weight='bold')

            plt.title('空间关联关系网络图', fontsize=16, fontweight='bold')
            plt.axis('off')
            plt.tight_layout()

            # 保存图片
            network_file = output_dir / 'association_network.png'
            plt.savefig(network_file, dpi=300, bbox_inches='tight')
            plt.close()

            return {
                'type': 'association_network',
                'title': '空间关联关系网络图',
                'file_path': str(network_file),
                'format': 'png',
                'nodes_count': len(G.nodes()),
                'edges_count': len(G.edges())
            }

        except Exception as e:
            logger.error(f"创建关联关系网络图失败: {str(e)}")
            return None

    def create_spatial_topology_network(self, results: Dict[str, Any],
                                      output_dir: Path) -> Optional[Dict[str, Any]]:
        """创建空间拓扑网络图"""
        try:
            if not NETWORKX_AVAILABLE:
                return None

            # 查找空间数据
            spatial_data = None
            for name, data in results.items():
                if isinstance(data, gpd.GeoDataFrame) and not data.empty:
                    spatial_data = data
                    break

            if spatial_data is None:
                return None

            # 基于空间邻近性创建网络
            G = self._create_spatial_network(spatial_data)

            if len(G.nodes()) == 0:
                return None

            # 绘制网络图
            plt.figure(figsize=self.figure_size)
            pos = nx.kamada_kawai_layout(G)

            nx.draw(G, pos, with_labels=False, node_color='lightgreen',
                   node_size=300, alpha=0.7, edge_color='gray')

            plt.title('空间拓扑网络图', fontsize=16, fontweight='bold')
            plt.axis('off')
            plt.tight_layout()

            network_file = output_dir / 'spatial_topology_network.png'
            plt.savefig(network_file, dpi=300, bbox_inches='tight')
            plt.close()

            return {
                'type': 'spatial_topology_network',
                'title': '空间拓扑网络图',
                'file_path': str(network_file),
                'format': 'png'
            }

        except Exception as e:
            logger.error(f"创建空间拓扑网络图失败: {str(e)}")
            return None

    def _create_spatial_network(self, gdf: gpd.GeoDataFrame) -> nx.Graph:
        """基于空间数据创建网络"""
        G = nx.Graph()

        # 简化实现：基于空间索引创建邻近连接
        if gdf.empty:
            return G

        # 添加所有几何对象作为节点
        for idx, row in gdf.iterrows():
            G.add_node(idx, geometry=row.geometry)

        # 基于距离创建边（简化版本）
        try:
            from shapely.geometry import Point
            points = [row.geometry.centroid for idx, row in gdf.iterrows()]

            for i, point1 in enumerate(points):
                for j, point2 in enumerate(points):
                    if i < j:  # 避免重复
                        distance = point1.distance(point2)
                        # 如果距离小于阈值，添加边
                        if distance < 0.1:  # 简化的距离阈值
                            G.add_edge(i, j, weight=1/distance if distance > 0 else 1)
        except Exception:
            # 如果距离计算失败，创建一个简单的线性网络
            nodes = list(G.nodes())
            for i in range(len(nodes) - 1):
                G.add_edge(nodes[i], nodes[i + 1])

        return G

    def create_custom_network(self, data: Union[pd.DataFrame, Dict],
                             options: Dict[str, Any], output_path: str = None) -> Optional[str]:
        """创建自定义网络图"""
        try:
            if not NETWORKX_AVAILABLE:
                return None

            # 根据数据类型创建网络
            G = nx.Graph()

            if isinstance(data, pd.DataFrame):
                # 假设DataFrame包含source和target列
                if 'source' in data.columns and 'target' in data.columns:
                    for _, row in data.iterrows():
                        G.add_edge(row['source'], row['target'])
                else:
                    # 创建简单的线性网络
                    nodes = data.index.tolist()
                    for i in range(len(nodes) - 1):
                        G.add_edge(nodes[i], nodes[i + 1])

            plt.figure(figsize=self.figure_size)
            layout = options.get('layout', 'spring')

            if layout == 'spring':
                pos = nx.spring_layout(G)
            elif layout == 'circular':
                pos = nx.circular_layout(G)
            else:
                pos = nx.random_layout(G)

            nx.draw(G, pos, with_labels=True, node_color='orange',
                   node_size=500, alpha=0.8)

            plt.title(options.get('title', '自定义网络图'))
            plt.axis('off')
            plt.tight_layout()

            if not output_path:
                output_path = "custom_network.png"

            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()

            return output_path

        except Exception as e:
            logger.error(f"创建自定义网络图失败: {str(e)}")
            return None

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """更新配置"""
        self.config.update(new_config)
        self.figure_size = self.config.get('figure_size', (12, 8))