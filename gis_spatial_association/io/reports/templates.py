"""
报告模板管理器

提供多种报告格式的模板引擎，支持HTML、PDF、Markdown、Excel等格式的
模板渲染和样式定制。

特点:
- 模块化模板系统
- 自定义样式支持
- 多语言支持
- 图表集成
- 响应式设计

作者: GIS空间关联系统开发团队
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class ReportTemplateManager:
    """
    报告模板管理器

    管理各种报告格式的模板和渲染引擎。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化模板管理器

        Args:
            config: 配置字典
        """
        self.config = config or {}

        # 模板目录
        self.template_dir = Path(__file__).parent / 'templates'
        self.custom_template_dir = Path(self.config.get('custom_template_dir', './custom_templates'))

        # 初始化模板引擎
        self.html_engine = HTMLTemplateEngine(self.config)
        self.pdf_engine = PDFTemplateEngine(self.config)
        self.markdown_engine = MarkdownTemplateEngine(self.config)
        self.excel_engine = ExcelTemplateEngine(self.config)

        # 自定义模板
        self.custom_templates = {}

        # 加载自定义模板
        self._load_custom_templates()

    def _load_custom_templates(self):
        """加载自定义模板"""
        try:
            if self.custom_template_dir.exists():
                for template_file in self.custom_template_dir.glob('*.html'):
                    template_name = template_file.stem
                    with open(template_file, 'r', encoding='utf-8') as f:
                        self.custom_templates[template_name] = f.read()
                    logger.info(f"加载自定义模板: {template_name}")

        except Exception as e:
            logger.warning(f"加载自定义模板失败: {str(e)}")

    def generate_html_report(self, report_data: Dict[str, Any], output_path: Path) -> Optional[str]:
        """
        生成HTML报告

        Args:
            report_data: 报告数据
            output_path: 输出路径

        Returns:
            Optional[str]: 生成的文件路径
        """
        return self.html_engine.render_report(report_data, output_path)

    def generate_pdf_report(self, report_data: Dict[str, Any], output_path: Path) -> Optional[str]:
        """
        生成PDF报告

        Args:
            report_data: 报告数据
            output_path: 输出路径

        Returns:
            Optional[str]: 生成的文件路径
        """
        return self.pdf_engine.render_report(report_data, output_path)

    def generate_markdown_report(self, report_data: Dict[str, Any], output_path: Path) -> Optional[str]:
        """
        生成Markdown报告

        Args:
            report_data: 报告数据
            output_path: 输出路径

        Returns:
            Optional[str]: 生成的文件路径
        """
        return self.markdown_engine.render_report(report_data, output_path)

    def generate_excel_report(self, report_data: Dict[str, Any], output_path: Path) -> Optional[str]:
        """
        生成Excel报告

        Args:
            report_data: 报告数据
            output_path: 输出路径

        Returns:
            Optional[str]: 生成的文件路径
        """
        return self.excel_engine.render_report(report_data, output_path)

    def add_custom_template(self, template_type: str, template_path: str) -> None:
        """
        添加自定义模板

        Args:
            template_type: 模板类型
            template_path: 模板路径
        """
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()

            self.custom_templates[template_type] = template_content
            logger.info(f"添加自定义模板: {template_type}")

        except Exception as e:
            logger.error(f"添加自定义模板失败: {str(e)}")

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """
        更新配置

        Args:
            new_config: 新配置
        """
        self.config.update(new_config)

        # 更新各引擎配置
        for engine in [self.html_engine, self.pdf_engine, self.markdown_engine, self.excel_engine]:
            if hasattr(engine, 'update_config'):
                engine.update_config(new_config)


class HTMLTemplateEngine:
    """
    HTML模板引擎

    生成交互式HTML报告，包含样式、图表和响应式设计。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化HTML模板引擎

        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.default_template = self._get_default_html_template()

    def render_report(self, report_data: Dict[str, Any], output_path: Path) -> Optional[str]:
        """
        渲染HTML报告

        Args:
            report_data: 报告数据
            output_path: 输出路径

        Returns:
            Optional[str]: 生成的文件路径
        """
        try:
            # 生成HTML内容
            html_content = self._generate_html_content(report_data)

            # 写入文件
            html_file = output_path / 'analysis_report.html'
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)

            logger.info(f"HTML报告生成成功: {html_file}")
            return str(html_file)

        except Exception as e:
            logger.error(f"HTML报告生成失败: {str(e)}")
            return None

    def _generate_html_content(self, report_data: Dict[str, Any]) -> str:
        """
        生成HTML内容

        Args:
            report_data: 报告数据

        Returns:
            str: HTML内容
        """
        template = self.default_template

        # 替换模板变量
        replacements = {
            '{{TITLE}}': report_data.get('metadata', {}).get('title', '分析报告'),
            '{{AUTHOR}}': report_data.get('metadata', {}).get('author', ''),
            '{{GENERATION_TIME}}': report_data.get('metadata', {}).get('generation_time', ''),
            '{{SUMMARY_SECTION}}': self._render_summary_section(report_data.get('summary', {})),
            '{{DATASETS_SECTION}}': self._render_datasets_section(report_data.get('datasets', {})),
            '{{STATISTICS_SECTION}}': self._render_statistics_section(report_data.get('statistics', {})),
            '{{ASSOCIATIONS_SECTION}}': self._render_associations_section(report_data.get('associations', {})),
            '{{QUALITY_SECTION}}': self._render_quality_section(report_data.get('quality_assessment', {})),
            '{{CHARTS_SECTION}}': self._render_charts_section(report_data.get('charts', {}))
        }

        html_content = template
        for placeholder, value in replacements.items():
            html_content = html_content.replace(placeholder, value)

        return html_content

    def _render_summary_section(self, summary_data: Dict[str, Any]) -> str:
        """渲染摘要部分"""
        if not summary_data:
            return ""

        html = '<div class="summary-section">'
        html += '<h2>📊 分析摘要</h2>'

        # 关键发现
        key_findings = summary_data.get('key_findings', [])
        if key_findings:
            html += '<h3>关键发现</h3><ul>'
            for finding in key_findings:
                html += f'<li>{finding}</li>'
            html += '</ul>'

        # 数据概览
        data_overview = summary_data.get('data_overview', {})
        if data_overview:
            html += '<h3>数据概览</h3>'
            html += '<div class="data-overview-cards">'
            html += f'<div class="card"><span class="number">{data_overview.get("total_datasets", 0)}</span><span>数据集</span></div>'
            html += f'<div class="card"><span class="number">{data_overview.get("total_records", 0):,}</span><span>记录</span></div>'
            html += '</div>'

        # 建议
        recommendations = summary_data.get('recommendations', [])
        if recommendations:
            html += '<h3>改进建议</h3><ul>'
            for rec in recommendations:
                html += f'<li>{rec}</li>'
            html += '</ul>'

        html += '</div>'
        return html

    def _render_datasets_section(self, datasets_data: Dict[str, Any]) -> str:
        """渲染数据集部分"""
        if not datasets_data:
            return ""

        html = '<div class="datasets-section">'
        html += '<h2>📁 数据集详情</h2>'

        for name, data in datasets_data.items():
            html += f'<div class="dataset-card">'
            html += f'<h3>{name}</h3>'
            html += f'<p><strong>类型:</strong> {data.get("type", "")}</p>'
            html += f'<p><strong>记录数:</strong> {data.get("record_count", 0):,}</p>'
            html += f'<p><strong>字段数:</strong> {data.get("column_count", 0)}</p>'

            if data.get('geometry_type'):
                html += f'<p><strong>几何类型:</strong> {data["geometry_type"]}</p>'

            html += '</div>'

        html += '</div>'
        return html

    def _render_statistics_section(self, stats_data: Dict[str, Any]) -> str:
        """渲染统计部分"""
        if not stats_data:
            return ""

        html = '<div class="statistics-section">'
        html += '<h2>📈 统计信息</h2>'
        html += '<div class="stats-grid">'

        stats_items = [
            ('总数据集', stats_data.get('total_datasets', 0), '个'),
            ('总记录数', stats_data.get('total_records', 0), '条'),
            ('总几何对象', stats_data.get('total_geometries', 0), '个'),
            ('数据体积', self._format_bytes(stats_data.get('data_volume', 0)), 'B')
        ]

        for label, value, unit in stats_items:
            if isinstance(value, (int, float)):
                value_str = f"{value:,}" if value >= 1000 else str(value)
            else:
                value_str = str(value)
            html += f'<div class="stat-item"><span class="stat-value">{value_str}</span><span class="stat-label">{label}</span></div>'

        html += '</div></div>'
        return html

    def _render_associations_section(self, associations_data: Dict[str, Any]) -> str:
        """渲染关联分析部分"""
        if not associations_data:
            return ""

        html = '<div class="associations-section">'
        html += '<h2>🔗 关联分析</h2>'

        total = associations_data.get('total_associations', 0)
        html += f'<p><strong>关联关系总数:</strong> {total}</p>'

        # 关联类型
        types = associations_data.get('association_types', {})
        if types:
            html += '<h3>关联类型分布</h3><ul>'
            for atype, count in types.items():
                html += f'<li>{atype}: {count}</li>'
            html += '</ul>'

        html += '</div>'
        return html

    def _render_quality_section(self, quality_data: Dict[str, Any]) -> str:
        """渲染质量评估部分"""
        if not quality_data:
            return ""

        html = '<div class="quality-section">'
        html += '<h2>✅ 质量评估</h2>'

        score = quality_data.get('overall_score', 0)
        html += f'<div class="quality-score">'
        html += f'<span class="score-value">{score:.1f}</span>'
        html += f'<span class="score-label">总体质量评分</span>'
        html += '</div>'

        # 质量等级
        level = self._get_quality_level(score)
        html += f'<p class="quality-level level-{level.lower()}">质量等级: {level}</p>'

        html += '</div>'
        return html

    def _render_charts_section(self, charts_data: Dict[str, Any]) -> str:
        """渲染图表部分"""
        if not charts_data:
            return ""

        html = '<div class="charts-section">'
        html += '<h2>📊 数据可视化</h2>'

        # 这里可以根据实际生成的图表添加HTML
        html += '<p>图表功能正在开发中...</p>'

        html += '</div>'
        return html

    def _format_bytes(self, bytes_value: int) -> str:
        """格式化字节数"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_value < 1024:
                return f"{bytes_value:.1f}"
            bytes_value /= 1024
        return f"{bytes_value:.1f}TB"

    def _get_quality_level(self, score: float) -> str:
        """获取质量等级"""
        if score >= 90:
            return '优秀'
        elif score >= 80:
            return '良好'
        elif score >= 70:
            return '中等'
        elif score >= 60:
            return '及格'
        else:
            return '需要改进'

    def _get_default_html_template(self) -> str:
        """获取默认HTML模板"""
        return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{TITLE}}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Microsoft YaHei', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f8f9fa;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 20px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 30px;
        }

        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }

        .header .meta {
            font-size: 1.1em;
            opacity: 0.9;
        }

        .section {
            background: white;
            padding: 30px;
            margin-bottom: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        .section h2 {
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.8em;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }

        .section h3 {
            color: #333;
            margin: 20px 0 15px 0;
            font-size: 1.4em;
        }

        .data-overview-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }

        .card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            border-left: 4px solid #667eea;
        }

        .card .number {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
            display: block;
        }

        .dataset-card {
            background: #f8f9fa;
            padding: 20px;
            margin: 15px 0;
            border-radius: 8px;
            border-left: 4px solid #28a745;
        }

        .dataset-card h3 {
            color: #28a745;
            margin-top: 0;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }

        .stat-item {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            border-left: 4px solid #ffc107;
        }

        .stat-value {
            font-size: 1.5em;
            font-weight: bold;
            color: #ffc107;
            display: block;
        }

        .stat-label {
            color: #666;
            font-size: 0.9em;
        }

        .quality-score {
            text-align: center;
            margin: 20px 0;
        }

        .score-value {
            font-size: 4em;
            font-weight: bold;
            color: #28a745;
            display: block;
        }

        .score-label {
            font-size: 1.2em;
            color: #666;
        }

        .quality-level {
            text-align: center;
            padding: 10px;
            border-radius: 5px;
            font-weight: bold;
            margin: 10px 0;
        }

        .level-优秀 { background-color: #d4edda; color: #155724; }
        .level-良好 { background-color: #cce5ff; color: #004085; }
        .level-中等 { background-color: #fff3cd; color: #856404; }
        .level-及格 { background-color: #f8d7da; color: #721c24; }
        .level-需要改进 { background-color: #f5c6cb; color: #721c24; }

        ul, ol {
            margin-left: 20px;
            margin-bottom: 15px;
        }

        li {
            margin-bottom: 5px;
        }

        @media (max-width: 768px) {
            .container {
                padding: 10px;
            }

            .header h1 {
                font-size: 2em;
            }

            .section {
                padding: 20px;
            }

            .data-overview-cards,
            .stats-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{TITLE}}</h1>
            <div class="meta">
                <p>作者: {{AUTHOR}} | 生成时间: {{GENERATION_TIME}}</p>
            </div>
        </div>

        {{SUMMARY_SECTION}}
        {{DATASETS_SECTION}}
        {{STATISTICS_SECTION}}
        {{ASSOCIATIONS_SECTION}}
        {{QUALITY_SECTION}}
        {{CHARTS_SECTION}}
    </div>
</body>
</html>
        """


class PDFTemplateEngine:
    """
    PDF模板引擎

    生成专业的PDF报告。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化PDF模板引擎

        Args:
            config: 配置字典
        """
        self.config = config or {}

    def render_report(self, report_data: Dict[str, Any], output_path: Path) -> Optional[str]:
        """
        渲染PDF报告

        Args:
            report_data: 报告数据
            output_path: 输出路径

        Returns:
            Optional[str]: 生成的文件路径
        """
        try:
            # 检查依赖
            try:
                from reportlab.lib.pagesizes import letter, A4
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
                from reportlab.lib.styles import getSampleStyleSheet
                from reportlab.lib.units import inch
            except ImportError:
                logger.error("需要安装reportlab库: pip install reportlab")
                return None

            # 创建PDF文档
            pdf_file = output_path / 'analysis_report.pdf'
            doc = SimpleDocTemplate(str(pdf_file), pagesize=A4)

            # 生成PDF内容
            story = self._generate_pdf_content(report_data)

            # 构建PDF
            doc.build(story)

            logger.info(f"PDF报告生成成功: {pdf_file}")
            return str(pdf_file)

        except Exception as e:
            logger.error(f"PDF报告生成失败: {str(e)}")
            return None

    def _generate_pdf_content(self, report_data: Dict[str, Any]) -> list:
        """生成PDF内容"""
        story = []

        try:
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import Paragraph, Spacer
            from reportlab.lib.units import inch

            styles = getSampleStyleSheet()

            # 标题
            title = report_data.get('metadata', {}).get('title', '分析报告')
            story.append(Paragraph(title, styles['Title']))
            story.append(Spacer(1, 0.2 * inch))

            # 元数据
            metadata = report_data.get('metadata', {})
            story.append(Paragraph(f"作者: {metadata.get('author', '')}", styles['Normal']))
            story.append(Paragraph(f"生成时间: {metadata.get('generation_time', '')}", styles['Normal']))
            story.append(Spacer(1, 0.3 * inch))

            # 摘要
            summary = report_data.get('summary', {})
            if summary:
                story.append(Paragraph("分析摘要", styles['Heading1']))

                key_findings = summary.get('key_findings', [])
                for finding in key_findings:
                    story.append(Paragraph(f"• {finding}", styles['Normal']))

                story.append(Spacer(1, 0.2 * inch))

            # 数据集
            datasets = report_data.get('datasets', {})
            if datasets:
                story.append(Paragraph("数据集详情", styles['Heading1']))

                for name, data in datasets.items():
                    story.append(Paragraph(f"{name}", styles['Heading2']))
                    story.append(Paragraph(f"类型: {data.get('type', '')}", styles['Normal']))
                    story.append(Paragraph(f"记录数: {data.get('record_count', 0):,}", styles['Normal']))
                    story.append(Spacer(1, 0.1 * inch))

        except ImportError:
            logger.error("PDF生成需要reportlab库")
        except Exception as e:
            logger.error(f"生成PDF内容失败: {str(e)}")

        return story


class MarkdownTemplateEngine:
    """
    Markdown模板引擎

    生成Markdown格式的报告。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化Markdown模板引擎

        Args:
            config: 配置字典
        """
        self.config = config or {}

    def render_report(self, report_data: Dict[str, Any], output_path: Path) -> Optional[str]:
        """
        渲染Markdown报告

        Args:
            report_data: 报告数据
            output_path: 输出路径

        Returns:
            Optional[str]: 生成的文件路径
        """
        try:
            markdown_content = self._generate_markdown_content(report_data)

            md_file = output_path / 'analysis_report.md'
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

            logger.info(f"Markdown报告生成成功: {md_file}")
            return str(md_file)

        except Exception as e:
            logger.error(f"Markdown报告生成失败: {str(e)}")
            return None

    def _generate_markdown_content(self, report_data: Dict[str, Any]) -> str:
        """生成Markdown内容"""
        lines = []

        # 标题和元数据
        metadata = report_data.get('metadata', {})
        lines.append(f"# {metadata.get('title', '分析报告')}")
        lines.append("")
        lines.append(f"**作者:** {metadata.get('author', '')}")
        lines.append(f"**生成时间:** {metadata.get('generation_time', '')}")
        lines.append("")

        # 摘要
        summary = report_data.get('summary', {})
        if summary:
            lines.append("## 📊 分析摘要")
            lines.append("")

            key_findings = summary.get('key_findings', [])
            if key_findings:
                lines.append("### 关键发现")
                for finding in key_findings:
                    lines.append(f"- {finding}")
                lines.append("")

        # 数据集
        datasets = report_data.get('datasets', {})
        if datasets:
            lines.append("## 📁 数据集详情")
            lines.append("")

            for name, data in datasets.items():
                lines.append(f"### {name}")
                lines.append(f"- **类型:** {data.get('type', '')}")
                lines.append(f"- **记录数:** {data.get('record_count', 0):,}")
                lines.append(f"- **字段数:** {data.get('column_count', 0)}")

                if data.get('geometry_type'):
                    lines.append(f"- **几何类型:** {data['geometry_type']}")

                lines.append("")

        # 统计信息
        stats = report_data.get('statistics', {})
        if stats:
            lines.append("## 📈 统计信息")
            lines.append("")
            lines.append(f"- **总数据集:** {stats.get('total_datasets', 0)}")
            lines.append(f"- **总记录数:** {stats.get('total_records', 0):,}")
            lines.append(f"- **总几何对象:** {stats.get('total_geometries', 0):,}")
            lines.append("")

        return "\n".join(lines)


class ExcelTemplateEngine:
    """
    Excel模板引擎

    生成Excel格式的分析报告。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化Excel模板引擎

        Args:
            config: 配置字典
        """
        self.config = config or {}

    def render_report(self, report_data: Dict[str, Any], output_path: Path) -> Optional[str]:
        """
        渲染Excel报告

        Args:
            report_data: 报告数据
            output_path: 输出路径

        Returns:
            Optional[str]: 生成的文件路径
        """
        try:
            import pandas as pd

            # 创建多个工作表的数据
            with pd.ExcelWriter(output_path / 'analysis_report.xlsx', engine='openpyxl') as writer:
                # 摘要工作表
                self._create_summary_sheet(report_data, writer)

                # 数据集工作表
                self._create_datasets_sheet(report_data, writer)

                # 统计工作表
                self._create_statistics_sheet(report_data, writer)

                # 质量评估工作表
                self._create_quality_sheet(report_data, writer)

            excel_file = output_path / 'analysis_report.xlsx'
            logger.info(f"Excel报告生成成功: {excel_file}")
            return str(excel_file)

        except Exception as e:
            logger.error(f"Excel报告生成失败: {str(e)}")
            return None

    def _create_summary_sheet(self, report_data: Dict[str, Any], writer):
        """创建摘要工作表"""
        summary = report_data.get('summary', {})
        metadata = report_data.get('metadata', {})

        summary_data = {
            '项目': ['报告标题', '作者', '生成时间'],
            '值': [
                metadata.get('title', ''),
                metadata.get('author', ''),
                metadata.get('generation_time', '')
            ]
        }

        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='摘要', index=False)

    def _create_datasets_sheet(self, report_data: Dict[str, Any], writer):
        """创建数据集工作表"""
        datasets = report_data.get('datasets', {})

        if not datasets:
            return

        dataset_list = []
        for name, data in datasets.items():
            dataset_info = {
                '数据集名称': name,
                '类型': data.get('type', ''),
                '记录数': data.get('record_count', 0),
                '字段数': data.get('column_count', 0),
                '几何类型': data.get('geometry_type', ''),
                '坐标系统': str(data.get('coordinate_system', '')) if data.get('coordinate_system') else ''
            }
            dataset_list.append(dataset_info)

        datasets_df = pd.DataFrame(dataset_list)
        datasets_df.to_excel(writer, sheet_name='数据集', index=False)

    def _create_statistics_sheet(self, report_data: Dict[str, Any], writer):
        """创建统计工作表"""
        stats = report_data.get('statistics', {})

        stats_data = {
            '统计项': ['总数据集', '总记录数', '总几何对象', '数据体积(字节)'],
            '值': [
                stats.get('total_datasets', 0),
                stats.get('total_records', 0),
                stats.get('total_geometries', 0),
                stats.get('data_volume', 0)
            ]
        }

        stats_df = pd.DataFrame(stats_data)
        stats_df.to_excel(writer, sheet_name='统计信息', index=False)

    def _create_quality_sheet(self, report_data: Dict[str, Any], writer):
        """创建质量评估工作表"""
        quality = report_data.get('quality_assessment', {})

        if not quality:
            return

        quality_data = {
            '评估项': ['总体评分', '质量等级'],
            '结果': [
                quality.get('overall_score', 0),
                self._get_quality_level_text(quality.get('overall_score', 0))
            ]
        }

        quality_df = pd.DataFrame(quality_data)
        quality_df.to_excel(writer, sheet_name='质量评估', index=False)

    def _get_quality_level_text(self, score: float) -> str:
        """获取质量等级文本"""
        if score >= 90:
            return '优秀'
        elif score >= 80:
            return '良好'
        elif score >= 70:
            return '中等'
        elif score >= 60:
            return '及格'
        else:
            return '需要改进'