"""
自适应空间索引系统

提供智能的空间索引构建和查询优化，根据数据特征自动选择最优的索引策略。
支持R-tree、STRtree和分层索引等多种索引类型。

Author: CCPM Auto Development System
"""

import logging
import time
import gc
from typing import List, Dict, Tuple, Optional, Union, Any
from abc import ABC, abstractmethod
import numpy as np
import psutil

# 尝试导入依赖库
try:
    from rtree import index
    HAS_RTREE = True
except ImportError:
    HAS_RTREE = False
    logging.warning("R-tree library not available")

try:
    from shapely.strtree import STRtree
    from shapely.geometry import Point, LineString, Polygon, box
    from shapely.geometry.base import BaseGeometry
    HAS_SHAPELY = True
except ImportError:
    HAS_SHAPELY = False
    logging.warning("Shapely library not available")

logger = logging.getLogger(__name__)


class SpatialIndexInterface(ABC):
    """空间索引接口"""

    @abstractmethod
    def build_index(self, geometries: List[BaseGeometry]) -> None:
        """构建索引"""
        pass

    @abstractmethod
    def query(self, geometry: BaseGeometry, predicate: str = 'intersects') -> List[int]:
        """查询索引"""
        pass

    @abstractmethod
    def query_nearest(self, geometry: BaseGeometry, num_results: int = 1) -> List[int]:
        """最近邻查询"""
        pass

    @abstractmethod
    def estimate_memory_usage(self) -> int:
        """估算内存使用"""
        pass


class RTreeIndex(SpatialIndexInterface):
    """R-tree空间索引实现"""

    def __init__(self):
        self.index: Optional[index.Index] = None
        self.geometries: List[BaseGeometry] = []
        self.built = False

    def build_index(self, geometries: List[BaseGeometry]) -> None:
        """构建R-tree索引"""
        if not HAS_RTREE:
            raise ImportError("R-tree library is required for RTreeIndex")

        logger.info(f"构建R-tree索引，要素数量: {len(geometries)}")
        start_time = time.time()

        self.geometries = geometries
        self.index = index.Index()

        for idx, geometry in enumerate(geometries):
            if geometry is not None and not geometry.is_empty:
                bounds = geometry.bounds
                self.index.insert(idx, bounds)

        self.built = True
        build_time = time.time() - start_time
        logger.info(f"R-tree索引构建完成，耗时: {build_time:.2f}秒")

    def query(self, geometry: BaseGeometry, predicate: str = 'intersects') -> List[int]:
        """查询R-tree索引"""
        if not self.built or self.index is None:
            return []

        query_bounds = geometry.bounds
        candidate_indices = list(self.index.intersection(query_bounds))

        # 进一步过滤候选结果
        result_indices = []
        for idx in candidate_indices:
            if idx < len(self.geometries):
                candidate_geom = self.geometries[idx]
                if candidate_geom is not None and not candidate_geom.is_empty:
                    if predicate == 'intersects' and geometry.intersects(candidate_geom):
                        result_indices.append(idx)
                    elif predicate == 'contains' and geometry.contains(candidate_geom):
                        result_indices.append(idx)
                    elif predicate == 'within' and geometry.within(candidate_geom):
                        result_indices.append(idx)

        return result_indices

    def query_nearest(self, geometry: BaseGeometry, num_results: int = 1) -> List[int]:
        """最近邻查询"""
        if not self.built or self.index is None:
            return []

        try:
            nearest_indices = list(self.index.nearest(geometry.bounds, num_results=num_results))
            return nearest_indices
        except Exception as e:
            logger.warning(f"最近邻查询失败: {str(e)}")
            return []

    def estimate_memory_usage(self) -> int:
        """估算R-tree索引内存使用"""
        if not self.built:
            return 0

        # 基于经验公式估算
        bytes_per_geometry = 150  # 经验值
        overhead_factor = 1.5  # R-tree的开销系数

        return int(len(self.geometries) * bytes_per_geometry * overhead_factor)


class STRTreeIndex(SpatialIndexInterface):
    """STR-tree空间索引实现"""

    def __init__(self):
        self.index: Optional[STRtree] = None
        self.geometries: List[BaseGeometry] = []
        self.built = False

    def build_index(self, geometries: List[BaseGeometry]) -> None:
        """构建STR-tree索引"""
        if not HAS_SHAPELY:
            raise ImportError("Shapely library is required for STRTreeIndex")

        logger.info(f"构建STR-tree索引，要素数量: {len(geometries)}")
        start_time = time.time()

        # 过滤有效几何对象
        valid_geometries = [geom for geom in geometries
                          if geom is not None and not geom.is_empty]

        self.geometries = valid_geometries
        self.index = STRtree(valid_geometries)

        self.built = True
        build_time = time.time() - start_time
        logger.info(f"STR-tree索引构建完成，耗时: {build_time:.2f}秒")

    def query(self, geometry: BaseGeometry, predicate: str = 'intersects') -> List[int]:
        """查询STR-tree索引"""
        if not self.built or self.index is None:
            return []

        try:
            if predicate == 'intersects':
                result_geometries = self.index.query(geometry, predicate='intersects')
            elif predicate == 'contains':
                result_geometries = self.index.query(geometry, predicate='contains')
            elif predicate == 'within':
                result_geometries = self.index.query(geometry, predicate='within')
            else:
                result_geometries = self.index.query(geometry, predicate='intersects')

            # 将几何对象转换回索引
            result_indices = []
            for result_geom in result_geometries:
                # 查找几何对象在原始列表中的索引
                try:
                    idx = self.geometries.index(result_geom)
                    result_indices.append(idx)
                except ValueError:
                    # 如果找不到，继续处理下一个
                    continue

            return result_indices

        except Exception as e:
            logger.warning(f"STR-tree查询失败: {str(e)}")
            return []

    def query_nearest(self, geometry: BaseGeometry, num_results: int = 1) -> List[int]:
        """最近邻查询"""
        if not self.built or self.index is None:
            return []

        try:
            nearest_geometries = self.index.nearest(geometry)[:num_results]
            nearest_indices = []

            for nearest_geom in nearest_geometries:
                try:
                    idx = self.geometries.index(nearest_geom)
                    nearest_indices.append(idx)
                except ValueError:
                    continue

            return nearest_indices

        except Exception as e:
            logger.warning(f"STR-tree最近邻查询失败: {str(e)}")
            return []

    def estimate_memory_usage(self) -> int:
        """估算STR-tree索引内存使用"""
        if not self.built:
            return 0

        # STR-tree通常比R-tree更节省内存
        bytes_per_geometry = 120  # 经验值
        overhead_factor = 1.3  # STR-tree的开销系数

        return int(len(self.geometries) * bytes_per_geometry * overhead_factor)


class BruteForceIndex(SpatialIndexInterface):
    """暴力搜索索引（用于小数据集）"""

    def __init__(self):
        self.geometries: List[BaseGeometry] = []
        self.built = False

    def build_index(self, geometries: List[BaseGeometry]) -> None:
        """构建暴力搜索索引"""
        logger.info(f"使用暴力搜索，要素数量: {len(geometries)}")
        self.geometries = geometries
        self.built = True

    def query(self, geometry: BaseGeometry, predicate: str = 'intersects') -> List[int]:
        """暴力搜索查询"""
        if not self.built:
            return []

        result_indices = []
        for idx, candidate_geom in enumerate(self.geometries):
            if candidate_geom is not None and not candidate_geom.is_empty:
                if predicate == 'intersects' and geometry.intersects(candidate_geom):
                    result_indices.append(idx)
                elif predicate == 'contains' and geometry.contains(candidate_geom):
                    result_indices.append(idx)
                elif predicate == 'within' and geometry.within(candidate_geom):
                    result_indices.append(idx)

        return result_indices

    def query_nearest(self, geometry: BaseGeometry, num_results: int = 1) -> List[int]:
        """暴力最近邻搜索"""
        if not self.built:
            return []

        distances = []
        for idx, candidate_geom in enumerate(self.geometries):
            if candidate_geom is not None and not candidate_geom.is_empty:
                distance = geometry.distance(candidate_geom)
                distances.append((distance, idx))

        # 按距离排序并返回前N个
        distances.sort()
        return [idx for _, idx in distances[:num_results]]

    def estimate_memory_usage(self) -> int:
        """暴力搜索内存使用（仅存储几何对象）"""
        if not self.built:
            return 0

        bytes_per_geometry = 80  # 仅几何对象本身
        return int(len(self.geometries) * bytes_per_geometry)


class AdaptiveSpatialIndex:
    """自适应空间索引构建器

    根据数据规模、内存限制和查询模式自动选择最优的索引策略。
    支持R-tree、STRtree和暴力搜索等多种索引类型。
    """

    def __init__(self,
                 geometry_count: int = 0,
                 memory_limit_gb: float = 4.0,
                 prefer_memory_efficiency: bool = False):
        """初始化自适应空间索引

        Args:
            geometry_count: 预估的几何对象数量
            memory_limit_gb: 内存限制（GB）
            prefer_memory_efficiency: 是否优先考虑内存效率
        """
        self.geometry_count = geometry_count
        self.memory_limit_bytes = memory_limit_gb * 1024**3
        self.prefer_memory_efficiency = prefer_memory_efficiency

        self.index_type = self._determine_optimal_index_type()
        self.spatial_index: Optional[SpatialIndexInterface] = None
        self.geometries: List[BaseGeometry] = []

        logger.info(f"自适应索引初始化: 几何数量={geometry_count}, "
                   f"内存限制={memory_limit_gb}GB, 索引类型={self.index_type}")

    def _determine_optimal_index_type(self) -> str:
        """确定最优索引类型"""
        # 检查可用库
        if not HAS_SHAPELY:
            logger.warning("Shapely不可用，回退到暴力搜索")
            return 'brute_force'

        # 基于数据量的策略选择
        if self.geometry_count < 500:
            return 'brute_force'
        elif self.geometry_count < 5000:
            if HAS_RTREE:
                return 'rtree'
            else:
                return 'str_tree'
        elif self.geometry_count < 50000:
            return 'str_tree'
        else:
            # 超大数据集，考虑内存使用
            available_memory = psutil.virtual_memory().available

            if self.prefer_memory_efficiency or available_memory < self.memory_limit_bytes * 0.5:
                return 'str_tree'  # 内存效率更高
            else:
                return 'str_tree'  # STRtree在各方面表现更好

    def build_index(self, geometries: List[BaseGeometry]) -> SpatialIndexInterface:
        """构建最优化的空间索引"""
        logger.info(f"开始构建空间索引，实际要素数量: {len(geometries)}")
        start_time = time.time()

        # 更新几何数量
        self.geometry_count = len(geometries)
        self.geometries = geometries

        # 重新评估索引类型
        original_type = self.index_type
        self.index_type = self._determine_optimal_index_type()

        if original_type != self.index_type:
            logger.info(f"根据实际数据量调整索引类型: {original_type} -> {self.index_type}")

        # 创建索引实例
        if self.index_type == 'rtree':
            self.spatial_index = RTreeIndex()
        elif self.index_type == 'str_tree':
            self.spatial_index = STRTreeIndex()
        elif self.index_type == 'brute_force':
            self.spatial_index = BruteForceIndex()
        else:
            logger.error(f"不支持的索引类型: {self.index_type}")
            self.spatial_index = BruteForceIndex()

        # 构建索引
        try:
            self.spatial_index.build_index(geometries)

            # 验证内存使用
            estimated_memory = self.spatial_index.estimate_memory_usage()
            logger.info(f"索引构建完成，类型={self.index_type}, "
                       f"预估内存使用={estimated_memory / 1024**2:.2f}MB")

            if estimated_memory > self.memory_limit_bytes:
                logger.warning(f"预估内存使用({estimated_memory / 1024**2:.2f}MB) "
                            f"超过限制({self.memory_limit_bytes / 1024**2:.2f}MB)")

        except Exception as e:
            logger.error(f"索引构建失败: {str(e)}")
            # 回退到暴力搜索
            self.index_type = 'brute_force'
            self.spatial_index = BruteForceIndex()
            self.spatial_index.build_index(geometries)

        build_time = time.time() - start_time
        logger.info(f"索引构建总耗时: {build_time:.2f}秒")

        return self.spatial_index

    def query(self,
              geometry: BaseGeometry,
              predicate: str = 'intersects',
              max_results: Optional[int] = None) -> List[int]:
        """查询空间索引"""
        if self.spatial_index is None:
            raise RuntimeError("索引尚未构建，请先调用build_index()")

        result_indices = self.spatial_index.query(geometry, predicate)

        if max_results is not None:
            result_indices = result_indices[:max_results]

        return result_indices

    def query_nearest(self,
                      geometry: BaseGeometry,
                      num_results: int = 1) -> List[int]:
        """最近邻查询"""
        if self.spatial_index is None:
            raise RuntimeError("索引尚未构建，请先调用build_index()")

        return self.spatial_index.query_nearest(geometry, num_results)

    def get_memory_usage(self) -> Dict[str, Any]:
        """获取内存使用信息"""
        if self.spatial_index is None:
            return {'error': '索引尚未构建'}

        estimated_usage = self.spatial_index.estimate_memory_usage()
        process = psutil.Process()
        current_memory = process.memory_info().rss
        available_memory = psutil.virtual_memory().available

        return {
            'index_type': self.index_type,
            'geometry_count': self.geometry_count,
            'estimated_index_usage_mb': estimated_usage / 1024**2,
            'current_process_memory_mb': current_memory / 1024**2,
            'available_memory_mb': available_memory / 1024**2,
            'memory_usage_percent': (current_memory / psutil.virtual_memory().total) * 100
        }

    def validate_index(self) -> Dict[str, Any]:
        """验证索引质量"""
        if self.spatial_index is None or len(self.geometries) == 0:
            return {'error': '索引尚未构建或没有数据'}

        # 随机选择一些几何对象进行验证
        sample_size = min(10, len(self.geometries))
        sample_indices = np.random.choice(len(self.geometries), sample_size, replace=False)

        validation_results = {
            'total_geometries': len(self.geometries),
            'sample_size': sample_size,
            'successful_queries': 0,
            'failed_queries': 0,
            'query_errors': []
        }

        for idx in sample_indices:
            try:
                geometry = self.geometries[idx]
                if geometry is not None and not geometry.is_empty:
                    # 执行查询测试
                    results = self.query(geometry)
                    validation_results['successful_queries'] += 1
                else:
                    validation_results['failed_queries'] += 1
                    validation_results['query_errors'].append(f"几何对象{idx}为空")
            except Exception as e:
                validation_results['failed_queries'] += 1
                validation_results['query_errors'].append(f"查询{idx}失败: {str(e)}")

        validation_results['success_rate'] = (
            validation_results['successful_queries'] / validation_results['sample_size']
        )

        return validation_results


class HierarchicalSpatialIndex:
    """分层空间索引系统

    针对超大数据集的多层索引优化，通过分层查询减少候选集大小。
    """

    def __init__(self, geometries: List[BaseGeometry], levels: int = 3):
        """初始化分层索引"""
        self.geometries = geometries
        self.levels = levels
        self.index_hierarchy: Dict[str, SpatialIndexInterface] = {}
        self.built = False

    def build_hierarchy(self) -> None:
        """构建分层索引结构"""
        logger.info(f"构建分层索引，层数: {self.levels}, 几何数量: {len(self.geometries)}")
        start_time = time.time()

        current_geometries = self.geometries

        for level in range(self.levels):
            logger.info(f"构建第{level}层索引，几何数量: {len(current_geometries)}")

            if level == 0:
                # 最底层：完整几何对象
                index_instance = AdaptiveSpatialIndex(len(current_geometries))
                self.index_hierarchy[f'level_{level}'] = index_instance.build_index(current_geometries)
            else:
                # 上层：几何对象边界框
                bounds_geometries = [box(*geom.bounds) for geom in current_geometries
                                   if geom is not None and not geom.is_empty]

                if bounds_geometries:
                    index_instance = AdaptiveSpatialIndex(len(bounds_geometries))
                    self.index_hierarchy[f'level_{level}'] = index_instance.build_index(bounds_geometries)

            # 如果数据量仍然很大，继续分层
            max_geoms_for_next_level = 10000 // (2 ** level)
            if len(current_geometries) > max_geoms_for_next_level:
                current_geometries = self._sample_geometries(current_geometries, factor=0.5)
            else:
                break

        self.built = True
        build_time = time.time() - start_time
        logger.info(f"分层索引构建完成，耗时: {build_time:.2f}秒")

    def _sample_geometries(self,
                          geometries: List[BaseGeometry],
                          factor: float = 0.5) -> List[BaseGeometry]:
        """采样几何对象"""
        if len(geometries) <= 10:
            return geometries

        sample_size = max(10, int(len(geometries) * factor))
        return np.random.choice(geometries, sample_size, replace=False).tolist()

    def query_with_early_termination(self,
                                   geometry: BaseGeometry,
                                   max_results: int = 100,
                                   predicate: str = 'intersects') -> List[int]:
        """带早期终止的分层查询"""
        if not self.built:
            raise RuntimeError("分层索引尚未构建，请先调用build_hierarchy()")

        candidates = set()
        total_checked = 0

        # 从顶层开始查询
        for level in reversed(range(self.levels)):
            level_key = f'level_{level}'
            if level_key not in self.index_hierarchy:
                continue

            level_index = self.index_hierarchy[level_key]

            if len(candidates) >= max_results:
                logger.debug(f"达到最大结果数{max_results}，终止查询")
                break

            if level == 0:
                # 最底层使用实际几何对象查询
                if isinstance(level_index, AdaptiveSpatialIndex):
                    new_candidates = level_index.query(geometry, predicate)
                else:
                    new_candidates = level_index.query(geometry, predicate)
            else:
                # 上层使用边界框查询
                query_box = box(*geometry.bounds)
                if isinstance(level_index, AdaptiveSpatialIndex):
                    new_candidates = level_index.query(query_box, 'intersects')
                else:
                    new_candidates = level_index.query(query_box, 'intersects')

            # 更新候选集
            candidates.update(new_candidates)
            total_checked += len(new_candidates)

            logger.debug(f"第{level}层查询完成，新增候选数: {len(new_candidates)}, "
                        f"总候选数: {len(candidates)}")

        # 转换为列表并限制结果数量
        result_indices = list(candidates)[:max_results]

        logger.debug(f"分层查询完成，总检查数: {total_checked}, "
                    f"最终结果数: {len(result_indices)}")

        return result_indices

    def get_hierarchy_info(self) -> Dict[str, Any]:
        """获取分层索引信息"""
        if not self.built:
            return {'error': '分层索引尚未构建'}

        info = {
            'levels': self.levels,
            'total_geometries': len(self.geometries),
            'level_info': {}
        }

        for level in range(self.levels):
            level_key = f'level_{level}'
            if level_key in self.index_hierarchy:
                level_index = self.index_hierarchy[level_key]

                level_info = {
                    'index_type': getattr(level_index, 'index_type', 'unknown'),
                    'built': True
                }

                # 获取内存使用信息
                if isinstance(level_index, AdaptiveSpatialIndex):
                    memory_info = level_index.get_memory_usage()
                    level_info.update(memory_info)

                info['level_info'][level_key] = level_info

        return info