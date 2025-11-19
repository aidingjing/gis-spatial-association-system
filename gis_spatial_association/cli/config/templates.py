"""
配置模板

提供各种预定义的配置模板：
- 默认配置模板
- 性能优化配置模板
- 验证配置模板
- 开发配置模板
- 生产配置模板
"""

from typing import Dict, Any

# 默认配置模板
DEFAULT_CONFIG = {
    "processing": {
        "max_neighbors": 1,
        "distance_threshold": 1000.0,
        "parallel": True,
        "chunk_size": 10000,
        "memory_limit": 2048,  # MB
        "coordinate_system": "EPSG:4326"
    },
    "validation": {
        "strict_mode": False,
        "auto_repair": True,
        "geometry_tolerance": 0.001,
        "attribute_checks": True,
        "coordinate_system_validation": True,
        "topology_validation": False
    },
    "output": {
        "default_format": "geojson",
        "compression": False,
        "precision": 6,
        "encoding": "utf-8",
        "include_metadata": True
    },
    "logging": {
        "level": "INFO",
        "file": "gis_association.log",
        "console": True,
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "max_size": "10MB",
        "backup_count": 5
    },
    "performance": {
        "enable_caching": True,
        "cache_size": 1000,
        "enable_indexing": True,
        "spatial_index": "rtree",
        "batch_processing": True,
        "memory_optimization": True
    },
    "ui": {
        "language": "zh",
        "progress_bar": True,
        "color_output": True,
        "verbose_errors": False,
        "auto_save_config": True
    }
}

# 性能优化配置模板
PERFORMANCE_CONFIG = {
    "processing": {
        "max_neighbors": 5,
        "distance_threshold": 500.0,
        "parallel": True,
        "chunk_size": 50000,
        "memory_limit": 4096,  # MB
        "coordinate_system": "EPSG:3857",
        "num_workers": -1,  # 使用所有CPU核心
        "enable_streaming": True
    },
    "validation": {
        "strict_mode": False,
        "auto_repair": False,  # 性能优先，不自动修复
        "geometry_tolerance": 0.01,
        "attribute_checks": False,
        "coordinate_system_validation": True,
        "topology_validation": False
    },
    "output": {
        "default_format": "gpkg",  # 更高效的格式
        "compression": True,
        "precision": 4,  # 降低精度以提高性能
        "encoding": "utf-8",
        "include_metadata": False  # 减少元数据
    },
    "logging": {
        "level": "WARNING",  # 减少日志输出
        "file": "gis_association.log",
        "console": False,
        "format": "%(levelname)s - %(message)s",
        "max_size": "50MB",
        "backup_count": 3
    },
    "performance": {
        "enable_caching": True,
        "cache_size": 10000,
        "enable_indexing": True,
        "spatial_index": "rtree",
        "batch_processing": True,
        "memory_optimization": True,
        "lazy_loading": True,
        "prefetch_size": 1000
    },
    "ui": {
        "language": "zh",
        "progress_bar": True,
        "color_output": False,  # 减少ANSI处理
        "verbose_errors": False,
        "auto_save_config": False
    }
}

# 验证配置模板
VALIDATION_CONFIG = {
    "processing": {
        "max_neighbors": 1,
        "distance_threshold": 1000.0,
        "parallel": False,  # 单线程以便调试
        "chunk_size": 1000,
        "memory_limit": 1024,
        "coordinate_system": "EPSG:4326"
    },
    "validation": {
        "strict_mode": True,  # 严格模式
        "auto_repair": True,
        "geometry_tolerance": 0.0001,  # 高精度
        "attribute_checks": True,
        "coordinate_system_validation": True,
        "topology_validation": True,
        "duplicate_check": True,
        "consistency_check": True
    },
    "output": {
        "default_format": "geojson",
        "compression": False,
        "precision": 10,  # 高精度
        "encoding": "utf-8",
        "include_metadata": True,
        "include_validation_report": True
    },
    "logging": {
        "level": "DEBUG",  # 详细日志
        "file": "gis_association_validation.log",
        "console": True,
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
        "max_size": "100MB",
        "backup_count": 10
    },
    "performance": {
        "enable_caching": False,  # 验证时禁用缓存
        "cache_size": 100,
        "enable_indexing": True,
        "spatial_index": "rtree",
        "batch_processing": False,  # 逐个处理
        "memory_optimization": True
    },
    "ui": {
        "language": "zh",
        "progress_bar": True,
        "color_output": True,
        "verbose_errors": True,  # 详细错误信息
        "auto_save_config": True,
        "show_validation_details": True
    }
}

# 开发配置模板
DEVELOPMENT_CONFIG = {
    "processing": {
        "max_neighbors": 1,
        "distance_threshold": 1000.0,
        "parallel": False,
        "chunk_size": 100,
        "memory_limit": 512,
        "coordinate_system": "EPSG:4326",
        "debug_mode": True
    },
    "validation": {
        "strict_mode": True,
        "auto_repair": True,
        "geometry_tolerance": 0.001,
        "attribute_checks": True,
        "coordinate_system_validation": True,
        "topology_validation": True
    },
    "output": {
        "default_format": "geojson",
        "compression": False,
        "precision": 6,
        "encoding": "utf-8",
        "include_metadata": True,
        "pretty_print": True
    },
    "logging": {
        "level": "DEBUG",
        "file": "gis_association_dev.log",
        "console": True,
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
        "max_size": "10MB",
        "backup_count": 5
    },
    "performance": {
        "enable_caching": False,
        "cache_size": 10,
        "enable_indexing": False,
        "batch_processing": False,
        "memory_optimization": False
    },
    "ui": {
        "language": "zh",
        "progress_bar": True,
        "color_output": True,
        "verbose_errors": True,
        "auto_save_config": True,
        "interactive_mode": True
    },
    "development": {
        "reload_on_change": True,
        "profiling": True,
        "benchmarking": True,
        "test_mode": True
    }
}

# 生产配置模板
PRODUCTION_CONFIG = {
    "processing": {
        "max_neighbors": 3,
        "distance_threshold": 500.0,
        "parallel": True,
        "chunk_size": 100000,
        "memory_limit": 8192,  # 8GB
        "coordinate_system": "EPSG:3857",
        "num_workers": 0,  # 自动检测
        "enable_streaming": True,
        "error_handling": "skip"
    },
    "validation": {
        "strict_mode": False,
        "auto_repair": False,
        "geometry_tolerance": 0.01,
        "attribute_checks": True,
        "coordinate_system_validation": True,
        "topology_validation": False
    },
    "output": {
        "default_format": "gpkg",
        "compression": True,
        "precision": 4,
        "encoding": "utf-8",
        "include_metadata": False,
        "batch_output": True
    },
    "logging": {
        "level": "INFO",
        "file": "/var/log/gis_association/production.log",
        "console": False,
        "format": "%(asctime)s - %(levelname)s - %(message)s",
        "max_size": "100MB",
        "backup_count": 20,
        "syslog": True
    },
    "performance": {
        "enable_caching": True,
        "cache_size": 50000,
        "enable_indexing": True,
        "spatial_index": "rtree",
        "batch_processing": True,
        "memory_optimization": True,
        "lazy_loading": True,
        "connection_pooling": True
    },
    "ui": {
        "language": "zh",
        "progress_bar": False,  # 非交互式环境
        "color_output": False,
        "verbose_errors": False,
        "auto_save_config": False,
        "silent_mode": True
    },
    "production": {
        "monitoring": True,
        "alerting": True,
        "backup_config": True,
        "health_checks": True
    }
}

# 配置模板集合
CONFIG_TEMPLATE = {
    'default': DEFAULT_CONFIG,
    'performance': PERFORMANCE_CONFIG,
    'validation': VALIDATION_CONFIG,
    'development': DEVELOPMENT_CONFIG,
    'production': PRODUCTION_CONFIG
}

# 配置描述
CONFIG_DESCRIPTIONS = {
    'default': {
        'name': '默认配置',
        'description': '适用于大多数使用场景的平衡配置',
        'use_case': '一般用途和入门用户'
    },
    'performance': {
        'name': '性能优化配置',
        'description': '针对大数据集和高性能需求优化的配置',
        'use_case': '处理大型数据集，追求处理速度'
    },
    'validation': {
        'name': '验证配置',
        'description': '严格的数据验证和质量检查配置',
        'use_case': '数据质量要求高的科研和工程项目'
    },
    'development': {
        'name': '开发配置',
        'description': '适用于开发和调试环境的配置',
        'use_case': '软件开发和功能测试'
    },
    'production': {
        'name': '生产配置',
        'description': '适用于生产环境的高稳定性配置',
        'use_case': '生产部署和自动化处理'
    }
}


def get_template_names() -> list:
    """获取所有可用模板名称"""
    return list(CONFIG_TEMPLATE.keys())


def get_template_info(template_name: str) -> Dict[str, Any]:
    """
    获取模板信息

    Args:
        template_name: 模板名称

    Returns:
        模板信息字典
    """
    if template_name not in CONFIG_TEMPLATE:
        raise ValueError(f"未知的配置模板: {template_name}")

    info = CONFIG_DESCRIPTIONS.get(template_name, {
        'name': template_name,
        'description': '自定义配置模板',
        'use_case': '特定用途'
    })

    info['config'] = CONFIG_TEMPLATE[template_name]
    return info


def list_templates() -> Dict[str, Dict[str, str]]:
    """列出所有可用模板及其描述"""
    return CONFIG_DESCRIPTIONS


def validate_template(template_name: str) -> bool:
    """
    验证模板是否存在且有效

    Args:
        template_name: 模板名称

    Returns:
        是否有效
    """
    return template_name in CONFIG_TEMPLATE


def get_template_keys(template_name: str) -> Dict[str, list]:
    """
    获取模板的配置键结构

    Args:
        template_name: 模板名称

    Returns:
        配置键结构字典
    """
    if template_name not in CONFIG_TEMPLATE:
        raise ValueError(f"未知的配置模板: {template_name}")

    def get_keys_recursive(config_dict, prefix=""):
        keys = {}
        for key, value in config_dict.items():
            current_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                keys[current_key] = list(value.keys())
                keys.update(get_keys_recursive(value, current_key))
            else:
                keys[current_key] = type(value).__name__
        return keys

    return get_keys_recursive(CONFIG_TEMPLATE[template_name])


def merge_templates(template_names: list) -> Dict[str, Any]:
    """
    合并多个配置模板

    Args:
        template_names: 模板名称列表，后面的模板会覆盖前面的

    Returns:
        合并后的配置
    """
    merged_config = {}

    for template_name in template_names:
        if template_name not in CONFIG_TEMPLATE:
            raise ValueError(f"未知的配置模板: {template_name}")

        def deep_merge(target, source):
            for key, value in source.items():
                if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                    deep_merge(target[key], value)
                else:
                    target[key] = value

        deep_merge(merged_config, CONFIG_TEMPLATE[template_name])

    return merged_config