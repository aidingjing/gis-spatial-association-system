"""
内存管理和分块数据处理模块

提供智能的内存管理和大数据集分块处理能力，避免内存溢出。
支持内存映射文件、流式处理和自适应分块大小调整。

Author: CCPM Auto Development System
"""

import logging
import time
import gc
import mmap
import os
import pickle
import tempfile
from typing import Iterator, List, Dict, Any, Callable, Optional, Union
from abc import ABC, abstractmethod
from itertools import islice
import psutil
import numpy as np

try:
    import pandas as pd
    import geopandas as gpd
    from shapely.geometry.base import BaseGeometry
    HAS_GEOSPATIAL = True
except ImportError:
    HAS_GEOSPATIAL = False
    logging.warning("GeoPandas/Shapely not available")

logger = logging.getLogger(__name__)


class MemoryMonitor:
    """内存监控器"""

    def __init__(self):
        self.process = psutil.Process()
        self.memory_history: List[Dict[str, float]] = []
        self.max_history_size = 100

    def get_memory_info(self) -> Dict[str, float]:
        """获取当前内存信息"""
        memory_info = self.process.memory_info()
        virtual_memory = psutil.virtual_memory()

        current_info = {
            'timestamp': time.time(),
            'rss_mb': memory_info.rss / 1024**2,
            'vms_mb': memory_info.vms / 1024**2,
            'percent': self.process.memory_percent(),
            'available_gb': virtual_memory.available / 1024**3,
            'system_usage_percent': virtual_memory.percent
        }

        # 记录历史
        self.memory_history.append(current_info)
        if len(self.memory_history) > self.max_history_size:
            self.memory_history.pop(0)

        return current_info

    def get_memory_trend(self, window_size: int = 10) -> Dict[str, float]:
        """获取内存使用趋势"""
        if len(self.memory_history) < 2:
            return {'trend_mb_per_sec': 0.0, 'volatility_mb': 0.0}

        recent_history = self.memory_history[-window_size:]
        times = [info['timestamp'] for info in recent_history]
        rss_values = [info['rss_mb'] for info in recent_history]

        # 计算趋势（线性回归）
        if len(times) > 1:
            time_span = times[-1] - times[0]
            rss_change = rss_values[-1] - rss_values[0]
            trend_mb_per_sec = rss_change / time_span if time_span > 0 else 0.0
        else:
            trend_mb_per_sec = 0.0

        # 计算波动性
        if len(rss_values) > 1:
            volatility_mb = np.std(rss_values)
        else:
            volatility_mb = 0.0

        return {
            'trend_mb_per_sec': trend_mb_per_sec,
            'volatility_mb': volatility_mb,
            'current_rss_mb': rss_values[-1] if rss_values else 0.0
        }

    def is_memory_pressure_high(self, threshold_percent: float = 80.0) -> bool:
        """检查内存压力是否过高"""
        current_info = self.get_memory_info()
        return (current_info['percent'] > threshold_percent or
                current_info['system_usage_percent'] > threshold_percent)

    def suggest_gc(self) -> bool:
        """建议是否需要垃圾回收"""
        trend = self.get_memory_trend()
        # 如果内存持续增长且当前使用率较高，建议GC
        return (trend['trend_mb_per_sec'] > 10.0 and
                self.get_memory_info()['percent'] > 70.0)

    def force_garbage_collection(self) -> Dict[str, Any]:
        """强制垃圾回收并报告结果"""
        pre_gc_memory = self.get_memory_info()

        # 执行多轮垃圾回收
        collected_objects = []
        for generation in range(3):
            collected = gc.collect()
            collected_objects.append(collected)

        post_gc_memory = self.get_memory_info()

        return {
            'pre_gc_rss_mb': pre_gc_memory['rss_mb'],
            'post_gc_rss_mb': post_gc_memory['rss_mb'],
            'memory_freed_mb': pre_gc_memory['rss_mb'] - post_gc_memory['rss_mb'],
            'collected_objects_by_generation': collected_objects,
            'total_collected_objects': sum(collected_objects)
        }


class ChunkedDataManager:
    """分块数据处理管理器

    智能管理大数据集的分块处理，避免内存溢出，支持自适应分块大小调整。
    """

    def __init__(self,
                 total_items: int = 0,
                 memory_limit_gb: float = 4.0,
                 target_memory_usage_percent: float = 70.0,
                 min_chunk_size: int = 100,
                 max_chunk_size: int = 10000):
        """初始化分块数据管理器

        Args:
            total_items: 总数据项数量
            memory_limit_gb: 内存限制（GB）
            target_memory_usage_percent: 目标内存使用百分比
            min_chunk_size: 最小块大小
            max_chunk_size: 最大块大小
        """
        self.total_items = total_items
        self.memory_limit_bytes = memory_limit_gb * 1024**3
        self.target_memory_usage_percent = target_memory_usage_percent
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size

        self.memory_monitor = MemoryMonitor()
        self.chunk_size = self._calculate_initial_chunk_size()
        self.active_chunks: Dict[int, Any] = {}
        self.processing_stats = {
            'total_chunks_processed': 0,
            'total_processing_time': 0.0,
            'avg_chunk_time': 0.0,
            'memory_errors': 0,
            'gc_forced_count': 0
        }

        logger.info(f"分块数据管理器初始化: 总数={total_items}, "
                   f"内存限制={memory_limit_gb}GB, 初始块大小={self.chunk_size}")

    def _calculate_initial_chunk_size(self) -> int:
        """计算初始块大小"""
        # 估算单个要素的内存占用
        estimated_item_size_bytes = 500  # 经验值，可根据实际数据调整
        available_memory_bytes = psutil.virtual_memory().available * 0.6  # 使用60%可用内存

        # 计算理论最大块大小
        max_items_by_memory = int(available_memory_bytes / estimated_item_size_bytes)

        # 考虑处理过程中的内存增长（3倍余量）
        safe_chunk_size = max_items_by_memory // 3

        # 确保块大小在合理范围内
        chunk_size = max(self.min_chunk_size,
                        min(safe_chunk_size, self.max_chunk_size))

        # 如果总数据量较小，块大小不超过总数据量
        if self.total_items > 0:
            chunk_size = min(chunk_size, self.total_items)

        return chunk_size

    def adjust_chunk_size(self, performance_metrics: Dict[str, float]) -> int:
        """根据性能指标调整块大小"""
        current_memory_percent = self.memory_monitor.get_memory_info()['percent']
        avg_chunk_time = performance_metrics.get('avg_chunk_time', 1.0)

        # 内存压力过高时减小块大小
        if current_memory_percent > self.target_memory_usage_percent:
            new_size = max(self.min_chunk_size, int(self.chunk_size * 0.7))
            logger.info(f"内存压力过高，减小块大小: {self.chunk_size} -> {new_size}")
            self.chunk_size = new_size
            return new_size

        # 处理时间过长时减小块大小
        if avg_chunk_time > 30.0:  # 超过30秒
            new_size = max(self.min_chunk_size, int(self.chunk_size * 0.8))
            logger.info(f"处理时间过长，减小块大小: {self.chunk_size} -> {new_size}")
            self.chunk_size = new_size
            return new_size

        # 内存充足且处理时间合理时，尝试增大块大小
        if (current_memory_percent < self.target_memory_usage_percent * 0.6 and
            avg_chunk_time < 10.0):
            new_size = min(self.max_chunk_size, int(self.chunk_size * 1.2))
            logger.info(f"内存充足，增大块大小: {self.chunk_size} -> {new_size}")
            self.chunk_size = new_size
            return new_size

        return self.chunk_size

    def process_in_chunks(self,
                         data_generator: Iterator[Any],
                         processing_function: Callable[[List[Any]], List[Any]],
                         progress_callback: Optional[Callable[[float, int, int], None]] = None) -> List[Any]:
        """分块处理数据

        Args:
            data_generator: 数据生成器
            processing_function: 处理函数
            progress_callback: 进度回调函数

        Returns:
            处理结果列表
        """
        logger.info(f"开始分块处理，块大小: {self.chunk_size}")
        start_time = time.time()

        results = []
        chunk_idx = 0
        processed_items = 0
        chunk_times = []

        try:
            while True:
                chunk_start_time = time.time()

                # 获取下一个数据块
                chunk_data = list(islice(data_generator, self.chunk_size))

                if not chunk_data:
                    break  # 数据处理完毕

                # 检查内存压力
                if self.memory_monitor.is_memory_pressure_high():
                    logger.warning("内存压力过高，执行垃圾回收")
                    gc_result = self.memory_monitor.force_garbage_collection()
                    self.processing_stats['gc_forced_count'] += 1

                    # 如果垃圾回收后内存压力仍然过高，减小块大小
                    if self.memory_monitor.is_memory_pressure_high():
                        self.chunk_size = max(self.min_chunk_size, int(self.chunk_size * 0.5))
                        logger.warning(f"减小块大小以应对内存压力: {self.chunk_size}")

                # 处理当前块
                try:
                    chunk_result = processing_function(chunk_data)
                    results.extend(chunk_result)

                    # 更新统计信息
                    chunk_time = time.time() - chunk_start_time
                    chunk_times.append(chunk_time)
                    processed_items += len(chunk_data)
                    chunk_idx += 1

                    self.processing_stats['total_chunks_processed'] += 1

                    # 进度回调
                    if progress_callback and self.total_items > 0:
                        progress = processed_items / self.total_items * 100
                        progress_callback(progress, chunk_idx, -1)

                    # 定期调整块大小
                    if chunk_idx % 5 == 0 and chunk_times:
                        avg_chunk_time = np.mean(chunk_times[-5:])
                        performance_metrics = {'avg_chunk_time': avg_chunk_time}
                        self.adjust_chunk_size(performance_metrics)

                    # 定期清理内存
                    if chunk_idx % 10 == 0:
                        del chunk_data
                        gc.collect()

                    logger.debug(f"块 {chunk_idx} 处理完成，"
                               f"数据项: {len(chunk_data)}, "
                               f"结果数: {len(chunk_result)}, "
                               f"耗时: {chunk_time:.2f}s")

                except MemoryError:
                    logger.error(f"块 {chunk_idx} 处理时内存不足")
                    self.processing_stats['memory_errors'] += 1

                    # 强制垃圾回收并减小块大小
                    self.memory_monitor.force_garbage_collection()
                    self.chunk_size = max(self.min_chunk_size, int(self.chunk_size * 0.5))

                    # 重试处理更小的块
                    retry_chunk_size = min(len(chunk_data), self.chunk_size)
                    retry_data = chunk_data[:retry_chunk_size]

                    logger.info(f"重试处理更小的块，大小: {retry_chunk_size}")
                    chunk_result = processing_function(retry_data)
                    results.extend(chunk_result)

        except Exception as e:
            logger.error(f"分块处理失败: {str(e)}")
            raise

        # 计算总体统计
        total_time = time.time() - start_time
        self.processing_stats['total_processing_time'] = total_time

        if chunk_times:
            self.processing_stats['avg_chunk_time'] = np.mean(chunk_times)

        logger.info(f"分块处理完成: 总块数={chunk_idx}, "
                   f"处理数据项={processed_items}, "
                   f"总结果数={len(results)}, "
                   f"总耗时={total_time:.2f}s, "
                   f"平均块耗时={self.processing_stats['avg_chunk_time']:.2f}s")

        return results

    def get_processing_stats(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        memory_info = self.memory_monitor.get_memory_info()
        memory_trend = self.memory_monitor.get_memory_trend()

        return {
            'chunk_size': self.chunk_size,
            'total_items': self.total_items,
            'processing_stats': self.processing_stats,
            'memory_info': memory_info,
            'memory_trend': memory_trend,
            'memory_pressure_high': self.memory_monitor.is_memory_pressure_high()
        }


class MMapDataProcessor:
    """内存映射文件处理器

    处理超大数据集，使用内存映射技术避免将整个文件加载到内存。
    支持分段处理和异步IO操作。
    """

    def __init__(self,
                 file_path: str,
                 segment_size_mb: int = 100,
                 create_temp_index: bool = True):
        """初始化内存映射处理器

        Args:
            file_path: 文件路径
            segment_size_mb: 段大小（MB）
            create_temp_index: 是否创建临时索引
        """
        self.file_path = file_path
        self.segment_size_bytes = segment_size_mb * 1024**2
        self.create_temp_index = create_temp_index

        self.mmap_handler = None
        self.file_size = 0
        self.segment_count = 0
        self.temp_index_path = None

        # 验证文件存在
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        self.file_size = os.path.getsize(file_path)
        self.segment_count = (self.file_size + self.segment_size_bytes - 1) // self.segment_size_bytes

        logger.info(f"内存映射处理器初始化: 文件={file_path}, "
                   f"大小={self.file_size / 1024**2:.2f}MB, "
                   f"段数={self.segment_count}")

    def __enter__(self):
        """上下文管理器入口"""
        self.open_mmap()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close_mmap()

    def open_mmap(self) -> mmap.mmap:
        """打开内存映射"""
        try:
            with open(self.file_path, 'r+b') as f:
                self.mmap_handler = mmap.mmap(f.fileno(), 0)
            logger.info(f"内存映射打开成功: {self.file_path}")
            return self.mmap_handler
        except Exception as e:
            logger.error(f"内存映射打开失败: {str(e)}")
            raise

    def close_mmap(self):
        """关闭内存映射"""
        if self.mmap_handler:
            try:
                self.mmap_handler.close()
                self.mmap_handler = None
                logger.info("内存映射已关闭")
            except Exception as e:
                logger.warning(f"关闭内存映射时出错: {str(e)}")

        # 清理临时索引文件
        if self.temp_index_path and os.path.exists(self.temp_index_path):
            try:
                os.remove(self.temp_index_path)
                self.temp_index_path = None
            except Exception as e:
                logger.warning(f"删除临时索引文件失败: {str(e)}")

    def process_segments(self,
                        processing_function: Callable[[bytes, int], List[Any]],
                        progress_callback: Optional[Callable[[float], None]] = None) -> List[Any]:
        """分段处理内存映射数据

        Args:
            processing_function: 段处理函数
            progress_callback: 进度回调函数

        Returns:
            所有段的处理结果
        """
        if self.mmap_handler is None:
            raise RuntimeError("内存映射未打开，请先调用open_mmap()")

        logger.info(f"开始分段处理，总段数: {self.segment_count}")
        start_time = time.time()

        all_results = []
        processed_segments = 0

        try:
            for segment_idx in range(self.segment_count):
                offset = segment_idx * self.segment_size_bytes
                segment_end = min(offset + self.segment_size_bytes, self.file_size)
                segment_size = segment_end - offset

                # 读取数据段
                segment_data = self.mmap_handler[offset:segment_end]

                # 处理数据段
                try:
                    segment_result = processing_function(segment_data, offset)
                    all_results.extend(segment_result)

                    processed_segments += 1

                    # 进度回调
                    if progress_callback:
                        progress = processed_segments / self.segment_count * 100
                        progress_callback(progress)

                    logger.debug(f"段 {segment_idx + 1}/{self.segment_count} 处理完成, "
                               f"数据大小: {segment_size / 1024**2:.2f}MB, "
                               f"结果数: {len(segment_result)}")

                except Exception as e:
                    logger.error(f"段 {segment_idx} 处理失败: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"分段处理失败: {str(e)}")
            raise

        total_time = time.time() - start_time
        logger.info(f"分段处理完成: 处理段数={processed_segments}/{self.segment_count}, "
                   f"总结果数={len(all_results)}, "
                   f"总耗时={total_time:.2f}s")

        return all_results

    def create_line_index(self) -> Dict[int, int]:
        """创建行索引（适用于文本文件）"""
        if self.mmap_handler is None:
            raise RuntimeError("内存映射未打开，请先调用open_mmap()")

        logger.info("创建行索引...")
        start_time = time.time()

        line_positions = []
        position = 0

        # 逐行扫描，记录行起始位置
        for line in iter(self.mmap_handler.readline, b''):
            line_positions.append(position)
            position = self.mmap_handler.tell()

            # 定期检查内存使用
            if len(line_positions) % 100000 == 0:
                logger.debug(f"已索引 {len(line_positions)} 行")

        # 保存索引到临时文件
        if self.create_temp_index:
            temp_fd, self.temp_index_path = tempfile.mkstemp(suffix='.idx')
            try:
                with os.fdopen(temp_fd, 'wb') as f:
                    pickle.dump(line_positions, f)
                logger.info(f"行索引已保存到: {self.temp_index_path}")
            except Exception as e:
                logger.warning(f"保存行索引失败: {str(e)}")
                if os.path.exists(self.temp_index_path):
                    os.remove(self.temp_index_path)
                self.temp_index_path = None

        index_time = time.time() - start_time
        logger.info(f"行索引创建完成: 总行数={len(line_positions)}, 耗时={index_time:.2f}s")

        return {i: pos for i, pos in enumerate(line_positions)}

    def get_memory_usage(self) -> Dict[str, float]:
        """获取内存使用信息"""
        process = psutil.Process()
        memory_info = process.memory_info()

        return {
            'rss_mb': memory_info.rss / 1024**2,
            'vms_mb': memory_info.vms / 1024**2,
            'memory_percent': process.memory_percent(),
            'file_size_mb': self.file_size / 1024**2,
            'segment_count': self.segment_count,
            'segment_size_mb': self.segment_size_bytes / 1024**2
        }


class StreamProcessor:
    """流式数据处理器

    用于处理流式数据或超大文件，支持实时处理和内存优化。
    """

    def __init__(self,
                 buffer_size: int = 8192,
                 max_memory_usage_mb: float = 512.0):
        """初始化流式处理器

        Args:
            buffer_size: 缓冲区大小
            max_memory_usage_mb: 最大内存使用量（MB）
        """
        self.buffer_size = buffer_size
        self.max_memory_usage_bytes = max_memory_usage_mb * 1024**2
        self.memory_monitor = MemoryMonitor()

    def process_file_stream(self,
                           file_path: str,
                           line_processor: Callable[[str], Any],
                           batch_processor: Optional[Callable[[List[Any]], List[Any]]] = None,
                           batch_size: int = 1000) -> List[Any]:
        """流式处理文件

        Args:
            file_path: 文件路径
            line_processor: 行处理函数
            batch_processor: 批处理函数（可选）
            batch_size: 批处理大小

        Returns:
            处理结果列表
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        logger.info(f"开始流式处理文件: {file_path}")
        start_time = time.time()

        results = []
        batch_results = []

        try:
            with open(file_path, 'r', encoding='utf-8', buffering=self.buffer_size) as f:
                line_count = 0

                for line in f:
                    try:
                        # 处理单行
                        line_result = line_processor(line.strip())

                        if line_result is not None:
                            if batch_processor:
                                batch_results.append(line_result)

                                # 批处理
                                if len(batch_results) >= batch_size:
                                    batch_output = batch_processor(batch_results)
                                    results.extend(batch_output)
                                    batch_results = []
                            else:
                                results.append(line_result)

                        line_count += 1

                        # 定期检查内存使用
                        if line_count % 10000 == 0:
                            if self.memory_monitor.is_memory_pressure_high():
                                logger.warning("内存压力过高，执行垃圾回收")
                                self.memory_monitor.force_garbage_collection()

                            logger.debug(f"已处理 {line_count} 行")

                    except Exception as e:
                        logger.warning(f"处理第 {line_count} 行时出错: {str(e)}")
                        continue

                # 处理剩余的批量数据
                if batch_processor and batch_results:
                    batch_output = batch_processor(batch_results)
                    results.extend(batch_output)

        except Exception as e:
            logger.error(f"流式处理失败: {str(e)}")
            raise

        total_time = time.time() - start_time
        logger.info(f"流式处理完成: 处理行数={line_count}, "
                   f"结果数={len(results)}, 耗时={total_time:.2f}s")

        return results