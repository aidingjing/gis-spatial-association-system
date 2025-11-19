#!/usr/bin/env python3
"""
性能优化模块综合测试

测试和验证所有性能优化模块的功能和性能表现。
包括基准测试、压力测试和集成测试。

Author: CCPM Auto Development System
"""

import sys
import os
import time
import logging
import tempfile
import traceback
from typing import List, Dict, Any

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import numpy as np
    import psutil
    import geopandas as gpd
    from shapely.geometry import Point, LineString
    HAS_DEPS = True
except ImportError as e:
    HAS_DEPS = False
    print(f"警告: 缺少依赖库: {e}")

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PerformanceTestSuite:
    """性能测试套件"""

    def __init__(self):
        """初始化测试套件"""
        self.test_results = {}
        self.passed_tests = 0
        self.failed_tests = 0

    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        logger.info("开始性能优化模块综合测试")
        start_time = time.time()

        try:
            # 1. 空间索引测试
            self.test_spatial_indexing()

            # 2. 内存管理测试
            self.test_memory_management()

            # 3. 并行计算测试
            self.test_parallel_processing()

            # 4. 缓存系统测试
            self.test_caching_system()

            # 5. 性能监控测试
            self.test_performance_monitoring()

            # 6. 集成测试
            self.test_integration()

        except Exception as e:
            logger.error(f"测试套件执行出错: {str(e)}")
            traceback.print_exc()

        total_time = time.time() - start_time

        # 生成测试报告
        report = {
            'total_time': total_time,
            'passed_tests': self.passed_tests,
            'failed_tests': self.failed_tests,
            'success_rate': self.passed_tests / max(1, self.passed_tests + self.failed_tests),
            'test_results': self.test_results
        }

        logger.info(f"测试完成: 通过={self.passed_tests}, 失败={self.failed_tests}, "
                   f"成功率={report['success_rate']:.1%}, 耗时={total_time:.2f}s")

        return report

    def test_spatial_indexing(self):
        """测试空间索引模块"""
        logger.info("测试空间索引模块...")

        try:
            from .indexing import AdaptiveSpatialIndex, HierarchicalSpatialIndex
            from .monitoring import PerformanceProfiler

            # 测试数据
            points = [Point(np.random.uniform(0, 1000), np.random.uniform(0, 1000))
                     for _ in range(1000)]

            # 测试自适应空间索引
            with PerformanceProfiler("adaptive_spatial_index") as profiler:
                adaptive_index = AdaptiveSpatialIndex(len(points))
                spatial_index = adaptive_index.build_index(points)

                # 执行查询测试
                query_count = 0
                for point in points[:100]:
                    results = spatial_index.query(point)
                    query_count += len(results)

                # 最近邻查询测试
                for point in points[:50]:
                    nearest = spatial_index.query_nearest(point, 3)
                    query_count += len(nearest)

            self._record_test_result(
                "adaptive_spatial_index",
                True,
                {
                    'execution_time': profiler.get_metric('execution_time'),
                    'memory_delta': profiler.get_metric('memory_delta'),
                    'query_count': query_count,
                    'index_type': adaptive_index.index_type
                }
            )

            # 测试分层空间索引
            if len(points) > 100:
                with PerformanceProfiler("hierarchical_spatial_index") as profiler:
                    hierarchical_index = HierarchicalSpatialIndex(points, levels=3)
                    hierarchical_index.build_hierarchy()

                    # 执行查询测试
                    query_count = 0
                    for point in points[:50]:
                        results = hierarchical_index.query_with_early_termination(point, 10)
                        query_count += len(results)

                self._record_test_result(
                    "hierarchical_spatial_index",
                    True,
                    {
                        'execution_time': profiler.get_metric('execution_time'),
                        'query_count': query_count,
                        'hierarchy_info': hierarchical_index.get_hierarchy_info()
                    }
                )

        except Exception as e:
            logger.error(f"空间索引测试失败: {str(e)}")
            self._record_test_result("spatial_indexing", False, {'error': str(e)})

    def test_memory_management(self):
        """测试内存管理模块"""
        logger.info("测试内存管理模块...")

        try:
            from .memory import ChunkedDataManager, MemoryMonitor, MMapDataProcessor
            from .monitoring import PerformanceProfiler

            # 测试内存监控器
            memory_monitor = MemoryMonitor()
            memory_info = memory_monitor.get_memory_info()
            memory_trend = memory_monitor.get_memory_trend()

            self._record_test_result(
                "memory_monitor",
                True,
                {
                    'current_memory_mb': memory_info['rss_mb'],
                    'memory_percent': memory_info['percent'],
                    'available_memory_gb': memory_info['available_gb']
                }
            )

            # 测试分块数据管理
            def test_data_generator():
                """测试数据生成器"""
                for i in range(10000):
                    yield f"test_data_{i}_{i * 2}_{i * 3}"

            def test_processing_function(data_chunk):
                """测试处理函数"""
                return [item.split('_') for item in data_chunk]

            with PerformanceProfiler("chunked_data_processing") as profiler:
                chunk_manager = ChunkedDataManager(
                    total_items=10000,
                    memory_limit_gb=1.0,
                    min_chunk_size=500,
                    max_chunk_size=2000
                )

                results = chunk_manager.process_in_chunks(
                    test_data_generator(),
                    test_processing_function
                )

            self._record_test_result(
                "chunked_data_manager",
                True,
                {
                    'execution_time': profiler.get_metric('execution_time'),
                    'processed_results': len(results),
                    'chunk_size': chunk_manager.chunk_size,
                    'processing_stats': chunk_manager.get_processing_stats()
                }
            )

            # 测试内存映射文件处理
            # 创建临时测试文件
            with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt') as f:
                for i in range(1000):
                    f.write(f"test_line_{i}_data_{i*2}_{i*3}\n")
                temp_file_path = f.name

            try:
                with PerformanceProfiler("mmap_processing") as profiler:
                    mmap_processor = MMapDataProcessor(temp_file_path, segment_size_mb=1)

                    def segment_processor(segment_data, offset):
                        """段处理函数"""
                        lines = segment_data.decode('utf-8').split('\n')
                        return [line.strip() for line in lines if line.strip()]

                    with mmap_processor:
                        mmap_results = mmap_processor.process_segments(segment_processor)

                self._record_test_result(
                    "mmap_data_processor",
                    True,
                    {
                        'execution_time': profiler.get_metric('execution_time'),
                        'processed_lines': len(mmap_results),
                        'file_size_mb': mmap_processor.file_size / 1024**2,
                        'segment_count': mmap_processor.segment_count
                    }
                )

            finally:
                # 清理临时文件
                os.unlink(temp_file_path)

        except Exception as e:
            logger.error(f"内存管理测试失败: {str(e)}")
            self._record_test_result("memory_management", False, {'error': str(e)})

    def test_parallel_processing(self):
        """测试并行处理模块"""
        logger.info("测试并行处理模块...")

        try:
            from .parallel import IntelligentTaskScheduler, ParallelProcessor, Task
            from .monitoring import PerformanceProfiler

            # 测试智能任务调度器
            def simple_task_function(task_data):
                """简单任务函数"""
                if isinstance(task_data, list):
                    # 模拟计算密集型任务
                    result = sum(i * i for i in task_data)
                    time.sleep(0.01)  # 模拟处理时间
                    return result
                else:
                    time.sleep(0.1)
                    return task_data * 2

            # 创建测试任务
            tasks = []
            for i in range(20):
                task_data = list(range(i * 10, (i + 1) * 10))
                task = Task(
                    task_id=f"test_task_{i}",
                    task_type="data_processing",
                    data=task_data,
                    priority=i % 3,  # 不同的优先级
                    estimated_duration=0.1
                )
                tasks.append(task)

            with PerformanceProfiler("intelligent_task_scheduler") as profiler:
                scheduler = IntelligentTaskScheduler(max_workers=4)

                with scheduler:
                    # 测试智能任务分配
                    task_assignments = scheduler.distribute_tasks(tasks)

                    # 执行并行任务
                    results = scheduler.execute_parallel_tasks(task_assignments, simple_task_function)

            self._record_test_result(
                "intelligent_task_scheduler",
                True,
                {
                    'execution_time': profiler.get_metric('execution_time'),
                    'tasks_count': len(tasks),
                    'successful_tasks': len([r for r in results.values() if r.success]),
                    'worker_assignments': [len(assignment) for assignment in task_assignments],
                    'scheduler_status': scheduler.get_scheduler_status()
                }
            )

            # 测试并行处理器
            with PerformanceProfiler("parallel_processor") as profiler:
                processor = ParallelProcessor(max_workers=4, enable_load_balancing=True)

                test_data = list(range(1000))
                parallel_results = processor.process_data_parallel(
                    test_data,
                    lambda x: x * x + 1,
                    task_type="math_computation"
                )

            self._record_test_result(
                "parallel_processor",
                True,
                {
                    'execution_time': profiler.get_metric('execution_time'),
                    'input_data_size': len(test_data),
                    'output_results_size': len(parallel_results),
                    'performance_stats': processor.get_performance_stats()
                }
            )

        except Exception as e:
            logger.error(f"并行处理测试失败: {str(e)}")
            self._record_test_result("parallel_processing", False, {'error': str(e)})

    def test_caching_system(self):
        """测试缓存系统"""
        logger.info("测试缓存系统...")

        try:
            from .cache import MemoryCache, DiskCache, MultiLevelCache, create_cache
            from .monitoring import PerformanceProfiler

            # 测试内存缓存
            with PerformanceProfiler("memory_cache") as profiler:
                memory_cache = MemoryCache(max_size_mb=10, max_entries=1000)

                # 存储测试数据
                test_data = {f"key_{i}": f"value_{i}" * 100 for i in range(500)}

                for key, value in test_data.items():
                    memory_cache.put(key, value)

                # 测试检索
                hit_count = 0
                for key in list(test_data.keys())[:250]:
                    value = memory_cache.get(key)
                    if value is not None:
                        hit_count += 1

                # 测试LRU淘汰
                for i in range(500, 800):
                    memory_cache.put(f"new_key_{i}", f"new_value_{i}" * 100)

            memory_stats = memory_cache.get_stats()

            self._record_test_result(
                "memory_cache",
                True,
                {
                    'execution_time': profiler.get_metric('execution_time'),
                    'hit_rate': memory_stats.hit_rate,
                    'entry_count': memory_stats.entry_count,
                    'current_size_mb': memory_stats.current_size_bytes / 1024**2,
                    'hits': memory_stats.hits,
                    'misses': memory_stats.misses,
                    'evictions': memory_stats.evictions
                }
            )

            # 测试磁盘缓存
            with PerformanceProfiler("disk_cache") as profiler:
                cache_dir = tempfile.mkdtemp(prefix='test_disk_cache_')
                disk_cache = DiskCache(cache_dir=cache_dir, max_size_gb=0.1)

                # 存储测试数据
                for i in range(100):
                    disk_cache.put(f"disk_key_{i}", {"data": list(range(100)), "index": i})

                # 测试检索
                hit_count = 0
                for i in range(100):
                    value = disk_cache.get(f"disk_key_{i}")
                    if value is not None:
                        hit_count += 1

            disk_stats = disk_cache.get_stats()

            self._record_test_result(
                "disk_cache",
                True,
                {
                    'execution_time': profiler.get_metric('execution_time'),
                    'hit_rate': disk_stats.hit_rate,
                    'entry_count': disk_stats.entry_count,
                    'current_size_mb': disk_stats.current_size_bytes / 1024**2,
                    'cache_dir': cache_dir
                }
            )

            # 测试多级缓存
            with PerformanceProfiler("multilevel_cache") as profiler:
                multilevel_cache = create_cache(
                    cache_type='multilevel',
                    memory_limit_mb=5,
                    disk_limit_gb=0.1
                )

                # 存储测试数据
                for i in range(200):
                    multilevel_cache.put(f"multi_key_{i}", {"complex_data": list(range(50)), "id": i})

                # 测试检索（部分在内存，部分在磁盘）
                hit_count = 0
                for i in range(200):
                    value = multilevel_cache.get(f"multi_key_{i}")
                    if value is not None:
                        hit_count += 1

                # 测试缓存提升
                for i in range(50):  # 频繁访问前50个，应该提升到内存
                    value = multilevel_cache.get(f"multi_key_{i}")

            multi_stats = multilevel_cache.get_stats()

            self._record_test_result(
                "multilevel_cache",
                True,
                {
                    'execution_time': profiler.get_metric('execution_time'),
                    'overall_hit_rate': multi_stats['overall']['hit_rate'],
                    'memory_hit_rate': multi_stats['memory_cache']['hit_rate'],
                    'disk_hit_rate': multi_stats['disk_cache']['hit_rate'],
                    'total_entries': multi_stats['overall']['entry_count'],
                    'memory_entries': multi_stats['memory_cache']['entry_count'],
                    'disk_entries': multi_stats['disk_cache']['entry_count']
                }
            )

        except Exception as e:
            logger.error(f"缓存系统测试失败: {str(e)}")
            self._record_test_result("caching_system", False, {'error': str(e)})

    def test_performance_monitoring(self):
        """测试性能监控模块"""
        logger.info("测试性能监控模块...")

        try:
            from .monitoring import PerformanceProfiler, ResourceMonitor, BenchmarkSuite, PerformanceMonitor

            # 测试性能分析器
            with PerformanceProfiler("test_profiler") as profiler:
                # 模拟一些计算
                result = sum(i * i for i in range(10000))
                time.sleep(0.1)

                # 添加自定义指标
                profiler.add_metric('computation_result', result, 'count', 'computation')
                profiler.add_metric('test_custom_metric', 42.0, 'unit', 'test')

            self._record_test_result(
                "performance_profiler",
                True,
                {
                    'execution_time': profiler.get_metric('execution_time'),
                    'memory_delta': profiler.get_metric('memory_delta'),
                    'computation_result': profiler.get_metric('computation_result'),
                    'custom_metric': profiler.get_metric('test_custom_metric'),
                    'metrics_count': len(profiler.metrics)
                }
            )

            # 测试资源监控器
            resource_monitor = ResourceMonitor(interval=0.1, max_history=100)
            resource_monitor.start_monitoring()
            time.sleep(0.5)  # 让监控器收集一些数据
            resource_monitor.stop_monitoring()

            current_snapshot = resource_monitor.get_current_snapshot()
            average_stats = resource_monitor.get_average_stats()
            peak_usage = resource_monitor.get_peak_usage()

            self._record_test_result(
                "resource_monitor",
                True,
                {
                    'monitoring_records': len(resource_monitor.resource_history),
                    'current_cpu': current_snapshot.cpu_percent if current_snapshot else 0,
                    'current_memory': current_snapshot.memory_percent if current_snapshot else 0,
                    'avg_cpu': average_stats.get('avg_cpu_percent', 0),
                    'peak_cpu': peak_usage.get('peak_cpu_percent', 0)
                }
            )

            # 测试基准测试套件
            benchmark_suite = BenchmarkSuite("test_benchmark")

            def test_function(x=1000):
                """测试函数"""
                return sum(i * i for i in range(x))

            benchmark_result = benchmark_suite.run_benchmark(
                test_function,
                "test_computation",
                iterations=3,
                warmup_iterations=1,
                x=5000
            )

            self._record_test_result(
                "benchmark_suite",
                True,
                {
                    'test_name': benchmark_result.test_name,
                    'execution_time': benchmark_result.execution_time,
                    'memory_peak_mb': benchmark_result.memory_peak_mb,
                    'success': benchmark_result.success,
                    'success_rate': benchmark_result.metrics.get('success_count', 0) / benchmark_result.metrics.get('iterations', 1)
                }
            )

        except Exception as e:
            logger.error(f"性能监控测试失败: {str(e)}")
            self._record_test_result("performance_monitoring", False, {'error': str(e)})

    def test_integration(self):
        """测试集成功能"""
        logger.info("测试集成功能...")

        try:
            from .indexing import AdaptiveSpatialIndex
            from .parallel import ParallelProcessor
            from .cache import MultiLevelCache
            from .memory import ChunkedDataManager
            from .monitoring import PerformanceMonitor

            # 创建综合性能监控器
            perf_monitor = PerformanceMonitor()
            perf_monitor.start_monitoring()

            try:
                # 创建缓存系统
                cache = MultiLevelCache(memory_limit_mb=10, disk_limit_gb=0.1)

                # 生成的测试数据
                test_data = [Point(np.random.uniform(0, 100), np.random.uniform(0, 100))
                            for _ in range(1000)]

                # 1. 使用空间索引加速查询
                profiler_id = perf_monitor.start_profiler("spatial_index_with_cache")

                # 检查缓存
                cache_key = "spatial_index_1000"
                spatial_index = cache.get(cache_key)

                if spatial_index is None:
                    # 构建索引
                    adaptive_index = AdaptiveSpatialIndex(len(test_data))
                    spatial_index = adaptive_index.build_index(test_data)
                    cache.put(cache_key, spatial_index, ttl_seconds=300)  # 5分钟缓存

                # 执行查询
                query_results = []
                for point in test_data[:100]:
                    results = spatial_index.query(point)
                    query_results.append(len(results))

                perf_monitor.stop_profiler(profiler_id)

                # 2. 使用并行处理进行批量计算
                def compute_distance_batch(points_batch):
                    """计算距离批次"""
                    distances = []
                    for i, p1 in enumerate(points_batch):
                        for p2 in points_batch[i+1:i+10]:  # 限制计算量
                            distances.append(p1.distance(p2))
                    return distances

                profiler_id = perf_monitor.start_profiler("parallel_distance_calculation")
                parallel_processor = ParallelProcessor(max_workers=4)

                distance_results = parallel_processor.process_data_parallel(
                    test_data,
                    compute_distance_batch,
                    task_type="distance_computation",
                    chunk_size=100
                )

                perf_monitor.stop_profiler(profiler_id)

                # 3. 使用分块管理器处理大数据
                def large_data_generator():
                    """大数据生成器"""
                    for i in range(50000):
                        yield {
                            'id': i,
                            'data': list(range(10)),
                            'metadata': f"item_{i}"
                        }

                def process_data_chunk(chunk):
                    """处理数据块"""
                    return [item['id'] * 2 for item in chunk]

                profiler_id = perf_monitor.start_profiler("chunked_large_data_processing")

                chunk_manager = ChunkedDataManager(
                    total_items=50000,
                    memory_limit_gb=0.5
                )

                processed_data = chunk_manager.process_in_chunks(
                    large_data_generator(),
                    process_data_chunk
                )

                perf_monitor.stop_profiler(profiler_id)

                # 获取监控摘要
                monitoring_summary = perf_monitor.get_monitoring_summary()

                self._record_test_result(
                    "integration_test",
                    True,
                    {
                        'query_results_count': len(query_results),
                        'distance_calculations': len(distance_results),
                        'processed_data_items': len(processed_data),
                        'cache_stats': cache.get_stats(),
                        'monitoring_summary': monitoring_summary,
                        'chunk_manager_stats': chunk_manager.get_processing_stats()
                    }
                )

            finally:
                perf_monitor.stop_monitoring()

        except Exception as e:
            logger.error(f"集成测试失败: {str(e)}")
            self._record_test_result("integration_test", False, {'error': str(e)})

    def _record_test_result(self, test_name: str, success: bool, metrics: Dict[str, Any]):
        """记录测试结果"""
        self.test_results[test_name] = {
            'success': success,
            'metrics': metrics,
            'timestamp': time.time()
        }

        if success:
            self.passed_tests += 1
            logger.info(f"✓ {test_name} 测试通过")
        else:
            self.failed_tests += 1
            logger.error(f"✗ {test_name} 测试失败: {metrics.get('error', '未知错误')}")


def main():
    """主函数"""
    print("=" * 60)
    print("GIS空间关联系统 - 性能优化模块综合测试")
    print("=" * 60)

    # 检查依赖
    if not HAS_DEPS:
        print("警告: 某些依赖库不可用，部分测试可能跳过")
        print()

    # 运行测试套件
    test_suite = PerformanceTestSuite()
    report = test_suite.run_all_tests()

    # 打印测试报告
    print("\n" + "=" * 60)
    print("测试报告")
    print("=" * 60)
    print(f"总测试时间: {report['total_time']:.2f}秒")
    print(f"通过测试: {report['passed_tests']}")
    print(f"失败测试: {report['failed_tests']}")
    print(f"成功率: {report['success_rate']:.1%}")

    print("\n详细结果:")
    for test_name, result in report['test_results'].items():
        status = "✓" if result['success'] else "✗"
        print(f"{status} {test_name}")
        if result['success']:
            for key, value in result['metrics'].items():
                if isinstance(value, float):
                    print(f"    {key}: {value:.3f}")
                else:
                    print(f"    {key}: {value}")
        else:
            print(f"    错误: {result['metrics'].get('error', '未知错误')}")

    print("\n" + "=" * 60)

    # 保存测试报告
    try:
        import json
        report_file = "performance_test_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"测试报告已保存到: {report_file}")
    except Exception as e:
        print(f"保存测试报告失败: {e}")

    return report['success_rate'] >= 0.8  # 80%以上成功率视为测试通过


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)