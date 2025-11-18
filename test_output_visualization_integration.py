"""
输出和可视化模块集成测试

测试整个输出和可视化系统的集成功能。

作者: GIS空间关联系统开发团队
"""

import os
import sys
import tempfile
import shutil
import logging
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, '/code/ca')

try:
    import pandas as pd
    import geopandas as gpd
    import numpy as np
    from shapely.geometry import Point, Polygon
except ImportError as e:
    print(f"依赖库缺失: {e}")
    sys.exit(1)

# 导入我们的模块
try:
    from gis_spatial_association.io import (
        ResultExporter, ReportGenerator, DataVisualizer,
        ResultValidator, QualityScorer, ResultAnalyzer
    )
    from gis_spatial_association.io.exporters import (
        ShapefileExporter, GeoJSONExporter, CSVExporter, ExcelExporter
    )
    from gis_spatial_association.io.visualization import (
        MapVisualizer, ChartVisualizer, NetworkVisualizer
    )
    from gis_spatial_association.io.reports import QualityReportGenerator
except ImportError as e:
    print(f"模块导入失败: {e}")
    sys.exit(1)

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_test_data():
    """创建测试数据"""
    logger.info("创建测试数据...")

    # 创建测试点数据
    np.random.seed(42)
    n_points = 100

    # 生成随机点
    lons = np.random.uniform(116.3, 116.5, n_points)
    lats = np.random.uniform(39.8, 40.0, n_points)

    points = [Point(lon, lat) for lon, lat in zip(lons, lats)]

    # 创建属性数据
    attributes = {
        'id': range(1, n_points + 1),
        'name': [f'Point_{i}' for i in range(1, n_points + 1)],
        'category': np.random.choice(['A', 'B', 'C'], n_points),
        'value': np.random.uniform(0, 100, n_points),
        'population': np.random.randint(100, 10000, n_points),
        'density': np.random.uniform(0.1, 10.0, n_points)
    }

    # 创建GeoDataFrame
    gdf = gpd.GeoDataFrame(attributes, geometry=points, crs='EPSG:4326')

    # 创建测试面数据
    polygons = []
    for i in range(20):
        x = np.random.uniform(116.3, 116.5)
        y = np.random.uniform(39.8, 40.0)
        width = np.random.uniform(0.001, 0.005)
        height = np.random.uniform(0.001, 0.005)

        polygon = Polygon([
            (x, y),
            (x + width, y),
            (x + width, y + height),
            (x, y + height)
        ])
        polygons.append(polygon)

    polygon_attributes = {
        'id': range(1, 21),
        'area_name': [f'Area_{i}' for i in range(1, 21)],
        'land_use': np.random.choice(['residential', 'commercial', 'industrial'], 20),
        'area_size': np.random.uniform(1000, 50000, 20),
        'building_count': np.random.randint(5, 200, 20)
    }

    polygon_gdf = gpd.GeoDataFrame(polygon_attributes, geometry=polygons, crs='EPSG:4326')

    # 创建关联关系数据
    associations = []
    for i in range(50):
        associations.append({
            'source': f'Point_{np.random.randint(1, n_points + 1)}',
            'target': f'Area_{np.random.randint(1, 21)}',
            'type': 'contains',
            'weight': np.random.uniform(0.1, 1.0),
            'quality_score': np.random.uniform(0.6, 1.0)
        })

    return {
        'point_data': gdf,
        'polygon_data': polygon_gdf,
        'associations': associations,
        'performance_metrics': {
            'processing_time': 125.5,
            'memory_usage': 1024 * 1024 * 50,  # 50MB
            'total_features': len(gdf) + len(polygon_gdf)
        }
    }


def test_export_functionality(test_data, temp_dir):
    """测试导出功能"""
    logger.info("测试导出功能...")

    try:
        # 测试结果导出器
        exporter = ResultExporter()

        export_config = {
            'formats': ['shapefile', 'geojson', 'csv', 'excel'],
            'output_directory': str(temp_dir / 'exports'),
            'generate_report': True
        }

        export_results = exporter.export_results(test_data, export_config)

        if export_results['success']:
            logger.info(f"✅ 导出成功，生成 {len(export_results['exported_files'])} 个文件")
            for file_path in export_results['exported_files']:
                logger.info(f"  - {file_path}")
        else:
            logger.error("❌ 导出失败")
            logger.error(f"错误: {export_results['errors']}")

        return export_results

    except Exception as e:
        logger.error(f"❌ 导出测试失败: {str(e)}")
        return None


def test_report_generation(test_data, temp_dir):
    """测试报告生成功能"""
    logger.info("测试报告生成功能...")

    try:
        # 测试报告生成器
        report_generator = ReportGenerator()

        report_dir = temp_dir / 'reports'
        report_results = report_generator.generate_report(
            test_data,
            str(report_dir),
            ['html', 'markdown']
        )

        if report_results['success']:
            logger.info(f"✅ 报告生成成功，耗时: {report_results['generation_time']:.2f}秒")
            for file_path in report_results['generated_files']:
                logger.info(f"  - {file_path}")
        else:
            logger.error("❌ 报告生成失败")
            logger.error(f"错误: {report_results['errors']}")

        return report_results

    except Exception as e:
        logger.error(f"❌ 报告生成测试失败: {str(e)}")
        return None


def test_visualization_functionality(test_data, temp_dir):
    """测试可视化功能"""
    logger.info("测试可视化功能...")

    try:
        # 测试数据可视化器
        visualizer = DataVisualizer()

        viz_dir = temp_dir / 'visualizations'
        dashboard_file = visualizer.create_visualization_dashboard(
            test_data,
            str(viz_dir),
            "GIS空间关联分析测试仪表板"
        )

        if dashboard_file:
            logger.info(f"✅ 可视化仪表板创建成功: {dashboard_file}")
        else:
            logger.error("❌ 可视化仪表板创建失败")

        # 测试单独可视化
        individual_viz = visualizer.create_individual_visualizations(
            test_data,
            str(viz_dir / 'individual'),
            ['maps', 'charts']
        )

        total_files = sum(len(files) for files in individual_viz.values())
        logger.info(f"✅ 单独可视化创建成功，共 {total_files} 个文件")

        return dashboard_file

    except Exception as e:
        logger.error(f"❌ 可视化测试失败: {str(e)}")
        return None


def test_quality_assessment(test_data, temp_dir):
    """测试质量评估功能"""
    logger.info("测试质量评估功能...")

    try:
        # 测试结果验证器
        validator = ResultValidator()
        validation_results = validator.validate_results(test_data)

        logger.info(f"✅ 验证完成，验证分数: {validation_results['validation_score']:.1f}")
        logger.info(f"总体验证: {'通过' if validation_results['overall_valid'] else '未通过'}")
        logger.info(f"错误数量: {len(validation_results['errors'])}")
        logger.info(f"警告数量: {len(validation_results['warnings'])}")

        # 测试质量评分器
        scorer = QualityScorer()
        quality_scores = scorer.calculate_quality_scores(validation_results)

        logger.info(f"✅ 质量评分完成")
        for metric, score in quality_scores.items():
            logger.info(f"  {metric}: {score:.1f}")

        # 测试结果分析器
        analyzer = ResultAnalyzer()
        analysis_summary = analyzer.analyze_results(
            test_data, validation_results, quality_scores
        )

        logger.info(f"✅ 结果分析完成")

        return {
            'validation': validation_results,
            'quality_scores': quality_scores,
            'analysis': analysis_summary
        }

    except Exception as e:
        logger.error(f"❌ 质量评估测试失败: {str(e)}")
        return None


def test_individual_exporters(test_data, temp_dir):
    """测试单独导出器"""
    logger.info("测试单独导出器...")

    exporters_test = {
        'Shapefile': ShapefileExporter(),
        'GeoJSON': GeoJSONExporter(),
        'CSV': CSVExporter(),
        'Excel': ExcelExporter()
    }

    results = {}

    for exporter_name, exporter in exporters_test.items():
        try:
            logger.info(f"  测试 {exporter_name} 导出器...")

            if exporter_name == 'CSV':
                # CSV导出器可以处理DataFrame
                data_to_export = test_data['point_data']
            else:
                # 其他导出器需要GeoDataFrame
                data_to_export = test_data['point_data']

            output_file = exporter.export(
                data_to_export,
                f'test_{exporter_name.lower()}',
                str(temp_dir / 'individual_exports')
            )

            if output_file:
                logger.info(f"    ✅ {exporter_name} 导出成功: {output_file}")
                results[exporter_name] = {'success': True, 'file': output_file}
            else:
                logger.error(f"    ❌ {exporter_name} 导出失败")
                results[exporter_name] = {'success': False, 'file': None}

        except Exception as e:
            logger.error(f"    ❌ {exporter_name} 测试失败: {str(e)}")
            results[exporter_name] = {'success': False, 'error': str(e)}

    return results


def run_integration_tests():
    """运行集成测试"""
    logger.info("🚀 开始输出和可视化模块集成测试")

    # 创建临时目录
    temp_dir = Path(tempfile.mkdtemp(prefix='gis_test_'))
    logger.info(f"测试目录: {temp_dir}")

    try:
        # 创建测试数据
        test_data = create_test_data()
        logger.info(f"✅ 测试数据创建完成")
        logger.info(f"  点数据: {len(test_data['point_data'])} 条记录")
        logger.info(f"  面数据: {len(test_data['polygon_data'])} 条记录")
        logger.info(f"  关联关系: {len(test_data['associations'])} 条")

        # 运行各项测试
        test_results = {}

        # 1. 测试导出功能
        test_results['export'] = test_export_functionality(test_data, temp_dir)

        # 2. 测试报告生成
        test_results['report'] = test_report_generation(test_data, temp_dir)

        # 3. 测试可视化功能
        test_results['visualization'] = test_visualization_functionality(test_data, temp_dir)

        # 4. 测试质量评估
        test_results['quality'] = test_quality_assessment(test_data, temp_dir)

        # 5. 测试单独导出器
        test_results['individual_exporters'] = test_individual_exporters(test_data, temp_dir)

        # 生成测试摘要
        generate_test_summary(test_results, temp_dir)

        logger.info("🎉 所有集成测试完成!")
        return True

    except Exception as e:
        logger.error(f"❌ 集成测试失败: {str(e)}")
        return False

    finally:
        # 清理临时目录（可选）
        # shutil.rmtree(temp_dir)
        logger.info(f"测试文件保留在: {temp_dir}")


def generate_test_summary(test_results, temp_dir):
    """生成测试摘要"""
    logger.info("📋 生成测试摘要...")

    summary = {
        'test_time': datetime.now().isoformat(),
        'test_directory': str(temp_dir),
        'results': {},
        'overall_status': 'success'
    }

    for test_name, result in test_results.items():
        if result is None:
            summary['results'][test_name] = {'status': 'failed', 'error': 'No result'}
            summary['overall_status'] = 'partial_failure'
        elif isinstance(result, dict) and not result.get('success', True):
            summary['results'][test_name] = {'status': 'failed', 'details': result}
            summary['overall_status'] = 'partial_failure'
        else:
            summary['results'][test_name] = {'status': 'success', 'details': result}

    # 保存摘要到文件
    summary_file = temp_dir / 'test_summary.json'
    try:
        import json
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"✅ 测试摘要保存到: {summary_file}")
    except Exception as e:
        logger.error(f"保存测试摘要失败: {str(e)}")

    # 打印摘要
    print("\n" + "="*60)
    print("📊 测试摘要报告")
    print("="*60)
    print(f"测试时间: {summary['test_time']}")
    print(f"测试目录: {summary['test_directory']}")
    print(f"总体状态: {summary['overall_status']}")
    print("\n详细结果:")
    for test_name, result in summary['results'].items():
        status_emoji = "✅" if result['status'] == 'success' else "❌"
        print(f"  {status_emoji} {test_name}: {result['status']}")
    print("="*60)


if __name__ == '__main__':
    success = run_integration_tests()
    sys.exit(0 if success else 1)