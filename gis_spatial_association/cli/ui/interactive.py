"""
交互式操作界面

提供用户友好的向导式操作界面：
- 文件选择和参数配置
- 实时预览和确认机制
- 错误处理和用户指导
- 多步骤操作流程
- 智能默认值和建议
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Callable

try:
    from rich.console import Console
    from rich.prompt import Prompt, IntPrompt, FloatPrompt, Confirm
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.layout import Layout
    from rich.columns import Columns
    from rich import print as rprint
    from rich.markdown import Markdown
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

import click
import logging

logger = logging.getLogger(__name__)


class InteractiveMode:
    """交互式操作模式"""

    def __init__(self, cli_context=None):
        """
        初始化交互式模式

        Args:
            cli_context: CLI上下文对象
        """
        self.cli_context = cli_context
        self.console = Console() if RICH_AVAILABLE else None
        self.session_data = {}
        self.current_step = 0
        self.steps = []

        # 配置管理器
        try:
            from ..config.manager import ConfigManager
            self.config_manager = ConfigManager()
            self.config_manager.load_config()
        except ImportError:
            self.config_manager = None

    def run(self):
        """运行交互式模式"""
        if self.console:
            self.console.print(Panel(
                "[bold blue]🗺️  GIS空间关联分析系统 - 交互式模式[/bold blue]\n\n"
                "欢迎使用交互式操作模式！我将引导您完成空间关联分析的设置和执行。\n"
                "按照提示操作，您可以随时输入 'quit' 退出，输入 'help' 获取帮助。",
                title="欢迎",
                border_style="blue"
            ))
        else:
            print("🗺️  GIS空间关联分析系统 - 交互式模式")
            print("=" * 50)

        try:
            while True:
                action = self._show_main_menu()

                if action == "process":
                    self._interactive_process()
                elif action == "validate":
                    self._interactive_validate()
                elif action == "config":
                    self._interactive_config()
                elif action == "info":
                    self._show_system_info()
                elif action == "help":
                    self._show_help()
                elif action == "quit":
                    self.console.print("[yellow]感谢使用GIS空间关联分析系统！[/yellow]") if self.console else print("感谢使用！")
                    break
                else:
                    self._show_error("无效的选择")

        except KeyboardInterrupt:
            self.console.print("\n[yellow]操作被用户中断[/yellow]") if self.console else print("\n操作被中断")
        except Exception as e:
            self._show_error(f"发生错误: {str(e)}")

    def _show_main_menu(self) -> str:
        """显示主菜单"""
        menu_items = [
            "process - 执行空间关联分析",
            "validate - 数据验证和修复",
            "config - 配置管理",
            "info - 系统信息",
            "help - 帮助信息",
            "quit - 退出程序"
        ]

        if self.console:
            menu_table = Table(show_header=True, header_style="bold magenta")
            menu_table.add_column("选项", style="cyan")
            menu_table.add_column("说明", style="white")

            for item in menu_items:
                option, description = item.split(" - ", 1)
                menu_table.add_row(option, description)

            self.console.print("\n[bold]请选择操作:[/bold]")
            self.console.print(menu_table)

            choice = Prompt.ask("请输入选项", choices=["process", "validate", "config", "info", "help", "quit"], default="process")
        else:
            print("\n主菜单:")
            for i, item in enumerate(menu_items, 1):
                print(f"{i}. {item}")

            choice_map = {
                "1": "process", "2": "validate", "3": "config",
                "4": "info", "5": "help", "6": "quit"
            }

            choice = input("请选择 (1-6): ").strip().lower()
            choice = choice_map.get(choice, choice)

        return choice

    def _interactive_process(self):
        """交互式处理模式"""
        if self.console:
            self.console.print(Panel(
                "[bold green]📊 空间关联分析向导[/bold green]\n\n"
                "我将引导您设置空间关联分析的各项参数。",
                title="分析向导",
                border_style="green"
            ))

        # 步骤1: 选择分析类型
        analysis_type = self._select_analysis_type()
        if analysis_type == "back":
            return

        # 步骤2: 选择输入文件
        input_files = self._select_input_files(analysis_type)
        if input_files == "back":
            return

        # 步骤3: 配置参数
        params = self._configure_parameters(analysis_type)
        if params == "back":
            return

        # 步骤4: 配置输出
        output_config = self._configure_output()
        if output_config == "back":
            return

        # 步骤5: 确认并执行
        if self._confirm_execution(analysis_type, input_files, params, output_config):
            self._execute_analysis(analysis_type, input_files, params, output_config)

    def _select_analysis_type(self) -> str:
        """选择分析类型"""
        if self.console:
            analysis_types = [
                ("point-line", "点-线最近邻关联分析", "分析点要素到线的最近邻关系"),
                ("line-line", "线-线相交检测分析", "检测线要素之间的相交关系"),
                ("line-polygon", "线-面包含判断分析", "判断线要素是否被面要素包含"),
                ("auto", "自动检测", "根据输入文件自动选择合适的分析方法")
            ]

            type_table = Table(show_header=True, header_style="bold magenta")
            type_table.add_column("类型", style="cyan")
            type_table.add_column("说明", style="white")
            type_table.add_column("描述", style="dim")

            for type_id, name, desc in analysis_types:
                type_table.add_row(type_id, name, desc)

            self.console.print("\n[bold]选择分析类型:[/bold]")
            self.console.print(type_table)

            choice = Prompt.ask(
                "请选择分析类型",
                choices=["point-line", "line-line", "line-polygon", "auto", "back"],
                default="auto"
            )
        else:
            print("\n分析类型:")
            print("1. point-line - 点-线最近邻关联分析")
            print("2. line-line - 线-线相交检测分析")
            print("3. line-polygon - 线-面包含判断分析")
            print("4. auto - 自动检测")
            print("0. 返回主菜单")

            choice_map = {
                "1": "point-line", "2": "line-line", "3": "line-polygon",
                "4": "auto", "0": "back"
            }
            choice = input("请选择 (0-4): ").strip().lower()
            choice = choice_map.get(choice, choice)

        return choice

    def _select_input_files(self, analysis_type: str) -> List[str] or str:
        """选择输入文件"""
        if self.console:
            self.console.print(f"\n[bold]选择 {analysis_type} 分析的输入文件[/bold]")
            self.console.print("支持格式: Shapefile (.shp), GeoJSON (.geojson), GeoPackage (.gpkg)")

        file_count = 2
        input_files = []

        for i in range(file_count):
            while True:
                prompt_text = f"请输入第 {i+1} 个文件路径"
                if self.console:
                    file_path = Prompt.ask(prompt_text)
                else:
                    file_path = input(f"{prompt_text}: ").strip()

                if file_path == "back":
                    return "back"

                if not file_path:
                    self._show_error("文件路径不能为空")
                    continue

                path = Path(file_path)
                if not path.exists():
                    self._show_error(f"文件不存在: {file_path}")
                    continue

                # 检查文件格式
                valid_extensions = {'.shp', '.geojson', '.gpkg'}
                if path.suffix.lower() not in valid_extensions:
                    self._show_error(f"不支持的文件格式: {path.suffix}")
                    continue

                input_files.append(str(path))
                break

        return input_files

    def _configure_parameters(self, analysis_type: str) -> Dict[str, Any] or str:
        """配置分析参数"""
        if self.console:
            self.console.print(f"\n[bold]配置 {analysis_type} 分析参数[/bold]")

        params = {}

        if analysis_type in ["point-line", "auto"]:
            # 距离阈值
            if self.console:
                distance = FloatPrompt.ask(
                    "距离阈值 (米)",
                    default=1000.0,
                    show_default=True
                )
            else:
                try:
                    distance = float(input("距离阈值 (米) [1000.0]: ") or "1000.0")
                except ValueError:
                    distance = 1000.0
            params['distance_threshold'] = distance

            # 最大邻居数
            if self.console:
                max_neighbors = IntPrompt.ask(
                    "最大邻居数量",
                    default=1,
                    show_default=True
                )
            else:
                try:
                    max_neighbors = int(input("最大邻居数量 [1]: ") or "1")
                except ValueError:
                    max_neighbors = 1
            params['max_neighbors'] = max_neighbors

        # 并行处理
        if self.console:
            parallel = Confirm.ask("启用并行处理", default=True)
        else:
            parallel = input("启用并行处理? (Y/n): ").lower() != 'n'
        params['parallel'] = parallel

        # 坐标系
        if self.console:
            crs = Prompt.ask(
                "目标坐标系 (留空保持原坐标系)",
                default=""
            )
        else:
            crs = input("目标坐标系 (留空保持原坐标系): ").strip()
        if crs:
            params['coordinate_system'] = crs

        return params

    def _configure_output(self) -> Dict[str, Any] or str:
        """配置输出选项"""
        if self.console:
            self.console.print("\n[bold]配置输出选项[/bold]")

        output_config = {}

        # 输出格式
        formats = ["geojson", "shp", "gpkg", "csv"]
        if self.console:
            format_choice = Prompt.ask(
                "输出格式",
                choices=formats,
                default="geojson"
            )
        else:
            print(f"输出格式选项: {', '.join(formats)}")
            format_choice = input("输出格式 [geojson]: ").strip().lower() or "geojson"
            if format_choice not in formats:
                format_choice = "geojson"
        output_config['format'] = format_choice

        # 输出路径
        if self.console:
            output_path = Prompt.ask(
                "输出文件路径 (留空自动生成)",
                default=""
            )
        else:
            output_path = input("输出文件路径 (留空自动生成): ").strip()
        if output_path:
            output_config['path'] = output_path

        return output_config

    def _confirm_execution(self, analysis_type: str, input_files: List[str],
                          params: Dict[str, Any], output_config: Dict[str, Any]) -> bool:
        """确认执行设置"""
        if self.console:
            confirm_table = Table(show_header=True, header_style="bold magenta")
            confirm_table.add_column("项目", style="cyan")
            confirm_table.add_column("值", style="white")

            confirm_table.add_row("分析类型", analysis_type)
            confirm_table.add_row("输入文件1", input_files[0])
            if len(input_files) > 1:
                confirm_table.add_row("输入文件2", input_files[1])

            for key, value in params.items():
                confirm_table.add_row(key.replace('_', ' ').title(), str(value))

            confirm_table.add_row("输出格式", output_config.get('format', 'geojson'))
            if 'path' in output_config:
                confirm_table.add_row("输出路径", output_config['path'])

            self.console.print("\n[bold]执行确认[/bold]")
            self.console.print(confirm_table)

            return Confirm.ask("确认执行上述分析?", default=True)
        else:
            print("\n执行确认:")
            print(f"分析类型: {analysis_type}")
            print(f"输入文件: {', '.join(input_files)}")
            print(f"参数: {params}")
            print(f"输出配置: {output_config}")

            confirm = input("确认执行? (Y/n): ").lower()
            return confirm != 'n'

    def _execute_analysis(self, analysis_type: str, input_files: List[str],
                         params: Dict[str, Any], output_config: Dict[str, Any]):
        """执行分析"""
        if self.console:
            self.console.print("\n[bold green]开始执行空间关联分析...[/bold green]")

        try:
            # 构建命令行参数
            cmd_args = ['process'] + input_files

            # 添加参数
            if 'distance_threshold' in params:
                cmd_args.extend(['--distance-threshold', str(params['distance_threshold'])])
            if 'max_neighbors' in params:
                cmd_args.extend(['--max-neighbors', str(params['max_neighbors'])])
            if 'parallel' in params:
                cmd_args.append('--parallel' if params['parallel'] else '--no-parallel')
            if 'coordinate_system' in params:
                cmd_args.extend(['--coordinate-system', params['coordinate_system']])

            # 输出配置
            if 'format' in output_config:
                cmd_args.extend(['--output-format', output_config['format']])
            if 'path' in output_config:
                cmd_args.extend(['--output', output_config['path']])

            # 执行命令
            from ..commands.process import process_cmd
            from click.testing import CliRunner

            runner = CliRunner()
            result = runner.invoke(process_cmd, cmd_args[1:])  # 跳过 'process' 参数

            if result.exit_code == 0:
                if self.console:
                    self.console.print("[bold green]✅ 分析执行成功![/bold green]")
                    if result.output:
                        self.console.print(Panel(result.output.strip(), title="输出结果"))
                else:
                    print("✅ 分析执行成功!")
                    if result.output:
                        print("输出结果:")
                        print(result.output)
            else:
                error_msg = result.output or "未知错误"
                self._show_error(f"分析执行失败: {error_msg}")

        except Exception as e:
            self._show_error(f"执行分析时发生错误: {str(e)}")

        if self.console:
            input("\n按回车键继续...")

    def _interactive_validate(self):
        """交互式验证模式"""
        if self.console:
            self.console.print(Panel(
                "[bold green]🔍 数据验证向导[/bold green]\n\n"
                "引导您完成数据质量验证和修复。",
                title="验证向导",
                border_style="green"
            ))

        # 选择验证文件
        input_files = self._select_validation_files()
        if input_files == "back":
            return

        # 配置验证选项
        validate_options = self._configure_validation_options()
        if validate_options == "back":
            return

        # 执行验证
        self._execute_validation(input_files, validate_options)

    def _select_validation_files(self) -> List[str] or str:
        """选择验证文件"""
        if self.console:
            self.console.print("\n[bold]选择要验证的数据文件[/bold]")

        files = []
        while True:
            if self.console:
                file_path = Prompt.ask("输入文件路径 (留空结束)")
                if not file_path:
                    break
            else:
                file_path = input("输入文件路径 (留空结束): ").strip()
                if not file_path:
                    break

            if file_path == "back":
                return "back"

            path = Path(file_path)
            if not path.exists():
                self._show_error(f"文件不存在: {file_path}")
                continue

            files.append(str(path))

        if not files:
            self._show_error("至少需要选择一个文件")
            return self._select_validation_files()

        return files

    def _configure_validation_options(self) -> Dict[str, Any] or str:
        """配置验证选项"""
        if self.console:
            self.console.print("\n[bold]配置验证选项[/bold]")

        options = {}

        if self.console:
            options['repair'] = Confirm.ask("自动修复发现的问题?", default=True)
            options['geometry_only'] = Confirm.ask("仅验证几何数据?", default=False)
            options['strict'] = Confirm.ask("启用严格模式?", default=False)
        else:
            options['repair'] = input("自动修复发现的问题? (Y/n): ").lower() != 'n'
            options['geometry_only'] = input("仅验证几何数据? (y/N): ").lower() == 'y'
            options['strict'] = input("启用严格模式? (y/N): ").lower() == 'y'

        return options

    def _execute_validation(self, input_files: List[str], options: Dict[str, Any]):
        """执行验证"""
        if self.console:
            self.console.print("\n[bold green]开始数据验证...[/bold green]")

        try:
            # 构建命令参数
            cmd_args = ['validate'] + input_files

            if options['repair']:
                cmd_args.append('--repair')
            if options['geometry_only']:
                cmd_args.append('--geometry-only')
            if options['strict']:
                cmd_args.append('--strict')

            # 执行验证命令
            from ..commands.validate import validate_cmd
            from click.testing import CliRunner

            runner = CliRunner()
            result = runner.invoke(validate_cmd, cmd_args[1:])  # 跳过 'validate' 参数

            if result.exit_code == 0:
                if self.console:
                    self.console.print("[bold green]✅ 验证完成![/bold green]")
                    if result.output:
                        self.console.print(Panel(result.output.strip(), title="验证结果"))
                else:
                    print("✅ 验证完成!")
                    if result.output:
                        print("验证结果:")
                        print(result.output)
            else:
                error_msg = result.output or "未知错误"
                self._show_error(f"验证失败: {error_msg}")

        except Exception as e:
            self._show_error(f"执行验证时发生错误: {str(e)}")

        if self.console:
            input("\n按回车键继续...")

    def _interactive_config(self):
        """交互式配置管理"""
        if self.console:
            self.console.print(Panel(
                "[bold blue]⚙️ 配置管理[/bold blue]\n\n"
                "管理系统配置文件和参数。",
                title="配置管理",
                border_style="blue"
            ))

        config_actions = [
            "show - 查看当前配置",
            "create - 创建新配置",
            "edit - 编辑配置",
            "reset - 重置配置",
            "back - 返回主菜单"
        ]

        if self.console:
            action_table = Table(show_header=False)
            action_table.add_column("选项", style="cyan")
            action_table.add_column("说明", style="white")

            for action in config_actions:
                option, desc = action.split(" - ", 1)
                action_table.add_row(option, desc)

            self.console.print(action_table)
            choice = Prompt.ask(
                "请选择操作",
                choices=["show", "create", "edit", "reset", "back"],
                default="show"
            )
        else:
            print("\n配置管理:")
            for i, action in enumerate(config_actions, 1):
                print(f"{i}. {action}")

            choice_map = {
                "1": "show", "2": "create", "3": "edit",
                "4": "reset", "5": "back"
            }
            choice = input("请选择 (1-5): ").strip().lower()
            choice = choice_map.get(choice, choice)

        if choice == "back":
            return

        # 执行配置操作
        if choice == "show":
            self._show_current_config()
        elif choice == "create":
            self._create_config()
        elif choice == "edit":
            self._edit_config()
        elif choice == "reset":
            self._reset_config()

    def _show_current_config(self):
        """显示当前配置"""
        if not self.config_manager:
            self._show_error("配置管理器不可用")
            return

        try:
            config = self.config_manager.get_config()

            if self.console:
                import yaml
                config_yaml = yaml.dump(config, default_flow_style=False, allow_unicode=True)
                self.console.print(Panel(
                    config_yaml.strip(),
                    title="当前配置",
                    border_style="blue"
                ))
            else:
                import yaml
                print("当前配置:")
                print(yaml.dump(config, default_flow_style=False, allow_unicode=True))

        except Exception as e:
            self._show_error(f"获取配置失败: {str(e)}")

        if self.console:
            input("\n按回车键继续...")

    def _show_system_info(self):
        """显示系统信息"""
        if self.console:
            self.console.print(Panel(
                "[bold blue]📊 系统信息[/bold blue]",
                border_style="blue"
            ))

        try:
            from ..commands.info import show_overview
            show_overview()
        except Exception as e:
            self._show_error(f"获取系统信息失败: {str(e)}")

        if self.console:
            input("\n按回车键继续...")

    def _show_help(self):
        """显示帮助信息"""
        help_text = """
GIS空间关联分析系统 - 帮助信息

## 主要功能

1. **空间关联分析** (process)
   - 点-线最近邻关联分析
   - 线-线相交检测分析
   - 线-面包含判断分析
   - 支持多种输入输出格式

2. **数据验证** (validate)
   - 几何数据有效性验证
   - 属性数据完整性检查
   - 坐标系验证
   - 自动数据修复

3. **配置管理** (config)
   - YAML/JSON配置文件支持
   - 配置模板和验证
   - 环境变量覆盖

4. **系统信息** (info)
   - 系统环境信息
   - 模块状态检查
   - 性能基准测试

## 支持的文件格式

**输入格式:**
- Shapefile (.shp)
- GeoJSON (.geojson)
- GeoPackage (.gpkg)
- CSV (.csv) - 需要坐标列

**输出格式:**
- Shapefile (.shp)
- GeoJSON (.geojson)
- GeoPackage (.gpkg)
- CSV (.csv)

## 快速开始

1. 选择分析类型
2. 选择输入文件
3. 配置分析参数
4. 设置输出选项
5. 确认并执行

## 获取帮助

- 在命令行中使用: gis-association --help
- 查看具体命令帮助: gis-association process --help
- 查看项目文档: https://github.com/your-repo
        """

        if self.console:
            self.console.print(Panel(
                Markdown(help_text),
                title="帮助信息",
                border_style="blue"
            ))
        else:
            print(help_text)

        input("\n按回车键继续...")

    def _show_error(self, message: str):
        """显示错误信息"""
        if self.console:
            self.console.print(f"[red]❌ {message}[/red]")
        else:
            print(f"❌ {message}")

    def _show_success(self, message: str):
        """显示成功信息"""
        if self.console:
            self.console.print(f"[green]✅ {message}[/green]")
        else:
            print(f"✅ {message}")

    def _show_warning(self, message: str):
        """显示警告信息"""
        if self.console:
            self.console.print(f"[yellow]⚠️  {message}[/yellow]")
        else:
            print(f"⚠️  {message}")