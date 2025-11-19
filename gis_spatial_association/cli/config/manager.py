"""
配置管理器

提供完整的配置管理功能：
- 配置文件加载和保存
- 环境变量覆盖
- 配置验证和默认值
- 配置热重载
- 多层配置合并
"""

import os
import sys
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器"""

    def __init__(self):
        """初始化配置管理器"""
        self.config_data = {}
        self.config_file_path = None
        self.global_config_path = Path.home() / '.gis_association' / 'config.yaml'
        self.local_config_path = Path.cwd() / '.gis_association_config.yaml'
        self.project_config_path = Path.cwd() / 'gis_association_config.yaml'
        self._load_order = [
            self.global_config_path,  # 全局配置 - 最低优先级
            self.local_config_path,    # 本地配置
            self.project_config_path   # 项目配置 - 最高优先级
        ]

    def load_config(self, config_file: Optional[Union[str, Path]] = None):
        """
        加载配置文件

        Args:
            config_file: 指定的配置文件路径，如果为None则按优先级自动加载
        """
        self.config_data = {}

        if config_file:
            # 加载指定的配置文件
            config_path = Path(config_file)
            if config_path.exists():
                self._load_single_config(config_path)
                self.config_file_path = config_path
            else:
                raise FileNotFoundError(f"配置文件不存在: {config_path}")
        else:
            # 按优先级自动加载配置
            loaded_configs = []
            for config_path in self._load_order:
                if config_path.exists():
                    self._load_single_config(config_path)
                    loaded_configs.append(config_path)

            if not loaded_configs:
                logger.info("未找到配置文件，使用默认配置")
                self._load_default_config()

        # 应用环境变量覆盖
        self._apply_env_overrides()

        # 验证配置
        self._validate_config()

        logger.debug(f"配置加载完成，来源: {self.config_file_path or '多层合并'}")

    def _load_single_config(self, config_path: Path):
        """加载单个配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    config = yaml.safe_load(f) or {}
                elif config_path.suffix.lower() == '.json':
                    config = json.load(f)
                else:
                    raise ValueError(f"不支持的配置文件格式: {config_path.suffix}")

            # 深度合并配置
            self._deep_merge(self.config_data, config)
            logger.debug(f"已加载配置文件: {config_path}")

        except Exception as e:
            logger.error(f"加载配置文件失败 {config_path}: {e}")
            raise

    def _load_default_config(self):
        """加载默认配置"""
        try:
            from .templates import DEFAULT_CONFIG
            self.config_data = DEFAULT_CONFIG.copy()
        except ImportError:
            # 如果无法导入默认配置，使用最小配置
            self.config_data = {
                'processing': {
                    'max_neighbors': 1,
                    'distance_threshold': 1000.0,
                    'parallel': True
                },
                'validation': {
                    'strict_mode': False,
                    'auto_repair': True
                },
                'output': {
                    'default_format': 'geojson'
                }
            }

    def _deep_merge(self, target: Dict, source: Dict):
        """深度合并字典"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value

    def _apply_env_overrides(self):
        """应用环境变量覆盖"""
        env_prefix = 'GIS_ASSOCIATION_'

        # 支持的环境变量
        env_mappings = {
            f'{env_prefix}MAX_NEIGHBORS': ('processing', 'max_neighbors', int),
            f'{env_prefix}DISTANCE_THRESHOLD': ('processing', 'distance_threshold', float),
            f'{env_prefix}PARALLEL': ('processing', 'parallel', bool),
            f'{env_prefix}STRICT_MODE': ('validation', 'strict_mode', bool),
            f'{env_prefix}AUTO_REPAIR': ('validation', 'auto_repair', bool),
            f'{env_prefix}OUTPUT_FORMAT': ('output', 'default_format', str),
            f'{env_prefix}LOG_LEVEL': ('logging', 'level', str),
            f'{env_prefix}LOG_FILE': ('logging', 'file', str),
        }

        for env_var, (section, key, var_type) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    # 类型转换
                    if var_type == bool:
                        converted_value = value.lower() in ('true', '1', 'yes', 'on')
                    elif var_type == int:
                        converted_value = int(value)
                    elif var_type == float:
                        converted_value = float(value)
                    else:
                        converted_value = value

                    # 设置配置值
                    if section not in self.config_data:
                        self.config_data[section] = {}
                    self.config_data[section][key] = converted_value

                    logger.debug(f"环境变量覆盖: {env_var} -> {section}.{key} = {converted_value}")

                except (ValueError, TypeError) as e:
                    logger.warning(f"环境变量类型转换失败 {env_var}={value}: {e}")

    def _validate_config(self):
        """验证配置"""
        try:
            from .schema import validate_config
            validate_config(self.config_data)
        except ImportError:
            # 如果无法导入验证器，进行基本验证
            self._basic_validation()

    def _basic_validation(self):
        """基本配置验证"""
        # 检查必需的配置节
        required_sections = ['processing']
        for section in required_sections:
            if section not in self.config_data:
                logger.warning(f"缺少必需的配置节: {section}")

        # 检查处理配置
        processing_config = self.config_data.get('processing', {})
        if 'max_neighbors' in processing_config:
            if not isinstance(processing_config['max_neighbors'], int) or processing_config['max_neighbors'] < 1:
                logger.warning("max_neighbors 必须是大于0的整数")

        if 'distance_threshold' in processing_config:
            if not isinstance(processing_config['distance_threshold'], (int, float)) or processing_config['distance_threshold'] <= 0:
                logger.warning("distance_threshold 必须是大于0的数值")

    def get_config(self) -> Dict[str, Any]:
        """获取完整配置"""
        return self.config_data.copy()

    def get_section(self, section_name: str, default: Any = None) -> Any:
        """获取配置节"""
        return self.config_data.get(section_name, default)

    def get_value(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置值

        Args:
            key_path: 配置键路径，如 'processing.max_neighbors'
            default: 默认值
        """
        keys = key_path.split('.')
        current = self.config_data

        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default

    def set_value(self, key_path: str, value: Any):
        """
        设置配置值

        Args:
            key_path: 配置键路径，如 'processing.max_neighbors'
            value: 配置值
        """
        keys = key_path.split('.')
        current = self.config_data

        # 导航到目标位置
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        # 设置值
        current[keys[-1]] = value

    def save_config(self, config_file: Optional[Union[str, Path]] = None):
        """
        保存配置到文件

        Args:
            config_file: 保存路径，如果为None则使用加载的路径
        """
        if config_file:
            save_path = Path(config_file)
        elif self.config_file_path:
            save_path = self.config_file_path
        else:
            # 默认保存到本地配置
            save_path = self.local_config_path

        # 确保目录存在
        save_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # 保存配置
            with open(save_path, 'w', encoding='utf-8') as f:
                if save_path.suffix.lower() in ['.yaml', '.yml']:
                    yaml.dump(self.config_data, f, default_flow_style=False, allow_unicode=True)
                elif save_path.suffix.lower() == '.json':
                    json.dump(self.config_data, f, indent=2, ensure_ascii=False)
                else:
                    # 默认保存为YAML
                    yaml.dump(self.config_data, f, default_flow_style=False, allow_unicode=True)

            logger.info(f"配置已保存到: {save_path}")
            self.config_file_path = save_path

        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            raise

    def create_default_config(self, config_path: Union[str, Path], template_type: str = 'default'):
        """
        创建默认配置文件

        Args:
            config_path: 配置文件路径
            template_type: 模板类型 ('default', 'performance', 'validation')
        """
        try:
            from .templates import CONFIG_TEMPLATE, DEFAULT_CONFIG
        except ImportError:
            raise ImportError("无法导入配置模板")

        # 选择配置模板
        if template_type == 'default':
            config_data = DEFAULT_CONFIG.copy()
        elif template_type in CONFIG_TEMPLATE:
            config_data = CONFIG_TEMPLATE[template_type].copy()
        else:
            raise ValueError(f"未知的配置模板类型: {template_type}")

        # 添加元数据
        try:
            import pandas as pd
            created_time = str(pd.Timestamp.now())
        except ImportError:
            from datetime import datetime
            created_time = datetime.now().isoformat()

        config_data['_metadata'] = {
            'version': '1.0.0',
            'created': created_time,
            'template': template_type
        }

        # 保存配置
        save_path = Path(config_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        with open(save_path, 'w', encoding='utf-8') as f:
            if save_path.suffix.lower() in ['.yaml', '.yml']:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
            elif save_path.suffix.lower() == '.json':
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            else:
                # 默认保存为YAML
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)

        logger.info(f"默认配置已创建: {save_path}")
        return save_path

    def reload_config(self):
        """重新加载配置"""
        if self.config_file_path:
            self.load_config(self.config_file_path)
        else:
            self.load_config()

    def get_config_info(self) -> Dict[str, Any]:
        """获取配置信息"""
        return {
            'config_file_path': str(self.config_file_path) if self.config_file_path else None,
            'global_config_exists': self.global_config_path.exists(),
            'local_config_exists': self.local_config_path.exists(),
            'project_config_exists': self.project_config_path.exists(),
            'sections': list(self.config_data.keys()),
            'env_overrides': [k for k in os.environ.keys() if k.startswith('GIS_ASSOCIATION_')]
        }

    def export_config(self, output_path: Union[str, Path], format_type: str = 'yaml'):
        """
        导出配置到文件

        Args:
            output_path: 输出文件路径
            format_type: 输出格式 ('yaml', 'json')
        """
        save_path = Path(output_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                if format_type.lower() == 'json':
                    json.dump(self.config_data, f, indent=2, ensure_ascii=False)
                else:
                    yaml.dump(self.config_data, f, default_flow_style=False, allow_unicode=True)

            logger.info(f"配置已导出到: {save_path}")
            return save_path

        except Exception as e:
            logger.error(f"导出配置失败: {e}")
            raise

    def merge_config(self, other_config: Dict[str, Any]):
        """
        合并其他配置

        Args:
            other_config: 要合并的配置字典
        """
        self._deep_merge(self.config_data, other_config)
        self._validate_config()

    def reset_to_default(self, section: Optional[str] = None):
        """
        重置配置为默认值

        Args:
            section: 要重置的配置节，如果为None则重置全部
        """
        try:
            from .templates import DEFAULT_CONFIG
        except ImportError:
            raise ImportError("无法导入默认配置")

        if section:
            if section in DEFAULT_CONFIG:
                self.config_data[section] = DEFAULT_CONFIG[section].copy()
            else:
                logger.warning(f"未知的配置节: {section}")
        else:
            self.config_data = DEFAULT_CONFIG.copy()

        self._validate_config()


# 全局配置管理器实例
_config_manager = None


def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def load_global_config():
    """加载全局配置"""
    config_manager = get_config_manager()
    config_manager.load_config()
    return config_manager.get_config()