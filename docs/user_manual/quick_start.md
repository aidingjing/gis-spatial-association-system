# 🚀 快速开始指南

欢迎使用GIS空间关联分析系统！本指南将帮助您在几分钟内快速上手使用这个强大的地理空间分析工具。

## 📋 开始之前

### 系统要求检查

在开始之前，请确保您的系统满足以下基本要求：

```bash
# 检查Python版本（需要3.8+）
python --version

# 检查pip是否可用
pip --version

# 检查可用内存（建议4GB+）
# Linux/macOS
free -h
# Windows
wmic computersystem get TotalPhysicalMemory
```

### 基本概念

- **点要素**: 具有经纬度坐标的位置点（如建筑物、监测站点）
- **线要素**: 由一系列点连接成的线性要素（如道路、河流、管线）
- **面要素**: 由闭合线构成的多边形区域（如行政区划、土地利用）
- **空间关联**: 地理要素之间的空间关系（如包含、相交、邻接等）

## ⚡ 5分钟快速体验

### 第一步：安装系统

```bash
# 1. 克隆项目
git clone https://github.com/your-repo/gis-spatial-association-system.git
cd gis-spatial-association-system

# 2. 创建虚拟环境（推荐）
python -m venv gis_env
source gis_env/bin/activate  # Linux/macOS
# 或 gis_env\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 安装项目
pip install -e .
```

### 第二步：验证安装

```bash
# 检查系统状态
gis-association --version

# 应该看到类似输出：
# GIS空间关联分析系统 v1.0.0
# 核心模块状态:
# • 关联分析模块: ✅ 可用
# • 相交检测模块: ✅ 可用
# • 包含分析模块: ✅ 可用
# • 坐标转换模块: ✅ 可用
# • 数据验证模块: ✅ 可用
```

### 第三步：准备测试数据

```bash
# 创建测试数据目录
mkdir test_data
cd test_data

# 下载示例数据（如果没有真实数据）
wget https://example.com/sample_points.shp
wget https://example.com/sample_lines.shp
wget https://example.com/sample_polygons.shp
```

### 第四步：执行第一次分析

```bash
# 点-线关联分析
gis-association process \
  --input-points sample_points.shp \
  --input-lines sample_lines.shp \
  --output point_line_associations.gpkg \
  --max-distance 1000

# 线-线相交检测
gis-association process \
  --input-lines sample_lines.shp \
  --second-input-lines sample_lines.shp \
  --output line_intersections.gpkg \
  --operation intersection

# 数据验证
gis-association validate sample_points.shp --repair
```

### 第五步：查看结果

```python
import geopandas as gpd
import matplotlib.pyplot as plt

# 加载关联分析结果
results = gpd.read_file('point_line_associations.gpkg')
print(f"找到 {len(results)} 个关联关系")

# 可视化结果
fig, ax = plt.subplots(figsize=(12, 8))
results.plot(ax=ax, column='distance', cmap='viridis', legend=True)
plt.title('点-线关联分析结果')
plt.show()
```

## 🎯 核心功能快速体验

### 1. 点-线最近邻关联

```bash
# 基础关联分析
gis-association process \
  --input-points monitoring_stations.shp \
  --input-lines rivers.shp \
  --output station_river_associations.gpkg

# 带参数的关联分析
gis-association process \
  --input-points buildings.shp \
  --input-lines roads.shp \
  --output building_road_associations.gpkg \
  --max-distance 500 \
  --parallel 4 \
  --output-format csv
```

### 2. 线-线相交检测

```bash
# 检测线要素之间的交点
gis-association process \
  --input-lines water_network.shp \
  --second-input-lines road_network.shp \
  --output intersections.gpkg \
  --operation intersection \
  --tolerance 1.0
```

### 3. 线-面包含分析

```bash
# 判断线是否被面包含
gis-association process \
  --input-lines pipelines.shp \
  --input-polygons protection_zones.shp \
  --output pipeline_zone_relations.gpkg \
  --operation containment
```

### 4. 坐标系转换

```bash
# 转换数据坐标系
gis-association process \
  --input-points data_wgs84.shp \
  --output data_cgs2000.shp \
  --transform-crs 4496 \
  --source-crs 4326
```

### 5. 数据质量验证

```bash
# 全面数据验证
gis-association validate \
  --input-path dataset.shp \
  --output-path validation_report.json \
  --check-geometry \
  --check-attributes \
  --check-crs \
  --repair
```

## 🛠️ 交互式模式体验

启动交互式模式，通过界面操作完成分析：

```bash
# 启动交互式模式
gis-association interactive
```

交互式模式提供：
- 📁 文件浏览器选择输入数据
- 🎛️ 参数设置界面
- 📊 实时进度显示
- 📈 结果预览和导出

## 📊 结果理解

### 输出文件结构

关联分析结果包含以下关键字段：

```json
{
  "point_id": "点要素ID",
  "line_id": "线要素ID",
  "distance": 123.45,
  "nearest_point": {"x": 116.123, "y": 39.456},
  "parallel_distance": 5.67,
  "perpendicular_distance": 2.34,
  "azimuth": 45.67
}
```

### 结果统计

```bash
# 查看结果统计信息
gis-association info --input result.gpkg --stats
```

## 🔧 常用配置选项

### 性能优化

```bash
# 启用并行计算
gis-association process \
  --input-points large_dataset.shp \
  --input-lines network.shp \
  --output result.gpkg \
  --parallel 8 \
  --chunk-size 1000
```

### 输出控制

```bash
# 指定输出格式和编码
gis-association process \
  --input-points data.shp \
  --input-lines lines.shp \
  --output result.geojson \
  --encoding utf-8 \
  --precision 6
```

### 过滤和筛选

```bash
# 根据属性过滤
gis-association process \
  --input-points points.shp \
  --input-lines lines.shp \
  --output result.gpkg \
  --point-filter "type='station'" \
  --line-filter "status='active'"
```

## 📈 进阶使用技巧

### 1. 批处理模式

```bash
# 处理多个文件
for file in data/*.shp; do
  gis-association process \
    --input-points "$file" \
    --input-lines network.shp \
    --output "results/$(basename "$file" .shp)_associations.gpkg"
done
```

### 2. 配置文件使用

```yaml
# config.yaml
analysis:
  max_distance: 1000
  parallel: true
  workers: 4

output:
  format: gpkg
  encoding: utf-8
  precision: 6

validation:
  check_geometry: true
  check_attributes: true
  auto_repair: true
```

```bash
# 使用配置文件
gis-association process \
  --input-points data.shp \
  --input-lines lines.shp \
  --output result.gpkg \
  --config config.yaml
```

### 3. 结果后处理

```python
import geopandas as gpd
import pandas as pd

# 加载结果
results = gpd.read_file('associations.gpkg')

# 统计分析
stats = results.groupby('point_id').agg({
    'distance': ['min', 'max', 'mean', 'count']
}).reset_index()

# 保存统计结果
stats.to_csv('association_statistics.csv')
```

## ❓ 常见问题

### Q: 安装时出现依赖冲突怎么办？

```bash
# 使用虚拟环境
python -m venv fresh_env
source fresh_env/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Q: 大数据集处理内存不足？

```bash
# 使用分块处理
gis-association process \
  --input-points large_dataset.shp \
  --input-lines network.shp \
  --output result.gpkg \
  --chunk-size 500 \
  --memory-limit 2048
```

### Q: 坐标系转换失败？

```bash
# 检查输入数据坐标系
gis-association info --input data.shp --crs-info

# 强制指定源坐标系
gis-association process \
  --input-points data.shp \
  --output transformed.shp \
  --source-crs 4326 \
  --target-crs 3857
```

## 🎉 下一步

恭喜！您已经成功掌握了GIS空间关联分析系统的基本使用方法。

接下来您可以：
- 📖 阅读[详细用户手册](installation.md)
- 🎯 查看[更多使用示例](../user_manual/usage_examples.md)
- 🔧 学习[CLI命令参考](../user_manual/cli_reference.md)
- 👨‍💻 探索[开发者文档](../../developer/)

## 📞 获取帮助

- 📧 邮箱支持: support@gis-association.com
- 🐛 问题反馈: [GitHub Issues](https://github.com/your-repo/gis-spatial-association-system/issues)
- 💬 社区讨论: [GitHub Discussions](https://github.com/your-repo/gis-spatial-association-system/discussions)

---

**祝您使用愉快！🗺️**