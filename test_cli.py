#!/usr/bin/env python3
"""
CLI功能测试脚本

测试GIS空间关联分析系统的CLI功能
"""

import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """测试模块导入"""
    print("🔍 测试模块导入...")

    try:
        from gis_spatial_association import __version__, _HAS_CLI
        print(f"✅ 主包导入成功 - 版本: {__version__}")
        print(f"✅ CLI模块可用: {_HAS_CLI}")
    except Exception as e:
        print(f"❌ 主包导入失败: {e}")
        return False

    if _HAS_CLI:
        try:
            from gis_spatial_association.cli import main, ProgressMonitor, InteractiveMode, ConfigManager
            print("✅ CLI核心模块导入成功")
        except Exception as e:
            print(f"❌ CLI模块导入失败: {e}")
            return False

    return True

def test_config_manager():
    """测试配置管理器"""
    print("\n⚙️ 测试配置管理器...")

    try:
        from gis_spatial_association.cli.config.manager import ConfigManager

        config_manager = ConfigManager()
        print("✅ ConfigManager创建成功")

        # 测试默认配置
        config_data = config_manager.get_config()
        print(f"✅ 获取配置成功，包含 {len(config_data)} 个配置节")

        return True
    except Exception as e:
        print(f"❌ 配置管理器测试失败: {e}")
        return False

def test_templates():
    """测试配置模板"""
    print("\n📋 测试配置模板...")

    try:
        from gis_spatial_association.cli.config.templates import get_template_names, CONFIG_DESCRIPTIONS

        template_names = get_template_names()
        print(f"✅ 可用模板: {', '.join(template_names)}")

        # 测试默认模板
        from gis_spatial_association.cli.config.templates import DEFAULT_CONFIG
        print(f"✅ 默认模板包含 {len(DEFAULT_CONFIG)} 个配置节")

        return True
    except Exception as e:
        print(f"❌ 配置模板测试失败: {e}")
        return False

def test_validation_schema():
    """测试验证模式"""
    print("\n✅ 测试验证模式...")

    try:
        from gis_spatial_association.cli.config.schema import get_validator, validate_config

        validator = get_validator()
        print("✅ 验证器创建成功")

        # 测试默认配置验证
        from gis_spatial_association.cli.config.templates import DEFAULT_CONFIG
        validate_config(DEFAULT_CONFIG)
        print("✅ 默认配置验证通过")

        return True
    except Exception as e:
        print(f"❌ 验证模式测试失败: {e}")
        return False

def test_progress_monitor():
    """测试进度监控"""
    print("\n📊 测试进度监控...")

    try:
        from gis_spatial_association.cli.ui.progress import ProgressMonitor

        # 检查Rich可用性
        try:
            from rich.console import Console
            rich_available = True
            print("✅ Rich库可用")
        except ImportError:
            rich_available = False
            print("⚠️ Rich库不可用，使用基础进度显示")

        monitor = ProgressMonitor(enable_rich=rich_available)
        print("✅ ProgressMonitor创建成功")

        # 测试任务添加
        task_id = monitor.add_task("test_task", "测试任务", total=100)
        print("✅ 任务添加成功")

        # 测试任务更新
        monitor.update_task(task_id, completed=50)
        print("✅ 任务更新成功")

        # 测试任务完成
        monitor.complete_task(task_id, True)
        print("✅ 任务完成成功")

        return True
    except Exception as e:
        print(f"❌ 进度监控测试失败: {e}")
        return False

def test_commands_structure():
    """测试命令结构"""
    print("\n🔧 测试命令结构...")

    commands = [
        "gis_spatial_association.cli.commands.process",
        "gis_spatial_association.cli.commands.validate",
        "gis_spatial_association.cli.commands.info",
        "gis_spatial_association.cli.commands.config"
    ]

    for command in commands:
        try:
            __import__(command)
            print(f"✅ {command.split('.')[-1]} 命令模块导入成功")
        except Exception as e:
            print(f"❌ {command.split('.')[-1]} 命令模块导入失败: {e}")
            return False

    return True

def test_cli_entry():
    """测试CLI入口"""
    print("\n🚀 测试CLI入口...")

    try:
        from gis_spatial_association.cli.main import main
        print("✅ CLI主入口函数导入成功")
        return True
    except Exception as e:
        print(f"❌ CLI入口测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🗺️  GIS空间关联分析系统 - CLI功能测试")
    print("=" * 50)

    tests = [
        ("模块导入", test_imports),
        ("配置管理器", test_config_manager),
        ("配置模板", test_templates),
        ("验证模式", test_validation_schema),
        ("进度监控", test_progress_monitor),
        ("命令结构", test_commands_structure),
        ("CLI入口", test_cli_entry),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name}测试异常: {e}")

    print("\n" + "=" * 50)
    print(f"测试完成: {passed}/{total} 通过")

    if passed == total:
        print("🎉 所有测试通过！CLI功能正常")
        return 0
    else:
        print("⚠️ 部分测试失败，请检查相关模块")
        return 1

if __name__ == "__main__":
    sys.exit(main())