"""
Validate子命令 - 数据验证和修复

提供全面的数据质量验证和修复功能：
- 几何数据验证
- 属性数据验证
- 坐标系验证
- 数据质量评分
- 自动修复功能
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

import click
import geopandas as gpd
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich.progress import Progress, SpinnerColumn, TextColumn

# 导入项目验证模块
try:
    from ...validation import (
        GeometryValidator, AttributeValidator, CoordinateSystemValidator,
        DataQualityScorer, DataRepairer
    )
    from ...validation.geometry import GeometryType
except ImportError as e:
    print(f"错误: 无法导入验证模块: {e}")
    sys.exit(1)

console = Console()


def load_data_for_validation(file_path: Path, **kwargs) -> gpd.GeoDataFrame:
    """加载待验证的数据"""
    try:
        if file_path.suffix.lower() == '.shp':
            gdf = gpd.read_file(file_path, **kwargs)
        elif file_path.suffix.lower() == '.geojson':
            gdf = gpd.read_file(file_path, **kwargs)
        elif file_path.suffix.lower() == '.gpkg':
            gdf = gpd.read_file(file_path, layer=kwargs.get('layer', 0), **kwargs)
        else:
            console.print(f"[red]错误: 不支持的文件格式: {file_path.suffix}[/red]")
            sys.exit(1)

        console.print(f"[green]✓[/green] 成功加载: {file_path.name} ({len(gdf)} 条记录)")
        return gdf

    except Exception as e:
        console.print(f"[red]错误: 无法加载文件 {file_path}: {str(e)}[/red]")
        sys.exit(1)


def display_validation_results(results: Dict[str, Any], file_name: str):
    """显示验证结果"""
    console.print(f"\n[bold blue]📋 {file_name} - 验证结果[/bold blue]")

    # 创建结果表格
    results_table = Table(show_header=True, header_style="bold magenta")
    results_table.add_column("验证项目", style="cyan")
    results_table.add_column("状态", style="bold")
    results_table.add_column("详情", style="dim")

    # 几何验证结果
    if 'geometry' in results:
        geom_results = results['geometry']
        geom_status = "✅ 通过" if geom_results.get('valid_count', 0) == geom_results.get('total_count', 0) else "❌ 失败"
        geom_details = f"有效: {geom_results.get('valid_count', 0)}/{geom_results.get('total_count', 0)}"
        results_table.add_row("几何有效性", geom_status, geom_details)

        if 'issues' in geom_results:
            for issue, count in geom_results['issues'].items():
                results_table.add_row(f"  - {issue}", "⚠️", f"{count} 个")

    # 属性验证结果
    if 'attributes' in results:
        attr_results = results['attributes']
        attr_status = "✅ 通过" if not attr_results.get('issues', []) else "❌ 失败"
        attr_details = f"检查字段: {len(attr_results.get('checked_fields', []))}"
        results_table.add_row("属性完整性", attr_status, attr_details)

        for issue in attr_results.get('issues', []):
            results_table.add_row(f"  - {issue}", "⚠️", "")

    # 坐标系验证结果
    if 'coordinate_system' in results:
        crs_results = results['coordinate_system']
        crs_status = "✅ 正常" if crs_results.get('is_valid', False) else "❌ 异常"
        crs_details = crs_results.get('crs_info', '未知')
        results_table.add_row("坐标系", crs_status, crs_details)

    # 数据质量评分
    if 'quality_score' in results:
        score = results['quality_score']
        score_color = "green" if score >= 80 else "yellow" if score >= 60 else "red"
        results_table.add_row("数据质量评分", f"[{score_color}]{score:.1f}/100[/{score_color}]", "")

    console.print(results_table)


def display_repair_summary(repair_results: Dict[str, Any], file_name: str):
    """显示修复摘要"""
    console.print(f"\n[bold green]🔧 {file_name} - 修复摘要[/bold green]")

    repair_table = Table(show_header=True, header_style="bold magenta")
    repair_table.add_column("修复项目", style="cyan")
    repair_table.add_column("修复数量", style="green")

    if 'geometry_repairs' in repair_results:
        for repair_type, count in repair_results['geometry_repairs'].items():
            repair_table.add_row(f"几何 - {repair_type}", str(count))

    if 'attribute_repairs' in repair_results:
        for repair_type, count in repair_results['attribute_repairs'].items():
            repair_table.add_row(f"属性 - {repair_type}", str(count))

    console.print(repair_table)


@click.command(name='validate')
@click.argument('input_files', nargs=-1, required=True)
@click.option('--repair/--no-repair', default=False, help='是否自动修复发现的问题')
@click.option('--output', '-o', type=click.Path(), help='验证报告输出路径')
@click.option('--report-format', type=click.Choice(['json', 'html', 'txt']),
              default='txt', help='报告格式')
@click.option('--geometry-only', is_flag=True, help='仅验证几何数据')
@click.option('--attributes-only', is_flag=True, help='仅验证属性数据')
@click.option('--strict/--lenient', default=False, help='严格模式验证')
@click.option('--layer', type=str, help='GeoPackage图层名称')
@click.option('--threshold', type=float, default=0.001,
              help='几何容差阈值')
@click.pass_context
def validate_cmd(ctx, input_files, repair, output, report_format,
                geometry_only, attributes_only, strict, layer, threshold):
    """
    数据验证和修复

    INPUT_FILES: 待验证的数据文件路径，支持Shapefile、GeoJSON、GeoPackage格式

    示例:
    \b
    # 基本验证
    gis-association validate data.shp

    # 验证并修复
    gis-association validate data.geojson --repair

    # 生成详细报告
    gis-association validate data.shp --output report.json --report-format json

    # 严格模式验证
    gis-association validate data.shp --strict --repair

    # 仅验证几何数据
    gis-association validate data.shp --geometry-only
    """

    console.print("[bold blue]🔍 开始数据验证...[/bold blue]")

    # 验证输入文件
    input_paths = []
    for file_path in input_files:
        path = Path(file_path)
        if not path.exists():
            console.print(f"[red]错误: 文件不存在: {file_path}[/red]")
            sys.exit(1)
        input_paths.append(path)

    all_results = {}
    all_repair_results = {}

    # 初始化验证器
    validators = {}
    if not attributes_only:
        validators['geometry'] = GeometryValidator(strict=strict, tolerance=threshold)
    if not geometry_only:
        validators['attributes'] = AttributeValidator(strict=strict)
        validators['coordinate_system'] = CoordinateSystemValidator(strict=strict)

    # 质量评分器
    quality_scorer = DataQualityScorer()

    # 数据修复器
    repairer = DataRepairer() if repair else None

    # 逐个验证文件
    for file_path in input_paths:
        console.print(f"\n[bold cyan]验证文件: {file_path.name}[/bold cyan]")

        # 加载数据
        load_kwargs = {}
        if layer:
            load_kwargs['layer'] = layer

        gdf = load_data_for_validation(file_path, **load_kwargs)

        file_results = {'file_name': file_path.name}
        original_gdf = gdf.copy()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            # 几何验证
            if 'geometry' in validators:
                task = progress.add_task("验证几何数据...", total=None)
                geom_results = validators['geometry'].validate_geometries(gdf)
                file_results['geometry'] = geom_results
                progress.update(task, description="几何验证完成")

            # 属性验证
            if 'attributes' in validators:
                task = progress.add_task("验证属性数据...", total=None)
                attr_results = validators['attributes'].validate_attributes(gdf)
                file_results['attributes'] = attr_results
                progress.update(task, description="属性验证完成")

            # 坐标系验证
            if 'coordinate_system' in validators:
                task = progress.add_task("验证坐标系...", total=None)
                crs_results = validators['coordinate_system'].validate_crs(gdf)
                file_results['coordinate_system'] = crs_results
                progress.update(task, description="坐标系验证完成")

            # 数据质量评分
            task = progress.add_task("计算质量分数...", total=None)
            try:
                quality_score = quality_scorer.calculate_quality_score(gdf)
                file_results['quality_score'] = quality_score
                progress.update(task, description=f"质量评分: {quality_score:.1f}/100")
            except Exception as e:
                file_results['quality_score'] = 0.0
                console.print(f"[yellow]质量评分失败: {str(e)}[/yellow]")

        # 显示验证结果
        display_validation_results(file_results, file_path.name)

        # 自动修复
        if repair:
            console.print(f"\n[bold yellow]🔧 开始自动修复 {file_path.name}...[/bold yellow]")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                repair_results = repairer.repair_data(gdf, file_results)
                all_repair_results[file_path.name] = repair_results

                # 显示修复摘要
                display_repair_summary(repair_results, file_path.name)

                # 保存修复后的数据
                if repair_results.get('repairs_made', False):
                    output_path = file_path.parent / f"{file_path.stem}_repaired{file_path.suffix}"
                    gdf.to_file(output_path)
                    console.print(f"[green]✓[/green] 修复后的数据已保存到: {output_path}")

        all_results[file_path.name] = file_results

    # 生成验证报告
    if output:
        report_path = Path(output)
        console.print(f"\n[bold blue]📄 生成验证报告: {report_path}[/bold blue]")

        if report_format == 'json':
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'validation_results': all_results,
                    'repair_results': all_repair_results,
                    'summary': {
                        'total_files': len(input_paths),
                        'validation_time': pd.Timestamp.now().isoformat()
                    }
                }, f, indent=2, ensure_ascii=False, default=str)

        elif report_format == 'txt':
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("GIS空间关联分析系统 - 数据验证报告\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"生成时间: {pd.Timestamp.now()}\n")
                f.write(f"验证文件数: {len(input_paths)}\n\n")

                for file_name, results in all_results.items():
                    f.write(f"文件: {file_name}\n")
                    f.write("-" * 30 + "\n")

                    if 'quality_score' in results:
                        f.write(f"数据质量评分: {results['quality_score']:.1f}/100\n")

                    if 'geometry' in results:
                        geom = results['geometry']
                        f.write(f"几何有效性: {geom.get('valid_count', 0)}/{geom.get('total_count', 0)}\n")

                    if 'attributes' in results:
                        f.write(f"属性问题: {len(results['attributes'].get('issues', []))}\n")

                    f.write("\n")

        console.print(f"[green]✓[/green] 验证报告已保存到: {report_path}")

    # 总体摘要
    console.print("\n[bold green]📊 验证摘要[/bold green]")

    summary_table = Table(show_header=True, header_style="bold magenta")
    summary_table.add_column("文件名", style="cyan")
    summary_table.add_column("记录数", style="blue")
    summary_table.add_column("质量评分", style="yellow")
    summary_table.add_column("状态", style="green")

    total_score = 0
    for file_path in input_paths:
        file_name = file_path.name
        if file_name in all_results:
            results = all_results[file_name]
            score = results.get('quality_score', 0)
            total_score += score

            # 获取记录数
            try:
                gdf = gpd.read_file(file_path)
                record_count = len(gdf)
            except:
                record_count = "未知"

            # 状态
            if score >= 80:
                status = "✅ 优秀"
            elif score >= 60:
                status = "⚠️ 良好"
            else:
                status = "❌ 需要修复"

            summary_table.add_row(file_name, str(record_count), f"{score:.1f}", status)

    console.print(summary_table)

    if len(input_paths) > 0:
        avg_score = total_score / len(input_paths)
        console.print(f"\n[bold]平均质量评分: {avg_score:.1f}/100[/bold]")

    console.print("\n[bold green]🎉 验证完成![/bold green]")


if __name__ == '__main__':
    validate_cmd()