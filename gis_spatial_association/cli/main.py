#!/usr/bin/env python3
"""
GIS空间关联分析系统 - 主CLI入口点

提供完整的命令行界面，支持：
- 空间关联分析处理
- 数据验证和修复
- 系统信息查看
- 配置管理
- 交互式操作模式
"""

import sys
import os
import logging
from pathlib import Path
from typing import Optional, List, Any

import click
from rich.console import Console
from rich.text import Text
from rich import print as rprint

# 导入项目模块
try:
    from .. import __version__
    try:
        from .. import _HAS_ASSOCIATION, _HAS_INTERSECTION, _HAS_CONTAINMENT, _HAS_TRANSFORMATION, _HAS_VALIDATION
    except ImportError:
        _HAS_ASSOCIATION = _HAS_INTERSECTION = _HAS_CONTAINMENT = _HAS_TRANSFORMATION = _HAS_VALIDATION = True

    from .ui.progress import ProgressMonitor
    from .ui.interactive import InteractiveMode
    from .config.manager import ConfigManager
except ImportError as e:
    print(f"警告: 部分CLI模块不可用: {e}")
    # 设置默认值
    from .. import __version__
    _HAS_ASSOCIATION = _HAS_INTERSECTION = _HAS_CONTAINMENT = _HAS_TRANSFORMATION = _HAS_VALIDATION = True

    # 尝试导入可用模块
    try:
        from .config.manager import ConfigManager
    except ImportError:
        ConfigManager = None

    try:
        from .ui.progress import ProgressMonitor
    except ImportError:
        ProgressMonitor = None

    try:
        from .ui.interactive import InteractiveMode
    except ImportError:
        InteractiveMode = None

# 全局控制台对象
try:
    console = Console()
except ImportError:
    console = None

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gis_association.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class CLIContext:
    """CLI上下文管理器"""

    def __init__(self):
        self.config_manager = ConfigManager() if ConfigManager else None
        self.progress_monitor = ProgressMonitor() if ProgressMonitor else None
        self.verbose = False
        self.quiet = False
        self.config_file = None

    def load_config(self, config_file: Optional[str] = None):
        """加载配置文件"""
        if not self.config_manager:
            return  # 配置管理器不可用

        if config_file:
            self.config_file = Path(config_file)
            if not self.config_file.exists():
                if console:
                    console.print(f"[red]错误: 配置文件不存在: {config_file}[/red]")
                else:
                    print(f"错误: 配置文件不存在: {config_file}")
                sys.exit(1)
        self.config_manager.load_config(self.config_file)


# 创建全局CLI上下文
cli_context = CLIContext()


@click.group(invoke_without_command=True)
@click.option('--version', '-v', is_flag=True, help='显示版本信息')
@click.option('--config', '-c', type=click.Path(exists=True), help='指定配置文件路径')
@click.option('--verbose', is_flag=True, help='详细输出模式')
@click.option('--quiet', '-q', is_flag=True, help='静默模式')
@click.option('--language', type=click.Choice(['zh', 'en']), default='zh', help='界面语言')
@click.pass_context
def cli(ctx, version, config, verbose, quiet, language):
    """
    🗺️  GIS空间关联分析系统

    一个功能强大的地理空间要素关联分析工具，支持：
    • 点-线最近邻关联分析
    • 线-线相交检测分析
    • 线-面包含判断分析
    • 坐标系转换处理
    • 全面的数据质量验证和修复

    使用 'gis-association COMMAND --help' 查看具体命令的帮助信息。
    """

    # 设置全局上下文
    cli_context.verbose = verbose
    cli_context.quiet = quiet
    cli_context.language = language

    # 加载配置
    cli_context.load_config(config)

    if version:
        show_version()
        sys.exit(0)

    # 如果没有指定命令，显示欢迎信息
    if ctx.invoked_subcommand is None:
        show_welcome()
        sys.exit(0)


def show_version():
    """显示版本信息"""
    if console:
        try:
            from rich.text import Text
            version_text = Text()
            version_text.append("GIS空间关联分析系统 ", style="bold blue")
            version_text.append(f"v{__version__}\n\n", style="bold")

            version_text.append("核心模块状态:\n", style="bold")
            version_text.append(f"• 关联分析模块: {'✅ 可用' if _HAS_ASSOCIATION else '❌ 不可用'}\n")
            version_text.append(f"• 相交检测模块: {'✅ 可用' if _HAS_INTERSECTION else '❌ 不可用'}\n")
            version_text.append(f"• 包含分析模块: {'✅ 可用' if _HAS_CONTAINMENT else '❌ 不可用'}\n")
            version_text.append(f"• 坐标转换模块: {'✅ 可用' if _HAS_TRANSFORMATION else '❌ 不可用'}\n")
            version_text.append(f"• 数据验证模块: {'✅ 可用' if _HAS_VALIDATION else '❌ 不可用'}\n")

            console.print(version_text)
        except ImportError:
            print(f"GIS空间关联分析系统 v{__version__}")
            print("核心模块状态:")
            print(f"• 关联分析模块: {'✅ 可用' if _HAS_ASSOCIATION else '❌ 不可用'}")
            print(f"• 相交检测模块: {'✅ 可用' if _HAS_INTERSECTION else '❌ 不可用'}")
            print(f"• 包含分析模块: {'✅ 可用' if _HAS_CONTAINMENT else '❌ 不可用'}")
            print(f"• 坐标转换模块: {'✅ 可用' if _HAS_TRANSFORMATION else '❌ 不可用'}")
            print(f"• 数据验证模块: {'✅ 可用' if _HAS_VALIDATION else '❌ 不可用'}")
    else:
        print(f"GIS空间关联分析系统 v{__version__}")
        print("核心模块状态:")
        print(f"• 关联分析模块: {'✅ 可用' if _HAS_ASSOCIATION else '❌ 不可用'}")
        print(f"• 相交检测模块: {'✅ 可用' if _HAS_INTERSECTION else '❌ 不可用'}")
        print(f"• 包含分析模块: {'✅ 可用' if _HAS_CONTAINMENT else '❌ 不可用'}")
        print(f"• 坐标转换模块: {'✅ 可用' if _HAS_TRANSFORMATION else '❌ 不可用'}")
        print(f"• 数据验证模块: {'✅ 可用' if _HAS_VALIDATION else '❌ 不可用'}")


def show_welcome():
    """显示欢迎信息"""
    welcome_text = Text()
    welcome_text.append("🗺️  欢迎使用GIS空间关联分析系统!\n\n", style="bold blue")

    welcome_text.append("主要功能:\n", style="bold")
    welcome_text.append("• process    - 执行空间关联分析\n")
    welcome_text.append("• validate   - 数据验证和修复\n")
    welcome_text.append("• info       - 查看系统信息\n")
    welcome_text.append("• config     - 配置管理\n\n")

    welcome_text.append("使用示例:\n", style="bold")
    welcome_text.append("gis-association process points.shp lines.shp\n")
    welcome_text.append("gis-association validate data.geojson --repair\n")
    welcome_text.append("gis-association interactive\n")
    welcome_text.append("gis-association --help\n\n")

    welcome_text.append("使用 'gis-association COMMAND --help' 获取详细帮助。", style="dim")

    console.print(welcome_text)


@cli.command()
@click.option('--mode', type=click.Choice(['batch', 'interactive']), default='batch',
              help='操作模式: batch(批处理) 或 interactive(交互式)')
@click.pass_context
def interactive(ctx, mode):
    """启动交互式操作模式"""
    if mode == 'interactive':
        interactive_mode = InteractiveMode(cli_context)
        interactive_mode.run()
    else:
        console.print("[yellow]使用 'gis-association process' 命令进行批处理操作[/yellow]")


# 导入子命令
try:
    from .commands.process import process_cmd
    from .commands.validate import validate_cmd
    from .commands.info import info_cmd
    from .commands.config import config_cmd

    # 注册子命令
    cli.add_command(process_cmd, name='process')
    cli.add_command(validate_cmd, name='validate')
    cli.add_command(info_cmd, name='info')
    cli.add_command(config_cmd, name='config')

except ImportError as e:
    logger.warning(f"无法导入子命令模块: {e}")
    console.print("[yellow]警告: 某些子命令可能不可用[/yellow]")


def main():
    """主入口函数"""
    try:
        # 设置环境变量支持中文
        if sys.platform.startswith('win'):
            import locale
            locale.setlocale(locale.LC_ALL, 'Chinese (Simplified)_China.utf8')
        else:
            os.environ['LANG'] = 'zh_CN.UTF-8'
            os.environ['LC_ALL'] = 'zh_CN.UTF-8'

        cli()

    except KeyboardInterrupt:
        console.print("\n[yellow]操作被用户中断[/yellow]")
        sys.exit(130)
    except Exception as e:
        logger.exception("程序运行时发生错误")
        console.print(f"[red]错误: {str(e)}[/red]")
        if cli_context.verbose:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    main()