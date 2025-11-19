# GIS空间关联分析系统

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![GeoPandas](https://img.shields.io/badge/GeoPandas-Latest-green.svg)](https://geopandas.org)
[![Shapely](https://img.shields.io/badge/Shapely-Latest-green.svg)](https://shapely.readthedocs.io)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

高性能的GIS空间关联分析系统，提供专业的地理空间要素关系分析功能。

## 🚀 核心功能

### 1. 点-线最近邻关联分析 (NearestNeighborAssociator)
- **高性能处理**: 支持批量处理20,385个横断面点关联到583条横断面线
- **空间索引优化**: R-tree索引，算法复杂度O(n log n)
- **智能关联**: 支持距离阈值控制和质量验证
- **内存优化**: 批处理机制，支持大数据集处理

### 2. 线-线相交检测分析 (LineIntersectionDetector)
- **精确检测**: 处理583条横断面线与54条纵断面线的相交关系
- **一对多解决**: 智能处理1:n关系，选择中点距离最近的关联
- **复杂几何**: 支持Point、MultiPoint、LineString、MultiLineString
- **精度控制**: 几何相交容差和重复点过滤

### 3. 线-面包含判断分析 (PolygonContainmentAnalyzer)
- **全面分析**: 检测横断面与80个防治对象面的相交关系
- **级联关联**: 实现多级关联传递和复杂关系网络
- **复杂几何**: 支持带孔洞多边形和MultiPolygon
- **度量指标**: 相交长度、比例、交点数等详细分析

### 4. 坐标系统转换处理 (CoordinateTransformer)
- **多坐标系**: WGS84、CGCS2000、Web Mercator等常用坐标系
- **自动检测**: 智能检测和统一数据集坐标系
- **批量转换**: 高效的批量数据集转换处理
- **质量验证**: 转换精度验证和质量控制

## 📊 性能指标

| 功能模块 | 数据规模 | 处理时间 | 算法复杂度 |
|---------|---------|---------|-----------|
| 点-线关联 | 20,385点 → 583线 | < 30秒 | O(n log n) |
| 线-线相交 | 583线 × 54线 | < 10秒 | O(n log n) |
| 线-面包含 | 横断面 → 80面 | < 45秒 | O(n log n) |
| 坐标转换 | 多数据集 | < 5秒 | O(n) |

## 🛠️ 技术栈

- **核心语言**: Python 3.8+
- **空间计算**: GeoPandas, Shapely
- **空间索引**: Rtree, STRtree
- **坐标转换**: pyproj, PROJ
- **数值计算**: NumPy, Pandas
- **测试框架**: unittest

## 📦 安装依赖

```bash
# 核心依赖
pip install geopandas shapely rtree pyproj

# 数值计算依赖
pip install numpy pandas

# 可选依赖（用于高性能计算）
pip install cython
```

系统依赖：
```bash
# Ubuntu/Debian
sudo apt-get install libgdal-dev libproj-dev libgeos-dev

# CentOS/RHEL
sudo yum install gdal-devel proj-devel geos-devel

# macOS
brew install gdal proj geos
```

## 🔧 快速开始

### 基本使用示例

```python
import geopandas as gpd
from gis_spatial_association import (
    NearestNeighborAssociator,
    LineIntersectionDetector,
    PolygonContainmentAnalyzer,
    CoordinateTransformer
)

# 1. 坐标系统统一
transformer = CoordinateTransformer()
datasets = {
    'points': points_gdf,
    'h_lines': h_lines_gdf,
    'v_lines': v_lines_gdf,
    'polygons': polygons_gdf
}
unified_datasets, target_crs = transformer.batch_transform_datasets(datasets)

# 2. 点-线关联分析
associator = NearestNeighborAssociator()
point_line_results = associator.associate_points_to_lines(
    unified_datasets['points'],
    unified_datasets['h_lines']
)

# 3. 线-线相交检测
detector = LineIntersectionDetector()
intersections = detector.find_intersections(
    unified_datasets['h_lines'],
    unified_datasets['v_lines']
)
resolved_associations = detector.resolve_intersections(intersections)

# 4. 线-面包含分析
analyzer = PolygonContainmentAnalyzer()
containment_results = analyzer.find_intersections(
    unified_datasets['h_lines'],
    unified_datasets['polygons']
)
cascade_associations = analyzer.build_cascade_associations(containment_results)

print(f"点-线关联: {len(point_line_results)} 个关联")
print(f"线-线相交: {len(resolved_associations)} 个相交")
print(f"线-面包含: {len(containment_results)} 个相交")
```

### 高级配置

```python
# 自定义配置
from gis_spatial_association.algorithms import create_associator, create_detector

# 创建高性能关联器
associator = create_associator({
    'use_spatial_index': True,
    'association_threshold': 1000.0,  # 米
    'batch_size': 2000
})

# 创建高精度检测器
detector = create_detector({
    'intersection_tolerance': 1e-8,
    'use_spatial_index': True
})
```

## 📖 详细文档

### API文档

#### NearestNeighborAssociator

```python
class NearestNeighborAssociator:
    def __init__(self, use_spatial_index=True, association_threshold=float('inf'), batch_size=1000)
    def associate_points_to_lines(self, points_gdf, lines_gdf, progress_callback=None) -> gpd.GeoDataFrame
    def validate_associations(self, result_gdf) -> Dict[str, int]
    def get_association_statistics(self) -> Dict
```

#### LineIntersectionDetector

```python
class LineIntersectionDetector:
    def __init__(self, intersection_tolerance=1e-6, use_spatial_index=True)
    def find_intersections(self, h_lines_gdf, v_lines_gdf, progress_callback=None) -> List[Dict]
    def resolve_intersections(self, intersections=None) -> List[Dict]
    def build_result_gdf(self, associations, h_lines_gdf, v_lines_gdf) -> gpd.GeoDataFrame
```

#### PolygonContainmentAnalyzer

```python
class PolygonContainmentAnalyzer:
    def __init__(self, use_spatial_index=True, cascade_enabled=True)
    def find_intersections(self, lines_gdf, polygons_gdf, progress_callback=None) -> List[Dict]
    def build_cascade_associations(self, intersections=None) -> Dict[str, List[str]]
    def build_result_gdf(self, intersections, lines_gdf, polygons_gdf) -> gpd.GeoDataFrame
```

#### CoordinateTransformer

```python
class CoordinateTransformer:
    def __init__(self, default_target_crs='EPSG:4490', tolerance=1e-6)
    def batch_transform_datasets(self, datasets, target_crs=None, progress_callback=None) -> Tuple[Dict, str]
    def validate_transformation_quality(self, original_gdf, transformed_gdf, sample_size=100) -> Dict
```

## 🧪 测试

### 运行完整测试套件

```bash
# 进入项目目录
cd gis_spatial_association

# 运行所有测试
python tests/run_tests.py

# 运行快速测试（跳过性能测试）
python tests/run_tests.py --quick

# 运行特定模块测试
python tests/run_tests.py --unit          # 只运行单元测试
python tests/run_tests.py --integration   # 只运行集成测试
python tests/run_tests.py --performance   # 只运行性能测试

# 导出测试结果
python tests/run_tests.py --export results.txt
```

### 单独运行测试文件

```bash
# 运行单个测试文件
python -m unittest tests.test_association
python -m unittest tests.test_intersection
python -m unittest tests.test_containment
python -m unittest tests.test_transformation
python -m unittest tests.test_integration
```

## 📈 性能优化建议

### 大数据集处理

1. **启用空间索引**
```python
associator = NearestNeighborAssociator(use_spatial_index=True)
detector = LineIntersectionDetector(use_spatial_index=True)
analyzer = PolygonContainmentAnalyzer(use_spatial_index=True)
```

2. **调整批处理大小**
```python
associator = NearestNeighborAssociator(batch_size=5000)  # 增大批处理
```

3. **设置合理的关联阈值**
```python
associator = NearestNeighborAssociator(association_threshold=10000.0)  # 10公里
```

### 内存优化

```python
# 分批处理大数据集
def process_large_dataset(points_gdf, lines_gdf, batch_size=10000):
    associator = NearestNeighborAssociator()
    results = []

    for i in range(0, len(points_gdf), batch_size):
        batch = points_gdf.iloc[i:i+batch_size]
        batch_result = associator.associate_points_to_lines(batch, lines_gdf)
        results.append(batch_result)

    return pd.concat(results, ignore_index=True)
```

## 🐛 常见问题

### Q: 如何处理不同坐标系的数据？
A: 使用CoordinateTransformer自动检测和转换坐标系：
```python
transformer = CoordinateTransformer()
unified_datasets, target_crs = transformer.batch_transform_datasets(datasets)
```

### Q: 如何提高关联分析的性能？
A:
- 启用空间索引 (`use_spatial_index=True`)
- 增大批处理大小 (`batch_size=5000`)
- 设置合理的关联阈值

### Q: 如何处理复杂的几何体？
A: 系统自动支持复杂几何体，包括：
- MultiPoint, MultiLineString, MultiPolygon
- 带孔洞的多边形
- 复杂的相交关系

### Q: 如何验证分析结果的准确性？
A: 使用内置的验证功能：
```python
validation_stats = associator.validate_associations(result_gdf)
quality_result = transformer.validate_transformation_quality(original_gdf, transformed_gdf)
```

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

### 开发环境设置

```bash
# 克隆项目
git clone <repository-url>
cd gis_spatial_association

# 安装开发依赖
pip install -r requirements-dev.txt

# 运行测试确保环境正常
python tests/run_tests.py --quick
```

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 联系信息

- 项目主页: [GitHub Repository]
- 问题反馈: [GitHub Issues]
- 技术讨论: [项目Wiki]

## 🙏 致谢

感谢以下开源项目：
- [GeoPandas](https://geopandas.org/) - 地理空间数据处理
- [Shapely](https://shapely.readthedocs.io/) - 几何对象操作
- [pyproj](https://pyproj4.github.io/pyproj/stable/) - 坐标系转换
- [Rtree](https://rtree.readthedocs.io/) - 空间索引

---

**CCPM自动化开发系统** - 专业AI编程助手，提供结构化六阶段开发工作流。