"""
Config子命令 - 配置管理

提供完整的配置管理功能：
- 配置文件的创建、编辑、查看
- 配置验证和模板生成
- 环境变量和命令行参数覆盖
- 配置导入导出
- 默认配置重置
"""

import os
import sys
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import print as rprint

# 导入配置管理器
try:
    from ..config.manager import ConfigManager
    from ..config.templates import CONFIG_TEMPLATE, DEFAULT_CONFIG
    from ..config.schema import validate_config
except ImportError as e:
    print(f"错误: 无法导入配置管理模块: {e}")
    sys.exit(1)

console = Console()


@click.group(name='config')
def config_cmd():
    """配置管理命令"""
    pass


@config_cmd.command('create')
@click.option('--path', '-p', type=click.Path(), help='配置文件保存路径')
@click.option('--format', type=click.Choice(['yaml', 'json']), default='yaml',
              help='配置文件格式')
@click.option('--template', type=click.Choice(['default', 'performance', 'validation']),
              default='default', help='配置模板类型')
def create_config(path, format, template):
    """创建新的配置文件"""

    if path:
        config_path = Path(path)
    else:
        # 默认配置文件路径
        config_dir = Path.home() / '.gis_association'
        config_dir.mkdir(exist_ok=True)
        config_path = config_dir / f'config.{format}'

    console.print(f"[bold blue]📝 创建配置文件: {config_path}[/bold blue]")

    # 选择配置模板
    if template == 'default':
        config_data = DEFAULT_CONFIG.copy()
    elif template == 'performance':
        config_data = CONFIG_TEMPLATE['performance'].copy()
    elif template == 'validation':
        config_data = CONFIG_TEMPLATE['validation'].copy()
    else:
        config_data = DEFAULT_CONFIG.copy()

    # 添加元数据
    config_data['_metadata'] = {
        'version': '1.0.0',
        'created': str(pd.Timestamp.now()),
        'template': template
    }

    try:
        # 保存配置文件
        if format == 'yaml':
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
        elif format == 'json':
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

        console.print(f"[green]✓[/green] 配置文件已创建: {config_path}")

        # 显示配置概览
        show_config_overview(config_data)

    except Exception as e:
        console.print(f"[red]创建配置文件失败: {str(e)}[/red]")
        sys.exit(1)


@config_cmd.command('show')
@click.option('--path', '-p', type=click.Path(exists=True), help='配置文件路径')
@click.option('--section', '-s', help='显示特定配置节')
@click.option('--format', type=click.Choice(['table', 'yaml', 'json']),
              default='table', help='显示格式')
def show_config(path, section, format):
    """显示配置文件内容"""

    config_manager = ConfigManager()
    config_manager.load_config(path)

    config_data = config_manager.get_config()

    if section:
        if section not in config_data:
            console.print(f"[red]错误: 配置节 '{section}' 不存在[/red]")
            sys.exit(1)
        config_data = {section: config_data[section]}

    console.print(f"[bold blue]📋 配置信息[/bold blue]")

    if format == 'table':
        display_config_table(config_data)
    elif format == 'yaml':
        console.print(Panel(yaml.dump(config_data, default_flow_style=False, allow_unicode=True),
                           title="配置内容 (YAML)"))
    elif format == 'json':
        console.print(Panel(json.dumps(config_data, indent=2, ensure_ascii=False),
                           title="配置内容 (JSON)"))


@config_cmd.command('edit')
@click.option('--path', '-p', type=click.Path(exists=True), help='配置文件路径')
@click.option('--key', '-k', required=True, help='配置键 (如: processing.max_neighbors)')
@click.option('--value', '-v', required=True, help='配置值')
def edit_config(path, key, value):
    """编辑配置文件"""

    console.print(f"[bold blue]✏️  编辑配置: {key} = {value}[/bold blue]")

    config_manager = ConfigManager()
    config_manager.load_config(path)

    # 解析嵌套键
    keys = key.split('.')
    current = config_manager.config_data

    # 导航到目标位置
    for k in keys[:-1]:
        if k not in current:
            current[k] = {}
        current = current[k]

    # 尝试解析值的类型
    try:
        # 尝试JSON解析
        parsed_value = json.loads(value)
    except json.JSONDecodeError:
        # 如果不是JSON，作为字符串处理
        if value.lower() in ('true', 'false'):
            parsed_value = value.lower() == 'true'
        elif value.isdigit():
            parsed_value = int(value)
        elif value.replace('.', '', 1).isdigit():
            parsed_value = float(value)
        else:
            parsed_value = value

    # 设置值
    current[keys[-1]] = parsed_value

    # 验证配置
    try:
        validate_config(config_manager.config_data)
    except Exception as e:
        console.print(f"[red]配置验证失败: {str(e)}[/red]")
        sys.exit(1)

    # 保存配置
    try:
        config_manager.save_config()
        console.print(f"[green]✓[/green] 配置已更新")
        show_config_overview(config_manager.config_data)
    except Exception as e:
        console.print(f"[red]保存配置失败: {str(e)}[/red]")
        sys.exit(1)


@config_cmd.command('validate')
@click.option('--path', '-p', type=click.Path(exists=True), help='配置文件路径')
def validate_config_cmd(path):
    """验证配置文件"""

    console.print(f"[bold blue]✅ 验证配置文件[/bold blue]")

    config_manager = ConfigManager()

    try:
        config_manager.load_config(path)
        console.print("[green]✓[/green] 配置文件格式正确")

        # 显示验证详情
        config_data = config_manager.get_config()
        validation_info = get_validation_info(config_data)
        display_validation_info(validation_info)

    except Exception as e:
        console.print(f"[red]配置验证失败: {str(e)}[/red]")
        sys.exit(1)


@config_cmd.command('reset')
@click.option('--global', 'global_reset', is_flag=True, help='重置全局配置')
@click.option('--local', is_flag=True, help='重置本地配置')
@click.option('--force', is_flag=True, help='强制重置，不询问确认')
def reset_config(global_reset, local, force):
    """重置配置为默认值"""

    if not force:
        if not click.confirm('确定要重置配置为默认值吗？此操作不可撤销。'):
            console.print("[yellow]操作已取消[/yellow]")
            return

    console.print("[bold blue]🔄 重置配置为默认值[/bold blue]")

    try:
        if global_reset:
            # 重置全局配置
            global_config_dir = Path.home() / '.gis_association'
            global_config_path = global_config_dir / 'config.yaml'

            if global_config_path.exists():
                global_config_path.unlink()

            # 创建默认全局配置
            global_config_dir.mkdir(exist_ok=True)
            with open(global_config_path, 'w', encoding='utf-8') as f:
                yaml.dump(DEFAULT_CONFIG, f, default_flow_style=False, allow_unicode=True)

            console.print("[green]✓[/green] 全局配置已重置")

        if local:
            # 重置本地配置
            local_config_path = Path.cwd() / '.gis_association_config.yaml'

            if local_config_path.exists():
                local_config_path.unlink()

            # 创建默认本地配置
            with open(local_config_path, 'w', encoding='utf-8') as f:
                yaml.dump(DEFAULT_CONFIG, f, default_flow_style=False, allow_unicode=True)

            console.print("[green]✓[/green] 本地配置已重置")

        if not global_reset and not local:
            console.print("[yellow]请指定 --global 或 --local 选项[/yellow]")

    except Exception as e:
        console.print(f"[red]重置配置失败: {str(e)}[/red]")
        sys.exit(1)


@config_cmd.command('export')
@click.option('--input', '-i', type=click.Path(exists=True), help='输入配置文件')
@click.option('--output', '-o', type=click.Path(), required=True, help='输出配置文件')
@click.option('--format', type=click.Choice(['yaml', 'json']), help='输出格式')
def export_config(input, output, format):
    """导出配置文件"""

    console.print(f"[bold blue]📤 导出配置文件[/bold blue]")

    try:
        config_manager = ConfigManager()
        config_manager.load_config(input)

        # 确定输出格式
        output_path = Path(output)
        if format:
            output_format = format
        else:
            output_format = 'yaml' if output_path.suffix.lower() in ['.yaml', '.yml'] else 'json'

        # 导出配置
        with open(output_path, 'w', encoding='utf-8') as f:
            if output_format == 'yaml':
                yaml.dump(config_manager.get_config(), f, default_flow_style=False, allow_unicode=True)
            else:
                json.dump(config_manager.get_config(), f, indent=2, ensure_ascii=False)

        console.print(f"[green]✓[/green] 配置已导出到: {output_path}")

    except Exception as e:
        console.print(f"[red]导出配置失败: {str(e)}[/red]")
        sys.exit(1)


@config_cmd.command('list')
def list_configs():
    """列出所有配置文件"""

    console.print("[bold blue]📋 配置文件列表[/bold blue]")

    config_paths = [
        Path.home() / '.gis_association' / 'config.yaml',  # 全局配置
        Path.cwd() / '.gis_association_config.yaml',       # 本地配置
        Path.cwd() / 'gis_association_config.yaml',        # 项目配置
    ]

    config_table = Table(show_header=True, header_style="bold magenta")
    config_table.add_column("配置文件", style="cyan")
    config_table.add_column("路径", style="blue")
    config_table.add_column("状态", style="bold")

    for config_path in config_paths:
        if config_path.exists():
            status = "✅ 存在"
            status_style = "green"
        else:
            status = "❌ 不存在"
            status_style = "red"

        config_name = {
            config_paths[0]: "全局配置",
            config_paths[1]: "本地配置",
            config_paths[2]: "项目配置"
        }.get(config_path, "未知配置")

        config_table.add_row(
            config_name,
            str(config_path),
            f"[{status_style}]{status}[/{status_style}]"
        )

    console.print(config_table)


def show_config_overview(config_data: Dict[str, Any]):
    """显示配置概览"""
    overview_table = Table(show_header=True, header_style="bold magenta")
    overview_table.add_column("配置节", style="cyan")
    overview_table.add_column("设置项数量", style="blue")

    for section_name, section_data in config_data.items():
        if section_name.startswith('_'):  # 跳过元数据
            continue
        if isinstance(section_data, dict):
            count = len(section_data)
        else:
            count = 1
        overview_table.add_row(section_name, str(count))

    console.print(overview_table)


def display_config_table(config_data: Dict[str, Any]):
    """以表格形式显示配置"""
    for section_name, section_data in config_data.items():
        if section_name.startswith('_'):  # 跳过元数据
            continue

        console.print(f"\n[bold cyan]{section_name}[/bold cyan]")

        if isinstance(section_data, dict):
            section_table = Table(show_header=False, box=None)
            section_table.add_column("配置项", style="blue")
            section_table.add_column("值", style="white")

            for key, value in section_data.items():
                if isinstance(value, dict):
                    value_str = f"{len(value)} 项配置"
                elif isinstance(value, list):
                    value_str = f"{len(value)} 项"
                else:
                    value_str = str(value)
                section_table.add_row(key, value_str)

            console.print(section_table)
        else:
            console.print(f"  {section_data}")


def get_validation_info(config_data: Dict[str, Any]) -> Dict[str, Any]:
    """获取配置验证信息"""
    validation_info = {
        'total_sections': 0,
        'valid_sections': 0,
        'warnings': [],
        'errors': []
    }

    for section_name, section_data in config_data.items():
        if section_name.startswith('_'):
            continue

        validation_info['total_sections'] += 1

        # 基本验证
        try:
            if section_name == 'processing' and isinstance(section_data, dict):
                # 验证处理配置
                required_keys = ['max_neighbors', 'distance_threshold', 'parallel']
                for key in required_keys:
                    if key not in section_data:
                        validation_info['warnings'].append(f"{section_name}.{key} 未设置")

            elif section_name == 'validation' and isinstance(section_data, dict):
                # 验证验证配置
                if 'strict_mode' in section_data and not isinstance(section_data['strict_mode'], bool):
                    validation_info['errors'].append(f"{section_name}.strict_mode 必须是布尔值")

            elif section_name == 'output' and isinstance(section_data, dict):
                # 验证输出配置
                if 'default_format' in section_data:
                    valid_formats = ['shp', 'geojson', 'gpkg', 'csv']
                    if section_data['default_format'] not in valid_formats:
                        validation_info['errors'].append(
                            f"{section_name}.default_format 必须是: {', '.join(valid_formats)}"
                        )

            validation_info['valid_sections'] += 1

        except Exception as e:
            validation_info['errors'].append(f"{section_name}: {str(e)}")

    return validation_info


def display_validation_info(validation_info: Dict[str, Any]):
    """显示验证信息"""
    # 基本统计
    stats_table = Table(show_header=False, box=None)
    stats_table.add_column("项目", style="cyan")
    stats_table.add_column("值", style="bold")

    stats_table.add_row("配置节数", str(validation_info['total_sections']))
    stats_table.add_row("有效节数", f"[green]{validation_info['valid_sections']}[/green]")
    console.print(stats_table)

    # 警告
    if validation_info['warnings']:
        console.print("\n[bold yellow]⚠️  警告:[/bold yellow]")
        for warning in validation_info['warnings']:
            console.print(f"  • {warning}")

    # 错误
    if validation_info['errors']:
        console.print("\n[bold red]❌ 错误:[/bold red]")
        for error in validation_info['errors']:
            console.print(f"  • {error}")


# 添加必要的导入
try:
    import pandas as pd
except ImportError:
    pd = None


if __name__ == '__main__':
    config_cmd()