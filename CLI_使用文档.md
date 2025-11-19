# GIS空间关联分析系统 - CLI用户界面和配置管理

## 🎯 概述

本文档描述了GIS空间关联分析系统的命令行界面(CLI)和配置管理系统，提供了用户友好的地理空间分析操作界面。

## 🚀 功能特性

### 核心功能
- **完整的CLI命令结构**: process, validate, info, config 四大核心命令
- **交互式模式**: 向导式操作流程，降低使用门槛
- **批处理模式**: 支持自动化脚本和批量处理
- **多格式支持**: Shapefile, GeoJSON, GeoPackage, CSV等主流格式
- **实时进度监控**: Rich库美化输出，支持进度条和性能监控

### 配置管理
- **YAML/JSON配置**: 人性化的配置文件格式
- **多种配置模板**: 默认、性能优化、验证、开发、生产环境模板
- **配置验证**: 完整的配置结构和值验证规则
- **环境变量覆盖**: 支持通过环境变量动态配置
- **配置热重载**: 无需重启即可应用新配置

### 用户体验
- **中英文界面**: 支持多语言切换
- **智能默认值**: 根据上下文提供合理的默认配置
- **错误处理**: 友好的错误提示和解决建议
- **帮助系统**: 完整的命令和参数帮助文档

## 📁 文件结构

```
gis_spatial_association/cli/
├── __init__.py                 # CLI模块导出
├── main.py                     # 主CLI入口点
├── commands/                   # 子命令模块
│   ├── __init__.py
│   ├── process.py             # 处理命令 - 空间关联分析
│   ├── validate.py            # 验证命令 - 数据验证
│   ├── info.py                # 信息命令 - 系统信息
│   └── config.py              # 配置命令 - 配置管理
├── ui/                        # 用户界面组件
│   ├── __init__.py
│   ├── progress.py            # 进度监控和显示
│   └── interactive.py         # 交互式操作界面
└── config/                    # 配置管理
    ├── __init__.py
    ├── manager.py             # 配置管理器
    ├── templates.py           # 配置模板
    └── schema.py              # 配置验证规则
```

## 🛠️ 安装和使用

### 基本使用

#### 1. 命令行帮助
```bash
# 查看总体帮助
./gis-association --help

# 查看特定命令帮助
./gis-association process --help
./gis-association validate --help
./gis-association config --help
```

#### 2. 交互式模式
```bash
# 启动交互式向导
./gis-association interactive
```

#### 3. 空间关联分析
```bash
# 点-线最近邻关联分析
./gis-association process points.shp lines.shp -t point-line -o result.geojson

# 线-线相交检测
./gis-association process roads1.shp roads2.shp -t line-line -o intersections.geojson

# 线-面包含判断
./gis-association process rivers.shp basins.shp -t line-polygon -o containment.geojson

# 自动检测分析类型
./gis-association process file1.geojson file2.geojson -o result.shp
```

#### 4. 数据验证
```bash
# 基本验证
./gis-association validate data.shp

# 验证并自动修复
./gis-association validate data.geojson --repair

# 生成验证报告
./gis-association validate data.shp --output report.json --report-format json

# 严格模式验证
./gis-association validate data.shp --strict --repair
```

#### 5. 系统信息查看
```bash
# 系统概览
./gis-association info

# 详细系统信息
./gis-association info --system

# 模块状态
./gis-association info --modules

# 数据文件分析
./gis-association info --data-file data.shp

# 性能基准
./gis-association info --performance
```

#### 6. 配置管理
```bash
# 创建配置文件
./gis-association config create --template default
./gis-association config create --template performance --format json

# 查看配置
./gis-association config show
./gis-association config show --format yaml

# 编辑配置
./gis-association config edit --key "processing.max_neighbors" --value 3

# 验证配置
./gis-association config validate

# 重置配置
./gis-association config reset --local
```

### 高级用法

#### 1. 批处理脚本
```bash
#!/bin/bash
# 批量处理脚本示例

INPUT_DIR="./data"
OUTPUT_DIR="./results"

for file1 in "$INPUT_DIR"/*_points.shp; do
    for file2 in "$INPUT_DIR"/*_lines.shp; do
        basename=$(basename "$file1" _points.shp)
        output="$OUTPUT_DIR/${basename}_result.geojson"

        echo "处理: $file1 + $file2 -> $output"
        ./gis-association process "$file1" "$file2" \
            -t point-line \
            -o "$output" \
            --distance-threshold 500 \
            --max-neighbors 3 \
            --parallel
    done
done
```

#### 2. 环境变量配置
```bash
# 设置环境变量
export GIS_ASSOCIATION_MAX_NEIGHBORS=5
export GIS_ASSOCIATION_DISTANCE_THRESHOLD=1000
export GIS_ASSOCIATION_PARALLEL=true
export GIS_ASSOCIATION_OUTPUT_FORMAT=geojson

# 运行分析（将使用环境变量中的配置）
./gis-association process data1.shp data2.shp -o result.geojson
```

## ⚙️ 配置系统详解

### 配置文件位置
1. **全局配置**: `~/.gis_association/config.yaml`
2. **本地配置**: `./.gis_association_config.yaml`
3. **项目配置**: `./gis_association_config.yaml`

配置优先级：项目配置 > 本地配置 > 全局配置 > 默认配置

### 配置模板类型

#### 默认配置 (default)
适用于大多数使用场景的平衡配置

#### 性能优化配置 (performance)
- 大数据集处理优化
- 并行处理启用
- 内存使用优化
- 缓存和索引加速

#### 验证配置 (validation)
- 严格数据验证
- 详细质量检查
- 高精度几何处理
- 完整验证报告

#### 开发配置 (development)
- 调试友好设置
- 详细日志输出
- 交互式功能启用
- 开发工具集成

#### 生产配置 (production)
- 稳定性和可靠性优先
- 监控和告警配置
- 错误处理优化
- 自动化部署支持

### 配置文件示例

```yaml
# 配置文件示例
processing:
  max_neighbors: 3
  distance_threshold: 1000.0
  parallel: true
  chunk_size: 10000
  memory_limit: 2048
  coordinate_system: "EPSG:4326"

validation:
  strict_mode: false
  auto_repair: true
  geometry_tolerance: 0.001
  attribute_checks: true

output:
  default_format: "geojson"
  compression: false
  precision: 6
  encoding: "utf-8"
  include_metadata: true

logging:
  level: "INFO"
  file: "gis_association.log"
  console: true

performance:
  enable_caching: true
  cache_size: 1000
  enable_indexing: true
  batch_processing: true

ui:
  language: "zh"
  progress_bar: true
  color_output: true
  verbose_errors: false
```

## 🔧 API集成

### Python模块使用

```python
# 导入CLI模块
from gis_spatial_association.cli.main import main
from gis_spatial_association.cli.ui.progress import ProgressMonitor
from gis_spatial_association.cli.config.manager import ConfigManager

# 使用配置管理器
config_manager = ConfigManager()
config_manager.load_config()
config = config_manager.get_config()

# 使用进度监控
with ProgressMonitor() as monitor:
    task_id = monitor.add_task("analysis", "空间分析", total=1000)

    for i in range(1000):
        # 执行分析步骤
        monitor.update_task(task_id, completed=i+1)

    monitor.complete_task(task_id)
```

### 配置管理API

```python
from gis_spatial_association.cli.config.manager import ConfigManager

# 创建配置管理器
config_manager = ConfigManager()

# 加载配置
config_manager.load_config("my_config.yaml")

# 获取配置值
max_neighbors = config_manager.get_value("processing.max_neighbors")
output_format = config_manager.get_value("output.default_format", "geojson")

# 设置配置值
config_manager.set_value("processing.parallel", True)
config_manager.set_value("validation.strict_mode", True)

# 保存配置
config_manager.save_config()

# 创建新配置文件
config_manager.create_default_config("new_config.yaml", "performance")
```

## 🐛 故障排除

### 常见问题

#### 1. 导入错误
```bash
# 问题：No module named 'rich' 或 'psutil'
# 解决：安装可选依赖
pip install rich psutil

# 或者使用基础模式
export GIS_ASSOCIATION_DISABLE_RICH=true
```

#### 2. 配置文件错误
```bash
# 验证配置文件
./gis-association config validate --config my_config.yaml

# 重置为默认配置
./gis-association config reset --local
```

#### 3. 内存不足
```bash
# 使用性能优化配置
./gis-association config create --template performance

# 或减小批处理大小
./gis-association process file1.shp file2.shp --chunk-size 1000
```

#### 4. 坐标系问题
```bash
# 指定目标坐标系
./gis-association process file1.shp file2.shp --coordinate-system "EPSG:3857"
```

### 调试模式

```bash
# 启用详细日志
export GIS_ASSOCIATION_LOG_LEVEL=DEBUG
./gis-association process data.shp --verbose

# 使用开发配置模板
./gis-association config create --template development
```

## 📈 性能优化

### 大数据集处理建议

1. **使用性能配置模板**
```bash
./gis-association config create --template performance
```

2. **启用并行处理**
```bash
./gis-association process data1.shp data2.shp --parallel
```

3. **调整批处理大小**
```bash
./gis-association process data1.shp data2.shp --chunk-size 50000
```

4. **增加内存限制**
```bash
./gis-association config edit --key "processing.memory_limit" --value 8192
```

### 监控和基准测试

```bash
# 查看系统资源状态
./gis-association info --performance

# 监控处理进度
./gis-association process data.shp --verbose
```

## 🤝 贡献和扩展

### 添加新的子命令

1. 在 `gis_spatial_association/cli/commands/` 下创建新文件
2. 继承Click命令结构
3. 在 `main.py` 中注册新命令
4. 添加帮助文档和测试

### 添加配置模板

1. 在 `templates.py` 中定义新模板
2. 在 `schema.py` 中添加验证规则
3. 更新模板描述和文档

### 扩展UI组件

1. 在 `ui/` 目录下添加新组件
2. 继承现有基类
3. 更新配置管理器集成

## 📚 参考资料

- [Click文档](https://click.palletsprojects.com/)
- [Rich库文档](https://rich.readthedocs.io/)
- [GeoPandas文档](https://geopandas.org/)
- [Shapely文档](https://shapely.readthedocs.io/)

---

**版本**: 1.0.0
**作者**: CCPM Auto Development System
**最后更新**: 2024年