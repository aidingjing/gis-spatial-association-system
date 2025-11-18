"""
验证模块测试包

提供GIS数据验证模块的全面测试套件，包括：
- 几何验证器测试
- 属性验证器测试
- 坐标系统验证器测试
- 数据质量评分器测试
- 数据修复工具测试
- 集成测试

Author: CCPM Auto Development System
"""

from .test_validation import (
    TestGeometryValidator,
    TestAttributeValidator,
    TestCoordinateSystemValidator,
    TestDataQualityScorer,
    TestDataRepairer,
    TestIntegration,
    run_validation_tests
)

__all__ = [
    'TestGeometryValidator',
    'TestAttributeValidator',
    'TestCoordinateSystemValidator',
    'TestDataQualityScorer',
    'TestDataRepairer',
    'TestIntegration',
    'run_validation_tests'
]