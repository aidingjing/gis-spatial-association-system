"""
Process子命令 - 空间关联分析处理

执行各种类型的空间关联分析：
- 点-线最近邻关联
- 线-线相交检测
- 线-面包含判断
- 批量处理和并行计算
"""

import os
import sys
import time
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

import click
import geopandas as gpd
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn

# 导入项目核心模块
try:
    from ...algorithms.association import NearestNeighborAssociator
    from ...algorithms.intersection import LineIntersectionDetector
    from ...algorithms.containment import PolygonContainmentAnalyzer
    from ...algorithms.transformation import CoordinateTransformer
    from ...performance.monitoring import PerformanceMonitor
    from ...validation import GeometryValidator, AttributeValidator, DataQualityScorer
except ImportError as e:
    print(f"错误: 无法导入核心算法模块: {e}")
    sys.exit(1)

console = Console()


def validate_files(file_paths: List[str]) -> List[Path]:
    """验证输入文件是否存在且格式正确"""
    valid_files = []
    for file_path in file_paths:
        path = Path(file_path)
        if not path.exists():
            console.print(f"[red]错误: 文件不存在: {file_path}[/red]")
            sys.exit(1)

        # 检查文件扩展名
        valid_extensions = {'.shp', '.geojson', '.gpkg', '.csv', '.json'}
        if path.suffix.lower() not in valid_extensions:
            console.print(f"[red]错误: 不支持的文件格式: {path.suffix}[/red]")
            console.print(f"支持的格式: {', '.join(valid_extensions)}")
            sys.exit(1)

        valid_files.append(path)

    return valid_files


def load_geodata(file_path: Path, **kwargs) -> gpd.GeoDataFrame:
    """加载地理数据"""
    try:
        if file_path.suffix.lower() == '.shp':
            # Shapefile格式
            gdf = gpd.read_file(file_path, **kwargs)
        elif file_path.suffix.lower() == '.geojson':
            # GeoJSON格式
            gdf = gpd.read_file(file_path, **kwargs)
        elif file_path.suffix.lower() == '.gpkg':
            # GeoPackage格式
            gdf = gpd.read_file(file_path, layer=kwargs.get('layer', 0), **kwargs)
        elif file_path.suffix.lower() == '.csv':
            # CSV格式，需要指定坐标列
            if 'x_col' not in kwargs or 'y_col' not in kwargs:
                console.print("[red]错误: CSV文件需要指定x_col和y_col参数[/red]")
                sys.exit(1)
            gdf = gpd.read_file(file_path, **kwargs)
            # 转换为GeoDataFrame
            from shapely.geometry import Point
            gdf['geometry'] = gdf.apply(
                lambda row: Point(row[kwargs['x_col']], row[kwargs['y_col']]),
                axis=1
            )
            gdf = gpd.GeoDataFrame(gdf, geometry='geometry')
        else:
            console.print(f"[red]错误: 不支持的文件格式: {file_path.suffix}[/red]")
            sys.exit(1)

        console.print(f"[green]✓[/green] 成功加载文件: {file_path.name} ({len(gdf)} 条记录)")
        return gdf

    except Exception as e:
        console.print(f"[red]错误: 无法加载文件 {file_path}: {str(e)}[/red]")
        sys.exit(1)


@click.command(name='process')
@click.argument('input_files', nargs=-1, required=True)
@click.option('--analysis-type', '-t',
              type=click.Choice(['point-line', 'line-line', 'line-polygon', 'auto']),
              default='auto', help='分析类型')
@click.option('--output', '-o', type=click.Path(), help='输出文件路径')
@click.option('--output-format', type=click.Choice(['shp', 'geojson', 'gpkg', 'csv']),
              default='geojson', help='输出格式')
@click.option('--distance-threshold', type=float, default=1000.0,
              help='距离阈值(米)，用于最近邻分析')
@click.option('--max-neighbors', type=int, default=1, help='最大邻居数量')
@click.option('--coordinate-system', type=str, help='目标坐标系(如EPSG:4326)')
@click.option('--parallel/--no-parallel', default=True, help='是否启用并行处理')
@click.option('--validate/--no-validate', default=True, help='是否进行数据验证')
@click.option('--x-col', type=str, help='CSV文件的X坐标列名')
@click.option('--y-col', type=str, help='CSV文件的Y坐标列名')
@click.option('--layer', type=str, help='GeoPackage图层名称')
@click.option('--summary/--no-summary', default=True, help='是否显示处理摘要')
@click.pass_context
def process_cmd(ctx, input_files, analysis_type, output, output_format,
                distance_threshold, max_neighbors, coordinate_system, parallel,
                validate, x_col, y_col, layer, summary):
    """
    执行空间关联分析处理

    INPUT_FILES: 输入文件路径，支持Shapefile、GeoJSON、GeoPackage、CSV格式

    示例:
    \b
    # 点-线最近邻关联分析
    gis-association process points.shp lines.shp -t point-line -o result.geojson

    # 线-线相交检测
    gis-association process roads1.shp roads2.shp -t line-line -o intersections.geojson

    # 线-面包含判断
    gis-association process rivers.shp basins.shp -t line-polygon -o containment.geojson

    # 自动检测分析类型
    gis-association process file1.geojson file2.geojson -o result.shp
    """

    start_time = time.time()

    # 验证输入文件
    console.print("[bold blue]🔍 验证输入文件...[/bold blue]")
    input_paths = validate_files(list(input_files))

    if len(input_paths) < 2:
        console.print("[red]错误: 至少需要2个输入文件进行分析[/red]")
        sys.exit(1)
    elif len(input_paths) > 2:
        console.print("[yellow]警告: 只使用前2个文件进行分析[/yellow]")
        input_paths = input_paths[:2]

    # 加载地理数据
    console.print("[bold blue]📂 加载地理数据...[/bold blue]")
    load_kwargs = {}
    if x_col:
        load_kwargs['x_col'] = x_col
    if y_col:
        load_kwargs['y_col'] = y_col
    if layer:
        load_kwargs['layer'] = layer

    try:
        gdf1 = load_geodata(input_paths[0], **load_kwargs)
        gdf2 = load_geodata(input_paths[1], **load_kwargs)
    except Exception as e:
        console.print(f"[red]数据加载失败: {str(e)}[/red]")
        sys.exit(1)

    # 数据验证
    if validate:
        console.print("[bold blue]✅ 数据质量验证...[/bold blue]")
        try:
            validator = GeometryValidator()
            quality_scorer = DataQualityScorer()

            # 验证几何数据
            valid1 = validator.validate_geometries(gdf1)
            valid2 = validator.validate_geometries(gdf2)

            # 计算质量分数
            score1 = quality_scorer.calculate_quality_score(valid1)
            score2 = quality_scorer.calculate_quality_score(valid2)

            console.print(f"[green]数据集1质量分数: {score1:.2f}[/green]")
            console.print(f"[green]数据集2质量分数: {score2:.2f}[/green]")

            gdf1, gdf2 = valid1, valid2

        except Exception as e:
            console.print(f"[yellow]数据验证失败，继续使用原始数据: {str(e)}[/yellow]")

    # 坐标系转换
    if coordinate_system:
        console.print(f"[bold blue]🗺️  坐标系转换至 {coordinate_system}...[/bold blue]")
        try:
            transformer = CoordinateTransformer()
            gdf1 = transformer.transform_gdf(gdf1, coordinate_system)
            gdf2 = transformer.transform_gdf(gdf2, coordinate_system)
            console.print("[green]✓[/green] 坐标系转换完成")
        except Exception as e:
            console.print(f"[yellow]坐标系转换失败: {str(e)}[/yellow]")

    # 自动检测分析类型
    if analysis_type == 'auto':
        console.print("[bold blue]🔬 自动检测分析类型...[/bold blue]")
        geom_type1 = gdf1.geometry.geom_type.iloc[0] if len(gdf1) > 0 else 'Unknown'
        geom_type2 = gdf2.geometry.geom_type.iloc[0] if len(gdf2) > 0 else 'Unknown'

        if 'Point' in str(geom_type1) and 'LineString' in str(geom_type2):
            analysis_type = 'point-line'
        elif 'LineString' in str(geom_type1) and 'LineString' in str(geom_type2):
            analysis_type = 'line-line'
        elif 'LineString' in str(geom_type1) and 'Polygon' in str(geom_type2):
            analysis_type = 'line-polygon'
        elif 'Polygon' in str(geom_type1) and 'LineString' in str(geom_type2):
            analysis_type = 'line-polygon'
            gdf1, gdf2 = gdf2, gdf1  # 交换顺序，确保线在前
        else:
            console.print(f"[red]错误: 无法识别的几何类型组合: {geom_type1} + {geom_type2}[/red]")
            sys.exit(1)

        console.print(f"[green]检测到分析类型: {analysis_type}[/green]")

    # 执行空间关联分析
    console.print(f"[bold blue]⚡ 执行 {analysis_type} 分析...[/bold blue]")

    try:
        # 启动性能监控
        perf_monitor = PerformanceMonitor()
        perf_monitor.start_monitoring()

        # 根据分析类型选择算法
        if analysis_type == 'point-line':
            associator = NearestNeighborAssociator(
                distance_threshold=distance_threshold,
                max_neighbors=max_neighbors,
                parallel=parallel
            )
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TimeRemainingColumn(),
                console=console
            ) as progress:
                task = progress.add_task("执行点-线关联分析...", total=100)
                result = associator.associate_points_to_lines(gdf1, gdf2)
                progress.update(task, completed=100)

        elif analysis_type == 'line-line':
            detector = LineIntersectionDetector(parallel=parallel)
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TimeRemainingColumn(),
                console=console
            ) as progress:
                task = progress.add_task("执行线-线相交检测...", total=100)
                result = detector.find_intersections(gdf1, gdf2)
                progress.update(task, completed=100)

        elif analysis_type == 'line-polygon':
            analyzer = PolygonContainmentAnalyzer(parallel=parallel)
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TimeRemainingColumn(),
                console=console
            ) as progress:
                task = progress.add_task("执行线-面包含分析...", total=100)
                result = analyzer.analyze_containment(gdf1, gdf2)
                progress.update(task, completed=100)

        else:
            console.print(f"[red]错误: 不支持的分析类型: {analysis_type}[/red]")
            sys.exit(1)

        # 停止性能监控
        perf_stats = perf_monitor.stop_monitoring()

    except Exception as e:
        console.print(f"[red]分析执行失败: {str(e)}[/red]")
        import traceback
        console.print(traceback.format_exc())
        sys.exit(1)

    # 保存结果
    if output:
        output_path = Path(output)
    else:
        # 自动生成输出文件名
        timestamp = int(time.time())
        output_name = f"association_result_{timestamp}.{output_format}"
        output_path = Path(output_name)

    console.print(f"[bold blue]💾 保存结果到 {output_path}...[/bold blue]")

    try:
        if output_format == 'shp':
            result.to_file(output_path, driver='ESRI Shapefile')
        elif output_format == 'geojson':
            result.to_file(output_path, driver='GeoJSON')
        elif output_format == 'gpkg':
            result.to_file(output_path, driver='GPKG')
        elif output_format == 'csv':
            # CSV格式需要将几何转换为WKT
            result_csv = result.copy()
            result_csv['geometry'] = result_csv.geometry.to_wkt()
            result_csv.to_csv(output_path, index=False)

        console.print(f"[green]✓[/green] 结果已保存到: {output_path}")

    except Exception as e:
        console.print(f"[red]保存结果失败: {str(e)}[/red]")
        sys.exit(1)

    # 显示处理摘要
    if summary:
        end_time = time.time()
        processing_time = end_time - start_time

        console.print("\n[bold green]📊 处理摘要[/bold green]")

        summary_table = Table(show_header=True, header_style="bold magenta")
        summary_table.add_column("项目", style="cyan")
        summary_table.add_column("值", style="green")

        summary_table.add_row("分析类型", analysis_type)
        summary_table.add_row("输入文件1", f"{input_paths[0].name} ({len(gdf1)} 条记录)")
        summary_table.add_row("输入文件2", f"{input_paths[1].name} ({len(gdf2)} 条记录)")
        summary_table.add_row("结果记录数", str(len(result)))
        summary_table.add_row("处理时间", f"{processing_time:.2f} 秒")
        summary_table.add_row("输出文件", str(output_path))

        if perf_stats:
            summary_table.add_row("内存使用峰值", f"{perf_stats.get('memory_peak', 'N/A')} MB")
            summary_table.add_row("CPU使用率", f"{perf_stats.get('cpu_usage', 'N/A')}%")

        console.print(summary_table)

    console.print("\n[bold green]🎉 分析完成![/bold green]")


if __name__ == '__main__':
    process_cmd()