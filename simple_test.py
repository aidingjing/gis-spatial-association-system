#!/usr/bin/env python3
"""
简化的CLI测试脚本
"""

import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

def test_basic_imports():
    """测试基本导入"""
    print("🔍 测试基本导入...")

    try:
        # 测试主包
        from gis_spatial_association import __version__
        print(f"✅ 主包版本: {__version__}")
    except Exception as e:
        print(f"❌ 主包导入失败: {e}")
        return False

    try:
        # 测试CLI模块
        from gis_spatial_association.cli.config import manager
        print("✅ 配置管理器模块导入成功")
    except Exception as e:
        print(f"❌ 配置管理器导入失败: {e}")
        return False

    try:
        # 测试配置模板
        from gis_spatial_association.cli.config import templates
        print("✅ 配置模板模块导入成功")
    except Exception as e:
        print(f"❌ 配置模板导入失败: {e}")
        return False

    return True

def test_config_functionality():
    """测试配置功能"""
    print("\n⚙️ 测试配置功能...")

    try:
        from gis_spatial_association.cli.config.manager import ConfigManager

        config_manager = ConfigManager()
        print("✅ 配置管理器创建成功")

        # 测试默认配置加载
        config_manager.load_config()
        config_data = config_manager.get_config()
        print(f"✅ 配置加载成功，包含 {len(config_data)} 个节")

        return True
    except Exception as e:
        print(f"❌ 配置功能测试失败: {e}")
        return False

def test_templates():
    """测试模板功能"""
    print("\n📋 测试模板功能...")

    try:
        from gis_spatial_association.cli.config.templates import (
            DEFAULT_CONFIG, CONFIG_TEMPLATE, get_template_names
        )

        template_names = get_template_names()
        print(f"✅ 可用模板: {', '.join(template_names)}")

        print(f"✅ 默认配置包含 {len(DEFAULT_CONFIG)} 个节")
        print(f"✅ 模板集合包含 {len(CONFIG_TEMPLATE)} 个模板")

        return True
    except Exception as e:
        print(f"❌ 模板功能测试失败: {e}")
        return False

def test_file_structure():
    """测试文件结构"""
    print("\n📁 测试文件结构...")

    expected_files = [
        "gis_spatial_association/cli/__init__.py",
        "gis_spatial_association/cli/main.py",
        "gis_spatial_association/cli/commands/__init__.py",
        "gis_spatial_association/cli/commands/process.py",
        "gis_spatial_association/cli/commands/validate.py",
        "gis_spatial_association/cli/commands/info.py",
        "gis_spatial_association/cli/commands/config.py",
        "gis_spatial_association/cli/ui/__init__.py",
        "gis_spatial_association/cli/ui/progress.py",
        "gis_spatial_association/cli/ui/interactive.py",
        "gis_spatial_association/cli/config/__init__.py",
        "gis_spatial_association/cli/config/manager.py",
        "gis_spatial_association/cli/config/templates.py",
        "gis_spatial_association/cli/config/schema.py",
    ]

    missing_files = []
    for file_path in expected_files:
        full_path = Path(file_path)
        if full_path.exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - 文件不存在")
            missing_files.append(file_path)

    return len(missing_files) == 0

def main():
    """主测试函数"""
    print("🗺️  GIS空间关联分析系统 - 简化测试")
    print("=" * 50)

    tests = [
        ("基本导入", test_basic_imports),
        ("配置功能", test_config_functionality),
        ("模板功能", test_templates),
        ("文件结构", test_file_structure),
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
        print("🎉 所有测试通过！CLI基础结构正常")
        return 0
    else:
        print("⚠️ 部分测试失败，请检查相关模块")
        return 1

if __name__ == "__main__":
    sys.exit(main())