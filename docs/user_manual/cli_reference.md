# 🔧 CLI命令参考

本文档详细介绍了GIS空间关联分析系统的所有命令行接口（CLI）命令、参数和用法。

## 📋 命令概览

```bash
gis-association [OPTIONS] COMMAND [ARGS]...

主要命令:
  process      执行空间关联分析处理
  validate     数据验证和修复
  info         查看系统信息和数据统计
  config       配置管理
  interactive  启动交互式操作模式
  --version    显示版本信息
  --help       显示帮助信息
```

## 🌟 全局选项

适用于所有命令的全局参数：

| 参数 | 简写 | 类型 | 默认值 | 描述 |
|------|------|------|--------|------|
| `--version` | `-v` | flag | False | 显示版本信息 |
| `--config` | `-c` | path | None | 指定配置文件路径 |
| `--verbose` | | flag | False | 详细输出模式 |
| `--quiet` | `-q` | flag | False | 静默模式 |
| `--language` | | choice | zh | 界面语言 (zh/en) |

### 示例
```bash
# 显示版本信息
gis-association --version

# 使用指定配置文件
gis-association --config /path/to/config.yaml process ...

# 详细输出模式
gis-association --verbose process ...

# 静默模式
gis-association --quiet process ...

# 英文界面
gis-association --language en process ...
```

## 🚀 process命令

执行空间关联分析处理的核心命令。

### 基础语法
```bash
gis-association process [OPTIONS]
```

### 输入数据选项

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `--input-points` | path | 条件必需 | 点要素输入文件路径 |
| `--input-lines` | path | 条件必需 | 线要素输入文件路径 |
| `--input-polygons` | path | 条件必需 | 面要素输入文件路径 |
| `--second-input-points` | path | 可选 | 第二个点要素输入文件 |
| `--second-input-lines` | path | 可选 | 第二个线要素输入文件 |

**注意**: 必须提供至少一个输入文件，具体取决于分析类型。

### 输出选项

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `--output` | path | None | 输出文件路径（必需） |
| `--output-format` | choice | gpkg | 输出格式 (shp/gpkg/geojson/csv) |
| `--output-encoding` | string | utf-8 | 输出文件编码 |
| `--precision` | integer | 6 | 坐标精度（小数位数） |

### 分析类型选项

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `--operation` | choice | association | 分析类型 (association/intersection/containment) |
| `--max-distance` | float | 1000.0 | 最大关联距离（米） |
| `--tolerance` | float | 0.0 | 容差值（米） |

### 性能选项

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `--parallel` | flag | False | 启用并行处理 |
| `--workers` | integer | 4 | 并行工作进程数 |
| `--chunk-size` | integer | 1000 | 分块处理大小 |
| `--memory-limit` | integer | 4096 | 内存限制（MB） |

### 过滤选项

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `--point-filter` | string | None | 点要素过滤表达式 |
| `--line-filter` | string | None | 线要素过滤表达式 |
| `--polygon-filter` | string | None | 面要素过滤表达式 |

### 坐标转换选项

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `--source-crs` | string | auto | 源坐标系EPSG代码 |
| `--target-crs` | string | auto | 目标坐标系EPSG代码 |
| `--transform-crs` | string | None | 转换坐标系EPSG代码 |

### 缓冲区选项

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `--buffer-distance` | float | 0.0 | 缓冲区距离（米） |
| `--buffer-segments` | integer | 16 | 缓冲区分段数 |

## 📝 使用示例

### 1. 点-线关联分析
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
  --parallel \
  --workers 8 \
  --output-format geojson
```

### 2. 线-线相交检测
```bash
# 相交检测
gis-association process \
  --input-lines water_network.shp \
  --second-input-lines road_network.shp \
  --output intersections.gpkg \
  --operation intersection \
  --tolerance 1.0

# 大数据集处理
gis-association process \
  --input-lines network.shp \
  --second-input-lines network.shp \
  --output network_intersections.gpkg \
  --operation intersection \
  --parallel \
  --chunk-size 5000 \
  --memory-limit 8192
```

### 3. 线-面包含分析
```bash
# 包含关系分析
gis-association process \
  --input-lines pipelines.shp \
  --input-polygons protection_zones.shp \
  --output pipeline_zone_relations.gpkg \
  --operation containment \
  --buffer-distance 10

# 坐标转换 + 包含分析
gis-association process \
  --input-lines pipelines_wgs84.shp \
  --input-polygons zones_cgs2000.shp \
  --output pipeline_zone_relations.gpkg \
  --operation containment \
  --source-crs 4326 \
  --target-crs 4496
```

### 4. 数据过滤和筛选
```bash
# 属性过滤
gis-association process \
  --input-points points.shp \
  --input-lines lines.shp \
  --output filtered_associations.gpkg \
  --point-filter "type='station' AND status='active'" \
  --line-filter "class='highway' AND surface='paved'"

# 空间过滤（通过缓冲区）
gis-association process \
  --input-points points.shp \
  --input-lines lines.shp \
  --output buffered_associations.gpkg \
  --buffer-distance 1000
```

### 5. 性能优化
```bash
# 大数据集并行处理
gis-association process \
  --input-points large_dataset.shp \
  --input-lines network.shp \
  --output result.gpkg \
  --parallel \
  --workers 12 \
  --chunk-size 2000 \
  --memory-limit 16384

# 内存限制模式
gis-association process \
  --input-points huge_dataset.shp \
  --input-lines network.shp \
  --output result.gpkg \
  --chunk-size 100 \
  --memory-limit 2048
```

## ✅ validate命令

数据验证和修复命令。

### 基础语法
```bash
gis-association validate [OPTIONS] INPUT_PATH
```

### 参数选项

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `INPUT_PATH` | path | 必需 | 输入数据文件路径 |
| `--output-path` | path | None | 验证报告输出路径 |
| `--check-geometry` | flag | True | 检查几何有效性 |
| `--check-attributes` | flag | True | 检查属性完整性 |
| `--check-crs` | flag | True | 检查坐标系统 |
| `--repair` | flag | False | 自动修复发现问题 |
| `--output-repaired` | path | None | 修复后数据输出路径 |

### 使用示例
```bash
# 基础验证
gis-association validate dataset.shp

# 全面验证
gis-association validate \
  dataset.shp \
  --output-path validation_report.json \
  --check-geometry \
  --check-attributes \
  --check-crs

# 验证并自动修复
gis-association validate \
  dataset.shp \
  --output-path validation_report.json \
  --repair \
  --output-repaired repaired_dataset.shp
```

## ℹ️ info命令

查看系统信息和数据统计。

### 基础语法
```bash
gis-association info [OPTIONS]
```

### 参数选项

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `--input` | path | None | 输入文件路径（可选） |
| `--stats` | flag | False | 显示详细统计信息 |
| `--crs-info` | flag | False | 显示坐标系统信息 |
| `--schema` | flag | False | 显示数据结构信息 |

### 使用示例
```bash
# 显示系统信息
gis-association info

# 显示数据统计
gis-association info --input dataset.shp --stats

# 显示坐标系信息
gis-association info --input dataset.shp --crs-info

# 显示数据结构
gis-association info --input dataset.shp --schema

# 显示全部信息
gis-association info --input dataset.shp --stats --crs-info --schema
```

## ⚙️ config命令

配置管理命令。

### 基础语法
```bash
gis-association config [OPTIONS] COMMAND [ARGS]...
```

### 子命令

#### show - 显示当前配置
```bash
gis-association config show
```

#### init - 初始化配置文件
```bash
gis-association config init [--path PATH]
```

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `--path` | path | ~/.gis_association/config.yaml | 配置文件路径 |

#### validate - 验证配置文件
```bash
gis-association config validate [--path PATH]
```

#### set - 设置配置项
```bash
gis-association config set KEY VALUE [--path PATH]
```

#### get - 获取配置项
```bash
gis-association config get KEY [--path PATH]
```

### 使用示例
```bash
# 显示当前配置
gis-association config show

# 初始化配置文件
gis-association config init --path ./my_config.yaml

# 设置配置项
gis-association config set analysis.max_distance 2000
gis-association config set parallel.workers 8

# 获取配置项
gis-association config get analysis.max_distance

# 验证配置文件
gis-association config validate
```

## 🎮 interactive命令

启动交互式操作模式。

### 基础语法
```bash
gis-association interactive [OPTIONS]
```

### 参数选项

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `--mode` | choice | batch | 操作模式 (batch/interactive) |

### 使用示例
```bash
# 启动交互式模式
gis-association interactive

# 启动批处理模式
gis-association interactive --mode batch
```

## 📄 输出格式说明

### GeoPackage (.gpkg)
- 默认输出格式
- 支持多图层
- 文件大小适中
- 完整保留属性信息

### Shapefile (.shp)
- 传统格式
- 兼容性好
- 字段名长度限制（10字符）
- 单文件系列

### GeoJSON (.json/.geojson)
- Web友好格式
- 人类可读
- 支持复杂几何
- 文件较大

### CSV (.csv)
- 表格格式
- Excel兼容
- 仅包含属性和坐标
- 不包含几何对象

## 🔧 配置文件格式

### YAML配置示例
```yaml
# 分析配置
analysis:
  max_distance: 1000.0
  tolerance: 0.0
  operation: association
  buffer_distance: 0.0

# 性能配置
parallel:
  enabled: true
  workers: 4
  chunk_size: 1000
  memory_limit: 4096

# 输出配置
output:
  format: gpkg
  encoding: utf-8
  precision: 6
  path: ./results

# 验证配置
validation:
  check_geometry: true
  check_attributes: true
  check_crs: true
  auto_repair: false

# 坐标系统配置
coordinate_system:
  source_crs: auto
  target_crs: auto
  transform_crs: null

# 过滤配置
filters:
  point_filter: null
  line_filter: null
  polygon_filter: null

# 日志配置
logging:
  level: INFO
  file: gis_association.log
  console: true
```

## 🚨 错误代码

| 代码 | 含义 | 解决方案 |
|------|------|----------|
| 0 | 成功 | - |
| 1 | 一般错误 | 检查命令和参数 |
| 2 | 文件不存在 | 确认文件路径正确 |
| 3 | 权限错误 | 检查文件读写权限 |
| 4 | 格式不支持 | 使用支持的格式 |
| 5 | 内存不足 | 增加内存或使用分块处理 |
| 6 | 依赖缺失 | 安装缺失的依赖包 |
| 7 | 配置错误 | 检查配置文件格式 |
| 8 | 网络错误 | 检查网络连接 |
| 130 | 用户中断 | 用户取消操作 |

## 💡 使用技巧

### 1. 命令行补全
```bash
# 启用bash补全（Linux/macOS）
eval "$(_GIS_ASSOCIATION_COMPLETE=bash_source gis-association)"

# 启用zsh补全
eval "$(_GIS_ASSOCIATION_COMPLETE=zsh_source gis-association)"
```

### 2. 批处理脚本
```bash
#!/bin/bash
# 批量处理脚本示例

INPUT_DIR="./input"
OUTPUT_DIR="./output"

for file in "$INPUT_DIR"/*.shp; do
    filename=$(basename "$file" .shp)
    echo "处理文件: $filename"

    gis-association process \
        --input-points "$file" \
        --input-lines "$INPUT_DIR/network.shp" \
        --output "$OUTPUT_DIR/${filename}_associations.gpkg" \
        --parallel \
        --workers 4

    echo "完成: $filename"
done
```

### 3. 配置文件使用
```bash
# 使用配置文件
gis-association --config my_config.yaml process \
    --input-points data.shp \
    --input-lines network.shp \
    --output result.gpkg
```

### 4. 管道操作
```bash
# 结合其他命令使用
gis-association info --input data.shp --stats | grep "total_features"
```

## 🔍 故障排除

### 常见问题

1. **命令未找到**
   ```bash
   # 检查安装
   pip show gis-spatial-association

   # 重新安装
   pip install -e .
   ```

2. **依赖缺失**
   ```bash
   # 安装依赖
   pip install -r requirements.txt

   # 检查依赖
   pip check
   ```

3. **权限错误**
   ```bash
   # 检查文件权限
   ls -la data.shp

   # 修改权限
   chmod 644 data.shp
   ```

4. **内存不足**
   ```bash
   # 减少并行度
   gis-association process ... --workers 2 --chunk-size 100

   # 增加虚拟内存（Linux）
   sudo swapon -s
   sudo fallocate -l 2G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

## 📞 获取帮助

- **在线帮助**: `gis-association COMMAND --help`
- **版本信息**: `gis-association --version`
- **配置帮助**: `gis-association config --help`
- **技术支持**: support@gis-association.com
- **问题报告**: [GitHub Issues](https://github.com/your-repo/gis-spatial-association-system/issues)

---

**掌握这些命令将让您充分发挥GIS空间关联分析系统的强大功能！🚀**