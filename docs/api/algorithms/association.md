# 📍 点-线关联分析API

## 概述

`NearestNeighborAssociator` 类提供点要素与线要素之间的最近邻关联分析功能。它可以高效地找到每个点要素到线要素的最近关联，并计算详细的几何关系信息。

## 主要类

### NearestNeighborAssociator

点-线关联分析的主要算法类。

#### 构造函数

```python
NearestNeighborAssociator(
    max_distance: float = 1000.0,
    return_all_fields: bool = False,
    calculate_parallel_distance: bool = True,
    calculate_perpendicular_distance: bool = True,
    calculate_azimuth: bool = True,
    parallel: bool = False,
    n_jobs: int = 4,
    use_spatial_index: bool = True,
    memory_limit: Optional[int] = None
)
```

**参数说明：**

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `max_distance` | float | 1000.0 | 最大关联距离（米） |
| `return_all_fields` | bool | False | 是否返回所有属性字段 |
| `calculate_parallel_distance` | bool | True | 是否计算平行距离 |
| `calculate_perpendicular_distance` | bool | True | 是否计算垂直距离 |
| `calculate_azimuth` | bool | True | 是否计算方位角 |
| `parallel` | bool | False | 是否启用并行处理 |
| `n_jobs` | int | 4 | 并行工作进程数 |
| `use_spatial_index` | bool | True | 是否使用空间索引 |
| `memory_limit` | Optional[int] | None | 内存限制（MB） |

#### 主要方法

##### associate()

执行点-线关联分析。

```python
associate(
    points: GeoDataFrame,
    lines: GeoDataFrame,
    point_id_column: str = None,
    line_id_column: str = None,
    progress_callback: Optional[Callable] = None
) -> GeoDataFrame
```

**参数说明：**

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `points` | GeoDataFrame | 是 | 点要素数据 |
| `lines` | GeoDataFrame | 是 | 线要素数据 |
| `point_id_column` | str | 否 | 点要素ID列名 |
| `line_id_column` | str | 否 | 线要素ID列名 |
| `progress_callback` | Callable | 否 | 进度回调函数 |

**返回值：**
- `GeoDataFrame`: 包含关联分析结果的数据框

##### batch_associate()

批量关联分析，适用于大数据集。

```python
batch_associate(
    points: GeoDataFrame,
    lines: GeoDataFrame,
    chunk_size: int = 1000,
    **kwargs
) -> GeoDataFrame
```

##### get_association_stats()

获取关联分析统计信息。

```python
get_association_stats(results: GeoDataFrame) -> Dict[str, Any]
```

## 使用示例

### 基础使用

```python
from gis_spatial_association import NearestNeighborAssociator
import geopandas as gpd

# 加载数据
points = gpd.read_file('monitoring_stations.shp')
lines = gpd.read_file('river_network.shp')

# 创建关联分析器
associator = NearestNeighborAssociator(
    max_distance=2000,  # 最大关联距离2000米
    calculate_parallel_distance=True,
    calculate_perpendicular_distance=True
)

# 执行关联分析
results = associator.associate(points, lines)

print(f"找到 {len(results)} 个关联关系")
print(results.head())
```

### 高级配置

```python
# 高性能配置
associator = NearestNeighborAssociator(
    max_distance=5000,
    return_all_fields=True,
    calculate_azimuth=True,
    parallel=True,
    n_jobs=8,
    use_spatial_index=True,
    memory_limit=8192
)

# 执行分析
results = associator.associate(
    points,
    lines,
    point_id_column='station_id',
    line_id_column='river_id'
)
```

### 大数据集处理

```python
# 分块处理大数据集
results = associator.batch_associate(
    points=large_points_dataset,
    lines=road_network,
    chunk_size=5000
)
```

## 结果格式

### 输出字段说明

关联分析结果包含以下字段：

| 字段名 | 类型 | 描述 |
|--------|------|------|
| `point_id` | str/int | 关联的点要素ID |
| `line_id` | str/int | 关联的线要素ID |
| `distance` | float | 最近距离（米） |
| `nearest_point_x` | float | 最近点X坐标 |
| `nearest_point_y` | float | 最近点Y坐标 |
| `parallel_distance` | float | 平行距离（米） |
| `perpendicular_distance` | float | 垂直距离（米） |
| `azimuth` | float | 方位角（度） |
| `intersection_ratio` | float | 在线上的位置比例（0-1） |

### 示例结果

```python
# 结果数据结构
results = pd.DataFrame({
    'point_id': ['station_001', 'station_002', 'station_003'],
    'line_id': ['river_001', 'river_001', 'river_002'],
    'distance': [150.5, 320.2, 85.7],
    'nearest_point_x': [116.123, 116.456, 116.789],
    'nearest_point_y': [39.456, 39.789, 40.123],
    'parallel_distance': [120.3, 280.1, 65.4],
    'perpendicular_distance': [45.2, 80.1, 25.3],
    'azimuth': [45.6, 123.4, 78.9],
    'intersection_ratio': [0.25, 0.75, 0.10]
})
```

## 性能优化

### 空间索引

系统自动使用Rtree空间索引来加速查询：

```python
# 手动控制空间索引
associator = NearestNeighborAssociator(
    use_spatial_index=True  # 启用空间索引（推荐）
)
```

### 并行处理

对于大数据集，启用并行处理：

```python
# 启用并行处理
associator = NearestNeighborAssociator(
    parallel=True,
    n_jobs=min(8, os.cpu_count())  # 使用CPU核心数
)
```

### 内存优化

```python
# 设置内存限制
associator = NearestNeighborAssociator(
    memory_limit=4096  # 4GB内存限制
)

# 分块处理
results = associator.batch_associate(
    points=large_dataset,
    lines=network,
    chunk_size=1000  # 每块1000个点
)
```

## 自定义扩展

### 自定义距离计算

```python
class CustomAssociator(NearestNeighborAssociator):
    def calculate_custom_distance(self, point, line):
        # 实现自定义距离计算逻辑
        return custom_distance

    def associate(self, points, lines, **kwargs):
        # 重写关联分析逻辑
        pass
```

### 自定义过滤器

```python
# 在关联分析前过滤数据
def filter_data(points, lines):
    # 自定义过滤逻辑
    filtered_points = points[points['type'] == 'station']
    filtered_lines = lines[lines['status'] == 'active']
    return filtered_points, filtered_lines

# 使用过滤器
filtered_points, filtered_lines = filter_data(points, lines)
results = associator.associate(filtered_points, filtered_lines)
```

## 错误处理

### 常见错误

```python
try:
    results = associator.associate(points, lines)
except ValueError as e:
    print(f"数据格式错误: {e}")
except MemoryError as e:
    print(f"内存不足: {e}")
except Exception as e:
    print(f"分析失败: {e}")
```

### 数据验证

```python
def validate_input_data(points, lines):
    """验证输入数据"""
    if len(points) == 0:
        raise ValueError("点数据为空")
    if len(lines) == 0:
        raise ValueError("线数据为空")

    if points.crs != lines.crs:
        lines = lines.to_crs(points.crs)

    return points, lines

# 验证并分析
points, lines = validate_input_data(points, lines)
results = associator.associate(points, lines)
```

## 统计分析

### 基础统计

```python
# 获取分析统计信息
stats = associator.get_association_stats(results)

print(f"总关联数: {stats['total_associations']}")
print(f"平均距离: {stats['avg_distance']:.2f}米")
print(f"最大距离: {stats['max_distance']:.2f}米")
print(f"最小距离: {stats['min_distance']:.2f}米")
```

### 高级统计

```python
import pandas as pd

def detailed_analysis(results):
    """详细分析关联结果"""

    # 距离分布统计
    distance_stats = results['distance'].describe()

    # 关联数量分布
    association_counts = results['point_id'].value_counts()

    # 距离分类
    results['distance_category'] = pd.cut(
        results['distance'],
        bins=[0, 100, 500, 1000, float('inf')],
        labels=['很近', '近', '中等', '远']
    )

    return {
        'distance_stats': distance_stats,
        'association_counts': association_counts,
        'distance_distribution': results['distance_category'].value_counts()
    }

analysis = detailed_analysis(results)
```

## 可视化

### 基础可视化

```python
import matplotlib.pyplot as plt

def visualize_associations(points, lines, results):
    """可视化关联分析结果"""

    fig, ax = plt.subplots(figsize=(12, 8))

    # 绘制原始数据
    points.plot(ax=ax, color='red', markersize=10, label='Points')
    lines.plot(ax=ax, color='blue', linewidth=1, label='Lines')

    # 绘制关联结果
    results.plot(ax=ax, column='distance', cmap='viridis',
                markersize=20, legend=True, label='Associations')

    ax.set_title('Point-Line Association Analysis')
    ax.legend()
    plt.show()
```

### 交互式可视化

```python
import plotly.express as px

def interactive_association_map(results):
    """创建交互式关联地图"""

    fig = px.scatter_mapbox(
        results,
        lat='nearest_point_y',
        lon='nearest_point_x',
        color='distance',
        size='distance',
        hover_data=['point_id', 'line_id', 'distance'],
        color_continuous_scale='Viridis',
        mapbox_style='open-street-map',
        title='Point-Line Associations'
    )

    return fig
```

## 最佳实践

### 1. 数据预处理

```python
# 数据清理
def preprocess_data(points, lines):
    """预处理数据"""

    # 移除重复要素
    points = points.drop_duplicates()
    lines = lines.drop_duplicates()

    # 移除无效几何
    points = points[points.geometry.is_valid]
    lines = lines[lines.geometry.is_valid]

    # 确保坐标系一致
    if points.crs != lines.crs:
        lines = lines.to_crs(points.crs)

    return points, lines
```

### 2. 参数调优

```python
# 根据数据特征调整参数
def optimize_parameters(points, lines):
    """根据数据特征优化参数"""

    # 计算数据范围
    bounds = points.total_bounds
    data_span = max(bounds[2] - bounds[0], bounds[3] - bounds[1])

    # 根据数据范围设置最大距离
    max_distance = data_span * 0.1  # 数据跨度的10%

    # 根据数据量设置并行度
    n_jobs = min(8, max(1, len(points) // 10000))

    return {
        'max_distance': max_distance,
        'parallel': len(points) > 10000,
        'n_jobs': n_jobs
    }
```

### 3. 内存管理

```python
# 大数据集内存优化
def memory_efficient_association(points, lines, memory_limit=4096):
    """内存高效的关联分析"""

    # 估算内存使用
    estimated_memory = len(points) * len(lines) * 8 / 1024 / 1024  # MB

    if estimated_memory > memory_limit:
        # 使用分块处理
        chunk_size = int(memory_limit * 1024 * 1024 / len(lines) / 8)
        associator = NearestNeighborAssociator()
        return associator.batch_associate(points, lines, chunk_size)
    else:
        # 直接处理
        associator = NearestNeighborAssociator()
        return associator.associate(points, lines)
```

---

**通过合理使用这些API，您可以充分发挥点-线关联分析的功能！🚀**