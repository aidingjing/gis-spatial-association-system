#!/usr/bin/env python3
"""
GIS空间关联分析系统测试运行器

提供完整的测试套件运行功能，包括单元测试、集成测试和性能测试。

Author: CCPM Auto Development System
"""

import unittest
import sys
import os
import time
import argparse
from io import StringIO

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入测试模块
from test_association import TestNearestNeighborAssociator, TestAssociationPerformance
from test_intersection import TestLineIntersectionDetector, TestIntersectionComplexGeometry, TestIntersectionPerformance
from test_containment import TestPolygonContainmentAnalyzer, TestContainmentComplexGeometry, TestContainmentPerformance
from test_transformation import TestCoordinateTransformer, TestCoordinateTransformationEdgeCases
from test_integration import TestSystemIntegration, TestEndToEndScenarios


class TestRunner:
    """测试运行器类"""

    def __init__(self, verbosity=2):
        self.verbosity = verbosity
        self.test_results = {}
        self.total_tests = 0
        self.total_failures = 0
        self.total_errors = 0
        self.total_time = 0

    def run_test_suite(self, test_suite, suite_name):
        """运行测试套件"""
        print(f"\n{'='*60}")
        print(f"运行测试套件: {suite_name}")
        print(f"{'='*60}")

        # 创建测试运行器
        stream = StringIO()
        runner = unittest.TextTestRunner(
            stream=stream,
            verbosity=self.verbosity,
            descriptions=True,
            failfast=False
        )

        # 运行测试
        start_time = time.time()
        result = runner.run(test_suite)
        end_time = time.time()

        # 获取测试输出
        output = stream.getvalue()
        print(output)

        # 记录结果
        suite_time = end_time - start_time
        self.test_results[suite_name] = {
            'tests_run': result.testsRun,
            'failures': len(result.failures),
            'errors': len(result.errors),
            'time': suite_time,
            'success_rate': (result.testsRun - len(result.failures) - len(result.errors)) / max(result.testsRun, 1) * 100
        }

        # 更新总计
        self.total_tests += result.testsRun
        self.total_failures += len(result.failures)
        self.total_errors += len(result.errors)
        self.total_time += suite_time

        return result

    def run_unit_tests(self):
        """运行单元测试"""
        print(f"\n{'#'*60}")
        print("# 单元测试")
        print(f"{'#'*60}")

        # 点-线关联算法测试
        suite1 = unittest.TestLoader().loadTestsFromTestCase(TestNearestNeighborAssociator)
        self.run_test_suite(suite1, "点-线最近邻关联算法")

        # 线-线相交检测算法测试
        suite2 = unittest.TestLoader().loadTestsFromTestCase(TestLineIntersectionDetector)
        self.run_test_suite(suite2, "线-线相交检测算法")

        # 线-面包含判断算法测试
        suite3 = unittest.TestLoader().loadTestsFromTestCase(TestPolygonContainmentAnalyzer)
        self.run_test_suite(suite3, "线-面包含判断算法")

        # 坐标转换处理测试
        suite4 = unittest.TestLoader().loadTestsFromTestCase(TestCoordinateTransformer)
        self.run_test_suite(suite4, "坐标系统转换处理")

    def run_complex_geometry_tests(self):
        """运行复杂几何测试"""
        print(f"\n{'#'*60}")
        print("# 复杂几何测试")
        print(f"{'#'*60}")

        # 复杂几何测试
        suite1 = unittest.TestLoader().loadTestsFromTestCase(TestIntersectionComplexGeometry)
        self.run_test_suite(suite1, "复杂线段相交")

        suite2 = unittest.TestLoader().loadTestsFromTestCase(TestContainmentComplexGeometry)
        self.run_test_suite(suite2, "复杂面包含")

        suite3 = unittest.TestLoader().loadTestsFromTestCase(TestCoordinateTransformationEdgeCases)
        self.run_test_suite(suite3, "坐标转换边界条件")

    def run_performance_tests(self):
        """运行性能测试"""
        print(f"\n{'#'*60}")
        print("# 性能测试")
        print(f"{'#'*60}")

        # 性能测试
        suite1 = unittest.TestLoader().loadTestsFromTestCase(TestAssociationPerformance)
        self.run_test_suite(suite1, "点-线关联性能测试")

        suite2 = unittest.TestLoader().loadTestsFromTestCase(TestIntersectionPerformance)
        self.run_test_suite(suite2, "线-线相交性能测试")

        suite3 = unittest.TestLoader().loadTestsFromTestCase(TestContainmentPerformance)
        self.run_test_suite(suite3, "线-面包含性能测试")

    def run_integration_tests(self):
        """运行集成测试"""
        print(f"\n{'#'*60}")
        print("# 集成测试")
        print(f"{'#'*60}")

        # 集成测试
        suite1 = unittest.TestLoader().loadTestsFromTestCase(TestSystemIntegration)
        self.run_test_suite(suite1, "系统集成测试")

        suite2 = unittest.TestLoader().loadTestsFromTestCase(TestEndToEndScenarios)
        self.run_test_suite(suite2, "端到端场景测试")

    def run_all_tests(self):
        """运行所有测试"""
        start_time = time.time()

        self.run_unit_tests()
        self.run_complex_geometry_tests()
        self.performance_tests_enabled = True
        self.run_performance_tests()
        self.run_integration_tests()

        total_time = time.time() - start_time
        self.print_summary(total_time)

    def run_quick_tests(self):
        """运行快速测试（跳过性能测试）"""
        start_time = time.time()

        self.run_unit_tests()
        self.run_integration_tests()

        total_time = time.time() - start_time
        self.print_summary(total_time)

    def print_summary(self, total_time):
        """打印测试总结"""
        print(f"\n{'='*80}")
        print("测试总结报告")
        print(f"{'='*80}")

        # 详细结果
        for suite_name, result in self.test_results.items():
            print(f"\n{suite_name}:")
            print(f"  测试数量: {result['tests_run']}")
            print(f"  失败数量: {result['failures']}")
            print(f"  错误数量: {result['errors']}")
            print(f"  成功率: {result['success_rate']:.1f}%")
            print(f"  执行时间: {result['time']:.2f}秒")

        # 总计
        print(f"\n{'-'*80}")
        print("总计:")
        print(f"  总测试数: {self.total_tests}")
        print(f"  总失败数: {self.total_failures}")
        print(f"  总错误数: {self.total_errors}")
        print(f"  总成功率: {((self.total_tests - self.total_failures - self.total_errors) / max(self.total_tests, 1) * 100):.1f}%")
        print(f"  总执行时间: {total_time:.2f}秒")
        print(f"  算法模块执行时间: {self.total_time:.2f}秒")

        # 状态
        if self.total_failures == 0 and self.total_errors == 0:
            print(f"\n✅ 所有测试通过！系统运行正常。")
            return 0
        else:
            print(f"\n❌ 测试发现问题！需要修复失败的测试。")
            return 1

    def export_results(self, filename="test_results.txt"):
        """导出测试结果到文件"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("GIS空间关联分析系统测试结果报告\n")
            f.write("="*50 + "\n\n")

            for suite_name, result in self.test_results.items():
                f.write(f"{suite_name}:\n")
                f.write(f"  测试数量: {result['tests_run']}\n")
                f.write(f"  失败数量: {result['failures']}\n")
                f.write(f"  错误数量: {result['errors']}\n")
                f.write(f"  成功率: {result['success_rate']:.1f}%\n")
                f.write(f"  执行时间: {result['time']:.2f}秒\n\n")

            f.write("-"*50 + "\n")
            f.write("总计:\n")
            f.write(f"  总测试数: {self.total_tests}\n")
            f.write(f"  总失败数: {self.total_failures}\n")
            f.write(f"  总错误数: {self.total_errors}\n")
            f.write(f"  总成功率: {((self.total_tests - self.total_failures - self.total_errors) / max(self.total_tests, 1) * 100):.1f}%\n")

        print(f"\n测试结果已导出到: {filename}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="GIS空间关联分析系统测试运行器")
    parser.add_argument("--verbosity", "-v", type=int, default=2, choices=[0, 1, 2],
                        help="测试输出详细程度 (0=静默, 1=正常, 2=详细)")
    parser.add_argument("--quick", "-q", action="store_true",
                        help="运行快速测试（跳过性能测试）")
    parser.add_argument("--unit", "-u", action="store_true",
                        help="只运行单元测试")
    parser.add_argument("--integration", "-i", action="store_true",
                        help="只运行集成测试")
    parser.add_argument("--performance", "-p", action="store_true",
                        help="只运行性能测试")
    parser.add_argument("--export", "-e", type=str,
                        help="导出测试结果到指定文件")

    args = parser.parse_args()

    # 创建测试运行器
    runner = TestRunner(verbosity=args.verbosity)

    try:
        if args.unit:
            runner.run_unit_tests()
        elif args.integration:
            runner.run_integration_tests()
        elif args.performance:
            runner.run_performance_tests()
        elif args.quick:
            runner.run_quick_tests()
        else:
            runner.run_all_tests()

        # 导出结果
        if args.export:
            runner.export_results(args.export)

        # 返回退出码
        return 0 if runner.total_failures == 0 and runner.total_errors == 0 else 1

    except KeyboardInterrupt:
        print("\n测试被用户中断")
        return 1
    except Exception as e:
        print(f"\n测试运行出错: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())