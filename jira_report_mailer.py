"""
JIRA Sprint Reporter - Enhanced Email Version
==============================================
Generates comprehensive sprint reports with screenshots for email delivery.

Features:
- Fetches sprint data from JIRA Agile API (rest/agile/1.0/)
- Generates interactive HTML reports with charts and tables
- Automatically captures screenshots of report sections
- Creates email-friendly HTML with embedded images
- Supports both Outlook and SMTP email delivery
- Configurable via environment variables
- Headless browser screenshot capture using Playwright
- Automatic image resizing and optimization
- Table-based email layout for maximum compatibility
- Section-based screenshot capture (summary, charts, tables)
"""

import os
import sys
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path
import base64
import io
import tempfile

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from dotenv import load_dotenv
from PIL import Image

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid."""
    pass


class JIRAConfig:
    """Manages JIRA configuration from environment variables."""

    REQUIRED_VARS = [
        'JIRA_BASE_URL',
        'JIRA_API_KEY',
        'JIRA_USERNAME',
        'JIRA_BOARD_ID',
        'JIRA_SPRINT_ID',
        'JIRA_PROJECT',
        'SPRINT_NAME'
    ]

    def __init__(self):
        load_dotenv()
        self._validate_config()
        self._load_config()

    def _validate_config(self):
        """Validate that all required environment variables are set."""
        missing_vars = [var for var in self.REQUIRED_VARS if not os.getenv(var)]
        if missing_vars:
            raise ConfigurationError(
                f"Missing required environment variables: {', '.join(missing_vars)}\n"
                f"Please set them in your .env file."
            )

    def _load_config(self):
        """Load configuration from environment variables."""
        self.base_url = os.getenv('JIRA_BASE_URL').rstrip('/')
        self.api_token = os.getenv('JIRA_API_KEY')
        self.username = os.getenv('JIRA_USERNAME')
        self.board_id = os.getenv('JIRA_BOARD_ID')
        self.sprint_id = os.getenv('JIRA_SPRINT_ID')
        self.project_key = os.getenv('JIRA_PROJECT')
        self.sprint_name = os.getenv('SPRINT_NAME')

        # Optional email configuration
        self.email_recipients = os.getenv('EMAIL_RECIPIENTS', '').split(',')
        self.email_recipients = [r.strip() for r in self.email_recipients if r.strip()]

        self.email_cc_recipients = os.getenv('EMAIL_CC_RECIPIENTS', '').split(',')
        self.email_cc_recipients = [r.strip() for r in self.email_cc_recipients if r.strip()]

        # SMTP configuration (optional)
        self.smtp_server = os.getenv('SMTP_SERVER')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.email_user = os.getenv('EMAIL_USER')
        self.email_password = os.getenv('EMAIL_PASSWORD')

        # Issue type configuration
        self.story_types = os.getenv('STORY_TYPES', 'Story').split(',')
        self.defect_types = os.getenv('DEFECT_TYPES', 'Escaped Defect,Bug,Defect').split(',')
        self.story_types = [t.strip() for t in self.story_types]
        self.defect_types = [t.strip() for t in self.defect_types]

        # Screenshot configuration
        self.screenshot_width = int(os.getenv('SCREENSHOT_WIDTH', '1400'))
        self.email_image_max_width = int(os.getenv('EMAIL_IMAGE_MAX_WIDTH', '1000'))


class JIRAClient:
    """Handles JIRA Agile API interactions."""

    def __init__(self, config: JIRAConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'Authorization': self._construct_auth_header()
        })

    def _construct_auth_header(self) -> str:
        """Construct Basic Auth header from credentials."""
        credentials = f"{self.config.username}:{self.config.api_token}"
        encoded = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        return f"Basic {encoded}"

    def fetch_sprint_issues(self, max_results: int = 50) -> List[Dict]:
        """
        Fetch all issues from the sprint using Agile API.
        Uses the /rest/agile/1.0/sprint/{sprintId}/issue endpoint.

        Args:
            max_results: Number of results per page

        Returns:
            List of issue dictionaries
        """
        api_url = f"{self.config.base_url}/rest/agile/1.0/sprint/{self.config.sprint_id}/issue"

        all_issues = []
        start_at = 0

        logger.info(f"Fetching sprint issues from: {api_url}")

        while True:
            params = {
                'startAt': start_at,
                'maxResults': max_results,
                'fields': 'key,summary,status,assignee,updated,issuetype,priority,created,reporter'
            }

            try:
                response = self.session.get(api_url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                with open("response.json", 'w') as f:
                    f.write(str(data))
                issues = data.get('issues', [])
                all_issues.extend(issues)

                total = data.get('total', 0)
                logger.info(f"Fetched {len(all_issues)}/{total} issues")

                if len(issues) < max_results:
                    break

                start_at += max_results

            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching issues: {e}")
                raise

        logger.info(f"Total sprint issues fetched: {len(all_issues)}")
        return all_issues


class IssueParser:
    """Parses JIRA issues into structured DataFrames."""

    @staticmethod
    def parse_issues(issues: List[Dict]) -> pd.DataFrame:
        """
        Parse JIRA issues into a pandas DataFrame.

        Args:
            issues: List of issue dictionaries from JIRA API

        Returns:
            DataFrame with parsed issue data
        """
        if not issues:
            logger.warning("No issues to parse")
            return pd.DataFrame()

        data = []
        for issue in issues:
            try:
                fields = issue.get('fields', {})

                assignee = fields.get('assignee')
                assignee_name = assignee.get('displayName') if assignee else 'Unassigned'

                reporter = fields.get('reporter')
                reporter_name = reporter.get('displayName') if reporter else 'Unknown'

                status = fields.get('status', {})
                status_name = status.get('name', 'Unknown')

                issuetype = fields.get('issuetype', {})
                issue_type_name = issuetype.get('name', 'Unknown')

                priority = fields.get('priority', {})
                priority_name = priority.get('name', 'None') if priority else 'None'

                updated_str = fields.get('updated', '')
                created_str = fields.get('created', '')

                updated_date = datetime.strptime(updated_str[:10], '%Y-%m-%d') if updated_str else None
                created_date = datetime.strptime(created_str[:10], '%Y-%m-%d') if created_str else None

                data.append({
                    'Task ID': issue.get('key', ''),
                    'Task Name': fields.get('summary', ''),
                    'Status': status_name,
                    'Assigned To': assignee_name,
                    'Reporter': reporter_name,
                    'Issue Type': issue_type_name,
                    'Priority': priority_name,
                    'Created': created_date,
                    'Last Updated': updated_date
                })

            except Exception as e:
                logger.warning(f"Error parsing issue {issue.get('key', 'unknown')}: {e}")
                continue

        df = pd.DataFrame(data)

        if not df.empty and 'Last Updated' in df.columns:
            df = df.sort_values('Last Updated', ascending=False)

        return df


class ReportGenerator:
    """Generates HTML reports with interactive visualizations."""

    def __init__(self, config: JIRAConfig):
        self.config = config

    def generate_html_report(
            self,
            story_df: pd.DataFrame,
            defect_df: pd.DataFrame,
            output_file: str = 'sprint_report.html'
    ) -> str:
        """
        Generate comprehensive HTML report with visualizations.

        Args:
            story_df: DataFrame containing story issues
            defect_df: DataFrame containing defect issues
            output_file: Path to output HTML file

        Returns:
            Path to generated HTML file
        """
        logger.info(f"Generating HTML report: {output_file}")

        # Create visualizations
        charts_html = self._generate_charts(story_df, defect_df)

        # Generate summary statistics
        summary_html = self._generate_summary_stats(story_df, defect_df)

        # Generate tables
        tables_html = self._generate_tables(story_df, defect_df)

        # Combine into full HTML report
        html_content = self._create_html_template(
            summary_html,
            charts_html,
            tables_html
        )

        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        logger.info(f"HTML report generated successfully: {output_file}")
        return output_file

    def _generate_summary_stats(
            self,
            story_df: pd.DataFrame,
            defect_df: pd.DataFrame
    ) -> str:
        """Generate summary statistics HTML."""
        total_stories = len(story_df)
        total_defects = len(defect_df)

        stories_done = len(story_df[story_df['Status'].str.contains('Done|Closed|Resolved', case=False,
                                                                    na=False)]) if not story_df.empty else 0
        stories_in_progress = len(story_df[story_df['Status'].str.contains('In Progress|Development', case=False,
                                                                           na=False)]) if not story_df.empty else 0
        stories_todo = total_stories - stories_done - stories_in_progress

        defects_open = len(defect_df[~defect_df['Status'].str.contains('Done|Closed|Resolved', case=False,
                                                                       na=False)]) if not defect_df.empty else 0
        defects_closed = total_defects - defects_open

        story_completion = (stories_done / total_stories * 100) if total_stories > 0 else 0
        defect_resolution = (defects_closed / total_defects * 100) if total_defects > 0 else 0

        return f"""
        <div class="summary-cards" id="summary-section">
            <div class="summary-card">
                <h3>Total Stories</h3>
                <div class="big-number">{total_stories}</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {story_completion}%"></div>
                </div>
                <div class="stat-detail">{stories_done} Done • {stories_in_progress} In Progress • {stories_todo} To Do</div>
            </div>

            <div class="summary-card">
                <h3>Total Defects</h3>
                <div class="big-number">{total_defects}</div>
                <div class="progress-bar">
                    <div class="progress-fill defect" style="width: {defect_resolution}%"></div>
                </div>
                <div class="stat-detail">{defects_closed} Resolved • {defects_open} Open</div>
            </div>

            <div class="summary-card">
                <h3>Completion Rate</h3>
                <div class="big-number">{story_completion:.1f}%</div>
                <div class="stat-detail">Story Completion</div>
            </div>

            <div class="summary-card">
                <h3>Defect Resolution</h3>
                <div class="big-number">{defect_resolution:.1f}%</div>
                <div class="stat-detail">Defects Resolved</div>
            </div>
        </div>
        """

    def _generate_charts(
            self,
            story_df: pd.DataFrame,
            defect_df: pd.DataFrame
    ) -> str:
        """Generate all charts for the report."""
        charts_html = ""

        # Story charts
        if not story_df.empty:
            story_status_chart = self._create_status_chart(story_df, "Stories")
            story_assignee_chart = self._create_assignee_chart(story_df, "Stories")
            charts_html += f"""
            <div class="chart-section" id="story-charts-section">
                <h2>📊 Story Metrics</h2>
                <div class="charts-row">
                    <div class="chart-container" id="story-status-chart">
                        {story_status_chart}
                    </div>
                    <div class="chart-container" id="story-assignee-chart">
                        {story_assignee_chart}
                    </div>
                </div>
            </div>
            """

        # Defect charts
        if not defect_df.empty:
            defect_status_chart = self._create_status_chart(defect_df, "Defects")
            defect_assignee_chart = self._create_assignee_chart(defect_df, "Defects")
            defect_priority_chart = self._create_priority_chart(defect_df)

            charts_html += f"""
            <div class="chart-section" id="defect-charts-section">
                <h2>🐛 Defect Metrics</h2>
                <div class="charts-row">
                    <div class="chart-container" id="defect-status-chart">
                        {defect_status_chart}
                    </div>
                    <div class="chart-container" id="defect-assignee-chart">
                        {defect_assignee_chart}
                    </div>
                </div>
                <div class="charts-row">
                    <div class="chart-container full-width" id="defect-priority-chart">
                        {defect_priority_chart}
                    </div>
                </div>
            </div>
            """

        return charts_html

    def _create_status_chart(self, df: pd.DataFrame, title: str) -> str:
        """Create status distribution chart."""
        if df.empty:
            return "<p>No data available</p>"

        # Get status counts
        status_counts = df['Status'].value_counts()

        # === COMPREHENSIVE DEBUGGING ===
        print(f"\n{'=' * 60}")
        print(f"DEBUG: Creating {title} Chart")
        print(f"{'=' * 60}")
        print(f"Total rows in DataFrame: {len(df)}")
        print(f"Unique statuses: {df['Status'].nunique()}")
        print(f"\nStatus breakdown:")
        for status, count in status_counts.items():
            percentage = (count / status_counts.sum()) * 100
            print(f"  {status:20s}: {count:3d} ({percentage:5.1f}%)")
        print(f"\nTotal: {status_counts.sum()}")

        # Verify the data types
        print(f"\nData types:")
        print(f"  status_counts.index type: {type(status_counts.index)}")
        print(f"  status_counts.values type: {type(status_counts.values)}")
        print(f"  First value type: {type(status_counts.values[0])}")

        # Check for any NaN or infinite values
        if status_counts.isna().any():
            print("WARNING: NaN values detected in counts!")
        if (status_counts == 0).any():
            print("WARNING: Zero values detected in counts!")

        print(f"{'=' * 60}\n")
        # === END DEBUGGING ===

        color_map = {
            'Done': '#28a745',
            'Closed': '#20c997',
            'Resolved': '#17a2b8',
            'In Progress': '#ffc107',
            'Development': '#fd7e14',
            'To Do': '#6c757d',
            'Open': '#dc3545',
            'Reopened': '#e83e8c',
            'FORMAL TEST': '#007bff',
            'INFORMAL TEST': '#6610f2'
        }

        colors = [color_map.get(status, f'#{hash(status) % 0xFFFFFF:06x}') for status in status_counts.index]

        fig = go.Figure(data=[go.Pie(
            labels=status_counts.index.tolist(),  # Convert to list explicitly
            values=status_counts.values.tolist(),  # Convert to list explicitly
            marker=dict(colors=colors, line=dict(color='white', width=2)),
            hole=0.4,
            textinfo='label+percent',
            textposition='outside',
            textfont=dict(size=11),
            hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>',
        )])

        fig.update_layout(
            title=dict(text=f"{title} - Status Distribution", x=0.5, xanchor='center'),
            showlegend=True,
            legend=dict(orientation="v", yanchor="bottom", y=0.5, xanchor="left", x=1.5),
            height=500,
            margin=dict(t=80, b=100, l=40, r=40),
            autosize=True
        )

        return fig.to_html(full_html=False, include_plotlyjs=False)

    def _create_assignee_chart(self, df: pd.DataFrame, title: str) -> str:
        """Create assignee distribution chart."""
        if df.empty:
            return "<p>No data available</p>"

        # Determine all unique assignees and ensure 'Unassigned' is included
        all_assignees = df['Assigned To'].unique().tolist()
        if 'Unassigned' not in all_assignees:
            all_assignees.append('Unassigned')  # Ensure 'Unassigned' is included

        # Calculate assignee counts and reindex to include all assignees
        assignee_counts = df['Assigned To'].value_counts()
        assignee_counts = assignee_counts.reindex(all_assignees, fill_value=0)

        # Convert reindexed data to list explicitly to avoid dropping the last value
        assignee_names = list(assignee_counts.index)
        assignee_values = list(assignee_counts.values)

        # Create bar chart with explicit horizontal orientation
        fig = go.Figure(data=[go.Bar(
            x=assignee_values,  # Number of tasks go on the x-axis
            y=assignee_names,  # Assignees go on the y-axis
            orientation='h',  # Horizontal bars
            marker=dict(
                color=assignee_values,  # Assign colors dynamically based on task counts
                colorscale='Viridis',  # Choose a color scale (e.g., 'Viridis', 'Blues', 'Plasma', etc.)
                showscale=True
            ),
            text=assignee_values,  # Display counts on bars
            textposition='auto',  # Position of text
            hovertemplate='<b>%{y}</b> Tasks: %{x} < extra > < / extra > '  # Hover text formatting
        )])

        # Update layout for better visualization
        fig.update_layout(
            title=f"{title} - Assignment Distribution",
            xaxis_title="Number of Tasks",
            yaxis_title="",  # No title for the y-axis
            height=400,  # Chart height
            margin=dict(t=50, b=50, l=150, r=20),  # Margins
        )

        # Return the figure as HTML
        return fig.to_html(full_html=False, include_plotlyjs=False)

    def _create_priority_chart(self, df: pd.DataFrame) -> str:
        """Create priority distribution chart for defects."""
        if df.empty:
            return "<p>No data available</p>"

        # Calculate priority counts
        priority_counts = df['Priority'].value_counts()
        all_priorities = ['Highest', 'High', 'Medium', 'Low', 'None']
        priority_counts = priority_counts.reindex(all_priorities, fill_value=0)

        # Define color mapping for priorities
        priority_colors = {
            'Highest': '#dc3545',
            'High': '#fd7e14',
            'Medium': '#ffc107',
            'Low': '#28a745',
            'None': '#e9ecef'
        }

        # Map colors to priorities
        colors = [priority_colors.get(p, '#007bff') for p in priority_counts.index]

        # Create bar chart with explicit vertical orientation
        fig = go.Figure(data=[go.Bar(
            x=priority_counts.index,  # Categories (priorities) go on the x-axis
            y=priority_counts.values,  # Counts go on the y-axis
            marker=dict(color=colors),  # Assign colors to bars
            text=priority_counts.values,  # Display counts on bars
            textposition='auto',  # Text position
            hovertemplate='<b>Priority: %{x}</b> Count: %{y} < extra > < / extra > ',
                orientation = 'v'  # Explicitly set orientation to vertical
                )])

        # Update layout for better visualization
        fig.update_layout(
            title="Defects - Priority Distribution",
            xaxis_title="Priority",  # Priority labels on x-axis
            yaxis_title="Count",  # Counts on y-axis
            height=350,  # Chart height
            margin=dict(t=50, b=50, l=50, r=20),  # Margins
            xaxis=dict(categoryorder="array", categoryarray=list(priority_colors.keys())),  # Preserve priority order
        )

        # Return the figure as HTML
        return fig.to_html(full_html=False, include_plotlyjs=False)

    def _generate_tables(self, story_df: pd.DataFrame, defect_df: pd.DataFrame) -> str:
        """Generate interactive tables."""
        tables_html = ""

        date_columns = ['Created', 'Last Updated']

        if not story_df.empty:
            story_display = story_df.copy()
            for col in date_columns:
                if col in story_display.columns:
                    story_display[col] = story_display[col].dt.strftime('%Y-%m-%d')

            tables_html += f"""
            <div class="table-section" id="stories-table-section">
                <h2>📝 Stories ({len(story_df)} total)</h2>
                <table id="stories_table" class="display data-table">
                    <thead>
                        <tr>
                            {''.join(f'<th>{col}</th>' for col in story_display.columns)}
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(
                '<tr>' + ''.join(f'<td>{cell}</td>' for cell in row) + '</tr>'
                for _, row in story_display.iterrows()
            )}
                    </tbody>
                </table>
            </div>
            """

        if not defect_df.empty:
            defect_display = defect_df.copy()
            for col in date_columns:
                if col in defect_display.columns:
                    defect_display[col] = defect_display[col].dt.strftime('%Y-%m-%d')

            tables_html += f"""
            <div class="table-section" id="defects-table-section">
                <h2>🐛 Defects ({len(defect_df)} total)</h2>
                <table id="defects_table" class="display data-table">
                    <thead>
                        <tr>
                            {''.join(f'<th>{col}</th>' for col in defect_display.columns)}
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(
                '<tr>' + ''.join(f'<td>{cell}</td>' for cell in row) + '</tr>'
                for _, row in defect_display.iterrows()
            )}
                    </tbody>
                </table>
            </div>
            """

        return tables_html

    def _create_html_template(
            self,
            summary_html: str,
            charts_html: str,
            tables_html: str
    ) -> str:
        """Create complete HTML template."""

        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sprint Report - {self.config.sprint_name}</title>

    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">

    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js" charset="utf-8"></script>
    <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js"></script>

    <style>
        :root {{
            --primary-color: #0066cc;
            --secondary-color: #6c757d;
            --success-color: #28a745;
            --warning-color: #ffc107;
            --danger-color: #dc3545;
            --light-bg: #f8f9fa;
            --dark-text: #212529;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: var(--dark-text);
            line-height: 1.6;
            padding: 20px;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
            overflow: hidden;
        }}

        .header {{
            background: linear-gradient(135deg, var(--primary-color) 0%, #004999 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}

        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
            font-weight: 700;
        }}

        .header .meta-info {{
            font-size: 1rem;
            opacity: 0.9;
        }}

        .content {{
            padding: 40px;
        }}

        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}

        .summary-card {{
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}

        .summary-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 15px rgba(0, 0, 0, 0.2);
        }}

        .summary-card h3 {{
            font-size: 1rem;
            color: var(--secondary-color);
            margin-bottom: 15px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .big-number {{
            font-size: 3rem;
            font-weight: 700;
            color: var(--primary-color);
            margin-bottom: 15px;
        }}

        .progress-bar {{
            height: 8px;
            background: #e9ecef;
            border-radius: 4px;
            overflow: hidden;
            margin-bottom: 10px;
        }}

        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, var(--success-color) 0%, #20c997 100%);
            transition: width 1s ease;
        }}

        .progress-fill.defect {{
            background: linear-gradient(90deg, var(--warning-color) 0%, #fd7e14 100%);
        }}

        .stat-detail {{
            font-size: 0.9rem;
            color: var(--secondary-color);
        }}

        .chart-section {{
            margin-bottom: 50px;
        }}

        .chart-section h2 {{
            font-size: 1.8rem;
            margin-bottom: 25px;
            color: var(--dark-text);
            border-bottom: 3px solid var(--primary-color);
            padding-bottom: 10px;
        }}

        .charts-row {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 30px;
            margin-bottom: 30px;
        }}

        .chart-container {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }}

        .chart-container.full-width {{
            grid-column: 1 / -1;
        }}

        .table-section {{
            margin-bottom: 50px;
        }}

        .table-section h2 {{
            font-size: 1.8rem;
            margin-bottom: 20px;
            color: var(--dark-text);
            border-bottom: 3px solid var(--primary-color);
            padding-bottom: 10px;
        }}

        .data-table {{
            width: 100% !important;
            font-size: 0.9rem;
        }}

        .data-table thead th {{
            background: var(--primary-color);
            color: white;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.85rem;
            letter-spacing: 0.5px;
            padding: 12px 8px;
        }}

        .data-table tbody td {{
            padding: 10px 8px;
            vertical-align: middle;
        }}

        .data-table tbody tr:hover {{
            background-color: #f1f3f5;
        }}

        .footer {{
            background: #2c3e50;
            color: white;
            text-align: center;
            padding: 25px;
            font-size: 0.9rem;
        }}

        @media (max-width: 768px) {{
            .header h1 {{
                font-size: 2rem;
            }}

            .charts-row {{
                grid-template-columns: 1fr;
            }}

            .summary-cards {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header" id="header-section">
            <h1><i class="fas fa-chart-line"></i> Sprint Report</h1>
            <div class="meta-info">
                <strong>{self.config.sprint_name}</strong>

                Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
            </div>
        </div>

        <div class="content">
            {summary_html}
            {charts_html}
            {tables_html}
        </div>

        <div class="footer">
            <p><i class="fas fa-code"></i> Auto-generated Sprint Report | JIRA Agile API Integration</p>
            <p>&copy; {datetime.now().year} - Powered by Python & Plotly</p>
        </div>
    </div>

    <script>
        $(document).ready(function() {{
            $('.data-table').DataTable({{
                pageLength: 25,
                order: [[8, 'desc']],
                responsive: true,
                language: {{
                    search: "Filter records:",
                    lengthMenu: "Show _MENU_ entries per page",
                    info: "Showing _START_ to _END_ of _TOTAL_ entries"
                }}
            }});
        }});
    </script>
</body>
</html>
"""


# ============================================================================
# NEW CLASSES: Screenshot Capture & Email Report Builder
# ============================================================================

class ReportScreenshotter:
    """Captures screenshots of HTML report sections using Playwright."""

    def __init__(self, config: JIRAConfig):
        self.config = config
        self.screenshot_dir = Path('report_screenshots')
        self.screenshot_dir.mkdir(exist_ok=True)

    def capture_report_sections(self, html_file: str) -> Dict[str, str]:
        """
        Capture screenshots of different report sections.

        Args:
            html_file: Path to HTML report file

        Returns:
            Dictionary mapping section names to screenshot file paths
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("Playwright not installed. Install with: pip install playwright")
            logger.error("Then run: playwright install chromium")
            raise ImportError("Playwright is required for screenshot capture")

        logger.info("Starting screenshot capture...")

        screenshots = {}
        html_path = Path(html_file).absolute()

        with sync_playwright() as p:
            # Check if custom chromium path is provided
            chromium_path = os.getenv('CHROMIUM_PATH')

            if chromium_path and os.path.exists(chromium_path):
                logger.info(f"Using custom Chromium from: {chromium_path}")
                browser = p.chromium.launch(
                    executable_path=chromium_path,
                    headless=True
                )
            else:
                logger.info("Using Playwright-managed Chromium")
                browser = p.chromium.launch(headless=True)

            page = browser.new_page(viewport={'width': self.config.screenshot_width, 'height': 1080})

            page.wait_for_timeout(1500)

            # Load the HTML file
            page.goto(f'file://{html_path}')

            # Wait for page to fully load (including plotly charts)
            page.wait_for_timeout(3000)  # 3 seconds for charts to render

            page.evaluate("""
            if (window.Plotly) {
            document.querySelectorAll('.js-plotly-plot').forEach(el => {
            Plotly.Plots.resize(el);
            });
            }
            """)

            page.wait_for_timeout(1000)
            # Capture header
            logger.info("Capturing header...")
            screenshots['header'] = self._capture_element(page, '#header-section', 'header.png')

            # Capture summary cards
            logger.info("Capturing summary section...")
            screenshots['summary'] = self._capture_element(page, '#summary-section', 'summary.png')

            # Capture story charts
            if page.query_selector('#story-charts-section'):
                logger.info("Capturing story charts...")
                screenshots['story_charts'] = self._capture_element(page, '#story-charts-section', 'story_charts.png')

            # Capture defect charts
            if page.query_selector('#defect-charts-section'):
                logger.info("Capturing defect charts...")
                screenshots['defect_charts'] = self._capture_element(page, '#defect-charts-section',
                                                                     'defect_charts.png')

            # Capture stories table
            if page.query_selector('#stories-table-section'):
                logger.info("Capturing stories table...")
                screenshots['stories_table'] = self._capture_element(page, '#stories-table-section',
                                                                     'stories_table.png')

            # Capture defects table
            if page.query_selector('#defects-table-section'):
                logger.info("Capturing defects table...")
                screenshots['defects_table'] = self._capture_element(page, '#defects-table-section',
                                                                     'defects_table.png')

            browser.close()

        logger.info(f"Captured {len(screenshots)} screenshots")
        return screenshots

    def _capture_element(self, page, selector: str, filename: str) -> str:
        """Capture screenshot of a specific element."""
        element = page.query_selector(selector)
        if element:
            screenshot_path = self.screenshot_dir / filename
            element.screenshot(path=str(screenshot_path))
            logger.info(f"  ✓ Saved: {filename}")
            return str(screenshot_path)
        else:
            logger.warning(f"  ✗ Element not found: {selector}")
            return None

    def resize_images(self, screenshots: Dict[str, str]) -> Dict[str, str]:
        """
        Resize images to be email-friendly.

        Args:
            screenshots: Dictionary of screenshot paths

        Returns:
            Dictionary of resized image paths
        """
        logger.info("Resizing images for email...")

        resized_dir = Path('report_screenshots_resized')
        resized_dir.mkdir(exist_ok=True)

        resized_screenshots = {}
        max_width = self.config.email_image_max_width

        for section, img_path in screenshots.items():
            if not img_path or not os.path.exists(img_path):
                continue

            try:
                with Image.open(img_path) as img:
                    # Calculate new dimensions
                    if img.width > max_width:
                        ratio = max_width / img.width
                        new_height = int(img.height * ratio)
                        img_resized = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                    else:
                        img_resized = img

                    # Save resized image
                    resized_path = resized_dir / Path(img_path).name
                    img_resized.save(resized_path, optimize=True, quality=85)
                    resized_screenshots[section] = str(resized_path)

                    logger.info(f"  ✓ Resized: {section}")

            except Exception as e:
                logger.error(f"  ✗ Error resizing {section}: {e}")
                resized_screenshots[section] = img_path  # Use original if resize fails

        return resized_screenshots


class EmailReportBuilder:
    """Builds email-friendly HTML reports with embedded images."""

    def __init__(self, config: JIRAConfig):
        self.config = config

    def build_email_html(self, screenshots: Dict[str, str]) -> str:
        """
        Build email-friendly HTML with embedded images.

        Args:
            screenshots: Dictionary of screenshot paths

        Returns:
            HTML content for email
        """
        logger.info("Building email-friendly HTML...")

        # Generate CID references for images
        image_sections = []

        # Header
        if 'header' in screenshots and screenshots['header']:
            image_sections.append({
                'cid': 'header',
                'path': screenshots['header'],
                'alt': 'Sprint Report Header'
            })

        # Summary
        if 'summary' in screenshots and screenshots['summary']:
            image_sections.append({
                'cid': 'summary',
                'path': screenshots['summary'],
                'alt': 'Sprint Summary'
            })

        # Story charts
        if 'story_charts' in screenshots and screenshots['story_charts']:
            image_sections.append({
                'cid': 'story_charts',
                'path': screenshots['story_charts'],
                'alt': 'Story Metrics'
            })

        # Defect charts
        if 'defect_charts' in screenshots and screenshots['defect_charts']:
            image_sections.append({
                'cid': 'defect_charts',
                'path': screenshots['defect_charts'],
                'alt': 'Defect Metrics'
            })

        # Stories table
        if 'stories_table' in screenshots and screenshots['stories_table']:
            image_sections.append({
                'cid': 'stories_table',
                'path': screenshots['stories_table'],
                'alt': 'Stories Table'
            })

        # Defects table
        if 'defects_table' in screenshots and screenshots['defects_table']:
            image_sections.append({
                'cid': 'defects_table',
                'path': screenshots['defects_table'],
                'alt': 'Defects Table'
            })

        # Build HTML with table layout
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sprint Report - {self.config.sprint_name}</title>
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
            background-color: #f4f4f4;
        }}

        .email-container {{
            max-width: 800px;
            margin: 0 auto;
            background-color: #ffffff;
        }}

        .section-image {{
            width: 100%;
            height: auto;
            display: block;
            margin: 0;
            padding: 0;
        }}

        .spacer {{
            height: 20px;
            background-color: #f4f4f4;
        }}
    </style>
</head>
<body>
    <table class="email-container" cellpadding="0" cellspacing="0" border="0" width="100%">
"""

        # Add each section as a row
        for idx, section in enumerate(image_sections):
            html_content += f"""
        <tr>
            <td align="center" style="padding: 0;">
                <img src="cid:{section['cid']}" alt="{section['alt']}" class="section-image" />
            </td>
        </tr>
"""
            # Add spacer between sections (except after last one)
            if idx < len(image_sections) - 1:
                html_content += """
        <tr>
            <td class="spacer"></td>
        </tr>
"""

        html_content += """
    </table>
</body>
</html>
"""

        return html_content


class EmailSender:
    """Handles email delivery via Outlook or SMTP with embedded screenshots."""

    def __init__(self, config: JIRAConfig):
        self.config = config

    def send_email_with_screenshots(
            self,
            screenshots: Dict[str, str],
            email_html: str,
            subject: Optional[str] = None
    ) -> bool:
        """
        Send email with embedded screenshot images.

        Args:
            screenshots: Dictionary of screenshot paths
            email_html: HTML content for email
            subject: Email subject

        Returns:
            True if sent successfully
        """
        if not self.config.email_recipients:
            logger.warning("No email recipients configured. Skipping email.")
            return False

        subject = subject or f"Sprint Report - {self.config.sprint_name}"

        # Try Outlook first
        try:
            return self._send_via_outlook(screenshots, email_html, subject)
        except Exception as e:
            logger.info(f"Outlook not available: {e}")

        #Fallback to SMTP
        if self.config.smtp_server:
            try:
                return self._send_via_smtp(screenshots, email_html, subject)
            except Exception as e:
                logger.error(f"SMTP send failed: {e}")
                return False

        logger.warning("No email method available")
        return False

    def _send_via_outlook(
            self,
            screenshots: Dict[str, str],
            email_html: str,
            subject: str
    ) -> bool:
        """Send email via Outlook (Windows only)."""
        try:
            import win32com.client as win32
        except ImportError:
            raise Exception("pywin32 not installed. Install with: pip install pywin32")

        logger.info("Creating Outlook email...")

        outlook = win32.Dispatch('Outlook.Application')
        logger.info("outlook Available.")
        mail = outlook.CreateItem(0)  # 0 = MailItem
        mail.Subject = subject
        mail.To = '; '.join(self.config.email_recipients)
        mail.Cc = '; '.join(self.config.email_cc_recipients)
        mail.BodyFormat = 2  # 2 = HTML format

        # Build HTML body with proper CID references for Outlook
        # Outlook uses cid:imagename.png format
        html_with_attachments = self._build_outlook_html(screenshots)
        mail.HTMLBody = html_with_attachments

        # Attach images and set them as inline/embedded
        attachment_index = 1
        logger.info("Starting Screen shot adding.")
        # Attach images as inline
        MAPI_PROP_CONTENT_ID = "http://schemas.microsoft.com/mapi/proptag/0x3712001F"
        MAPI_PROP_HIDDEN = "http://schemas.microsoft.com/mapi/proptag/0x7FFE000B"

        for section, img_path in screenshots.items():
            if not img_path or not os.path.exists(img_path):
                logger.warning(f"Skipping {section} — file not found: {img_path}")
                continue

            try:
                # ────────────────────────────────────────────────
                # Make absolutely sure we have a Windows-friendly path
                abs_path = os.path.abspath(img_path)  # resolves relative paths
                win_path = str(Path(abs_path).resolve())  # pathlib helps clean it
                win_path = win_path.replace('/', '\\')  # force backslashes

                if not os.path.exists(win_path):
                    logger.error(f"File really does not exist: {win_path}")
                    continue

                logger.debug(f"Attaching full path: {win_path}")

                attachment = mail.Attachments.Add(win_path)

                # Rest remains the same
                filename = os.path.basename(win_path)
                pr_attach_content_id = "http://schemas.microsoft.com/mapi/proptag/0x3712001F"
                attachment.PropertyAccessor.SetProperty(pr_attach_content_id, f"<{section}>")

                pr_attachment_hidden = "http://schemas.microsoft.com/mapi/proptag/0x7FFE000B"
                attachment.PropertyAccessor.SetProperty(pr_attachment_hidden, True)

                logger.info(f"  ✓ Attached: {filename} as CID:<{section}> from {win_path}")

            except Exception as attach_err:
                logger.error(f"Failed to attach {section}: {attach_err}", exc_info=True)

        try:
            # Option A: send directly
            mail.Send()
            # Option B: let user review
            # mail.Display()
            logger.info("✓ Email sent / prepared via Outlook")
            return True

        except Exception as e:
            logger.error(f"Outlook send failed: {e}")
            return False

    def _build_outlook_html(self, screenshots: Dict[str, str]) -> str:
        """
        Build Outlook-specific HTML with proper CID references.

        Outlook requires cid: references to match the Content-ID of attachments.
        """
        # Generate image sections
        image_sections = []

        section_order = ['header', 'summary', 'story_charts', 'defect_charts', 'stories_table', 'defects_table']
        section_titles = {
            'header': 'Sprint Report Header',
            'summary': 'Sprint Summary',
            'story_charts': 'Story Metrics',
            'defect_charts': 'Defect Metrics',
            'stories_table': 'Stories Table',
            'defects_table': 'Defects Table'
        }

        for section in section_order:
            if section in screenshots and screenshots[section]:
                image_sections.append({
                    'cid': section,
                    'alt': section_titles.get(section, section.replace('_', ' ').title())
                })

        # Build HTML
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: Arial, Helvetica, sans-serif;
            background-color: #f4f4f4;
        }}
        .email-container {{
            max-width: 800px;
            margin: 0 auto;
            background-color: #ffffff;
        }}
        .section-image {{
            width: 100%;
            max-width: 800px;
            height: auto;
            display: block;
            margin: 0;
            padding: 0;
            border: none;
        }}
        .spacer {{
            height: 15px;
            background-color: #f4f4f4;
        }}
    </style>
</head>
<body>
    <table class="email-container" cellpadding="0" cellspacing="0" border="0" width="100%" style="max-width: 800px; margin: 0 auto;">
"""

        # Add each image section
        for idx, section in enumerate(image_sections):
            html += f"""
        <tr>
            <td align="center" style="padding: 0;">
                <img src="cid:{section['cid']}" alt="{section['alt']}" class="section-image" style="width: 100%; max-width: 800px; height: auto; display: block; border: none;" />
            </td>
        </tr>
"""
            # Add spacer between sections (except last one)
            if idx < len(image_sections) - 1:
                html += """
        <tr>
            <td style="height: 15px; background-color: #f4f4f4;"></td>
        </tr>
"""

        html += """
    </table>
</body>
</html>
"""

        return html

    def _send_via_smtp(
            self,
            screenshots: Dict[str, str],
            email_html: str,
            subject: str
    ) -> bool:
        import smtplib
        import ssl
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.image import MIMEImage

        try:
            context = ssl.create_default_context()

            msg = MIMEMultipart('related')
            msg['Subject'] = subject
            msg['From'] = self.config.email_user
            msg['To'] = ', '.join(self.config.email_recipients)
            logger.info(f"Attempting login with user: {self.config.email_user}")
            logger.info(f"Password length: {len(self.config.email_password)}")
            logger.info(f"Recipients: {self.config.email_recipients}")
            if hasattr(self.config, 'email_cc_recipients') and self.config.email_cc_recipients:
                msg['Cc'] = ', '.join(self.config.email_cc_recipients)

            # HTML body
            msg_alternative = MIMEMultipart('alternative')
            msg.attach(msg_alternative)
            msg_alternative.attach(MIMEText(email_html, 'html', 'utf-8'))

            # Embed images
            for section, img_path in screenshots.items():
                if not img_path or not os.path.exists(img_path):
                    logger.warning(f"Skipping missing image: {section} → {img_path}")
                    continue
                with open(img_path, 'rb') as f:
                    img = MIMEImage(f.read())
                    img.add_header('Content-ID', f'<{section}>')
                    img.add_header('Content-Disposition', 'inline', filename=os.path.basename(img_path))
                    msg.attach(img)

            logger.info(f"Connecting to {self.config.smtp_server}:{self.config.smtp_port}")

            with smtplib.SMTP_SSL(
                    self.config.smtp_server,
                    self.config.smtp_port,
                    context=context
            ) as server:
                logger.info(f"logging in...")
                server.login(self.config.email_user, self.config.email_password)
                logger.info(f"logged in...")
                server.send_message(msg)


            logger.info("Email sent successfully via SMTP")
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"Authentication failed: {e} → most likely wrong app password or 2FA not set up correctly")
            logger.error("→ Go to https://myaccount.google.com/apppasswords and generate a new one")
            return False
        except Exception as e:
            logger.error(f"SMTP send failed: {e}", exc_info=True)
            return False


def main():
    """Main execution function."""
    try:
        logger.info("=" * 60)
        logger.info("JIRA Sprint Reporter - Enhanced Email Version")
        logger.info("=" * 60)

        # Load configuration
        logger.info("Loading configuration...")
        config = JIRAConfig()
        logger.info(f"Sprint: {config.sprint_name}")
        logger.info(f"Project: {config.project_key}")

        # Initialize JIRA client
        logger.info("Initializing JIRA client...")
        jira_client = JIRAClient(config)

        # Fetch sprint issues
        logger.info("Fetching sprint issues...")
        sprint_issues = jira_client.fetch_sprint_issues()

        if not sprint_issues:
            logger.warning("No issues found")
            return

        # Parse issues
        logger.info("Parsing issues...")
        df = IssueParser.parse_issues(sprint_issues)

        # Separate stories and defects
        story_df = df[df['Issue Type'].isin(config.story_types)]
        defect_df = df[df['Issue Type'].isin(config.defect_types)]

        logger.info(f"Stories: {len(story_df)}")
        logger.info(f"Defects: {len(defect_df)}")

        # Export to CSV
        if not story_df.empty:
            story_df.to_csv('sprint_stories.csv', index=False)
            logger.info("Stories exported to CSV")

        if not defect_df.empty:
            defect_df.to_csv('sprint_defects.csv', index=False)
            logger.info("Defects exported to CSV")

        # Generate HTML report (for web viewing)
        logger.info("Generating HTML report...")
        report_gen = ReportGenerator(config)
        html_file = report_gen.generate_html_report(story_df, defect_df)
        logger.info(f"✓ HTML report: {html_file}")

        # NEW: Capture screenshots for email
        if config.email_recipients:
            logger.info("\n" + "=" * 60)
            logger.info("Preparing email version with screenshots...")
            logger.info("=" * 60)

            try:
                # Capture screenshots
                screenshotter = ReportScreenshotter(config)
                screenshots = screenshotter.capture_report_sections(html_file)

                # Resize for email
                resized_screenshots = screenshotter.resize_images(screenshots)

                # Build email HTML
                email_builder = EmailReportBuilder(config)
                email_html = email_builder.build_email_html(resized_screenshots)

                # Send email
                email_sender = EmailSender(config)
                email_sent = email_sender.send_email_with_screenshots(
                    resized_screenshots,
                    email_html
                )

                if email_sent:
                    logger.info("✓ Email sent successfully")
                else:
                    logger.warning("✗ Email sending failed")

            except ImportError as e:
                logger.error(f"\n{'=' * 60}")
                logger.error("MISSING DEPENDENCY: Playwright")
                logger.error("=" * 60)
                logger.error("To enable screenshot-based email reports, install:")
                logger.error("  pip install playwright pillow")
                logger.error("  playwright install chromium")
                logger.error(f"\nError: {e}")
                logger.error("=" * 60)
                logger.info(f"\n✓ HTML report still available: {html_file}")

            except Exception as e:
                logger.error(f"Screenshot/Email error: {e}", exc_info=True)
                logger.info(f"✓ HTML report still available: {html_file}")

        else:
            logger.info(f"✓ Report generated: {html_file}")
            logger.info("  (Email skipped - no recipients configured)")

        logger.info("\n" + "=" * 60)
        logger.info("JIRA Sprint Reporter - Completed")
        logger.info("=" * 60)

    except ConfigurationError as e:
        logger.error(f"Configuration Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
