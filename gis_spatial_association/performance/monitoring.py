"""
性能监控和基准测试系统

提供全面的性能监控、基准测试和性能分析功能。
支持实时监控、性能瓶颈分析和优化建议。

Author: CCPM Auto Development System
"""

import logging
import time
import os
import json
import threading
import statistics
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
from collections import defaultdict, deque
import psutil
import numpy as np

try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    HAS_PLOTTING = True
except ImportError:
    HAS_PLOTTING = False
    logging.warning("Matplotlib/Seaborn not available, plotting functions will be disabled")

try:
    from shapely.geometry import Point, LineString, Polygon
    import geopandas as gpd
    HAS_GEOSPATIAL = True
except ImportError:
    HAS_GEOSPATIAL = False
    logging.warning("GeoPandas/Shapely not available, some benchmarks will be skipped")

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """性能指标数据结构"""
    name: str
    value: float
    unit: str
    timestamp: float
    category: str = 'general'
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class BenchmarkResult:
    """基准测试结果"""
    test_name: str
    execution_time: float
    memory_peak_mb: float
    cpu_usage_percent: float
    success: bool
    error_message: Optional[str] = None
    metrics: Optional[Dict[str, float]] = None
    dataset_size: int = 0


@dataclass
class SystemResourceSnapshot:
    """系统资源快照"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_available_gb: float
    disk_usage_percent: float
    network_io: Dict[str, int]
    process_count: int


class PerformanceProfiler:
    """性能分析器"""

    def __init__(self, name: str = "default"):
        """初始化性能分析器

        Args:
            name: 分析器名称
        """
        self.name = name
        self.metrics: List[PerformanceMetric] = []
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.baseline_memory: Optional[float] = None
        self.peak_memory: Optional[float] = None

    def __enter__(self):
        """上下文管理器入口"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop()

    def start(self):
        """开始性能分析"""
        self.start_time = time.time()
        process = psutil.Process()
        self.baseline_memory = process.memory_info().rss / 1024**2  # MB
        self.peak_memory = self.baseline_memory
        logger.debug(f"性能分析器 '{self.name}' 已启动")

    def stop(self):
        """停止性能分析"""
        if self.start_time is None:
            raise RuntimeError("分析器尚未启动，请先调用start()")

        self.end_time = time.time()

        # 记录最终内存使用
        process = psutil.Process()
        current_memory = process.memory_info().rss / 1024**2
        self.peak_memory = max(self.peak_memory or 0, current_memory)

        execution_time = self.end_time - self.start_time

        # 记录基本性能指标
        self.add_metric('execution_time', execution_time, 'seconds', 'timing')
        self.add_metric('memory_delta', (self.peak_memory - self.baseline_memory), 'MB', 'memory')
        self.add_metric('peak_memory', self.peak_memory, 'MB', 'memory')

        logger.debug(f"性能分析器 '{self.name}' 已停止: "
                    f"耗时={execution_time:.3f}s, "
                    f"内存增量={(self.peak_memory - self.baseline_memory):.2f}MB")

    def add_metric(self, name: str, value: float, unit: str, category: str = 'general', metadata: Optional[Dict[str, Any]] = None):
        """添加性能指标"""
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            timestamp=time.time(),
            category=category,
            metadata=metadata
        )
        self.metrics.append(metric)

    def get_metric(self, name: str) -> Optional[float]:
        """获取指定名称的指标值"""
        for metric in self.metrics:
            if metric.name == name:
                return metric.value
        return None

    def get_metrics_by_category(self, category: str) -> List[PerformanceMetric]:
        """获取指定类别的指标"""
        return [m for m in self.metrics if m.category == category]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'name': self.name,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': (self.end_time or 0) - (self.start_time or 0),
            'baseline_memory_mb': self.baseline_memory,
            'peak_memory_mb': self.peak_memory,
            'metrics': [asdict(m) for m in self.metrics]
        }


class ResourceMonitor:
    """系统资源监控器"""

    def __init__(self, interval: float = 1.0, max_history: int = 3600):
        """初始化资源监控器

        Args:
            interval: 监控间隔（秒）
            max_history: 最大历史记录数
        """
        self.interval = interval
        self.max_history = max_history
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.resource_history: deque = deque(maxlen=max_history)
        self.network_io_baseline: Optional[Dict[str, int]] = None

    def start_monitoring(self):
        """开始资源监控"""
        if self.monitoring:
            return

        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

        # 记录初始网络IO
        self.network_io_baseline = psutil.net_io_counters()._asdict()

        logger.info(f"资源监控已启动，间隔: {self.interval}s")

    def stop_monitoring(self):
        """停止资源监控"""
        if not self.monitoring:
            return

        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)

        logger.info("资源监控已停止")

    def _monitor_loop(self):
        """监控循环"""
        while self.monitoring:
            try:
                snapshot = self._take_snapshot()
                self.resource_history.append(snapshot)
                time.sleep(self.interval)
            except Exception as e:
                logger.warning(f"资源监控出错: {str(e)}")
                time.sleep(self.interval)

    def _take_snapshot(self) -> SystemResourceSnapshot:
        """获取系统资源快照"""
        # CPU和内存
        cpu_percent = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()

        # 磁盘使用率（当前目录）
        disk_usage = psutil.disk_usage('.')
        disk_percent = disk_usage.used / disk_usage.total * 100

        # 网络IO
        current_network = psutil.net_io_counters()._asdict()
        network_io = {}
        if self.network_io_baseline:
            for key in current_network:
                network_io[key] = current_network[key] - self.network_io_baseline.get(key, 0)
        else:
            network_io = current_network

        # 进程数
        process_count = len(psutil.pids())

        return SystemResourceSnapshot(
            timestamp=time.time(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_available_gb=memory.available / 1024**3,
            disk_usage_percent=disk_percent,
            network_io=network_io,
            process_count=process_count
        )

    def get_current_snapshot(self) -> Optional[SystemResourceSnapshot]:
        """获取最新的资源快照"""
        return self.resource_history[-1] if self.resource_history else None

    def get_average_stats(self, window_seconds: int = 60) -> Dict[str, float]:
        """获取平均统计信息"""
        if not self.resource_history:
            return {}

        cutoff_time = time.time() - window_seconds
        recent_snapshots = [s for s in self.resource_history if s.timestamp > cutoff_time]

        if not recent_snapshots:
            return {}

        return {
            'avg_cpu_percent': statistics.mean([s.cpu_percent for s in recent_snapshots]),
            'avg_memory_percent': statistics.mean([s.memory_percent for s in recent_snapshots]),
            'max_cpu_percent': max([s.cpu_percent for s in recent_snapshots]),
            'max_memory_percent': max([s.memory_percent for s in recent_snapshots]),
            'avg_memory_available_gb': statistics.mean([s.memory_available_gb for s in recent_snapshots])
        }

    def get_peak_usage(self) -> Dict[str, float]:
        """获取峰值使用情况"""
        if not self.resource_history:
            return {}

        return {
            'peak_cpu_percent': max([s.cpu_percent for s in self.resource_history]),
            'peak_memory_percent': max([s.memory_percent for s in self.resource_history]),
            'min_memory_available_gb': min([s.memory_available_gb for s in self.resource_history])
        }


class BenchmarkSuite:
    """基准测试套件"""

    def __init__(self, name: str = "spatial_performance"):
        """初始化基准测试套件

        Args:
            name: 测试套件名称
        """
        self.name = name
        self.results: List[BenchmarkResult] = []
        self.profiler = PerformanceProfiler(f"benchmark_{name}")

    def run_benchmark(self,
                     test_function: Callable,
                     test_name: str,
                     iterations: int = 1,
                     warmup_iterations: int = 0,
                     **kwargs) -> BenchmarkResult:
        """运行单个基准测试

        Args:
            test_function: 测试函数
            test_name: 测试名称
            iterations: 迭代次数
            warmup_iterations: 预热迭代次数
            **kwargs: 传递给测试函数的参数

        Returns:
            基准测试结果
        """
        logger.info(f"开始基准测试: {test_name} (迭代: {iterations}, 预热: {warmup_iterations})")

        # 预热
        for i in range(warmup_iterations):
            try:
                test_function(**kwargs)
            except Exception as e:
                logger.warning(f"预热第{i+1}次失败: {str(e)}")

        # 正式测试
        execution_times = []
        memory_peaks = []
        cpu_usages = []
        success_count = 0

        for i in range(iterations):
            try:
                with PerformanceProfiler(f"{test_name}_iteration_{i}") as profiler:
                    result = test_function(**kwargs)

                execution_times.append(profiler.get_metric('execution_time') or 0.0)
                memory_peaks.append(profiler.get_metric('peak_memory') or 0.0)

                # 获取CPU使用率
                cpu_percent = psutil.cpu_percent(interval=None)
                cpu_usages.append(cpu_percent)

                success_count += 1

                logger.debug(f"测试 {test_name} 迭代 {i+1} 完成: "
                           f"耗时={execution_times[-1]:.3f}s, "
                           f"内存={memory_peaks[-1]:.2f}MB")

            except Exception as e:
                logger.error(f"测试 {test_name} 迭代 {i+1} 失败: {str(e)}")
                execution_times.append(float('inf'))
                memory_peaks.append(0.0)
                cpu_usages.append(0.0)

        # 计算统计结果
        successful_times = [t for t in execution_times if t != float('inf')]
        if successful_times:
            avg_time = statistics.mean(successful_times)
            median_time = statistics.median(successful_times)
            std_time = statistics.stdev(successful_times) if len(successful_times) > 1 else 0.0
        else:
            avg_time = median_time = std_time = float('inf')

        successful_memories = [m for i, m in enumerate(memory_peaks) if execution_times[i] != float('inf')]
        avg_memory = statistics.mean(successful_memories) if successful_memories else 0.0

        successful_cpus = [c for i, c in enumerate(cpu_usages) if execution_times[i] != float('inf')]
        avg_cpu = statistics.mean(successful_cpus) if successful_cpus else 0.0

        # 创建结果对象
        result = BenchmarkResult(
            test_name=test_name,
            execution_time=avg_time,
            memory_peak_mb=avg_memory,
            cpu_usage_percent=avg_cpu,
            success=success_count > 0,
            error_message=None if success_count > 0 else f"所有{iterations}次迭代都失败",
            metrics={
                'iterations': iterations,
                'success_count': success_count,
                'median_time': median_time,
                'std_time': std_time,
                'min_time': min(successful_times) if successful_times else float('inf'),
                'max_time': max(successful_times) if successful_times else float('inf')
            },
            dataset_size=kwargs.get('dataset_size', 0)
        )

        self.results.append(result)

        logger.info(f"基准测试完成: {test_name}, "
                   f"平均耗时={avg_time:.3f}s, "
                   f"内存={avg_memory:.2f}MB, "
                   f"成功率={success_count}/{iterations}")

        return result

    def run_spatial_benchmarks(self) -> Dict[str, BenchmarkResult]:
        """运行空间算法基准测试"""
        if not HAS_GEOSPATIAL:
            logger.warning("空间库不可用，跳过空间基准测试")
            return {}

        logger.info("开始空间算法基准测试")
        results = {}

        # 测试数据集大小
        dataset_sizes = [1000, 5000, 10000, 20000]

        for size in dataset_sizes:
            logger.info(f"测试数据集大小: {size}")

            # 生成测试数据
            points = self._generate_test_points(size)
            lines = self._generate_test_lines(size // 10)

            # 点线关联基准测试
            if len(points) > 0 and len(lines) > 0:
                result = self.run_benchmark(
                    test_function=self._benchmark_point_line_association,
                    test_name=f"point_line_association_{size}",
                    iterations=3,
                    points=points,
                    lines=lines,
                    dataset_size=size
                )
                results[f"point_line_association_{size}"] = result

            # 空间索引基准测试
            result = self.run_benchmark(
                test_function=self._benchmark_spatial_index,
                test_name=f"spatial_index_{size}",
                iterations=3,
                geometries=points,
                dataset_size=size
            )
            results[f"spatial_index_{size}"] = result

            # 几何操作基准测试
            result = self.run_benchmark(
                test_function=self._benchmark_geometry_operations,
                test_name=f"geometry_operations_{size}",
                iterations=3,
                geometries=points,
                dataset_size=size
            )
            results[f"geometry_operations_{size}"] = result

        return results

    def _generate_test_points(self, count: int) -> List[Point]:
        """生成测试点"""
        points = []
        for i in range(count):
            x = np.random.uniform(0, 1000)
            y = np.random.uniform(0, 1000)
            points.append(Point(x, y))
        return points

    def _generate_test_lines(self, count: int) -> List[LineString]:
        """生成测试线"""
        lines = []
        for i in range(count):
            points = []
            for j in range(np.random.randint(2, 6)):
                x = np.random.uniform(0, 1000)
                y = np.random.uniform(0, 1000)
                points.append((x, y))
            lines.append(LineString(points))
        return lines

    def _benchmark_point_line_association(self, points: List[Point], lines: List[LineString]) -> int:
        """点线关联基准测试函数"""
        associations = 0
        for point in points:
            min_distance = float('inf')
            for line in lines:
                distance = point.distance(line)
                if distance < min_distance:
                    min_distance = distance
            if min_distance < 10.0:  # 阈值
                associations += 1
        return associations

    def _benchmark_spatial_index(self, geometries: List[Point]) -> int:
        """空间索引基准测试函数"""
        try:
            from .indexing import AdaptiveSpatialIndex
            index = AdaptiveSpatialIndex(len(geometries))
            spatial_index = index.build_index(geometries)

            # 执行一些查询测试
            query_count = 0
            for geom in geometries[:min(100, len(geometries))]:
                results = spatial_index.query(geom)
                query_count += len(results)

            return query_count
        except Exception as e:
            logger.error(f"空间索引测试失败: {str(e)}")
            return 0

    def _benchmark_geometry_operations(self, geometries: List[Point]) -> int:
        """几何操作基准测试函数"""
        operations = 0
        for i, geom in enumerate(geometries[:-1]):
            next_geom = geometries[i + 1]
            # 执行各种几何操作
            _ = geom.distance(next_geom)
            _ = geom.buffer(1.0)
            _ = geom.within(next_geom.buffer(10.0))
            operations += 3
        return operations

    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        if not self.results:
            return {"error": "没有基准测试结果"}

        # 按测试名称分组
        grouped_results = defaultdict(list)
        for result in self.results:
            test_type = result.test_name.rsplit('_', 1)[0]  # 移除数据集大小后缀
            grouped_results[test_type].append(result)

        # 计算统计信息
        report = {
            'suite_name': self.name,
            'total_tests': len(self.results),
            'successful_tests': len([r for r in self.results if r.success]),
            'test_summary': {},
            'performance_trends': {},
            'recommendations': []
        }

        for test_type, results_list in grouped_results.items():
            successful_results = [r for r in results_list if r.success]

            if successful_results:
                execution_times = [r.execution_time for r in successful_results]
                memory_usages = [r.memory_peak_mb for r in successful_results]
                dataset_sizes = [r.dataset_size for r in successful_results]

                report['test_summary'][test_type] = {
                    'count': len(successful_results),
                    'avg_execution_time': statistics.mean(execution_times),
                    'min_execution_time': min(execution_times),
                    'max_execution_time': max(execution_times),
                    'avg_memory_usage': statistics.mean(memory_usages),
                    'performance_per_item': self._calculate_performance_per_item(execution_times, dataset_sizes)
                }

                # 性能趋势分析
                if len(dataset_sizes) > 1:
                    report['performance_trends'][test_type] = self._analyze_performance_trends(
                        execution_times, dataset_sizes)

        # 生成优化建议
        report['recommendations'] = self._generate_recommendations(grouped_results)

        return report

    def _calculate_performance_per_item(self, times: List[float], sizes: List[int]) -> float:
        """计算每项性能指标"""
        if not times or not sizes:
            return 0.0

        per_item_rates = [size / time if time > 0 else 0 for time, size in zip(times, sizes)]
        return statistics.mean(per_item_rates)

    def _analyze_performance_trends(self, times: List[float], sizes: List[int]) -> Dict[str, float]:
        """分析性能趋势"""
        if len(times) < 2 or len(sizes) < 2:
            return {}

        # 简单的线性趋势分析
        sorted_pairs = sorted(zip(sizes, times))
        sizes_sorted, times_sorted = zip(*sorted_pairs)

        # 计算增长率
        growth_rates = []
        for i in range(1, len(sizes_sorted)):
            size_growth = (sizes_sorted[i] - sizes_sorted[i-1]) / sizes_sorted[i-1]
            time_growth = (times_sorted[i] - times_sorted[i-1]) / max(times_sorted[i-1], 0.001)
            growth_rate = time_growth / max(size_growth, 0.001) if size_growth > 0 else float('inf')
            growth_rates.append(growth_rate)

        return {
            'avg_growth_rate': statistics.mean(growth_rates) if growth_rates else 0.0,
            'max_growth_rate': max(growth_rates) if growth_rates else 0.0,
            'complexity_order': 'linear' if statistics.mean(growth_rates) < 2.0 else 'quadratic'
        }

    def _generate_recommendations(self, grouped_results: Dict[str, List[BenchmarkResult]]) -> List[str]:
        """生成性能优化建议"""
        recommendations = []

        for test_type, results_list in grouped_results.items():
            successful_results = [r for r in results_list if r.success]

            if not successful_results:
                recommendations.append(f"{test_type}: 所有测试都失败，需要检查算法实现")
                continue

            avg_execution_time = statistics.mean([r.execution_time for r in successful_results])
            avg_memory_usage = statistics.mean([r.memory_peak_mb for r in successful_results])

            # 执行时间建议
            if avg_execution_time > 60.0:  # 超过1分钟
                recommendations.append(f"{test_type}: 执行时间过长({avg_execution_time:.1f}s)，建议优化算法或使用并行处理")

            # 内存使用建议
            if avg_memory_usage > 1000.0:  # 超过1GB
                recommendations.append(f"{test_type}: 内存使用过高({avg_memory_usage:.1f}MB)，建议使用分块处理或流式算法")

            # 性能一致性建议
            execution_times = [r.execution_time for r in successful_results]
            if len(execution_times) > 1:
                std_dev = statistics.stdev(execution_times)
                mean = statistics.mean(execution_times)
                cv = std_dev / mean if mean > 0 else 0

                if cv > 0.3:  # 变异系数超过30%
                    recommendations.append(f"{test_type}: 性能波动较大，建议优化内存管理或减少系统负载影响")

        return recommendations

    def save_results(self, file_path: str):
        """保存基准测试结果"""
        try:
            results_data = {
                'suite_name': self.name,
                'timestamp': time.time(),
                'results': [asdict(r) for r in self.results],
                'performance_report': self.get_performance_report()
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, indent=2, ensure_ascii=False)

            logger.info(f"基准测试结果已保存到: {file_path}")

        except Exception as e:
            logger.error(f"保存基准测试结果失败: {str(e)}")


class PerformanceMonitor:
    """综合性能监控器"""

    def __init__(self,
                 enable_resource_monitoring: bool = True,
                 resource_interval: float = 1.0,
                 enable_profiling: bool = True):
        """初始化性能监控器

        Args:
            enable_resource_monitoring: 是否启用资源监控
            resource_interval: 资源监控间隔
            enable_profiling: 是否启用性能分析
        """
        self.enable_resource_monitoring = enable_resource_monitoring
        self.enable_profiling = enable_profiling

        self.resource_monitor = None
        if enable_resource_monitoring:
            self.resource_monitor = ResourceMonitor(resource_interval)

        self.active_profilers: Dict[str, PerformanceProfiler] = {}
        self.benchmark_suite = BenchmarkSuite()

        logger.info("性能监控器初始化完成")

    def start_monitoring(self):
        """开始性能监控"""
        if self.resource_monitor:
            self.resource_monitor.start_monitoring()

        logger.info("性能监控已启动")

    def stop_monitoring(self):
        """停止性能监控"""
        if self.resource_monitor:
            self.resource_monitor.stop_monitoring()

        # 停止所有活动分析器
        for profiler in self.active_profilers.values():
            if profiler.start_time and not profiler.end_time:
                profiler.stop()

        logger.info("性能监控已停止")

    def start_profiler(self, name: str) -> str:
        """启动性能分析器"""
        if not self.enable_profiling:
            logger.warning("性能分析功能未启用")
            return ""

        profiler_id = f"{name}_{time.time()}"
        profiler = PerformanceProfiler(name)
        profiler.start()

        self.active_profilers[profiler_id] = profiler
        return profiler_id

    def stop_profiler(self, profiler_id: str) -> Optional[PerformanceProfiler]:
        """停止指定的性能分析器"""
        if profiler_id not in self.active_profilers:
            logger.warning(f"未找到分析器: {profiler_id}")
            return None

        profiler = self.active_profilers[profiler_id]
        profiler.stop()

        # 从活动列表中移除
        self.active_profilers.pop(profiler_id, None)

        return profiler

    def get_monitoring_summary(self) -> Dict[str, Any]:
        """获取监控摘要"""
        summary = {
            'timestamp': time.time(),
            'resource_monitoring_enabled': self.enable_resource_monitoring,
            'profiling_enabled': self.enable_profiling,
            'active_profilers': len(self.active_profilers),
            'completed_profilers': len(self.benchmark_suite.results)
        }

        if self.resource_monitor:
            current_snapshot = self.resource_monitor.get_current_snapshot()
            average_stats = self.resource_monitor.get_average_stats()
            peak_usage = self.resource_monitor.get_peak_usage()

            summary['current_resources'] = asdict(current_snapshot) if current_snapshot else {}
            summary['average_stats'] = average_stats
            summary['peak_usage'] = peak_usage

        return summary

    def run_performance_test(self,
                           test_function: Callable,
                           test_name: str,
                           **kwargs) -> BenchmarkResult:
        """运行性能测试"""
        return self.benchmark_suite.run_benchmark(test_function, test_name, **kwargs)

    def generate_performance_report(self) -> Dict[str, Any]:
        """生成综合性能报告"""
        report = {
            'monitoring_summary': self.get_monitoring_summary(),
            'benchmark_results': self.benchmark_suite.get_performance_report(),
            'recommendations': []
        }

        # 综合优化建议
        if self.resource_monitor:
            current = self.resource_monitor.get_current_snapshot()
            if current and current.cpu_percent > 80:
                report['recommendations'].append("CPU使用率过高，建议优化算法或减少并行度")

            if current and current.memory_percent > 85:
                report['recommendations'].append("内存使用率过高，建议使用分块处理或增加系统内存")

        return report

    def export_report(self, file_path: str, format: str = 'json'):
        """导出性能报告"""
        report = self.generate_performance_report()

        try:
            if format.lower() == 'json':
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)
            else:
                raise ValueError(f"不支持的导出格式: {format}")

            logger.info(f"性能报告已导出到: {file_path}")

        except Exception as e:
            logger.error(f"导出性能报告失败: {str(e)}")


# 全局性能监控实例
_global_monitor: Optional[PerformanceMonitor] = None


def get_global_monitor() -> PerformanceMonitor:
    """获取全局性能监控实例"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor


def start_global_monitoring():
    """启动全局性能监控"""
    monitor = get_global_monitor()
    monitor.start_monitoring()


def stop_global_monitoring():
    """停止全局性能监控"""
    monitor = get_global_monitor()
    monitor.stop_monitoring()


def profile_function(name: str):
    """性能分析装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            monitor = get_global_monitor()
            profiler_id = monitor.start_profiler(name)

            try:
                result = func(*args, **kwargs)
                return result
            finally:
                profiler = monitor.stop_profiler(profiler_id)
                if profiler:
                    logger.debug(f"函数 {name} 性能分析完成: "
                               f"耗时={profiler.get_metric('execution_time'):.3f}s")
        return wrapper
    return decorator