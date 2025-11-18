"""
Info子命令 - 系统信息显示

显示系统、模块和数据的详细信息：
- 系统环境和依赖信息
- 模块状态和能力
- 数据文件信息
- 性能基准和统计
- 支持的功能和格式
"""

import os
import sys
import platform
import importlib
from pathlib import Path
from typing import Dict, List, Any, Optional

import click
import geopandas as gpd
import pandas as pd
import psutil
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree
from rich.columns import Columns
from rich import box

console = Console()


def get_system_info() -> Dict[str, Any]:
    """获取系统环境信息"""
    return {
        'platform': platform.platform(),
        'python_version': platform.python_version(),
        'architecture': platform.architecture()[0],
        'processor': platform.processor(),
        'cpu_count': os.cpu_count(),
        'memory_total': f"{psutil.virtual_memory().total / (1024**3):.1f} GB",
        'memory_available': f"{psutil.virtual_memory().available / (1024**3):.1f} GB"
    }


def get_dependency_info() -> Dict[str, Any]:
    """获取依赖包信息"""
    dependencies = {}

    packages = [
        'geopandas', 'pandas', 'numpy', 'shapely', 'fiona', 'pyproj',
        'rtree', 'click', 'rich', 'psutil', 'scipy', 'sklearn'
    ]

    for package in packages:
        try:
            module = importlib.import_module(package)
            version = getattr(module, '__version__', 'unknown')
            dependencies[package] = {
                'version': version,
                'status': '✅ 已安装',
                'location': getattr(module, '__file__', 'unknown')
            }
        except ImportError:
            dependencies[package] = {
                'version': 'N/A',
                'status': '❌ 未安装',
                'location': 'N/A'
            }

    return dependencies


def get_module_status() -> Dict[str, Any]:
    """获取GIS空间关联分析模块状态"""
    modules_status = {}

    try:
        from ...algorithms.association import NearestNeighborAssociator
        modules_status['association'] = {
            'name': '关联分析模块',
            'status': '✅ 可用',
            'description': '点-线最近邻关联分析',
            'class': 'NearestNeighborAssociator'
        }
    except ImportError:
        modules_status['association'] = {
            'name': '关联分析模块',
            'status': '❌ 不可用',
            'description': '点-线最近邻关联分析',
            'class': 'NearestNeighborAssociator'
        }

    try:
        from ...algorithms.intersection import LineIntersectionDetector
        modules_status['intersection'] = {
            'name': '相交检测模块',
            'status': '✅ 可用',
            'description': '线-线相交检测分析',
            'class': 'LineIntersectionDetector'
        }
    except ImportError:
        modules_status['intersection'] = {
            'name': '相交检测模块',
            'status': '❌ 不可用',
            'description': '线-线相交检测分析',
            'class': 'LineIntersectionDetector'
        }

    try:
        from ...algorithms.containment import PolygonContainmentAnalyzer
        modules_status['containment'] = {
            'name': '包含分析模块',
            'status': '✅ 可用',
            'description': '线-面包含判断分析',
            'class': 'PolygonContainmentAnalyzer'
        }
    except ImportError:
        modules_status['containment'] = {
            'name': '包含分析模块',
            'status': '❌ 不可用',
            'description': '线-面包含判断分析',
            'class': 'PolygonContainmentAnalyzer'
        }

    try:
        from ...algorithms.transformation import CoordinateTransformer
        modules_status['transformation'] = {
            'name': '坐标转换模块',
            'status': '✅ 可用',
            'description': '坐标系转换处理',
            'class': 'CoordinateTransformer'
        }
    except ImportError:
        modules_status['transformation'] = {
            'name': '坐标转换模块',
            'status': '❌ 不可用',
            'description': '坐标系转换处理',
            'class': 'CoordinateTransformer'
        }

    try:
        from ...validation import GeometryValidator, AttributeValidator, DataQualityScorer
        modules_status['validation'] = {
            'name': '数据验证模块',
            'status': '✅ 可用',
            'description': '全面的数据质量验证和修复',
            'classes': ['GeometryValidator', 'AttributeValidator', 'DataQualityScorer']
        }
    except ImportError:
        modules_status['validation'] = {
            'name': '数据验证模块',
            'status': '❌ 不可用',
            'description': '全面的数据质量验证和修复',
            'classes': ['GeometryValidator', 'AttributeValidator', 'DataQualityScorer']
        }

    try:
        from ...performance import PerformanceMonitor, MemoryOptimizer
        modules_status['performance'] = {
            'name': '性能优化模块',
            'status': '✅ 可用',
            'description': '性能监控和内存优化',
            'classes': ['PerformanceMonitor', 'MemoryOptimizer']
        }
    except ImportError:
        modules_status['performance'] = {
            'name': '性能优化模块',
            'status': '❌ 不可用',
            'description': '性能监控和内存优化',
            'classes': ['PerformanceMonitor', 'MemoryOptimizer']
        }

    return modules_status


def get_supported_formats() -> Dict[str, List[str]]:
    """获取支持的文件格式"""
    return {
        'input_formats': [
            'Shapefile (.shp)',
            'GeoJSON (.geojson)',
            'GeoPackage (.gpkg)',
            'CSV (.csv) - 需要坐标列',
            'KML (.kml)',
            'FileGDB (.gdb)'
        ],
        'output_formats': [
            'Shapefile (.shp)',
            'GeoJSON (.geojson)',
            'GeoPackage (.gpkg)',
            'CSV (.csv)',
            'KML (.kml)',
            'GeoTIFF (.tif)'
        ]
    }


def analyze_data_file(file_path: Path) -> Dict[str, Any]:
    """分析数据文件信息"""
    try:
        gdf = gpd.read_file(file_path)

        # 基本信息
        info = {
            'file_name': file_path.name,
            'file_size': f"{file_path.stat().st_size / (1024*1024):.2f} MB",
            'record_count': len(gdf),
            'columns': len(gdf.columns),
            'geometry_type': str(gdf.geometry.geom_type.iloc[0]) if len(gdf) > 0 else 'Unknown',
            'crs': str(gdf.crs) if gdf.crs else 'Unknown',
            'bounds': str(gdf.total_bounds.tolist()) if len(gdf) > 0 else 'Unknown'
        }

        # 列信息
        info['column_info'] = []
        for col in gdf.columns:
            if col != 'geometry':
                dtype = str(gdf[col].dtype)
                null_count = gdf[col].isnull().sum()
                info['column_info'].append({
                    'name': col,
                    'type': dtype,
                    'null_count': null_count
                })

        # 几何统计
        if len(gdf) > 0:
            geom_types = gdf.geometry.geom_type.value_counts().to_dict()
            info['geometry_types'] = geom_types

        return info

    except Exception as e:
        return {
            'file_name': file_path.name,
            'error': str(e)
        }


@click.command(name='info')
@click.option('--system', is_flag=True, help='显示系统信息')
@click.option('--dependencies', is_flag=True, help='显示依赖包信息')
@click.option('--modules', is_flag=True, help='显示模块状态')
@click.option('--formats', is_flag=True, help='显示支持的文件格式')
@click.option('--data-file', type=click.Path(exists=True), help='分析指定数据文件')
@click.option('--performance', is_flag=True, help='显示性能基准信息')
@click.option('--all', 'show_all', is_flag=True, help='显示所有信息')
@click.pass_context
def info_cmd(ctx, system, dependencies, modules, formats, data_file, performance, show_all):
    """
    显示系统信息

    示例:
    \b
    # 显示系统概览
    gis-association info

    # 显示详细系统信息
    gis-association info --system

    # 显示模块状态
    gis-association info --modules

    # 分析数据文件
    gis-association info --data-file data.shp

    # 显示所有信息
    gis-association info --all
    """

    # 如果没有指定任何选项，显示概览信息
    if not any([system, dependencies, modules, formats, data_file, performance, show_all]):
        show_overview()
        return

    if show_all or system:
        show_system_info()

    if show_all or dependencies:
        show_dependency_info()

    if show_all or modules:
        show_module_status()

    if show_all or formats:
        show_supported_formats()

    if data_file:
        show_data_file_info(Path(data_file))

    if performance:
        show_performance_info()


def show_overview():
    """显示系统概览"""
    console.print("[bold blue]🗺️  GIS空间关联分析系统 - 系统概览[/bold blue]\n")

    # 版本信息
    try:
        from ... import __version__, __author__
        version_text = Text()
        version_text.append("版本: ", style="bold")
        version_text.append(f"{__version__}\n", style="green")
        version_text.append("作者: ", style="bold")
        version_text.append(f"{__author__}\n", style="blue")
        console.print(Panel(version_text, title="📦 版本信息"))
    except ImportError:
        console.print("[yellow]警告: 无法获取版本信息[/yellow]")

    # 模块状态概览
    modules_status = get_module_status()
    available_modules = sum(1 for m in modules_status.values() if '✅' in m['status'])
    total_modules = len(modules_status)

    module_text = Text()
    module_text.append(f"可用模块: {available_modules}/{total_modules}\n", style="bold green")

    for module_key, module_info in modules_status.items():
        status_color = "green" if '✅' in module_info['status'] else "red"
        module_text.append(f"{module_info['status']} {module_info['name']}\n", style=status_color)

    console.print(Panel(module_text, title="🔧 模块状态"))

    # 系统资源概览
    system_info = get_system_info()
    resource_text = Text()
    resource_text.append(f"CPU核心: {system_info['cpu_count']}\n", style="blue")
    resource_text.append(f"内存总量: {system_info['memory_total']}\n", style="blue")
    resource_text.append(f"可用内存: {system_info['memory_available']}\n", style="green")
    resource_text.append(f"Python版本: {system_info['python_version']}\n", style="blue")

    console.print(Panel(resource_text, title="💻 系统资源"))


def show_system_info():
    """显示详细系统信息"""
    console.print("\n[bold blue]💻 系统环境信息[/bold blue]")

    system_info = get_system_info()

    info_table = Table(show_header=True, header_style="bold magenta")
    info_table.add_column("项目", style="cyan")
    info_table.add_column("值", style="white")

    info_table.add_row("操作系统", system_info['platform'])
    info_table.add_row("Python版本", system_info['python_version'])
    info_table.add_row("架构", system_info['architecture'])
    info_table.add_row("处理器", system_info['processor'] or 'Unknown')
    info_table.add_row("CPU核心数", str(system_info['cpu_count']))
    info_table.add_row("内存总量", system_info['memory_total'])
    info_table.add_row("可用内存", system_info['memory_available'])

    console.print(info_table)


def show_dependency_info():
    """显示依赖包信息"""
    console.print("\n[bold blue]📦 依赖包信息[/bold blue]")

    dependencies = get_dependency_info()

    dep_table = Table(show_header=True, header_style="bold magenta")
    dep_table.add_column("包名", style="cyan")
    dep_table.add_column("版本", style="blue")
    dep_table.add_column("状态", style="bold")

    for package, info in dependencies.items():
        status_color = "green" if '✅' in info['status'] else "red"
        dep_table.add_row(package, info['version'], f"[{status_color}]{info['status']}[/{status_color}]")

    console.print(dep_table)


def show_module_status():
    """显示模块状态"""
    console.print("\n[bold blue]🔧 模块状态详情[/bold blue]")

    modules_status = get_module_status()

    for module_key, module_info in modules_status.items():
        # 创建模块信息面板
        module_text = Text()
        module_text.append(f"状态: {module_info['status']}\n", style="bold")
        module_text.append(f"描述: {module_info['description']}\n", style="dim")

        if 'class' in module_info:
            module_text.append(f"主类: {module_info['class']}\n", style="blue")
        elif 'classes' in module_info:
            module_text.append(f"包含类: {', '.join(module_info['classes'])}\n", style="blue")

        panel_color = "green" if '✅' in module_info['status'] else "red"
        console.print(Panel(module_text, title=module_info['name'], border_style=panel_color))


def show_supported_formats():
    """显示支持的文件格式"""
    console.print("\n[bold blue]📄 支持的文件格式[/bold blue]")

    formats_info = get_supported_formats()

    # 创建两列表格
    format_table = Table(show_header=True, header_style="bold magenta")
    format_table.add_column("输入格式", style="cyan")
    format_table.add_column("输出格式", style="green")

    # 取最长的列表长度
    max_len = max(len(formats_info['input_formats']), len(formats_info['output_formats']))

    for i in range(max_len):
        input_fmt = formats_info['input_formats'][i] if i < len(formats_info['input_formats']) else ""
        output_fmt = formats_info['output_formats'][i] if i < len(formats_info['output_formats']) else ""
        format_table.add_row(input_fmt, output_fmt)

    console.print(format_table)


def show_data_file_info(file_path: Path):
    """显示数据文件信息"""
    console.print(f"\n[bold blue]📊 数据文件分析: {file_path.name}[/bold blue]")

    file_info = analyze_data_file(file_path)

    if 'error' in file_info:
        console.print(f"[red]分析失败: {file_info['error']}[/red]")
        return

    # 基本信息
    basic_table = Table(show_header=True, header_style="bold magenta")
    basic_table.add_column("属性", style="cyan")
    basic_table.add_column("值", style="white")

    basic_table.add_row("文件大小", file_info['file_size'])
    basic_table.add_row("记录数", str(file_info['record_count']))
    basic_table.add_row("字段数", str(file_info['columns']))
    basic_table.add_row("几何类型", file_info['geometry_type'])
    basic_table.add_row("坐标系", file_info['crs'])
    basic_table.add_row("边界范围", file_info['bounds'])

    console.print(basic_table)

    # 列信息
    if file_info['column_info']:
        console.print("\n[bold]字段信息:[/bold]")
        col_table = Table(show_header=True, header_style="bold magenta")
        col_table.add_column("字段名", style="cyan")
        col_table.add_column("数据类型", style="blue")
        col_table.add_row("空值数量", style="yellow")

        for col_info in file_info['column_info']:
            col_table.add_row(
                col_info['name'],
                col_info['type'],
                str(col_info['null_count'])
            )

        console.print(col_table)

    # 几何类型统计
    if 'geometry_types' in file_info:
        console.print("\n[bold]几何类型分布:[/bold]")
        geom_table = Table(show_header=True, header_style="bold magenta")
        geom_table.add_column("几何类型", style="cyan")
        geom_table.add_column("数量", style="green")

        for geom_type, count in file_info['geometry_types'].items():
            geom_table.add_row(str(geom_type), str(count))

        console.print(geom_table)


def show_performance_info():
    """显示性能基准信息"""
    console.print("\n[bold blue]⚡ 性能基准信息[/bold blue]")

    try:
        from ...performance import PerformanceMonitor
        perf_monitor = PerformanceMonitor()

        # 当前性能状态
        current_perf = perf_monitor.get_current_performance()

        perf_table = Table(show_header=True, header_style="bold magenta")
        perf_table.add_column("指标", style="cyan")
        perf_table.add_column("当前值", style="white")
        perf_table.add_column("状态", style="bold")

        # CPU使用率
        cpu_usage = current_perf.get('cpu_usage', 0)
        cpu_status = "🟢 正常" if cpu_usage < 70 else "🟡 较高" if cpu_usage < 90 else "🔴 过高"
        perf_table.add_row("CPU使用率", f"{cpu_usage:.1f}%", cpu_status)

        # 内存使用
        memory_usage = current_perf.get('memory_usage', 0)
        mem_status = "🟢 正常" if memory_usage < 70 else "🟡 较高" if memory_usage < 90 else "🔴 过高"
        perf_table.add_row("内存使用率", f"{memory_usage:.1f}%", mem_status)

        console.print(perf_table)

        # 建议配置
        console.print("\n[bold]性能优化建议:[/bold]")

        recommendations = []
        if cpu_usage > 80:
            recommendations.append("• CPU使用率较高，建议启用并行处理")
        if memory_usage > 80:
            recommendations.append("• 内存使用率较高，建议分批处理大数据")

        if not recommendations:
            recommendations.append("• 系统性能状态良好，可以处理常规任务")
            recommendations.append("• 对于大数据集，建议启用并行处理以提升效率")

        for rec in recommendations:
            console.print(rec)

    except ImportError:
        console.print("[yellow]性能监控模块不可用[/yellow]")


if __name__ == '__main__':
    info_cmd()