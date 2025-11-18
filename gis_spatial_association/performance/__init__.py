"""
性能优化模块

提供高性能的空间数据处理能力，包括：
- 自适应空间索引系统
- 分块数据管理
- 智能任务调度
- 多级缓存系统
- 性能监控和基准测试

Author: CCPM Auto Development System
"""

from .indexing import AdaptiveSpatialIndex, HierarchicalSpatialIndex
from .memory import ChunkedDataManager, MMapDataProcessor
from .parallel import IntelligentTaskScheduler, ParallelProcessor
from .cache import MultiLevelCache, MemoryCache, DiskCache
from .monitoring import PerformanceMonitor, BenchmarkRunner

__all__ = [
    # 空间索引
    'AdaptiveSpatialIndex',
    'HierarchicalSpatialIndex',

    # 内存管理
    'ChunkedDataManager',
    'MMapDataProcessor',

    # 并行计算
    'IntelligentTaskScheduler',
    'ParallelProcessor',

    # 缓存系统
    'MultiLevelCache',
    'MemoryCache',
    'DiskCache',

    # 监控系统
    'PerformanceMonitor',
    'BenchmarkRunner'
]

__version__ = '1.0.0'