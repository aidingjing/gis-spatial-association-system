# 📚 使用示例

本文档提供了GIS空间关联分析系统的详细使用示例，涵盖各种实际应用场景和高级用法。

## 🎯 目录

- [基础使用示例](#基础使用示例)
- [点-线关联分析示例](#点-线关联分析示例)
- [线-线相交检测示例](#线-线相交检测示例)
- [线-面包含分析示例](#线-面包含分析示例)
- [坐标转换示例](#坐标转换示例)
- [数据验证示例](#数据验证示例)
- [批处理示例](#批处理示例)
- [性能优化示例](#性能优化示例)
- [可视化示例](#可视化示例)
- [实际应用案例](#实际应用案例)

## 🏗️ 基础使用示例

### 简单的点-线关联

```bash
# 最基础的关联分析
gis-association process \
  --input-points sample_points.shp \
  --input-lines sample_lines.shp \
  --output result.gpkg
```

**Python API示例：**
```python
from gis_spatial_association import NearestNeighborAssociator
import geopandas as gpd

# 加载数据
points = gpd.read_file('sample_points.shp')
lines = gpd.read_file('sample_lines.shp')

# 创建关联分析器
associator = NearestNeighborAssociator()

# 执行分析
results = associator.associate(points, lines)

# 保存结果
results.to_file('result.gpkg', driver='GPKG')
```

## 📍 点-线关联分析示例

### 示例1：监测站点与河流关联

```bash
# 环境监测站点到河流的关联分析
gis-association process \
  --input-points monitoring_stations.shp \
  --input-lines rivers.shp \
  --output station_river_associations.gpkg \
  --max-distance 2000 \
  --parallel 4 \
  --output-encoding utf-8
```

**Python代码：**
```python
from gis_spatial_association import NearestNeighborAssociator
import geopandas as gpd

# 加载数据
stations = gpd.read_file('monitoring_stations.shp')
rivers = gpd.read_file('rivers.shp')

# 高级关联分析配置
associator = NearestNeighborAssociator(
    max_distance=2000,  # 最大关联距离2000米
    return_all_fields=True,  # 返回所有属性字段
    calculate_parallel_distance=True,  # 计算平行距离
    calculate_perpendicular_distance=True,  # 计算垂直距离
    calculate_azimuth=True  # 计算方位角
)

# 执行分析
results = associator.associate(stations, rivers)

# 添加分析统计信息
results['distance_category'] = pd.cut(
    results['distance'],
    bins=[0, 500, 1000, 2000],
    labels=['很近', '近', '中等']
)

# 保存结果
results.to_file('station_river_associations.gpkg', driver='GPKG')
```

### 示例2：公交站点与道路网络关联

```python
import geopandas as gpd
from gis_spatial_association import NearestNeighborAssociator
import pandas as pd

def analyze_bus_stop_road_associations(bus_stops_path, roads_path, output_path):
    """
    分析公交站点与道路网络的关联关系
    """
    # 加载数据
    bus_stops = gpd.read_file(bus_stops_path)
    roads = gpd.read_file(roads_path)

    # 确保坐标系一致
    if bus_stops.crs != roads.crs:
        roads = roads.to_crs(bus_stops.crs)

    # 只考虑主要道路
    main_roads = roads[roads['road_class'].isin(['primary', 'secondary', 'tertiary'])]

    # 创建关联分析器
    associator = NearestNeighborAssociator(
        max_distance=500,  # 公交站点通常离道路不超过500米
        parallel=True,
        n_jobs=4
    )

    # 执行关联分析
    associations = associator.associate(bus_stops, main_roads)

    # 添加分析结果分类
    associations['accessibility'] = associations['distance'].apply(
        lambda d: 'excellent' if d < 50 else 'good' if d < 200 else 'poor'
    )

    # 统计信息
    stats = {
        'total_stops': len(bus_stops),
        'associated_stops': len(associations),
        'association_rate': len(associations) / len(bus_stops) * 100,
        'avg_distance': associations['distance'].mean(),
        'median_distance': associations['distance'].median()
    }

    # 保存结果和统计信息
    associations.to_file(output_path, driver='GPKG')

    # 保存统计信息
    import json
    with open(output_path.replace('.gpkg', '_stats.json'), 'w') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    return associations, stats

# 使用示例
results, stats = analyze_bus_stop_road_associations(
    'bus_stops.shp',
    'road_network.shp',
    'bus_stop_associations.gpkg'
)

print(f"关联率: {stats['association_rate']:.1f}%")
print(f"平均距离: {stats['avg_distance']:.1f}米")
```

## 🔀 线-线相交检测示例

### 示例1：道路网络交叉口检测

```bash
# 检测道路网络中的所有交叉口
gis-association process \
  --input-lines road_network.shp \
  --second-input-lines road_network.shp \
  --output road_intersections.gpkg \
  --operation intersection \
  --tolerance 1.0 \
  --parallel 8
```

**Python代码：**
```python
from gis_spatial_association import LineIntersectionDetector
import geopandas as gpd

def detect_road_intersections(roads_path, output_path):
    """
    检测道路网络交叉口
    """
    # 加载道路数据
    roads = gpd.read_file(roads_path)

    # 创建相交检测器
    detector = LineIntersectionDetector(
        tolerance=1.0,  # 1米容差
        include_overlaps=True,  # 包含重叠
        return_intersection_points=True
    )

    # 检测相交
    intersections = detector.find_intersections(roads, roads)

    # 添加交叉口分类
    intersections['intersection_type'] = intersections.apply(
        lambda row: classify_intersection(row), axis=1
    )

    # 保存结果
    intersections.to_file(output_path, driver='GPKG')

    return intersections

def classify_intersection(intersection_row):
    """
    分类交叉口类型
    """
    intersection_count = intersection_row.get('intersection_count', 2)

    if intersection_count == 2:
        return 'simple_cross'
    elif intersection_count == 3:
        return 't_junction'
    elif intersection_count == 4:
        return 'cross_junction'
    else:
        return 'complex_junction'

# 使用示例
intersections = detect_road_intersections(
    'road_network.shp',
    'road_intersections.gpkg'
)

print(f"发现 {len(intersections)} 个交叉口")
```

### 示例2：管网冲突检测

```python
def detect_pipe_conflicts(water_pipes_path, gas_pipes_path, output_path):
    """
    检测水管与燃气管的冲突点
    """
    # 加载管网数据
    water_pipes = gpd.read_file(water_pipes_path)
    gas_pipes = gpd.read_file(gas_pipes_path)

    # 创建相交检测器
    detector = LineIntersectionDetector(
        tolerance=0.5,  # 0.5米容差
        min_intersection_length=1.0,  # 最小相交长度
        include_touches=False  # 忽略端点接触
    )

    # 检测冲突
    conflicts = detector.find_intersections(water_pipes, gas_pipes)

    # 添加冲突严重程度评估
    conflicts['severity'] = conflicts.apply(
        lambda row: assess_conflict_severity(row), axis=1
    )

    # 保存结果
    conflicts.to_file(output_path, driver='GPKG')

    return conflicts

def assess_conflict_severity(conflict_row):
    """
    评估冲突严重程度
    """
    # 这里可以根据实际情况定义评估逻辑
    intersection_length = conflict_row.get('intersection_length', 0)

    if intersection_length > 5:
        return 'high'
    elif intersection_length > 1:
        return 'medium'
    else:
        return 'low'
```

## 🏘️ 线-面包含分析示例

### 示例1：管线与保护区关系分析

```bash
# 分析管线是否穿过保护区
gis-association process \
  --input-lines pipelines.shp \
  --input-polygons protection_zones.shp \
  --output pipeline_zone_relations.gpkg \
  --operation containment \
  --buffer-distance 10
```

**Python代码：**
```python
from gis_spatial_association import PolygonContainmentAnalyzer
import geopandas as gpd

def analyze_pipeline_zone_relations(pipelines_path, zones_path, output_path):
    """
    分析管线与保护区的关系
    """
    # 加载数据
    pipelines = gpd.read_file(pipelines_path)
    protection_zones = gpd.read_file(zones_path)

    # 创建包含分析器
    analyzer = PolygonContainmentAnalyzer(
        buffer_distance=10,  # 10米缓冲区
        check_partial_containment=True,  # 检查部分包含
        calculate_containment_percentage=True
    )

    # 执行分析
    relations = analyzer.analyze_containment(pipelines, protection_zones)

    # 添加风险评估
    relations['risk_level'] = relations.apply(
        lambda row: assess_risk_level(row), axis=1
    )

    # 保存结果
    relations.to_file(output_path, driver='GPKG')

    return relations

def assess_risk_level(relation_row):
    """
    评估风险等级
    """
    zone_type = relation_row.get('zone_type', '')
    containment_pct = relation_row.get('containment_percentage', 0)

    if 'core' in zone_type.lower():
        return 'critical'
    elif 'buffer' in zone_type.lower() and containment_pct > 50:
        return 'high'
    elif containment_pct > 20:
        return 'medium'
    else:
        return 'low'
```

### 示例2：道路与行政区划分析

```python
def analyze_road_admin_relations(roads_path, admin_areas_path, output_path):
    """
    分析道路与行政区划的关系
    """
    # 加载数据
    roads = gpd.read_file(roads_path)
    admin_areas = gpd.read_file(admin_areas_path)

    # 创建分析器
    analyzer = PolygonContainmentAnalyzer(
        calculate_intersection_length=True,
        calculate_containment_percentage=True
    )

    # 分析关系
    relations = analyzer.analyze_containment(roads, admin_areas)

    # 统计每个行政区的道路长度
    road_stats = relations.groupby('polygon_id').agg({
        'intersection_length': 'sum',
        'line_id': 'count'
    }).rename(columns={
        'line_id': 'road_count'
    })

    # 合并统计信息
    relations = relations.merge(
        road_stats,
        left_on='polygon_id',
        right_index=True,
        suffixes=('', '_total')
    )

    return relations
```

## 🌐 坐标转换示例

### 示例1：批量坐标系转换

```bash
# 将数据从WGS84转换为CGCS2000
gis-association process \
  --input-points data_wgs84.shp \
  --output data_cgs2000.shp \
  --transform-crs 4496 \
  --source-crs 4326 \
  --preserve-attributes
```

**Python代码：**
```python
from gis_spatial_association import CoordinateTransformer
import geopandas as gpd

def transform_coordinates_batch(input_path, output_path, source_crs, target_crs):
    """
    批量转换坐标系
    """
    # 加载数据
    gdf = gpd.read_file(input_path)

    # 创建坐标转换器
    transformer = CoordinateTransformer(
        source_crs=source_crs,
        target_crs=target_crs,
        preserve_precision=True
    )

    # 执行转换
    transformed_gdf = transformer.transform(gdf)

    # 保存结果
    transformed_gdf.to_file(output_path, driver='GPKG')

    return transformed_gdf

# 使用示例
transformed_data = transform_coordinates_batch(
    'data_wgs84.shp',
    'data_cgs2000.shp',
    'EPSG:4326',
    'EPSG:4496'
)
```

### 示例2：多数据集统一坐标系

```python
def unify_coordinate_systems(data_paths, output_dir, target_crs='EPSG:3857'):
    """
    将多个数据集统一到同一坐标系
    """
    import os
    from pathlib import Path

    os.makedirs(output_dir, exist_ok=True)

    for data_path in data_paths:
        # 加载数据
        gdf = gpd.read_file(data_path)

        # 获取原始坐标系
        source_crs = gdf.crs

        if source_crs != target_crs:
            # 创建转换器
            transformer = CoordinateTransformer(
                source_crs=source_crs,
                target_crs=target_crs
            )

            # 执行转换
            gdf_transformed = transformer.transform(gdf)

            # 保存结果
            filename = Path(data_path).stem
            output_path = os.path.join(output_dir, f"{filename}_transformed.gpkg")
            gdf_transformed.to_file(output_path, driver='GPKG')

            print(f"转换完成: {data_path} -> {output_path}")
        else:
            print(f"跳过 {data_path}: 已经是目标坐标系")
```

## ✅ 数据验证示例

### 示例1：全面数据质量检查

```bash
# 全面数据验证和修复
gis-association validate \
  --input-path dataset.shp \
  --output-path validation_report.json \
  --check-geometry \
  --check-attributes \
  --check-crs \
  --repair \
  --output-repaired repaired_dataset.shp
```

**Python代码：**
```python
from gis_spatial_association import (
    GeometryValidator,
    AttributeValidator,
    CoordinateSystemValidator,
    DataQualityScorer,
    DataRepairer
)
import geopandas as gpd
import json

def comprehensive_data_validation(data_path, output_report_path):
    """
    全面数据质量验证
    """
    # 加载数据
    gdf = gpd.read_file(data_path)

    # 初始化验证器
    geometry_validator = GeometryValidator()
    attribute_validator = AttributeValidator()
    crs_validator = CoordinateSystemValidator()
    quality_scorer = DataQualityScorer()

    # 执行验证
    validation_report = {
        'file_path': data_path,
        'validation_timestamp': pd.Timestamp.now().isoformat(),
        'total_features': len(gdf)
    }

    # 几何验证
    geometry_issues = geometry_validator.validate(gdf)
    validation_report['geometry_validation'] = {
        'total_issues': len(geometry_issues),
        'issues': geometry_issues
    }

    # 属性验证
    attribute_issues = attribute_validator.validate(gdf)
    validation_report['attribute_validation'] = {
        'total_issues': len(attribute_issues),
        'issues': attribute_issues
    }

    # 坐标系验证
    crs_issues = crs_validator.validate(gdf)
    validation_report['crs_validation'] = crs_issues

    # 质量评分
    quality_score = quality_scorer.score(gdf)
    validation_report['quality_score'] = quality_score

    # 保存报告
    with open(output_report_path, 'w', encoding='utf-8') as f:
        json.dump(validation_report, f, indent=2, ensure_ascii=False, default=str)

    return validation_report
```

### 示例2：自动数据修复

```python
def auto_data_repair(data_path, output_path):
    """
    自动修复数据问题
    """
    # 加载数据
    gdf = gpd.read_file(data_path)

    # 创建修复器
    repairer = DataRepairer(
        fix_invalid_geometries=True,
        fill_missing_values=True,
        fix_invalid_crs=True,
        remove_duplicates=True
    )

    # 执行修复
    repaired_gdf = repairer.repair(gdf)

    # 保存修复后的数据
    repaired_gdf.to_file(output_path, driver='GPKG')

    # 生成修复报告
    repair_report = {
        'original_count': len(gdf),
        'repaired_count': len(repaired_gdf),
        'removed_count': len(gdf) - len(repaired_gdf),
        'fixes_applied': repairer.get_applied_fixes()
    }

    return repaired_gdf, repair_report
```

## 🔄 批处理示例

### 示例1：处理多个文件

```python
import os
import glob
from pathlib import Path

def batch_association_analysis(input_dir, points_pattern, lines_pattern, output_dir):
    """
    批量关联分析
    """
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 获取所有匹配的文件
    point_files = glob.glob(os.path.join(input_dir, points_pattern))
    line_files = glob.glob(os.path.join(input_dir, lines_pattern))

    results = []

    for point_file in point_files:
        for line_file in line_files:
            # 生成输出文件名
            point_name = Path(point_file).stem
            line_name = Path(line_file).stem
            output_file = os.path.join(
                output_dir,
                f"{point_name}_{line_name}_associations.gpkg"
            )

            try:
                # 执行关联分析
                os.system(f'''
                gis-association process \\
                  --input-points "{point_file}" \\
                  --input-lines "{line_file}" \\
                  --output "{output_file}" \\
                  --parallel 4
                ''')

                results.append({
                    'point_file': point_file,
                    'line_file': line_file,
                    'output_file': output_file,
                    'status': 'success'
                })

                print(f"✅ 完成: {point_name} + {line_name}")

            except Exception as e:
                results.append({
                    'point_file': point_file,
                    'line_file': line_file,
                    'output_file': output_file,
                    'status': 'failed',
                    'error': str(e)
                })

                print(f"❌ 失败: {point_name} + {line_name} - {e}")

    return results
```

### 示例2：配置文件驱动批处理

```python
import yaml
import json

def config_driven_batch_processing(config_path):
    """
    基于配置文件的批处理
    """
    # 加载配置
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    results = []

    for task in config['tasks']:
        task_name = task['name']
        task_config = task['config']

        print(f"执行任务: {task_name}")

        try:
            # 构建命令
            cmd = build_command_from_config(task_config)

            # 执行命令
            result = os.system(cmd)

            if result == 0:
                results.append({
                    'task': task_name,
                    'status': 'success',
                    'config': task_config
                })
                print(f"✅ 任务完成: {task_name}")
            else:
                results.append({
                    'task': task_name,
                    'status': 'failed',
                    'error_code': result
                })
                print(f"❌ 任务失败: {task_name}")

        except Exception as e:
            results.append({
                'task': task_name,
                'status': 'error',
                'error': str(e)
            })
            print(f"❌ 任务错误: {task_name} - {e}")

    # 保存批处理结果
    output_path = config.get('output_path', 'batch_results.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    return results

def build_command_from_config(config):
    """
    从配置构建命令行
    """
    cmd_parts = ['gis-association', 'process']

    # 添加输入参数
    if 'input_points' in config:
        cmd_parts.extend(['--input-points', config['input_points']])
    if 'input_lines' in config:
        cmd_parts.extend(['--input-lines', config['input_lines']])
    if 'input_polygons' in config:
        cmd_parts.extend(['--input-polygons', config['input_polygons']])

    # 添加输出参数
    if 'output' in config:
        cmd_parts.extend(['--output', config['output']])

    # 添加分析参数
    if 'max_distance' in config:
        cmd_parts.extend(['--max-distance', str(config['max_distance'])])
    if 'parallel' in config:
        cmd_parts.extend(['--parallel', str(config['parallel'])])

    return ' '.join(cmd_parts)
```

## ⚡ 性能优化示例

### 示例1：大数据集优化处理

```python
def optimized_large_dataset_processing(points_path, lines_path, output_path):
    """
    大数据集优化处理
    """
    # 分块加载和处理
    chunk_size = 10000

    # 创建关联分析器
    associator = NearestNeighborAssociator(
        max_distance=5000,
        parallel=True,
        n_jobs=8,
        use_spatial_index=True
    )

    # 分块处理点数据
    points_chunks = pd.read_csv(points_path.replace('.shp', '.csv'), chunksize=chunk_size)

    all_results = []

    for i, points_chunk in enumerate(points_chunks):
        print(f"处理第 {i+1} 个数据块...")

        # 转换为GeoDataFrame
        points_gdf = gpd.GeoDataFrame(points_chunk)

        # 执行关联分析
        chunk_results = associator.associate(points_gdf, lines_path)

        all_results.append(chunk_results)

        # 释放内存
        del points_gdf, chunk_results

    # 合并所有结果
    final_results = pd.concat(all_results, ignore_index=True)

    # 保存结果
    final_results.to_file(output_path, driver='GPKG')

    return final_results
```

### 示例2：内存优化策略

```python
def memory_efficient_processing(input_paths, output_path):
    """
    内存高效的处理策略
    """
    import gc

    results = []

    for i, input_path in enumerate(input_paths):
        print(f"处理文件 {i+1}/{len(input_paths)}: {input_path}")

        # 加载单个文件
        gdf = gpd.read_file(input_path)

        # 执行分析
        processed_gdf = process_single_file(gdf)

        # 收集结果
        results.append(processed_gdf)

        # 释放内存
        del gdf, processed_gdf
        gc.collect()

    # 合并并保存结果
    final_result = pd.concat(results, ignore_index=True)
    final_result.to_file(output_path, driver='GPKG')

    return final_result
```

## 📊 可视化示例

### 示例1：关联结果可视化

```python
import matplotlib.pyplot as plt
import seaborn as sns
import contextily as ctx

def visualize_association_results(points_path, lines_path, associations_path):
    """
    可视化关联分析结果
    """
    # 加载数据
    points = gpd.read_file(points_path)
    lines = gpd.read_file(lines_path)
    associations = gpd.read_file(associations_path)

    # 创建图表
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # 子图1：原始数据
    ax1 = axes[0, 0]
    points.plot(ax=ax1, color='red', markersize=10, label='Points')
    lines.plot(ax=ax1, color='blue', linewidth=1, label='Lines')
    ax1.set_title('原始数据')
    ax1.legend()

    # 子图2：关联关系热力图
    ax2 = axes[0, 1]
    associations.plot(ax=ax2, column='distance', cmap='viridis',
                     legend=True, markersize=20)
    ax2.set_title('关联距离分布')

    # 子图3：距离分布直方图
    ax3 = axes[1, 0]
    sns.histplot(data=associations, x='distance', bins=30, ax=ax3)
    ax3.set_title('距离分布直方图')
    ax3.set_xlabel('距离 (米)')

    # 子图4：关联数量统计
    ax4 = axes[1, 1]
    association_counts = associations['point_id'].value_counts().head(10)
    association_counts.plot(kind='bar', ax=ax4)
    ax4.set_title('Top 10 关联数量')
    ax4.set_xlabel('点ID')
    ax4.set_ylabel('关联数量')
    ax4.tick_params(axis='x', rotation=45)

    plt.tight_layout()
    plt.savefig('association_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()
```

### 示例2：交互式可视化

```python
import plotly.express as px
import plotly.graph_objects as go

def create_interactive_association_map(associations_path):
    """
    创建交互式关联地图
    """
    # 加载关联结果
    associations = gpd.read_file(associations_path)

    # 提取坐标
    associations['lon'] = associations.geometry.x
    associations['lat'] = associations.geometry.y

    # 创建交互式地图
    fig = px.scatter_mapbox(
        associations,
        lat="lat",
        lon="lon",
        color="distance",
        size="distance",
        hover_data=['point_id', 'line_id', 'distance'],
        color_continuous_scale="Viridis",
        size_max=15,
        zoom=10,
        mapbox_style="open-street-map",
        title="空间关联分析结果"
    )

    # 更新布局
    fig.update_layout(
        height=600,
        coloraxis_colorbar=dict(
            title="距离 (米)",
            thicknessmode="pixels",
            thickness=20,
            lenmode="pixels",
            len=300
        )
    )

    # 保存为HTML
    fig.write_html("interactive_associations.html")
    fig.show()
```

## 🏭 实际应用案例

### 案例1：城市交通规划

```python
def urban_transport_planning_analysis():
    """
    城市交通规划综合分析
    """
    # 数据路径
    data_dir = "urban_transport_data"

    # 1. 公交站点与道路关联分析
    bus_stops = gpd.read_file(f"{data_dir}/bus_stops.shp")
    road_network = gpd.read_file(f"{data_dir}/roads.shp")

    associator = NearestNeighborAssociator(max_distance=300)
    stop_road_associations = associator.associate(bus_stops, road_network)

    # 2. 地铁站与周边设施关联
    subway_stations = gpd.read_file(f"{data_dir}/subway_stations.shp")
    facilities = gpd.read_file(f"{data_dir}/facilities.shp")

    station_facility_associations = associator.associate(subway_stations, facilities)

    # 3. 交叉口检测
    intersection_detector = LineIntersectionDetector()
    intersections = intersection_detector.find_intersections(road_network, road_network)

    # 4. 综合分析报告
    report = {
        'bus_stop_coverage': len(stop_road_associations) / len(bus_stops) * 100,
        'avg_stop_to_road_distance': stop_road_associations['distance'].mean(),
        'total_intersections': len(intersections),
        'station_facility_ratio': len(station_facility_associations) / len(subway_stations)
    }

    return {
        'stop_road_associations': stop_road_associations,
        'station_facility_associations': station_facility_associations,
        'intersections': intersections,
        'report': report
    }
```

### 案例2：环境监测网络优化

```python
def environmental_monitoring_optimization():
    """
    环境监测网络优化分析
    """
    # 加载数据
    monitoring_sites = gpd.read_file("environmental/monitoring_sites.shp")
    pollution_sources = gpd.read_file("environmental/pollution_sources.shp")
    rivers = gpd.read_file("environmental/rivers.shp")
    protected_areas = gpd.read_file("environmental/protected_areas.shp")

    # 1. 监测站点与污染源关联
    site_source_associator = NearestNeighborAssociator(max_distance=5000)
    site_source_relations = site_source_associator.associate(monitoring_sites, pollution_sources)

    # 2. 监测站点与河流关联
    site_river_relations = site_source_associator.associate(monitoring_sites, rivers)

    # 3. 污染源与保护区关系分析
    zone_analyzer = PolygonContainmentAnalyzer(buffer_distance=1000)
    source_zone_relations = zone_analyzer.analyze_containment(pollution_sources, protected_areas)

    # 4. 网络覆盖评估
    coverage_assessment = assess_monitoring_coverage(
        monitoring_sites, pollution_sources, site_source_relations
    )

    return {
        'site_source_relations': site_source_relations,
        'site_river_relations': site_river_relations,
        'source_zone_relations': source_zone_relations,
        'coverage_assessment': coverage_assessment
    }

def assess_monitoring_coverage(sites, sources, relations):
    """
    评估监测网络覆盖情况
    """
    # 计算覆盖的污染源数量
    covered_sources = relations['line_id'].nunique()
    total_sources = len(sources)
    coverage_rate = covered_sources / total_sources * 100

    # 计算平均监测距离
    avg_distance = relations['distance'].mean()

    # 识别未覆盖区域
    uncovered_sources = sources[~sources.index.isin(relations['line_id'])]

    return {
        'coverage_rate': coverage_rate,
        'covered_sources': covered_sources,
        'uncovered_sources': len(uncovered_sources),
        'avg_distance': avg_distance,
        'uncovered_source_areas': uncovered_sources
    }
```

## 🎯 总结

以上示例展示了GIS空间关联分析系统在各种场景下的应用方法。关键要点：

1. **选择合适的分析方法**：根据具体问题选择点-线、线-线或线-面分析
2. **合理设置参数**：距离阈值、并行度等参数显著影响结果
3. **数据预处理很重要**：确保坐标系一致、数据质量良好
4. **结果验证和可视化**：通过可视化检查分析结果的合理性
5. **性能优化**：对大数据集使用分块处理和并行计算

## 📞 获取帮助

如需更多帮助，请参考：
- [CLI命令参考](cli_reference.md)
- [API文档](../api/)
- [故障排除指南](troubleshooting.md)
- [社区讨论](https://github.com/your-repo/gis-spatial-association-system/discussions)