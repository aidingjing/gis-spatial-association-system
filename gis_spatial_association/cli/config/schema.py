"""
配置验证规则

定义配置文件的结构和验证规则：
- 配置项类型验证
- 值范围验证
- 依赖关系验证
- 自定义验证函数
"""

import re
from typing import Dict, Any, List, Union, Callable, Optional
import logging

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """配置验证错误"""
    pass


class ConfigValidator:
    """配置验证器"""

    def __init__(self):
        self.validation_rules = self._get_validation_rules()
        self.custom_validators = {}

    def _get_validation_rules(self) -> Dict[str, Any]:
        """获取验证规则定义"""
        return {
            "processing": {
                "type": dict,
                "required": True,
                "fields": {
                    "max_neighbors": {
                        "type": int,
                        "required": True,
                        "min_value": 1,
                        "max_value": 100,
                        "description": "最大邻居数量"
                    },
                    "distance_threshold": {
                        "type": (int, float),
                        "required": True,
                        "min_value": 0,
                        "max_value": 1000000,
                        "description": "距离阈值(米)"
                    },
                    "parallel": {
                        "type": bool,
                        "required": False,
                        "default": True,
                        "description": "是否启用并行处理"
                    },
                    "chunk_size": {
                        "type": int,
                        "required": False,
                        "min_value": 1,
                        "max_value": 1000000,
                        "default": 10000,
                        "description": "批处理块大小"
                    },
                    "memory_limit": {
                        "type": int,
                        "required": False,
                        "min_value": 64,
                        "max_value": 65536,
                        "default": 2048,
                        "description": "内存限制(MB)"
                    },
                    "coordinate_system": {
                        "type": str,
                        "required": False,
                        "pattern": r'^EPSG:\d+$',
                        "default": "EPSG:4326",
                        "description": "坐标系(如EPSG:4326)"
                    },
                    "num_workers": {
                        "type": int,
                        "required": False,
                        "min_value": -1,
                        "max_value": 64,
                        "default": -1,
                        "description": "工作进程数(-1为自动)"
                    }
                }
            },
            "validation": {
                "type": dict,
                "required": True,
                "fields": {
                    "strict_mode": {
                        "type": bool,
                        "required": False,
                        "default": False,
                        "description": "严格模式"
                    },
                    "auto_repair": {
                        "type": bool,
                        "required": False,
                        "default": True,
                        "description": "自动修复"
                    },
                    "geometry_tolerance": {
                        "type": (int, float),
                        "required": False,
                        "min_value": 0,
                        "max_value": 1,
                        "default": 0.001,
                        "description": "几何容差"
                    },
                    "attribute_checks": {
                        "type": bool,
                        "required": False,
                        "default": True,
                        "description": "属性检查"
                    },
                    "coordinate_system_validation": {
                        "type": bool,
                        "required": False,
                        "default": True,
                        "description": "坐标系验证"
                    },
                    "topology_validation": {
                        "type": bool,
                        "required": False,
                        "default": False,
                        "description": "拓扑验证"
                    }
                }
            },
            "output": {
                "type": dict,
                "required": True,
                "fields": {
                    "default_format": {
                        "type": str,
                        "required": False,
                        "choices": ["shp", "geojson", "gpkg", "csv", "kml"],
                        "default": "geojson",
                        "description": "默认输出格式"
                    },
                    "compression": {
                        "type": bool,
                        "required": False,
                        "default": False,
                        "description": "是否压缩输出"
                    },
                    "precision": {
                        "type": int,
                        "required": False,
                        "min_value": 0,
                        "max_value": 15,
                        "default": 6,
                        "description": "坐标精度"
                    },
                    "encoding": {
                        "type": str,
                        "required": False,
                        "default": "utf-8",
                        "description": "文件编码"
                    },
                    "include_metadata": {
                        "type": bool,
                        "required": False,
                        "default": True,
                        "description": "是否包含元数据"
                    }
                }
            },
            "logging": {
                "type": dict,
                "required": False,
                "fields": {
                    "level": {
                        "type": str,
                        "required": False,
                        "choices": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        "default": "INFO",
                        "description": "日志级别"
                    },
                    "file": {
                        "type": str,
                        "required": False,
                        "default": "gis_association.log",
                        "description": "日志文件路径"
                    },
                    "console": {
                        "type": bool,
                        "required": False,
                        "default": True,
                        "description": "是否输出到控制台"
                    },
                    "format": {
                        "type": str,
                        "required": False,
                        "default": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                        "description": "日志格式"
                    },
                    "max_size": {
                        "type": str,
                        "required": False,
                        "pattern": r'^\d+[KMGT]?B$',
                        "default": "10MB",
                        "description": "日志文件最大大小"
                    }
                }
            },
            "performance": {
                "type": dict,
                "required": False,
                "fields": {
                    "enable_caching": {
                        "type": bool,
                        "required": False,
                        "default": True,
                        "description": "启用缓存"
                    },
                    "cache_size": {
                        "type": int,
                        "required": False,
                        "min_value": 1,
                        "max_value": 100000,
                        "default": 1000,
                        "description": "缓存大小"
                    },
                    "enable_indexing": {
                        "type": bool,
                        "required": False,
                        "default": True,
                        "description": "启用空间索引"
                    },
                    "spatial_index": {
                        "type": str,
                        "required": False,
                        "choices": ["rtree", "quadtree", "kdtree"],
                        "default": "rtree",
                        "description": "空间索引类型"
                    },
                    "batch_processing": {
                        "type": bool,
                        "required": False,
                        "default": True,
                        "description": "批处理模式"
                    }
                }
            },
            "ui": {
                "type": dict,
                "required": False,
                "fields": {
                    "language": {
                        "type": str,
                        "required": False,
                        "choices": ["zh", "en"],
                        "default": "zh",
                        "description": "界面语言"
                    },
                    "progress_bar": {
                        "type": bool,
                        "required": False,
                        "default": True,
                        "description": "显示进度条"
                    },
                    "color_output": {
                        "type": bool,
                        "required": False,
                        "default": True,
                        "description": "彩色输出"
                    },
                    "verbose_errors": {
                        "type": bool,
                        "required": False,
                        "default": False,
                        "description": "详细错误信息"
                    }
                }
            }
        }

    def validate(self, config: Dict[str, Any]) -> List[str]:
        """
        验证配置

        Args:
            config: 配置字典

        Returns:
            验证错误列表，空列表表示验证通过
        """
        errors = []

        try:
            self._validate_section(config, "", self.validation_rules)
        except ValidationError as e:
            errors.append(str(e))

        # 自定义验证
        for validator_name, validator_func in self.custom_validators.items():
            try:
                validator_func(config)
            except ValidationError as e:
                errors.append(f"自定义验证({validator_name}): {str(e)}")

        return errors

    def _validate_section(self, config: Dict[str, Any], path: str, rules: Dict[str, Any]):
        """验证配置节"""
        for key, rule in rules.items():
            current_path = f"{path}.{key}" if path else key

            if key == "fields":
                # 处理字段规则
                self._validate_fields(config, path, rule)
                continue

            if key not in config:
                if rule.get("required", False):
                    raise ValidationError(f"缺少必需的配置项: {current_path}")
                continue

            value = config[key]

            # 类型验证
            expected_type = rule.get("type")
            if expected_type and not isinstance(value, expected_type):
                if isinstance(expected_type, tuple):
                    type_names = [t.__name__ for t in expected_type]
                    raise ValidationError(
                        f"{current_path}: 类型错误，期望 {' 或 '.join(type_names)}，实际 {type(value).__name__}"
                    )
                else:
                    raise ValidationError(
                        f"{current_path}: 类型错误，期望 {expected_type.__name__}，实际 {type(value).__name__}"
                    )

            # 值验证
            if isinstance(value, (int, float)):
                min_val = rule.get("min_value")
                max_val = rule.get("max_value")
                if min_val is not None and value < min_val:
                    raise ValidationError(f"{current_path}: 值 {value} 小于最小值 {min_val}")
                if max_val is not None and value > max_val:
                    raise ValidationError(f"{current_path}: 值 {value} 大于最大值 {max_val}")

            # 选择项验证
            choices = rule.get("choices")
            if choices and value not in choices:
                raise ValidationError(f"{current_path}: 无效值 '{value}'，可选值: {choices}")

            # 正则表达式验证
            pattern = rule.get("pattern")
            if pattern and isinstance(value, str):
                if not re.match(pattern, value):
                    raise ValidationError(f"{current_path}: 值 '{value}' 不匹配模式 '{pattern}'")

            # 递归验证嵌套字典
            if isinstance(value, dict) and isinstance(rule, dict):
                self._validate_section(value, current_path, rule)

    def _validate_fields(self, config: Dict[str, Any], path: str, field_rules: Dict[str, Any]):
        """验证字段配置"""
        for field_name, field_rule in field_rules.items():
            current_path = f"{path}.{field_name}" if path else field_name

            if field_name not in config:
                if field_rule.get("required", False):
                    raise ValidationError(f"缺少必需的字段: {current_path}")
                # 使用默认值
                if "default" in field_rule:
                    config[field_name] = field_rule["default"]
                continue

            value = config[field_name]

            # 类型验证
            expected_type = field_rule.get("type")
            if expected_type and not isinstance(value, expected_type):
                if isinstance(expected_type, tuple):
                    type_names = [t.__name__ for t in expected_type]
                    raise ValidationError(
                        f"{current_path}: 类型错误，期望 {' 或 '.join(type_names)}，实际 {type(value).__name__}"
                    )
                else:
                    raise ValidationError(
                        f"{current_path}: 类型错误，期望 {expected_type.__name__}，实际 {type(value).__name__}"
                    )

            # 值范围验证
            if isinstance(value, (int, float)):
                min_val = field_rule.get("min_value")
                max_val = field_rule.get("max_value")
                if min_val is not None and value < min_val:
                    raise ValidationError(f"{current_path}: 值 {value} 小于最小值 {min_val}")
                if max_val is not None and value > max_val:
                    raise ValidationError(f"{current_path}: 值 {value} 大于最大值 {max_val}")

            # 选择项验证
            choices = field_rule.get("choices")
            if choices and value not in choices:
                raise ValidationError(f"{current_path}: 无效值 '{value}'，可选值: {choices}")

            # 正则表达式验证
            pattern = field_rule.get("pattern")
            if pattern and isinstance(value, str):
                if not re.match(pattern, value):
                    raise ValidationError(f"{current_path}: 值 '{value}' 不匹配模式 '{pattern}'")

    def add_custom_validator(self, name: str, validator_func: Callable[[Dict[str, Any]], None]):
        """
        添加自定义验证器

        Args:
            name: 验证器名称
            validator_func: 验证函数，接受配置字典参数
        """
        self.custom_validators[name] = validator_func

    def get_field_description(self, section: str, field: str) -> Optional[str]:
        """获取字段描述"""
        if section in self.validation_rules:
            fields = self.validation_rules[section].get("fields", {})
            if field in fields:
                return fields[field].get("description")
        return None

    def get_field_choices(self, section: str, field: str) -> Optional[List[str]]:
        """获取字段可选值"""
        if section in self.validation_rules:
            fields = self.validation_rules[section].get("fields", {})
            if field in fields:
                return fields[field].get("choices")
        return None


# 全局验证器实例
_validator = None


def get_validator() -> ConfigValidator:
    """获取全局验证器实例"""
    global _validator
    if _validator is None:
        _validator = ConfigValidator()
    return _validator


def validate_config(config: Dict[str, Any]) -> bool:
    """
    验证配置

    Args:
        config: 配置字典

    Returns:
        验证是否通过

    Raises:
        ValidationError: 验证失败时抛出
    """
    validator = get_validator()
    errors = validator.validate(config)

    if errors:
        error_msg = "配置验证失败:\n" + "\n".join(f"  • {error}" for error in errors)
        raise ValidationError(error_msg)

    return True


def validate_section(config: Dict[str, Any], section_name: str) -> List[str]:
    """
    验证特定配置节

    Args:
        config: 配置字典
        section_name: 节名称

    Returns:
        验证错误列表
    """
    validator = get_validator()
    if section_name not in validator.validation_rules:
        return [f"未知的配置节: {section_name}"]

    section_config = config.get(section_name, {})
    errors = []

    try:
        validator._validate_section({section_name: section_config}, section_name, {section_name: validator.validation_rules[section_name]})
    except ValidationError as e:
        errors.append(str(e))

    return errors


def get_config_schema() -> Dict[str, Any]:
    """获取配置模式定义"""
    validator = get_validator()
    return validator.validation_rules


def add_custom_validator(name: str, validator_func: Callable[[Dict[str, Any]], None]):
    """添加自定义验证器"""
    validator = get_validator()
    validator.add_custom_validator(name, validator_func)


# 内置自定义验证器
def validate_performance_consistency(config: Dict[str, Any]):
    """验证性能配置的一致性"""
    processing = config.get("processing", {})
    performance = config.get("performance", {})

    # 检查并行处理配置
    if processing.get("parallel", True) and not performance.get("enable_caching", True):
        raise ValidationError("并行处理模式下建议启用缓存以提升性能")

    # 检查内存配置
    memory_limit = processing.get("memory_limit", 2048)
    chunk_size = processing.get("chunk_size", 10000)

    # 估算单个块的内存使用 (粗略估算)
    estimated_chunk_memory = chunk_size * 0.1  # 每个记录约0.1MB
    if estimated_chunk_memory > memory_limit * 0.5:  # 不超过内存限制的50%
        raise ValidationError(f"块大小 {chunk_size} 可能超出内存限制 {memory_limit}MB")


def validate_coordinate_system_consistency(config: Dict[str, Any]):
    """验证坐标系配置的一致性"""
    processing = config.get("processing", {})
    validation = config.get("validation", {})

    crs = processing.get("coordinate_system")
    if crs and validation.get("coordinate_system_validation", True):
        # 验证EPSG代码格式
        if not re.match(r'^EPSG:\d+$', crs):
            raise ValidationError(f"无效的坐标系格式: {crs}，应为 'EPSG:数字' 格式")


# 注册内置自定义验证器
add_custom_validator("performance_consistency", validate_performance_consistency)
add_custom_validator("coordinate_system_consistency", validate_coordinate_system_consistency)