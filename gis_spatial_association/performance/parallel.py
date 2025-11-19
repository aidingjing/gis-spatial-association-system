"""
并行计算框架

提供智能的任务调度和并行处理能力，支持多进程、多线程和异步IO。
包括负载均衡、任务分配优化和资源管理功能。

Author: CCPM Auto Development System
"""

import logging
import time
import queue
import threading
import multiprocessing as mp
from typing import List, Dict, Any, Callable, Optional, Union, Tuple
from abc import ABC, abstractmethod
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import psutil
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Task:
    """任务数据结构"""
    task_id: str
    task_type: str
    data: Any
    priority: int = 0
    estimated_duration: float = 1.0
    memory_requirement_mb: float = 100.0
    cpu_requirement: int = 1


@dataclass
class TaskResult:
    """任务结果数据结构"""
    task_id: str
    result: Any
    execution_time: float
    memory_peak_mb: float
    success: bool
    error_message: Optional[str] = None


class ResourceMonitor:
    """资源监控器"""

    def __init__(self):
        self.cpu_count = mp.cpu_count()
        self.memory_total_gb = psutil.virtual_memory().total / 1024**3
        self.monitoring = False
        self.monitor_thread = None
        self.resource_history = []
        self.max_history_size = 60  # 保存60秒的历史

    def start_monitoring(self, interval: float = 1.0):
        """开始资源监控"""
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,))
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        logger.info("资源监控已启动")

    def stop_monitoring(self):
        """停止资源监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
        logger.info("资源监控已停止")

    def _monitor_loop(self, interval: float):
        """监控循环"""
        while self.monitoring:
            try:
                cpu_percent = psutil.cpu_percent(interval=None)
                memory = psutil.virtual_memory()

                resource_info = {
                    'timestamp': time.time(),
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_available_gb': memory.available / 1024**3,
                    'load_avg': psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0.0
                }

                self.resource_history.append(resource_info)
                if len(self.resource_history) > self.max_history_size:
                    self.resource_history.pop(0)

                time.sleep(interval)

            except Exception as e:
                logger.warning(f"资源监控出错: {str(e)}")
                time.sleep(interval)

    def get_current_status(self) -> Dict[str, float]:
        """获取当前资源状态"""
        if not self.resource_history:
            return self._get_snapshot()

        # 返回最新的状态
        return self.resource_history[-1].copy()

    def get_average_load(self, window_seconds: int = 10) -> Dict[str, float]:
        """获取平均负载"""
        if not self.resource_history:
            return self._get_snapshot()

        cutoff_time = time.time() - window_seconds
        recent_data = [info for info in self.resource_history if info['timestamp'] > cutoff_time]

        if not recent_data:
            return self._get_snapshot()

        return {
            'avg_cpu_percent': np.mean([info['cpu_percent'] for info in recent_data]),
            'avg_memory_percent': np.mean([info['memory_percent'] for info in recent_data]),
            'max_cpu_percent': np.max([info['cpu_percent'] for info in recent_data]),
            'max_memory_percent': np.max([info['memory_percent'] for info in recent_data])
        }

    def _get_snapshot(self) -> Dict[str, float]:
        """获取当前快照"""
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()

        return {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_available_gb': memory.available / 1024**3,
            'load_avg': psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0.0
        }

    def can_allocate_resources(self, cpu_cores: int, memory_gb: float) -> bool:
        """检查是否可以分配资源"""
        current_status = self.get_current_status()
        avg_load = self.get_average_load()

        # 检查CPU可用性
        available_cpu_cores = self.cpu_count * (1 - current_status['cpu_percent'] / 100)
        if available_cpu_cores < cpu_cores:
            return False

        # 检查内存可用性
        available_memory_gb = current_status['memory_available_gb']
        if available_memory_gb < memory_gb * 1.2:  # 保留20%余量
            return False

        # 检查负载是否过高
        if avg_load['avg_cpu_percent'] > 90 or avg_load['avg_memory_percent'] > 90:
            return False

        return True


class TaskComplexityEstimator:
    """任务复杂度估算器"""

    def __init__(self):
        self.complexity_factors = {
            'point_line_association': {'base': 1.0, 'data_factor': 0.001, 'complexity_growth': 'linear'},
            'line_line_intersection': {'base': 1.5, 'data_factor': 0.002, 'complexity_growth': 'quadratic'},
            'polygon_containment': {'base': 2.0, 'data_factor': 0.003, 'complexity_growth': 'quadratic'},
            'coordinate_transformation': {'base': 0.5, 'data_factor': 0.0005, 'complexity_growth': 'linear'},
            'spatial_query': {'base': 1.0, 'data_factor': 0.0015, 'complexity_growth': 'log'},
            'data_processing': {'base': 0.8, 'data_factor': 0.0008, 'complexity_growth': 'linear'},
            'file_io': {'base': 0.3, 'data_factor': 0.0002, 'complexity_growth': 'linear'}
        }

    def estimate_task_complexity(self, task: Task) -> float:
        """估算任务复杂度"""
        task_type = task.task_type
        data_size = getattr(task.data, '__len__', lambda: 1)() if hasattr(task.data, '__len__') else 1

        if task_type not in self.complexity_factors:
            # 未知任务类型，使用默认估算
            return float(data_size) * 0.001

        factor = self.complexity_factors[task_type]
        base_complexity = factor['base']
        data_factor = factor['data_factor']
        growth_type = factor['complexity_growth']

        # 根据数据量计算复杂度
        if growth_type == 'linear':
            size_factor = data_size * data_factor
        elif growth_type == 'quadratic':
            size_factor = (data_size ** 1.5) * data_factor
        elif growth_type == 'log':
            size_factor = np.log1p(data_size) * data_factor * 1000
        else:
            size_factor = data_size * data_factor

        # 应用优先级调整
        priority_factor = 1.0 + (task.priority / 10.0)

        return base_complexity + size_factor * priority_factor

    def estimate_resource_requirements(self, task: Task) -> Dict[str, float]:
        """估算资源需求"""
        complexity = self.estimate_task_complexity(task)

        # 基于复杂度估算CPU需求（1-4核）
        cpu_requirement = min(4, max(1, int(np.ceil(complexity / 2.0))))

        # 基于任务类型和数据量估算内存需求
        base_memory = task.memory_requirement_mb
        data_size = getattr(task.data, '__len__', lambda: 1)() if hasattr(task.data, '__len__') else 1
        memory_requirement = base_memory + (data_size * 0.01)  # 每个数据项额外0.01MB

        # 基于复杂度调整内存需求
        memory_requirement *= (1.0 + complexity * 0.1)

        return {
            'cpu_cores': cpu_requirement,
            'memory_mb': memory_requirement,
            'estimated_duration': task.estimated_duration * complexity,
            'complexity_score': complexity
        }


class IntelligentTaskScheduler:
    """智能任务调度器

    根据系统资源状态和任务特征，智能分配任务到不同的工作进程。
    支持负载均衡、优先级调度和资源约束。
    """

    def __init__(self,
                 max_workers: Optional[int] = None,
                 use_process_pool: bool = True,
                 enable_monitoring: bool = True):
        """初始化任务调度器

        Args:
            max_workers: 最大工作进程数
            use_process_pool: 是否使用进程池（True）或线程池（False）
            enable_monitoring: 是否启用资源监控
        """
        self.max_workers = max_workers or mp.cpu_count()
        self.use_process_pool = use_process_pool
        self.enable_monitoring = enable_monitoring

        # 组件初始化
        self.resource_monitor = ResourceMonitor()
        self.complexity_estimator = TaskComplexityEstimator()

        # 任务队列和管理
        self.task_queue = queue.PriorityQueue()
        self.completed_tasks: Dict[str, TaskResult] = {}
        self.running_tasks: Dict[str, Task] = {}

        # 工作池
        self.executor: Optional[Union[ProcessPoolExecutor, ThreadPoolExecutor]] = None
        self.worker_stats: Dict[int, Dict[str, Any]] = {}

        # 统计信息
        self.scheduler_stats = {
            'total_tasks_scheduled': 0,
            'total_tasks_completed': 0,
            'total_tasks_failed': 0,
            'total_execution_time': 0.0,
            'avg_task_duration': 0.0,
            'resource_rejections': 0
        }

        logger.info(f"智能任务调度器初始化: 最大工作进程={self.max_workers}, "
                   f"使用进程池={use_process_pool}")

        if self.enable_monitoring:
            self.resource_monitor.start_monitoring()

    def __enter__(self):
        """上下文管理器入口"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.shutdown()

    def start(self):
        """启动调度器"""
        if self.use_process_pool:
            self.executor = ProcessPoolExecutor(max_workers=self.max_workers)
        else:
            self.executor = ThreadPoolExecutor(max_workers=self.max_workers)

        logger.info(f"任务调度器已启动: {type(self.executor).__name__}")

    def shutdown(self, wait: bool = True):
        """关闭调度器"""
        if self.executor:
            self.executor.shutdown(wait=wait)
            self.executor = None

        if self.enable_monitoring:
            self.resource_monitor.stop_monitoring()

        logger.info("任务调度器已关闭")

    def submit_task(self,
                    task: Task,
                    processing_function: Callable[[Any], Any]) -> str:
        """提交任务到调度器

        Args:
            task: 任务对象
            processing_function: 处理函数

        Returns:
            任务ID
        """
        # 检查资源可用性
        resource_req = self.complexity_estimator.estimate_resource_requirements(task)

        if not self.resource_monitor.can_allocate_resources(
                resource_req['cpu_cores'], resource_req['memory_mb'] / 1024):
            self.scheduler_stats['resource_rejections'] += 1
            logger.warning(f"资源不足，拒绝任务: {task.task_id}")
            raise ResourceWarning(f"系统资源不足以执行任务: {task.task_id}")

        # 添加任务到队列（使用负优先级，因为PriorityQueue是最小堆）
        priority = -task.priority
        task_item = (priority, time.time(), task, processing_function)
        self.task_queue.put(task_item)

        self.scheduler_stats['total_tasks_scheduled'] += 1
        logger.debug(f"任务已提交到队列: {task.task_id}")

        return task.task_id

    def distribute_tasks(self, tasks: List[Task]) -> List[List[Task]]:
        """智能任务分配

        Args:
            tasks: 任务列表

        Returns:
            分配给每个工作进程的任务列表
        """
        logger.info(f"开始智能任务分配，任务数量: {len(tasks)}")

        # 估算所有任务的复杂度和资源需求
        task_complexities = []
        resource_requirements = []

        for task in tasks:
            complexity = self.complexity_estimator.estimate_task_complexity(task)
            resource_req = self.complexity_estimator.estimate_resource_requirements(task)

            task_complexities.append(complexity)
            resource_requirements.append(resource_req)

        # 使用贪心算法进行负载均衡
        worker_loads = [{'cpu_load': 0, 'memory_load': 0, 'time_load': 0}
                       for _ in range(self.max_workers)]
        task_assignments = [[] for _ in range(self.max_workers)]

        # 按复杂度和优先级排序任务
        indexed_tasks = sorted(enumerate(tasks),
                             key=lambda x: (task_complexities[x[0]], -x[1].priority),
                             reverse=True)

        for task_idx, task in indexed_tasks:
            resource_req = resource_requirements[task_idx]

            # 找到负载最轻的工作进程
            best_worker = min(range(self.max_workers),
                            key=lambda i: self._calculate_worker_load(
                                worker_loads[i], resource_req))

            # 分配任务
            task_assignments[best_worker].append(task)
            worker_loads[best_worker]['cpu_load'] += resource_req['cpu_cores']
            worker_loads[best_worker]['memory_load'] += resource_req['memory_mb']
            worker_loads[best_worker]['time_load'] += resource_req['estimated_duration']

        # 记录分配结果
        for i, assignment in enumerate(task_assignments):
            total_complexity = sum(task_complexities[t[0]] for t in assignment if isinstance(t, tuple))
            logger.debug(f"工作进程 {i}: 分配 {len(assignment)} 个任务, "
                        f"总复杂度: {total_complexity:.2f}")

        return task_assignments

    def _calculate_worker_load(self, worker_load: Dict[str, float], task_req: Dict[str, float]) -> float:
        """计算工作进程负载分数"""
        cpu_score = worker_load['cpu_load'] / self.max_workers
        memory_score = worker_load['memory_load'] / (self.resource_monitor.memory_total_gb * 1024)
        time_score = worker_load['time_load'] / 3600  # 以小时为单位

        # 加权计算总负载
        return cpu_score * 0.4 + memory_score * 0.4 + time_score * 0.2

    def execute_parallel_tasks(self,
                              task_assignments: List[List[Task]],
                              processing_function: Callable[[Task], Any]) -> Dict[str, TaskResult]:
        """执行并行任务

        Args:
            task_assignments: 任务分配列表
            processing_function: 处理函数

        Returns:
            任务结果字典
        """
        if not self.executor:
            raise RuntimeError("调度器未启动，请先调用start()")

        logger.info(f"开始执行并行任务，工作进程数: {len(task_assignments)}")
        start_time = time.time()

        futures = []
        worker_task_mapping = {}

        # 提交任务到工作进程
        for worker_id, tasks in enumerate(task_assignments):
            if not tasks:
                continue

            for task in tasks:
                self.running_tasks[task.task_id] = task

                # 提交任务
                future = self.executor.submit(self._execute_task_with_monitoring,
                                            task, processing_function)
                futures.append(future)
                worker_task_mapping[future] = (worker_id, task)

        # 收集结果
        all_results = {}
        completed_count = 0

        try:
            for future in as_completed(futures):
                worker_id, task = worker_task_mapping[future]

                try:
                    result = future.result(timeout=300)  # 5分钟超时
                    all_results[task.task_id] = result

                    if result.success:
                        self.scheduler_stats['total_tasks_completed'] += 1
                    else:
                        self.scheduler_stats['total_tasks_failed'] += 1
                        logger.error(f"任务执行失败: {task.task_id}, 错误: {result.error_message}")

                except Exception as e:
                    logger.error(f"任务执行异常: {task.task_id}, 异常: {str(e)}")
                    error_result = TaskResult(
                        task_id=task.task_id,
                        result=None,
                        execution_time=0.0,
                        memory_peak_mb=0.0,
                        success=False,
                        error_message=str(e)
                    )
                    all_results[task.task_id] = error_result
                    self.scheduler_stats['total_tasks_failed'] += 1

                finally:
                    # 从运行中的任务列表移除
                    self.running_tasks.pop(task.task_id, None)
                    completed_count += 1

                    logger.debug(f"任务完成: {task.task_id} ({completed_count}/{len(futures)})")

        except KeyboardInterrupt:
            logger.warning("任务执行被用户中断")
            raise

        finally:
            # 更新统计信息
            total_time = time.time() - start_time
            self.scheduler_stats['total_execution_time'] += total_time

            if completed_count > 0:
                successful_results = [r for r in all_results.values() if r.success]
                if successful_results:
                    avg_duration = np.mean([r.execution_time for r in successful_results])
                    self.scheduler_stats['avg_task_duration'] = avg_duration

        logger.info(f"并行任务执行完成: 总数={completed_count}, "
                   f"成功={self.scheduler_stats['total_tasks_completed']}, "
                   f"失败={self.scheduler_stats['total_tasks_failed']}, "
                   f"总耗时={total_time:.2f}s")

        # 更新完成任务结果
        self.completed_tasks.update(all_results)

        return all_results

    def _execute_task_with_monitoring(self, task: Task, processing_function: Callable[[Any], Any]) -> TaskResult:
        """执行单个任务并监控资源使用"""
        import psutil
        process = psutil.Process()

        start_time = time.time()
        start_memory = process.memory_info().rss / 1024**2  # MB

        try:
            # 执行任务
            result_data = processing_function(task.data)

            execution_time = time.time() - start_time
            end_memory = process.memory_info().rss / 1024**2
            memory_peak_mb = max(end_memory - start_memory, 0.0)

            return TaskResult(
                task_id=task.task_id,
                result=result_data,
                execution_time=execution_time,
                memory_peak_mb=memory_peak_mb,
                success=True
            )

        except Exception as e:
            execution_time = time.time() - start_time
            end_memory = process.memory_info().rss / 1024**2
            memory_peak_mb = max(end_memory - start_memory, 0.0)

            logger.error(f"任务执行失败: {task.task_id}, 错误: {str(e)}")

            return TaskResult(
                task_id=task.task_id,
                result=None,
                execution_time=execution_time,
                memory_peak_mb=memory_peak_mb,
                success=False,
                error_message=str(e)
            )

    def get_scheduler_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        resource_status = self.resource_monitor.get_current_status()
        avg_load = self.resource_monitor.get_average_load()

        return {
            'scheduler_stats': self.scheduler_stats,
            'resource_status': resource_status,
            'average_load': avg_load,
            'running_tasks_count': len(self.running_tasks),
            'completed_tasks_count': len(self.completed_tasks),
            'queue_size': self.task_queue.qsize(),
            'max_workers': self.max_workers,
            'executor_type': type(self.executor).__name__ if self.executor else None
        }

    def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """获取任务结果"""
        return self.completed_tasks.get(task_id)

    def cancel_task(self, task_id: str) -> bool:
        """取消任务（仅对未开始的任务有效）"""
        # 这里可以实现更复杂的任务取消逻辑
        if task_id in self.running_tasks:
            logger.warning(f"无法取消正在运行的任务: {task_id}")
            return False

        # 从队列中移除（需要重新实现队列逻辑以支持删除）
        logger.info(f"任务取消请求: {task_id}")
        return True


class ParallelProcessor:
    """并行处理器封装

    简化并行处理的高级接口，自动处理任务分配和资源管理。
    """

    def __init__(self,
                 max_workers: Optional[int] = None,
                 chunk_size: Optional[int] = None,
                 enable_load_balancing: bool = True):
        """初始化并行处理器

        Args:
            max_workers: 最大工作进程数
            chunk_size: 数据分块大小
            enable_load_balancing: 是否启用负载均衡
        """
        self.max_workers = max_workers or mp.cpu_count()
        self.chunk_size = chunk_size
        self.enable_load_balancing = enable_load_balancing

        self.scheduler = IntelligentTaskScheduler(
            max_workers=self.max_workers,
            use_process_pool=True,
            enable_monitoring=True
        )

        logger.info(f"并行处理器初始化: 工作进程={self.max_workers}, "
                   f"分块大小={chunk_size}, 负载均衡={enable_load_balancing}")

    def process_data_parallel(self,
                             data_list: List[Any],
                             processing_function: Callable[[Any], Any],
                             task_type: str = 'data_processing',
                             progress_callback: Optional[Callable[[float], None]] = None) -> List[Any]:
        """并行处理数据列表

        Args:
            data_list: 数据列表
            processing_function: 处理函数
            task_type: 任务类型
            progress_callback: 进度回调函数

        Returns:
            处理结果列表
        """
        logger.info(f"开始并行数据处理，数据量: {len(data_list)}")
        start_time = time.time()

        # 分块数据
        chunk_size = self.chunk_size or max(1, len(data_list) // self.max_workers)
        data_chunks = [data_list[i:i + chunk_size]
                      for i in range(0, len(data_list), chunk_size)]

        # 创建任务
        tasks = []
        for i, chunk in enumerate(data_chunks):
            task = Task(
                task_id=f"{task_type}_chunk_{i}",
                task_type=task_type,
                data=chunk,
                priority=0,
                estimated_duration=len(chunk) * 0.1,  # 估算每个项目0.1秒
                memory_requirement_mb=len(chunk) * 0.5  # 估算每个项目0.5MB
            )
            tasks.append(task)

        # 启动调度器
        with self.scheduler as scheduler:
            if self.enable_load_balancing:
                # 智能任务分配
                task_assignments = scheduler.distribute_tasks(tasks)
                results = scheduler.execute_parallel_tasks(task_assignments, processing_function)
            else:
                # 简单的轮询分配
                task_assignments = [tasks[i::self.max_workers] for i in range(self.max_workers)]
                results = scheduler.execute_parallel_tasks(task_assignments, processing_function)

        # 整理结果
        final_results = []
        completed_count = 0

        for task in tasks:
            if task.task_id in results and results[task.task_id].success:
                final_results.extend(results[task.task_id].result)
                completed_count += 1

                if progress_callback:
                    progress = completed_count / len(tasks) * 100
                    progress_callback(progress)

        total_time = time.time() - start_time
        logger.info(f"并行处理完成: 成功任务={completed_count}/{len(tasks)}, "
                   f"结果数={len(final_results)}, 耗时={total_time:.2f}s")

        return final_results

    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        return self.scheduler.get_scheduler_status()