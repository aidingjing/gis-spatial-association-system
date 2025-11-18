"""
仪表板生成器

生成综合性的HTML仪表板，集成所有可视化结果。

特点:
- 响应式设计
- 交互式组件
- 多图表集成
- 自定义主题
- 导出功能

作者: GIS空间关联系统开发团队
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class DashboardGenerator:
    """
    仪表板生成器

    生成包含所有可视化的综合仪表板。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def generate_dashboard(self, dashboard_data: Dict[str, Any], output_path: Path) -> Optional[str]:
        """生成HTML仪表板"""
        try:
            # 生成HTML内容
            html_content = self._generate_dashboard_html(dashboard_data)

            # 保存仪表板
            dashboard_file = output_path / 'visualization_dashboard.html'
            with open(dashboard_file, 'w', encoding='utf-8') as f:
                f.write(html_content)

            logger.info(f"✅ 仪表板生成成功: {dashboard_file}")
            return str(dashboard_file)

        except Exception as e:
            logger.error(f"生成仪表板失败: {str(e)}")
            return None

    def _generate_dashboard_html(self, data: Dict[str, Any]) -> str:
        """生成仪表板HTML"""
        template = self._get_dashboard_template()

        # 替换模板变量
        replacements = {
            '{{TITLE}}': data.get('title', '可视化仪表板'),
            '{{GENERATION_TIME}}': data.get('generation_time', ''),
            '{{MAPS_SECTION}}': self._render_maps_section(data.get('maps', [])),
            '{{CHARTS_SECTION}}': self._render_charts_section(data.get('charts', [])),
            '{{NETWORKS_SECTION}}': self._render_networks_section(data.get('networks', [])),
            '{{SUMMARY_SECTION}}': self._render_summary_section(data.get('summary', {})),
            '{{METADATA_SECTION}}': self._render_metadata_section(data.get('metadata', {}))
        }

        html_content = template
        for placeholder, value in replacements.items():
            html_content = html_content.replace(placeholder, value)

        return html_content

    def _render_maps_section(self, maps: List[Dict[str, Any]]) -> str:
        """渲染地图部分"""
        if not maps:
            return ""

        html = '<div class="maps-section"><h2>🗺️ 地图可视化</h2><div class="maps-grid">'

        for map_viz in maps:
            if map_viz.get('format') == 'html':
                html += f'''
                <div class="viz-card">
                    <h3>{map_viz.get('title', '')}</h3>
                    <iframe src="{Path(map_viz['file_path']).name}" width="100%" height="400"></iframe>
                    <p>{map_viz.get('description', '')}</p>
                </div>
                '''
            else:
                html += f'''
                <div class="viz-card">
                    <h3>{map_viz.get('title', '')}</h3>
                    <img src="{Path(map_viz['file_path']).name}" alt="{map_viz.get('title', '')}" style="width: 100%;">
                    <p>{map_viz.get('description', '')}</p>
                </div>
                '''

        html += '</div></div>'
        return html

    def _render_charts_section(self, charts: List[Dict[str, Any]]) -> str:
        """渲染图表部分"""
        if not charts:
            return ""

        html = '<div class="charts-section"><h2>📊 统计图表</h2><div class="charts-grid">'

        for chart in charts:
            html += f'''
            <div class="viz-card">
                <h3>{chart.get('title', '')}</h3>
                <img src="{Path(chart['file_path']).name}" alt="{chart.get('title', '')}" style="width: 100%;">
                <p>{chart.get('description', '')}</p>
            </div>
            '''

        html += '</div></div>'
        return html

    def _render_networks_section(self, networks: List[Dict[str, Any]]) -> str:
        """渲染网络图部分"""
        if not networks:
            return ""

        html = '<div class="networks-section"><h2>🔗 网络关系图</h2><div class="networks-grid">'

        for network in networks:
            html += f'''
            <div class="viz-card">
                <h3>{network.get('title', '')}</h3>
                <img src="{Path(network['file_path']).name}" alt="{network.get('title', '')}" style="width: 100%;">
                <p>{network.get('description', '')}</p>
            </div>
            '''

        html += '</div></div>'
        return html

    def _render_summary_section(self, summary: Dict[str, Any]) -> str:
        """渲染摘要部分"""
        if not summary:
            return ""

        html = f'''
        <div class="summary-section">
            <h2>📈 可视化摘要</h2>
            <div class="summary-stats">
                <div class="stat-item">
                    <span class="stat-number">{summary.get('total_visualizations', 0)}</span>
                    <span class="stat-label">总可视化数</span>
                </div>
                <div class="stat-item">
                    <span class="stat-number">{summary.get('map_count', 0)}</span>
                    <span class="stat-label">地图</span>
                </div>
                <div class="stat-item">
                    <span class="stat-number">{summary.get('chart_count', 0)}</span>
                    <span class="stat-label">图表</span>
                </div>
                <div class="stat-item">
                    <span class="stat-number">{summary.get('network_count', 0)}</span>
                    <span class="stat-label">网络图</span>
                </div>
            </div>
        </div>
        '''

        return html

    def _render_metadata_section(self, metadata: Dict[str, Any]) -> str:
        """渲染元数据部分"""
        if not metadata:
            return ""

        html = f'''
        <div class="metadata-section">
            <h2>ℹ️ 元数据</h2>
            <ul>
                <li>数据集数量: {metadata.get('total_datasets', 0)}</li>
                <li>包含空间数据: {'是' if metadata.get('has_geospatial_data') else '否'}</li>
                <li>包含关联数据: {'是' if metadata.get('has_association_data') else '否'}</li>
                <li>包含质量数据: {'是' if metadata.get('has_quality_data') else '否'}</li>
            </ul>
        </div>
        '''

        return html

    def _get_dashboard_template(self) -> str:
        """获取仪表板HTML模板"""
        return '''
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
            background-color: #f5f5f5;
        }

        .container {
            max-width: 1400px;
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

        .viz-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }

        .maps-grid, .charts-grid, .networks-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
        }

        .viz-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }

        .viz-card h3 {
            color: #333;
            margin-bottom: 15px;
            font-size: 1.3em;
        }

        .viz-card img {
            border-radius: 5px;
            max-width: 100%;
            height: auto;
        }

        .viz-card iframe {
            border: none;
            border-radius: 5px;
        }

        .summary-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }

        .stat-item {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }

        .stat-number {
            font-size: 2em;
            font-weight: bold;
            display: block;
        }

        .stat-label {
            font-size: 0.9em;
            opacity: 0.9;
        }

        .metadata-section ul {
            list-style: none;
            padding: 0;
        }

        .metadata-section li {
            background: #f8f9fa;
            padding: 10px 15px;
            margin: 5px 0;
            border-radius: 5px;
            border-left: 4px solid #667eea;
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

            .viz-grid,
            .maps-grid,
            .charts-grid,
            .networks-grid {
                grid-template-columns: 1fr;
            }
        }

        .loading {
            text-align: center;
            padding: 20px;
            color: #666;
        }

        .error {
            background: #f8d7da;
            color: #721c24;
            padding: 15px;
            border-radius: 5px;
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🗺️ {{TITLE}}</h1>
            <div class="meta">
                <p>生成时间: {{GENERATION_TIME}}</p>
            </div>
        </div>

        {{SUMMARY_SECTION}}
        {{MAPS_SECTION}}
        {{CHARTS_SECTION}}
        {{NETWORKS_SECTION}}
        {{METADATA_SECTION}}
    </div>

    <script>
        // 添加简单的交互功能
        document.addEventListener('DOMContentLoaded', function() {
            console.log('仪表板加载完成');
        });
    </script>
</body>
</html>
        '''