"""
属性数据验证模块

提供全面的属性数据质量检查功能，包括：
- 字段类型验证和转换
- 值域范围和唯一性约束检查
- 缺失值检测和数据完整性验证
- 自定义验证规则和阈值配置

Author: CCPM Auto Development System
"""

import logging
import numpy as np
import pandas as pd
import geopandas as gpd
from typing import Dict, List, Tuple, Optional, Union, Any, Set
from datetime import datetime
import re
from enum import Enum

logger = logging.getLogger(__name__)


class DataType(Enum):
    """支持的数据类型枚举"""
    STRING = 'string'
    INTEGER = 'integer'
    FLOAT = 'float'
    BOOLEAN = 'boolean'
    DATE = 'date'
    DATETIME = 'datetime'
    CATEGORICAL = 'categorical'


class AttributeValidationError:
    """属性验证错误类"""

    def __init__(self,
                 field_name: str,
                 error_type: str,
                 message: str,
                 row_id: Optional[Union[int, str]] = None,
                 field_value: Any = None):
        self.field_name = field_name
        self.error_type = error_type
        self.message = message
        self.row_id = row_id
        self.field_value = field_value
        self.severity = self._determine_severity(error_type)

    def _determine_severity(self, error_type: str) -> str:
        """根据错误类型确定严重程度"""
        high_severity = {'missing_required', 'invalid_type', 'out_of_range'}
        medium_severity = {'duplicate_value', 'format_error', 'precision_loss'}
        low_severity = {'warning', 'suspicious_value'}

        if error_type in high_severity:
            return 'high'
        elif error_type in medium_severity:
            return 'medium'
        else:
            return 'low'

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'field_name': self.field_name,
            'error_type': self.error_type,
            'message': self.message,
            'row_id': self.row_id,
            'field_value': str(self.field_value) if self.field_value is not None else None,
            'severity': self.severity
        }


class ValidationRule:
    """验证规则类"""

    def __init__(self,
                 field_name: str,
                 data_type: DataType,
                 required: bool = True,
                 min_value: Optional[Union[int, float]] = None,
                 max_value: Optional[Union[int, float]] = None,
                 allowed_values: Optional[Set] = None,
                 unique: bool = False,
                 pattern: Optional[str] = None,
                 min_length: Optional[int] = None,
                 max_length: Optional[int] = None,
                 custom_validator: Optional[callable] = None):
        self.field_name = field_name
        self.data_type = data_type
        self.required = required
        self.min_value = min_value
        self.max_value = max_value
        self.allowed_values = allowed_values
        self.unique = unique
        self.pattern = pattern
        self.min_length = min_length
        self.max_length = max_length
        self.custom_validator = custom_validator

    def validate(self, value: Any, row_id: Union[int, str]) -> List[AttributeValidationError]:
        """验证单个值"""
        errors = []

        # 检查必填字段
        if self.required and (value is None or pd.isna(value)):
            errors.append(AttributeValidationError(
                self.field_name, 'missing_required',
                f'必填字段 {self.field_name} 为空', row_id, value
            ))
            return errors  # 必填字段为空时，不进行其他检查

        # 如果值为空且非必填，跳过其他检查
        if value is None or pd.isna(value):
            return errors

        # 类型检查
        if not self._check_type(value):
            errors.append(AttributeValidationError(
                self.field_name, 'invalid_type',
                f'字段 {self.field_name} 类型错误，期望 {self.data_type.value}，实际 {type(value)}',
                row_id, value
            ))

        # 范围检查
        if self.data_type in [DataType.INTEGER, DataType.FLOAT]:
            if not self._check_range(value):
                errors.append(AttributeValidationError(
                    self.field_name, 'out_of_range',
                    f'字段 {self.field_name} 值 {value} 超出范围 [{self.min_value}, {self.max_value}]',
                    row_id, value
                ))

        # 允许值检查
        if self.allowed_values and value not in self.allowed_values:
            errors.append(AttributeValidationError(
                self.field_name, 'invalid_value',
                f'字段 {self.field_name} 值 {value} 不在允许的值列表中',
                row_id, value
            ))

        # 模式检查
        if self.pattern and isinstance(value, str):
            if not re.match(self.pattern, value):
                errors.append(AttributeValidationError(
                    self.field_name, 'format_error',
                    f'字段 {self.field_name} 值 {value} 不符合格式要求',
                    row_id, value
                ))

        # 长度检查
        if isinstance(value, str):
            if self.min_length and len(value) < self.min_length:
                errors.append(AttributeValidationError(
                    self.field_name, 'min_length',
                    f'字段 {self.field_name} 长度 {len(value)} 小于最小长度 {self.min_length}',
                    row_id, value
                ))
            if self.max_length and len(value) > self.max_length:
                errors.append(AttributeValidationError(
                    self.field_name, 'max_length',
                    f'字段 {self.field_name} 长度 {len(value)} 超过最大长度 {self.max_length}',
                    row_id, value
                ))

        # 自定义验证器
        if self.custom_validator:
            try:
                custom_result = self.custom_validator(value, row_id)
                if custom_result is not True:
                    if isinstance(custom_result, str):
                        errors.append(AttributeValidationError(
                            self.field_name, 'custom_validation',
                            f'字段 {self.field_name} 自定义验证失败: {custom_result}',
                            row_id, value
                        ))
            except Exception as e:
                errors.append(AttributeValidationError(
                    self.field_name, 'custom_validation_error',
                    f'字段 {self.field_name} 自定义验证器执行错误: {str(e)}',
                    row_id, value
                ))

        return errors

    def _check_type(self, value: Any) -> bool:
        """检查数据类型"""
        try:
            if self.data_type == DataType.STRING:
                return isinstance(value, str)
            elif self.data_type == DataType.INTEGER:
                return isinstance(value, (int, np.integer)) or (
                    isinstance(value, float) and value.is_integer()
                )
            elif self.data_type == DataType.FLOAT:
                return isinstance(value, (int, float, np.number))
            elif self.data_type == DataType.BOOLEAN:
                return isinstance(value, (bool, np.bool_))
            elif self.data_type == DataType.DATE:
                if isinstance(value, str):
                    pd.to_datetime(value).date()
                    return True
                elif isinstance(value, (datetime, pd.Timestamp)):
                    return True
                return False
            elif self.data_type == DataType.DATETIME:
                if isinstance(value, str):
                    pd.to_datetime(value)
                    return True
                elif isinstance(value, (datetime, pd.Timestamp)):
                    return True
                return False
            elif self.data_type == DataType.CATEGORICAL:
                return True  # 分类数据类型灵活处理
        except:
            return False
        return False

    def _check_range(self, value: Union[int, float]) -> bool:
        """检查数值范围"""
        try:
            # 确保值是数值类型
            if not isinstance(value, (int, float, np.number)):
                return True  # 非数值类型跳过范围检查

            numeric_value = float(value)
            if self.min_value is not None and numeric_value < self.min_value:
                return False
            if self.max_value is not None and numeric_value > self.max_value:
                return False
            return True
        except (ValueError, TypeError):
            # 转换失败时跳过范围检查
            return True


class AttributeValidator:
    """属性数据验证器

    支持全面的属性数据质量检查，包括：
    - 字段类型、值域范围、唯一性约束检查
    - 缺失值检测和数据类型转换
    - 自定义验证规则和阈值配置
    - 2,706个纵断面点的属性完整性验证

    Attributes:
        rules: 验证规则字典
        errors: 验证错误列表
        statistics: 统计信息
    """

    def __init__(self, rules: Optional[List[ValidationRule]] = None):
        """初始化属性验证器

        Args:
            rules: 验证规则列表，如果为None则使用默认规则
        """
        self.rules: Dict[str, ValidationRule] = {}
        self.errors: List[AttributeValidationError] = []
        self.statistics: Dict = {}

        if rules:
            for rule in rules:
                self.rules[rule.field_name] = rule

    def add_rule(self, rule: ValidationRule):
        """添加验证规则"""
        self.rules[rule.field_name] = rule

    def remove_rule(self, field_name: str):
        """移除验证规则"""
        if field_name in self.rules:
            del self.rules[field_name]

    def validate_geodataframe(self, gdf: gpd.GeoDataFrame) -> Dict:
        """验证GeoDataFrame的属性数据

        Args:
            gdf: 要验证的GeoDataFrame

        Returns:
            包含验证结果的字典
        """
        self.errors = []
        self.statistics = self._initialize_statistics()

        logger.info(f"开始验证 {len(gdf)} 条记录的属性数据")

        # 如果没有定义规则，自动生成规则
        if not self.rules:
            self._auto_generate_rules(gdf)

        # 逐行验证
        for idx, row in gdf.iterrows():
            row_id = getattr(row, 'id', idx)
            self._validate_row(row, row_id)

        # 检查唯一性约束（需要全局检查）
        self._check_uniqueness_constraints(gdf)

        # 计算统计信息
        self._calculate_statistics(gdf)

        return self._generate_validation_report()

    def _validate_row(self, row: pd.Series, row_id: Union[int, str]):
        """验证单行数据"""
        for field_name, rule in self.rules.items():
            if field_name in row.index:
                value = row[field_name]
                row_errors = rule.validate(value, row_id)
                self.errors.extend(row_errors)

    def _check_uniqueness_constraints(self, gdf: gpd.GeoDataFrame):
        """检查唯一性约束"""
        for field_name, rule in self.rules.items():
            if rule.unique and field_name in gdf.columns:
                # 检查重复值
                duplicates = gdf[gdf.duplicated(subset=field_name, keep=False)]
                for idx, row in duplicates.iterrows():
                    value = row[field_name]
                    row_id = getattr(row, 'id', idx)
                    self.errors.append(AttributeValidationError(
                        field_name, 'duplicate_value',
                        f'字段 {field_name} 值 {value} 重复', row_id, value
                    ))

    def _auto_generate_rules(self, gdf: gpd.GeoDataFrame):
        """自动生成验证规则"""
        for column in gdf.columns:
            if column == 'geometry':  # 跳过几何列
                continue

            series = gdf[column]
            data_type = self._infer_data_type(series)

            # 创建基本规则
            rule = ValidationRule(
                field_name=column,
                data_type=data_type,
                required=not series.isna().all()  # 如果全为空，则非必填
            )

            # 根据数据类型添加特定规则
            if data_type == DataType.INTEGER:
                if not series.empty:
                    rule.min_value = series.min()
                    rule.max_value = series.max()
            elif data_type == DataType.FLOAT:
                if not series.empty:
                    rule.min_value = series.min()
                    rule.max_value = series.max()
            elif data_type == DataType.STRING:
                if not series.empty:
                    str_lengths = series.astype(str).str.len()
                    if not str_lengths.empty:
                        rule.max_length = int(str_lengths.quantile(0.95)) * 2  # 95%分位数的2倍

                    # 检查是否为分类数据
                    unique_ratio = series.nunique() / len(series)
                    if unique_ratio < 0.1:  # 唯一值比例小于10%，认为是分类数据
                        rule.data_type = DataType.CATEGORICAL
                        rule.allowed_values = set(series.dropna().unique())

            self.rules[column] = rule

    def _infer_data_type(self, series: pd.Series) -> DataType:
        """推断数据类型"""
        # 移除空值进行类型推断
        non_null_series = series.dropna()

        if non_null_series.empty:
            return DataType.STRING

        # 尝试转换为各种类型
        try:
            # 检查是否为数值型
            pd.to_numeric(non_null_series)
            if all(non_null_series.astype(float).apply(lambda x: x.is_integer())):
                return DataType.INTEGER
            else:
                return DataType.FLOAT
        except:
            pass

        try:
            # 检查是否为日期型
            pd.to_datetime(non_null_series)
            return DataType.DATE
        except:
            pass

        try:
            # 检查是否为布尔型
            if all(str(val).lower() in ['true', 'false', '1', '0', 'yes', 'no']
                   for val in non_null_series):
                return DataType.BOOLEAN
        except:
            pass

        # 默认为字符串型
        return DataType.STRING

    def _initialize_statistics(self) -> Dict:
        """初始化统计信息"""
        return {
            'total_records': 0,
            'total_fields': 0,
            'missing_values': {},
            'field_types': {},
            'error_types': {},
            'severity_counts': {'high': 0, 'medium': 0, 'low': 0},
            'field_completeness': {}
        }

    def _calculate_statistics(self, gdf: gpd.GeoDataFrame):
        """计算统计信息"""
        self.statistics['total_records'] = len(gdf)
        self.statistics['total_fields'] = len(gdf.columns) - 1  # 减去几何列

        # 计算每个字段的缺失值和完整性
        for column in gdf.columns:
            if column == 'geometry':
                continue

            missing_count = gdf[column].isna().sum()
            total_count = len(gdf)
            completeness = (total_count - missing_count) / total_count * 100

            self.statistics['missing_values'][column] = missing_count
            self.statistics['field_completeness'][column] = round(completeness, 2)

            # 推断字段类型
            if column in self.rules:
                self.statistics['field_types'][column] = self.rules[column].data_type.value

        # 统计错误类型
        for error in self.errors:
            error_type = error.error_type
            self.statistics['error_types'][error_type] = \
                self.statistics['error_types'].get(error_type, 0) + 1
            self.statistics['severity_counts'][error.severity] += 1

    def _generate_validation_report(self) -> Dict:
        """生成验证报告"""
        # 计算总体完整性分数
        avg_completeness = 0
        if self.statistics['field_completeness']:
            avg_completeness = sum(self.statistics['field_completeness'].values()) / \
                             len(self.statistics['field_completeness'])

        # 计算质量分数
        quality_score = self._calculate_quality_score()

        return {
            'summary': {
                'total_records': self.statistics['total_records'],
                'total_fields': self.statistics['total_fields'],
                'average_completeness': round(avg_completeness, 2),
                'total_errors': len(self.errors),
                'quality_score': quality_score
            },
            'field_completeness': self.statistics['field_completeness'],
            'missing_values': self.statistics['missing_values'],
            'field_types': self.statistics['field_types'],
            'error_types': self.statistics['error_types'],
            'severity_distribution': self.statistics['severity_counts'],
            'errors': [error.to_dict() for error in self.errors]
        }

    def _calculate_quality_score(self) -> float:
        """计算质量分数 (0-100)"""
        if self.statistics['total_fields'] == 0:
            return 0.0

        # 基础分数：平均完整性
        base_score = sum(self.statistics['field_completeness'].values()) / \
                    max(1, len(self.statistics['field_completeness']))

        # 错误惩罚
        total_records = max(1, self.statistics['total_records'])
        high_penalty = (self.statistics['severity_counts']['high'] / total_records) * 20
        medium_penalty = (self.statistics['severity_counts']['medium'] / total_records) * 10
        low_penalty = (self.statistics['severity_counts']['low'] / total_records) * 5

        total_penalty = high_penalty + medium_penalty + low_penalty

        # 最终分数
        final_score = max(0, base_score - total_penalty)
        return round(final_score, 2)

    def get_data_cleaning_suggestions(self) -> List[Dict]:
        """获取数据清洗建议"""
        suggestions = []

        # 缺失值处理建议
        for field, missing_count in self.statistics['missing_values'].items():
            if missing_count > 0:
                missing_ratio = missing_count / max(1, self.statistics['total_records'])

                if missing_ratio > 0.5:
                    suggestions.append({
                        'field': field,
                        'issue': 'high_missing_rate',
                        'description': f'字段 {field} 缺失率过高 ({missing_ratio:.1%})',
                        'suggestion': '考虑删除该字段或检查数据收集流程',
                        'auto_fixable': False
                    })
                elif missing_ratio > 0.1:
                    suggestions.append({
                        'field': field,
                        'issue': 'moderate_missing_rate',
                        'description': f'字段 {field} 有较多缺失值 ({missing_ratio:.1%})',
                        'suggestion': '使用插值或默认值填充缺失值',
                        'auto_fixable': True
                    })

        # 重复值处理建议
        duplicate_errors = [e for e in self.errors if e.error_type == 'duplicate_value']
        if duplicate_errors:
            affected_fields = set(e.field_name for e in duplicate_errors)
            for field in affected_fields:
                suggestions.append({
                    'field': field,
                    'issue': 'duplicate_values',
                    'description': f'字段 {field} 存在重复值',
                    'suggestion': '检查是否应该为唯一字段，或考虑去重处理',
                    'auto_fixable': True
                })

        # 类型转换建议
        type_errors = [e for e in self.errors if e.error_type == 'invalid_type']
        if type_errors:
            affected_fields = set(e.field_name for e in type_errors)
            for field in affected_fields:
                suggestions.append({
                    'field': field,
                    'issue': 'type_inconsistency',
                    'description': f'字段 {field} 存在类型不一致',
                    'suggestion': '统一字段数据类型，进行类型转换',
                    'auto_fixable': True
                })

        return suggestions

    def create_default_gis_rules(self) -> List[ValidationRule]:
        """创建默认的GIS数据验证规则"""
        return [
            # ID字段规则
            ValidationRule('id', DataType.INTEGER, required=True, unique=True),
            ValidationRule('FID', DataType.INTEGER, required=False, unique=True),

            # 名称字段规则
            ValidationRule('name', DataType.STRING, required=False, max_length=255),
            ValidationRule('NAME', DataType.STRING, required=False, max_length=255),

            # 数值字段规则
            ValidationRule('elevation', DataType.FLOAT, required=False, min_value=-1000, max_value=10000),
            ValidationRule('length', DataType.FLOAT, required=False, min_value=0),
            ValidationRule('area', DataType.FLOAT, required=False, min_value=0),

            # 编码字段规则
            ValidationRule('code', DataType.STRING, required=False, max_length=50, pattern=r'^[A-Za-z0-9_\-]+$'),
            ValidationRule('type', DataType.STRING, required=False, max_length=100),

            # 日期字段规则
            ValidationRule('create_date', DataType.DATE, required=False),
            ValidationRule('update_date', DataType.DATETIME, required=False),
        ]