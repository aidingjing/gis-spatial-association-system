"""
进度监控系统

提供实时进度显示和性能监控功能：
- 多阶段进度条显示
- 性能指标监控
- 实时状态更新
- 资源使用监控
- 详细日志记录
"""

import time
import threading
import psutil
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

try:
    from rich.console import Console
    from rich.progress import (
        Progress, SpinnerColumn, TextColumn, BarColumn,
        TimeRemainingColumn, TaskID, TaskProgress
    )
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.live import Live
    from rich.layout import Layout
    from rich.align import Align
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None
    Progress = None

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

import logging

logger = logging.getLogger(__name__)


@dataclass
class TaskInfo:
    """任务信息"""
    name: str
    total: int = 100
    completed: int = 0
    description: str = ""
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    status: str = "pending"  # pending, running, completed, failed
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def progress_percent(self) -> float:
        """进度百分比"""
        if self.total == 0:
            return 0.0
        return (self.completed / self.total) * 100

    @property
    def elapsed_time(self) -> float:
        """已用时间"""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time

    @property
    def estimated_remaining_time(self) -> Optional[float]:
        """预估剩余时间"""
        if self.completed == 0 or self.total == 0:
            return None

        elapsed = self.elapsed_time
        rate = self.completed / elapsed
        remaining_items = self.total - self.completed

        if rate == 0:
            return None
        return remaining_items / rate


@dataclass
class PerformanceMetrics:
    """性能指标"""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_mb: float = 0.0
    memory_available_mb: float = 0.0
    disk_io_read_mb: float = 0.0
    disk_io_write_mb: float = 0.0
    network_io_sent_mb: float = 0.0
    network_io_recv_mb: float = 0.0
    timestamp: float = field(default_factory=time.time)


class ProgressMonitor:
    """进度监控器"""

    def __init__(self, console: Optional[Console] = None, enable_rich: bool = True):
        """
        初始化进度监控器

        Args:
            console: Rich控制台对象
            enable_rich: 是否启用Rich界面
        """
        self.console = console or Console() if RICH_AVAILABLE and enable_rich else None
        self.enable_rich = enable_rich and RICH_AVAILABLE and self.console is not None

        self.tasks: Dict[str, TaskInfo] = {}
        self.main_progress: Optional[Progress] = None
        self.live: Optional[Live] = None
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None

        # 性能监控
        self.performance_history: List[PerformanceMetrics] = []
        self.max_history_size = 1000
        self.performance_monitor_interval = 1.0  # 秒

        # 回调函数
        self.progress_callbacks: List[Callable[[str, TaskInfo], None]] = []
        self.completion_callbacks: List[Callable[[str, TaskInfo], None]] = []

        # 基准性能数据
        self.baseline_performance: Optional[PerformanceMetrics] = None

        if self.enable_rich:
            self._setup_rich_progress()
        else:
            self._setup_basic_progress()

    def _setup_rich_progress(self):
        """设置Rich进度条"""
        if not self.console:
            return

        self.main_progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=self.console,
            transient=True
        )

    def _setup_basic_progress(self):
        """设置基础进度显示"""
        pass

    def add_task(self,
                task_id: str,
                name: str,
                total: int = 100,
                description: str = "",
                **metadata) -> str:
        """
        添加任务

        Args:
            task_id: 任务ID
            name: 任务名称
            total: 总工作量
            description: 任务描述
            **metadata: 额外元数据

        Returns:
            任务ID
        """
        task = TaskInfo(
            name=name,
            total=total,
            description=description or name,
            metadata=metadata
        )

        self.tasks[task_id] = task

        if self.enable_rich and self.main_progress:
            # 创建Rich任务
            task.metadata['rich_task_id'] = self.main_progress.add_task(
                description=task.description,
                total=total
            )

        logger.info(f"添加任务: {task_id} - {name}")
        return task_id

    def update_task(self,
                   task_id: str,
                   completed: Optional[int] = None,
                   description: Optional[str] = None,
                   status: Optional[str] = None,
                   **metadata):
        """
        更新任务进度

        Args:
            task_id: 任务ID
            completed: 完成量
            description: 新描述
            status: 新状态
            **metadata: 额外元数据
        """
        if task_id not in self.tasks:
            logger.warning(f"任务不存在: {task_id}")
            return

        task = self.tasks[task_id]

        if completed is not None:
            task.completed = min(completed, task.total)

        if description:
            task.description = description

        if status:
            task.status = status
            if status == "completed":
                task.end_time = time.time
                task.completed = task.total
            elif status == "failed":
                task.end_time = time.time

        # 更新元数据
        task.metadata.update(metadata)

        # 更新Rich进度条
        if self.enable_rich and self.main_progress and 'rich_task_id' in task.metadata:
            rich_task_id = task.metadata['rich_task_id']
            self.main_progress.update(
                rich_task_id,
                completed=task.completed,
                description=task.description
            )

        # 调用进度回调
        for callback in self.progress_callbacks:
            try:
                callback(task_id, task)
            except Exception as e:
                logger.error(f"进度回调错误: {e}")

    def start_monitoring(self):
        """开始监控"""
        if self.is_monitoring:
            return

        self.is_monitoring = True

        # 记录基准性能
        self.baseline_performance = self._get_performance_metrics()

        if self.enable_rich and self.main_progress:
            self.live = Live(
                self._create_dashboard(),
                console=self.console,
                refresh_per_second=4
            )
            self.live.start()
        else:
            # 启动基础监控线程
            self.monitor_thread = threading.Thread(
                target=self._basic_monitoring_loop,
                daemon=True
            )
            self.monitor_thread.start()

        logger.info("进度监控已启动")

    def stop_monitoring(self) -> Dict[str, Any]:
        """停止监控并返回统计信息"""
        if not self.is_monitoring:
            return {}

        self.is_monitoring = False

        if self.live:
            self.live.stop()
            self.live = None

        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)

        # 生成统计报告
        stats = self._generate_statistics()

        logger.info("进度监控已停止")
        return stats

    def _get_performance_metrics(self) -> PerformanceMetrics:
        """获取当前性能指标"""
        if not PSUTIL_AVAILABLE:
            # 如果psutil不可用，返回默认指标
            return PerformanceMetrics()

        try:
            # CPU和内存
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()

            # 磁盘I/O
            disk_io = psutil.disk_io_counters()
            disk_read = disk_io.read_bytes / (1024 * 1024) if disk_io else 0
            disk_write = disk_io.write_bytes / (1024 * 1024) if disk_io else 0

            # 网络I/O
            network_io = psutil.net_io_counters()
            net_sent = network_io.bytes_sent / (1024 * 1024) if network_io else 0
            net_recv = network_io.bytes_recv / (1024 * 1024) if network_io else 0

            return PerformanceMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory.used / (1024 * 1024),
                memory_available_mb=memory.available / (1024 * 1024),
                disk_io_read_mb=disk_read,
                disk_io_write_mb=disk_write,
                network_io_sent_mb=net_sent,
                network_io_recv_mb=net_recv
            )
        except Exception as e:
            logger.error(f"获取性能指标失败: {e}")
            return PerformanceMetrics()

    def _record_performance(self):
        """记录性能指标"""
        if not self.is_monitoring:
            return

        metrics = self._get_performance_metrics()
        self.performance_history.append(metrics)

        # 限制历史记录大小
        if len(self.performance_history) > self.max_history_size:
            self.performance_history = self.performance_history[-self.max_history_size:]

    def _create_dashboard(self) -> Table:
        """创建监控仪表板"""
        if not self.enable_rich:
            return None

        # 创建主表格
        dashboard = Table(show_header=True, header_style="bold magenta")
        dashboard.add_column("监控项目", style="cyan")
        dashboard.add_column("值", style="green")
        dashboard.add_column("状态", style="bold")

        # 任务进度
        if self.tasks:
            dashboard.add_row("", "", "")
            dashboard.add_row("[bold]任务进度[/bold]", "", "")

            for task_id, task in self.tasks.items():
                status_color = {
                    "pending": "yellow",
                    "running": "blue",
                    "completed": "green",
                    "failed": "red"
                }.get(task.status, "white")

                dashboard.add_row(
                    f"  {task.name}",
                    f"{task.completed}/{task.total} ({task.progress_percent:.1f}%)",
                    f"[{status_color}]{task.status}[/{status_color}]"
                )

        # 性能指标
        if self.performance_history:
            current_perf = self.performance_history[-1]
            dashboard.add_row("", "", "")
            dashboard.add_row("[bold]性能指标[/bold]", "", "")

            dashboard.add_row("CPU使用率", f"{current_perf.cpu_percent:.1f}%",
                            "🟢" if current_perf.cpu_percent < 70 else "🟡" if current_perf.cpu_percent < 90 else "🔴")
            dashboard.add_row("内存使用率", f"{current_perf.memory_percent:.1f}%",
                            "🟢" if current_perf.memory_percent < 70 else "🟡" if current_perf.memory_percent < 90 else "🔴")
            dashboard.add_row("可用内存", f"{current_perf.memory_available_mb:.1f} MB", "")
            dashboard.add_row("磁盘读取", f"{current_perf.disk_io_read_mb:.1f} MB", "")
            dashboard.add_row("磁盘写入", f"{current_perf.disk_io_write_mb:.1f} MB", "")

        # 时间戳
        dashboard.add_row("", "", "")
        dashboard.add_row("更新时间", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "")

        return dashboard

    def _basic_monitoring_loop(self):
        """基础监控循环"""
        while self.is_monitoring:
            try:
                self._record_performance()
                time.sleep(self.performance_monitor_interval)
            except Exception as e:
                logger.error(f"监控循环错误: {e}")
                break

    def _generate_statistics(self) -> Dict[str, Any]:
        """生成统计信息"""
        stats = {
            "tasks": {},
            "performance": {},
            "summary": {}
        }

        # 任务统计
        total_tasks = len(self.tasks)
        completed_tasks = sum(1 for task in self.tasks.values() if task.status == "completed")
        failed_tasks = sum(1 for task in self.tasks.values() if task.status == "failed")

        stats["summary"] = {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "success_rate": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        }

        # 任务详细信息
        for task_id, task in self.tasks.items():
            stats["tasks"][task_id] = {
                "name": task.name,
                "status": task.status,
                "progress": task.progress_percent,
                "elapsed_time": task.elapsed_time,
                "estimated_remaining": task.estimated_remaining_time
            }

        # 性能统计
        if self.performance_history:
            cpu_values = [p.cpu_percent for p in self.performance_history]
            memory_values = [p.memory_percent for p in self.performance_history]

            stats["performance"] = {
                "cpu_avg": sum(cpu_values) / len(cpu_values),
                "cpu_max": max(cpu_values),
                "memory_avg": sum(memory_values) / len(memory_values),
                "memory_max": max(memory_values),
                "samples_count": len(self.performance_history)
            }

        return stats

    def get_current_performance(self) -> Dict[str, Any]:
        """获取当前性能状态"""
        current = self._get_performance_metrics()

        result = {
            "cpu_usage": current.cpu_percent,
            "memory_usage": current.memory_percent,
            "memory_used_mb": current.memory_used_mb,
            "memory_available_mb": current.memory_available_mb,
            "timestamp": current.timestamp
        }

        # 如果有基准数据，计算相对变化
        if self.baseline_performance:
            result["cpu_change"] = current.cpu_percent - self.baseline_performance.cpu_percent
            result["memory_change"] = current.memory_percent - self.baseline_performance.memory_percent

        return result

    def add_progress_callback(self, callback: Callable[[str, TaskInfo], None]):
        """添加进度回调函数"""
        self.progress_callbacks.append(callback)

    def add_completion_callback(self, callback: Callable[[str, TaskInfo], None]):
        """添加完成回调函数"""
        self.completion_callbacks.append(callback)

    def complete_task(self, task_id: str, success: bool = True):
        """标记任务完成"""
        if task_id not in self.tasks:
            return

        task = self.tasks[task_id]
        task.status = "completed" if success else "failed"
        task.end_time = time.time()
        task.completed = task.total

        # 更新Rich进度条
        if self.enable_rich and self.main_progress and 'rich_task_id' in task.metadata:
            rich_task_id = task.metadata['rich_task_id']
            self.main_progress.update(
                rich_task_id,
                completed=task.total,
                description=f"{task.description} - {'✅' if success else '❌'}"
            )

        # 调用完成回调
        for callback in self.completion_callbacks:
            try:
                callback(task_id, task)
            except Exception as e:
                logger.error(f"完成回调错误: {e}")

    def get_task_info(self, task_id: str) -> Optional[TaskInfo]:
        """获取任务信息"""
        return self.tasks.get(task_id)

    def get_all_tasks(self) -> Dict[str, TaskInfo]:
        """获取所有任务信息"""
        return self.tasks.copy()

    def clear_tasks(self):
        """清除所有任务"""
        self.tasks.clear()

        if self.enable_rich and self.main_progress:
            # 清除Rich任务
            self.main_progress.tasks.clear()

    def export_performance_data(self, format_type: str = "dict") -> Any:
        """
        导出性能数据

        Args:
            format_type: 导出格式 ('dict', 'csv', 'json')

        Returns:
            导出的数据
        """
        if format_type == "dict":
            return [
                {
                    "timestamp": p.timestamp,
                    "cpu_percent": p.cpu_percent,
                    "memory_percent": p.memory_percent,
                    "memory_used_mb": p.memory_used_mb,
                    "disk_io_read_mb": p.disk_io_read_mb,
                    "disk_io_write_mb": p.disk_io_write_mb
                }
                for p in self.performance_history
            ]
        elif format_type == "csv":
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["timestamp", "cpu_percent", "memory_percent", "memory_used_mb",
                           "disk_io_read_mb", "disk_io_write_mb"])

            for p in self.performance_history:
                writer.writerow([p.timestamp, p.cpu_percent, p.memory_percent,
                               p.memory_used_mb, p.disk_io_read_mb, p.disk_io_write_mb])

            return output.getvalue()
        elif format_type == "json":
            import json
            return json.dumps(self.export_performance_data("dict"), indent=2)
        else:
            raise ValueError(f"不支持的导出格式: {format_type}")


# 上下文管理器支持
class ProgressContext:
    """进度监控上下文管理器"""

    def __init__(self, monitor: ProgressMonitor, task_name: str, total: int = 100):
        self.monitor = monitor
        self.task_name = task_name
        self.total = total
        self.task_id = None

    def __enter__(self):
        self.task_id = self.monitor.add_task(self.task_id or self.task_name, self.task_name, self.total)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.task_id:
            success = exc_type is None
            self.monitor.complete_task(self.task_id, success)
        return False

    def update(self, completed: int, description: str = None):
        """更新进度"""
        if self.task_id:
            self.monitor.update_task(self.task_id, completed=completed, description=description)


# 便捷函数
def create_progress_monitor(console: Optional[Console] = None) -> ProgressMonitor:
    """创建进度监控器"""
    return ProgressMonitor(console)


def progress_context(monitor: ProgressMonitor, task_name: str, total: int = 100) -> ProgressContext:
    """创建进度上下文"""
    return ProgressContext(monitor, task_name, total)