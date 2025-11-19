# 📦 安装指南

本指南将详细介绍如何在各种操作系统上安装和配置GIS空间关联分析系统。

## 📋 系统要求

### 最低要求
- **操作系统**: Windows 10, Linux (Ubuntu 18.04+), macOS 10.14+
- **Python**: 3.8 或更高版本
- **内存**: 2GB RAM
- **存储**: 1GB 可用磁盘空间
- **网络**: 用于下载依赖包（可选）

### 推荐配置
- **操作系统**: Windows 11, Ubuntu 20.04+, macOS 12+
- **Python**: 3.9-3.11
- **内存**: 8GB+ RAM
- **存储**: 5GB+ 可用磁盘空间
- **CPU**: 4核心+处理器（用于并行计算）

### 支持的Python版本
| Python版本 | 支持状态 | 推荐程度 |
|-----------|---------|---------|
| 3.8 | ✅ 完全支持 | ⭐⭐⭐ |
| 3.9 | ✅ 完全支持 | ⭐⭐⭐⭐ |
| 3.10 | ✅ 完全支持 | ⭐⭐⭐⭐⭐ |
| 3.11 | ✅ 完全支持 | ⭐⭐⭐⭐ |
| 3.12 | 🚧 测试中 | ⭐⭐ |

## 🔧 安装方式

### 方式一：标准安装（推荐）

#### 第一步：安装Python

**Windows:**
1. 访问 [Python官网](https://www.python.org/downloads/)
2. 下载Python 3.9-3.11版本
3. 安装时勾选"Add Python to PATH"
4. 验证安装：
```cmd
python --version
pip --version
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3.9 python3.9-pip python3.9-venv
python3.9 --version
pip3.9 --version
```

**macOS:**
```bash
# 使用Homebrew
brew install python@3.9
python3.9 --version
pip3.9 --version

# 或从官网下载安装包
```

#### 第二步：创建虚拟环境（强烈推荐）

```bash
# 创建虚拟环境
python -m venv gis_association_env

# 激活虚拟环境
# Windows
gis_association_env\Scripts\activate
# Linux/macOS
source gis_association_env/bin/activate

# 升级pip
pip install --upgrade pip
```

#### 第三步：下载并安装项目

```bash
# 克隆项目
git clone https://github.com/your-repo/gis-spatial-association-system.git
cd gis-spatial-association-system

# 安装项目依赖
pip install -r requirements.txt

# 安装项目（开发模式）
pip install -e .

# 验证安装
gis-association --version
```

### 方式二：Conda安装

```bash
# 创建Conda环境
conda create -n gis_association python=3.9
conda activate gis_association

# 安装基础依赖
conda install -c conda-forge geopandas shapely rtree pyproj

# 安装项目
git clone https://github.com/your-repo/gis-spatial-association-system.git
cd gis-spatial-association-system
pip install -e .

# 验证安装
gis-association --version
```

### 方式三：Docker安装

```bash
# 拉取Docker镜像
docker pull gis-association:latest

# 运行容器
docker run -it --rm \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/output:/app/output \
  gis-association:latest

# 或使用docker-compose
docker-compose up -d
```

## 📦 依赖包说明

### 核心依赖

| 包名 | 版本要求 | 用途 |
|------|---------|------|
| geopandas | >=0.12.0 | 地理空间数据处理 |
| shapely | >=1.8.0 | 几何对象操作 |
| rtree | >=1.0.0 | 空间索引 |
| pyproj | >=3.3.0 | 坐标系转换 |
| pandas | >=1.4.0 | 数据处理 |
| numpy | >=1.21.0 | 数值计算 |
| fiona | >=1.8.0 | 矢量数据IO |
| pyogrio | >=0.5.0 | 地理数据读写 |

### CLI和可视化依赖

| 包名 | 版本要求 | 用途 |
|------|---------|------|
| click | >=8.0.0 | 命令行界面 |
| rich | >=12.0.0 | 终端美化 |
| tqdm | >=4.64.0 | 进度条显示 |
| matplotlib | >=3.5.0 | 基础绘图 |
| seaborn | >=0.11.0 | 统计可视化 |

### 可选依赖

| 包名 | 版本要求 | 用途 | 安装命令 |
|------|---------|------|---------|
| jupyter | >=1.0.0 | 交互式开发 | `pip install gis-association[jupyter]` |
| plotly | >=5.0.0 | 交互式可视化 | `pip install gis-association[plotting]` |
| pytest | >=7.0.0 | 单元测试 | `pip install gis-association[test]` |
| sphinx | >=4.0.0 | 文档生成 | `pip install gis-association[docs]` |

## 🐛 常见安装问题

### 问题1：Python版本不兼容

**症状:**
```
ERROR: Package requires a different Python
```

**解决方案:**
```bash
# 检查Python版本
python --version

# 如果版本过低，升级Python
# Windows: 重新安装新版本Python
# Linux: 使用pyenv管理多版本
curl https://pyenv.run | bash
pyenv install 3.9.16
pyenv global 3.9.16
```

### 问题2：GDAL安装失败

**症状:**
```
ERROR: Could not find a version that satisfies the requirement GDAL
```

**解决方案:**

**Windows:**
```cmd
# 下载预编译的GDAL包
pip install GDAL-3.4.3-cp39-cp39-win_amd64.whl
```

**Linux:**
```bash
# 安装系统依赖
sudo apt install libgdal-dev
sudo apt install gdal-bin
export CPLUS_INCLUDE_PATH=/usr/include/gdal
export C_INCLUDE_PATH=/usr/include/gdal
pip install GDAL
```

**macOS:**
```bash
# 使用Homebrew安装
brew install gdal
pip install GDAL
```

### 问题3：RTree安装失败

**症状:**
```
ERROR: Could not build wheels for rtree
```

**解决方案:**

**Windows:**
```cmd
# 安装Visual Studio Build Tools
# 或下载预编译包
pip install rtree-1.0.0-cp39-cp39-win_amd64.whl
```

**Linux:**
```bash
# 安装libspatialindex
sudo apt install libspatialindex-dev
pip install rtree
```

### 问题4：权限错误

**症状:**
```
ERROR: Could not install packages due to an EnvironmentError
```

**解决方案:**
```bash
# 使用用户安装
pip install --user -e .

# 或使用虚拟环境
python -m venv venv
source venv/bin/activate
pip install -e .
```

## 🔄 升级指南

### 从旧版本升级

```bash
# 1. 备份当前配置
cp ~/.gis_association/config.yaml config_backup.yaml

# 2. 激活虚拟环境
source gis_association_env/bin/activate

# 3. 更新项目
cd gis-spatial-association-system
git pull origin main

# 4. 更新依赖
pip install --upgrade -r requirements.txt

# 5. 重新安装
pip install -e .

# 6. 验证升级
gis-association --version
```

### 依赖包升级

```bash
# 升级所有依赖
pip install --upgrade -r requirements.txt

# 检查包兼容性
pip check

# 如有冲突，逐个解决
pip install --upgrade geopandas
pip install --upgrade shapely
```

## 🧪 验证安装

### 基础功能测试

```bash
# 1. 检查版本和模块状态
gis-association --version

# 2. 运行内置测试
gis-association --test

# 3. 检查配置文件
gis-association config --show

# 4. 运行简单示例
python -c "
from gis_spatial_association import NearestNeighborAssociator
print('✅ 核心模块导入成功')
"
```

### 完整功能测试

```bash
# 1. 创建测试数据
python -c "
import geopandas as gpd
from shapely.geometry import Point, LineString
import pandas as pd

# 创建测试点
points = gpd.GeoDataFrame({
    'id': [1, 2, 3],
    'name': ['A', 'B', 'C'],
    'geometry': [Point(0, 0), Point(1, 1), Point(2, 0)]
})
points.to_file('test_points.shp')

# 创建测试线
lines = gpd.GeoDataFrame({
    'id': [1, 2],
    'name': ['Line1', 'Line2'],
    'geometry': [LineString([(0, -1), (0, 2)]), LineString([(1, 0), (3, 0)])]
})
lines.to_file('test_lines.shp')
"

# 2. 运行关联分析
gis-association process \
  --input-points test_points.shp \
  --input-lines test_lines.shp \
  --output test_result.gpkg

# 3. 检查结果
python -c "
import geopandas as gpd
result = gpd.read_file('test_result.gpkg')
print(f'✅ 找到 {len(result)} 个关联关系')
"
```

## 🔧 配置优化

### 环境变量配置

```bash
# 添加到 ~/.bashrc 或 ~/.zshrc
export GIS_ASSOCIATION_CONFIG_PATH=/path/to/config
export GIS_ASSOCIATION_CACHE_DIR=/path/to/cache
export GIS_ASSOCIATION_LOG_LEVEL=INFO
export GIS_ASSOCIATION_MAX_WORKERS=4

# 重新加载配置
source ~/.bashrc
```

### 性能优化设置

```bash
# 设置numpy线程数
export OMP_NUM_THREADS=4

# 设置GDAL缓存
export GDAL_CACHE_MAX=512

# 设置并行处理
export OPENBLAS_NUM_THREADS=4
```

## 📱 IDE集成

### VS Code配置

```json
// .vscode/settings.json
{
    "python.defaultInterpreterPath": "./gis_association_env/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "black",
    "jupyter.jupyterServerType": "local"
}
```

### PyCharm配置

1. 设置Python解释器指向虚拟环境
2. 安装GeoPandas插件
3. 配置代码样式为Black
4. 启用科学计算模式

## 🎯 下一步

安装完成后，您可以：

- 📖 阅读[快速开始指南](quick_start.md)
- 🎯 查看[使用示例](usage_examples.md)
- 🔧 学习[CLI命令参考](cli_reference.md)
- 🐛 了解[故障排除](troubleshooting.md)

## 📞 获取帮助

如果在安装过程中遇到问题：

- 📧 技术支持: support@gis-association.com
- 🐛 Bug报告: [GitHub Issues](https://github.com/your-repo/gis-spatial-association-system/issues)
- 💬 社区讨论: [GitHub Discussions](https://github.com/your-repo/gis-spatial-association-system/discussions)
- 📖 详细文档: [在线文档](https://gis-association.readthedocs.io/)

---

**安装成功后，祝您使用愉快！🎉**