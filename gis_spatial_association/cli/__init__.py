"""
GIS空间关联分析系统 - 命令行界面模块

提供用户友好的命令行界面，包括：
- 完整的CLI命令结构
- 交互式模式和批处理模式
- 实时进度显示和状态报告
- 配置管理和帮助文档
"""

__version__ = "1.0.0"

try:
    from .main import main
    from .ui.progress import ProgressMonitor
    from .ui.interactive import InteractiveMode
    from .config.manager import ConfigManager
    __all__ = ['main', 'ProgressMonitor', 'InteractiveMode', 'ConfigManager']
except ImportError as e:
    import logging
    logging.warning(f"CLI模块导入失败: {e}")
    main = None
    ProgressMonitor = None
    InteractiveMode = None
    ConfigManager = None
    __all__ = []