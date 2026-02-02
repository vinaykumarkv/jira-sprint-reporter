# API Integration Guide

Complete guide for integrating JIRA Sprint Reporter with external APIs and services.

---

## 📋 Table of Contents

1. [JIRA API Deep Dive](#jira-api-deep-dive)
2. [Slack Integration](#slack-integration)
3. [Microsoft Teams Integration](#microsoft-teams-integration)
4. [Confluence Integration](#confluence-integration)
5. [Google Drive Integration](#google-drive-integration)
6. [Custom Webhooks](#custom-webhooks)
7. [Database Integration](#database-integration)
8. [Advanced Examples](#advanced-examples)

---

## 🔷 JIRA API Deep Dive

### Essential JIRA Endpoints

#### 1. Authentication Test
```bash
curl -u your.email@company.com:your_api_token \
  -H "Accept: application/json" \
  https://yourcompany.atlassian.net/rest/api/3/myself
```

#### 2. List All Boards
```bash
curl -u email:token \
  "https://yourcompany.atlassian.net/rest/agile/1.0/board"
```

**Response:**
```json
{
  "maxResults": 50,
  "startAt": 0,
  "total": 3,
  "isLast": true,
  "values": [
    {
      "id": 123,
      "self": "https://yourcompany.atlassian.net/rest/agile/1.0/board/123",
      "name": "Development Board",
      "type": "scrum"
    }
  ]
}
```

#### 3. List Board Sprints
```bash
curl -u email:token \
  "https://yourcompany.atlassian.net/rest/agile/1.0/board/123/sprint"
```

#### 4. Get Sprint Details
```bash
curl -u email:token \
  "https://yourcompany.atlassian.net/rest/agile/1.0/sprint/456"
```

**Response:**
```json
{
  "id": 456,
  "self": "https://yourcompany.atlassian.net/rest/agile/1.0/sprint/456",
  "state": "active",
  "name": "Sprint 24",
  "startDate": "2024-02-01T10:00:00.000Z",
  "endDate": "2024-02-15T10:00:00.000Z",
  "originBoardId": 123,
  "goal": "Complete user authentication feature"
}
```

#### 5. Advanced Issue Search (JQL)
```python
import requests
import base64

def search_issues_jql(jql_query: str, fields: List[str] = None):
    """
    Search JIRA issues using JQL.
    
    Args:
        jql_query: JQL query string
        fields: List of fields to return
        
    Returns:
        Dictionary with search results
    """
    auth = base64.b64encode(
        f"{os.getenv('JIRA_USERNAME')}:{os.getenv('JIRA_API_KEY')}".encode()
    ).decode()
    
    headers = {
        'Authorization': f'Basic {auth}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'jql': jql_query,
        'fields': fields or ['summary', 'status', 'assignee', 'created'],
        'maxResults': 100
    }
    
    response = requests.post(
        f"{os.getenv('JIRA_BASE_URL')}/rest/api/3/search",
        json=payload,
        headers=headers
    )
    
    return response.json()

# Example usage
results = search_issues_jql(
    jql_query='project = PROJ AND sprint = 456 AND status = "In Progress"',
    fields=['key', 'summary', 'assignee', 'priority']
)
```

#### 6. Get Custom Fields
```python
def get_custom_fields():
    """Retrieve all custom fields for mapping."""
    response = requests.get(
        f"{os.getenv('JIRA_BASE_URL')}/rest/api/3/field",
        headers=headers
    )
    
    custom_fields = {}
    for field in response.json():
        if field['custom']:
            custom_fields[field['name']] = field['id']
    
    return custom_fields

# Usage
fields = get_custom_fields()
story_points_field = fields.get('Story Points', 'customfield_10016')
```

### Advanced JIRA Features

#### Story Points Extraction
```python
def fetch_sprint_issues_with_story_points(sprint_id: int) -> pd.DataFrame:
    """Fetch issues including story points."""
    
    # First, get custom field ID for story points
    custom_fields = get_custom_fields()
    story_points_field = custom_fields.get('Story Points', 'customfield_10016')
    
    # Fetch issues with story points
    params = {
        'fields': f'key,summary,status,assignee,{story_points_field}'
    }
    
    response = requests.get(
        f"{base_url}/rest/agile/1.0/sprint/{sprint_id}/issue",
        params=params,
        headers=headers
    )
    
    issues = []
    for issue in response.json()['issues']:
        fields = issue['fields']
        issues.append({
            'key': issue['key'],
            'summary': fields['summary'],
            'status': fields['status']['name'],
            'assignee': fields.get('assignee', {}).get('displayName', 'Unassigned'),
            'story_points': fields.get(story_points_field, 0)
        })
    
    return pd.DataFrame(issues)
```

#### Sprint Velocity Calculation
```python
def calculate_sprint_velocity(sprint_id: int) -> Dict:
    """Calculate sprint velocity metrics."""
    
    df = fetch_sprint_issues_with_story_points(sprint_id)
    
    total_points = df['story_points'].sum()
    completed_points = df[
        df['status'].isin(['Done', 'Closed', 'Resolved'])
    ]['story_points'].sum()
    
    in_progress_points = df[
        df['status'].str.contains('In Progress|Development', case=False)
    ]['story_points'].sum()
    
    return {
        'total_points': total_points,
        'completed_points': completed_points,
        'in_progress_points': in_progress_points,
        'completion_rate': (completed_points / total_points * 100) if total_points > 0 else 0,
        'average_points_per_issue': total_points / len(df) if len(df) > 0 else 0
    }
```

---

## 💬 Slack Integration

### Setup Slack Webhook

1. Go to: https://api.slack.com/messaging/webhooks
2. Create new app or use existing
3. Add "Incoming Webhooks" feature
4. Activate and create webhook URL
5. Copy webhook URL to `.env`:

```env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### Basic Slack Notification

```python
import requests
from typing import Dict, Any

def send_slack_notification(
    webhook_url: str,
    sprint_name: str,
    stats: Dict[str, Any],
    report_url: Optional[str] = None
) -> bool:
    """
    Send sprint report notification to Slack.
    
    Args:
        webhook_url: Slack webhook URL
        sprint_name: Name of the sprint
        stats: Dictionary with sprint statistics
        report_url: Optional URL to full report
        
    Returns:
        True if sent successfully
    """
    
    # Determine status emoji
    completion_rate = stats.get('story_completion_rate', 0)
    if completion_rate >= 90:
        status_emoji = "🟢"
    elif completion_rate >= 70:
        status_emoji = "🟡"
    else:
        status_emoji = "🔴"
    
    # Build message
    message = {
        "text": f"{status_emoji} Sprint Report: {sprint_name}",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📊 {sprint_name} - Sprint Report"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Total Stories:*\n{stats.get('total_stories', 0)}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Completed:*\n{stats.get('stories_done', 0)}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Total Defects:*\n{stats.get('total_defects', 0)}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Resolved:*\n{stats.get('defects_resolved', 0)}"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Completion Rate:* {completion_rate:.1f}%\n*Velocity:* {stats.get('velocity', 0)} points"
                }
            }
        ]
    }
    
    # Add button to full report if URL provided
    if report_url:
        message["blocks"].append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📄 View Full Report"
                    },
                    "url": report_url,
                    "style": "primary"
                }
            ]
        })
    
    # Send to Slack
    try:
        response = requests.post(webhook_url, json=message, timeout=10)
        response.raise_for_status()
        logger.info("✓ Slack notification sent")
        return True
    except Exception as e:
        logger.error(f"✗ Slack notification failed: {e}")
        return False

# Add to main() function
if os.getenv('SLACK_WEBHOOK_URL'):
    slack_stats = {
        'sprint_name': config.sprint_name,
        'total_stories': len(story_df),
        'stories_done': len(story_df[story_df['Status'].str.contains('Done|Closed', case=False, na=False)]),
        'total_defects': len(defect_df),
        'defects_resolved': len(defect_df[defect_df['Status'].str.contains('Done|Closed', case=False, na=False)]),
        'story_completion_rate': (stories_done / total_stories * 100) if total_stories > 0 else 0
    }
    send_slack_notification(
        os.getenv('SLACK_WEBHOOK_URL'),
        config.sprint_name,
        slack_stats,
        report_url="file:///path/to/sprint_report.html"
    )
```

### Advanced Slack: File Upload

```python
def upload_report_to_slack(
    token: str,
    channel: str,
    file_path: str,
    title: str,
    initial_comment: str
) -> bool:
    """Upload HTML report file to Slack channel."""
    
    url = "https://slack.com/api/files.upload"
    
    headers = {
        'Authorization': f'Bearer {token}'
    }
    
    files = {
        'file': open(file_path, 'rb')
    }
    
    data = {
        'channels': channel,
        'title': title,
        'initial_comment': initial_comment
    }
    
    response = requests.post(url, headers=headers, files=files, data=data)
    return response.json().get('ok', False)
```

---

## 🔷 Microsoft Teams Integration

### Setup Teams Webhook

1. In Teams, go to channel → ⋯ → Connectors
2. Search for "Incoming Webhook"
3. Click "Configure"
4. Name it "JIRA Sprint Reporter"
5. Copy webhook URL to `.env`:

```env
TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/YOUR-WEBHOOK-URL
```

### Send Teams Notification

```python
def send_teams_notification(
    webhook_url: str,
    sprint_name: str,
    stats: Dict[str, Any],
    report_url: Optional[str] = None
) -> bool:
    """
    Send sprint report to Microsoft Teams.
    
    Args:
        webhook_url: Teams webhook URL
        sprint_name: Sprint name
        stats: Statistics dictionary
        report_url: Optional URL to full report
        
    Returns:
        True if sent successfully
    """
    
    # Determine theme color based on completion
    completion_rate = stats.get('story_completion_rate', 0)
    if completion_rate >= 90:
        theme_color = "00FF00"  # Green
    elif completion_rate >= 70:
        theme_color = "FFA500"  # Orange
    else:
        theme_color = "FF0000"  # Red
    
    message = {
        "@type": "MessageCard",
        "@context": "https://schema.org/extensions",
        "summary": f"Sprint Report: {sprint_name}",
        "themeColor": theme_color,
        "title": f"📊 Sprint Report - {sprint_name}",
        "sections": [
            {
                "activityTitle": "Sprint Summary",
                "facts": [
                    {
                        "name": "Total Stories:",
                        "value": str(stats.get('total_stories', 0))
                    },
                    {
                        "name": "Stories Completed:",
                        "value": f"{stats.get('stories_done', 0)} ({completion_rate:.1f}%)"
                    },
                    {
                        "name": "Total Defects:",
                        "value": str(stats.get('total_defects', 0))
                    },
                    {
                        "name": "Defects Resolved:",
                        "value": str(stats.get('defects_resolved', 0))
                    },
                    {
                        "name": "Sprint Velocity:",
                        "value": f"{stats.get('velocity', 0)} story points"
                    }
                ],
                "markdown": True
            }
        ]
    }
    
    # Add action button if report URL provided
    if report_url:
        message["potentialAction"] = [
            {
                "@type": "OpenUri",
                "name": "View Full Report",
                "targets": [
                    {
                        "os": "default",
                        "uri": report_url
                    }
                ]
            }
        ]
    
    try:
        response = requests.post(webhook_url, json=message, timeout=10)
        response.raise_for_status()
        logger.info("✓ Teams notification sent")
        return True
    except Exception as e:
        logger.error(f"✗ Teams notification failed: {e}")
        return False
```

---

## 📄 Confluence Integration

### Setup

```bash
pip install atlassian-python-api
```

### Publish Report to Confluence

```python
from atlassian import Confluence

def publish_to_confluence(
    html_content: str,
    space_key: str,
    parent_page_id: Optional[str] = None,
    page_title: Optional[str] = None
) -> Dict:
    """
    Publish sprint report to Confluence.
    
    Args:
        html_content: HTML content of report
        space_key: Confluence space key
        parent_page_id: Optional parent page ID
        page_title: Optional custom page title
        
    Returns:
        Dictionary with page details
    """
    
    confluence = Confluence(
        url=os.getenv('JIRA_BASE_URL'),  # Usually same domain
        username=os.getenv('JIRA_USERNAME'),
        password=os.getenv('JIRA_API_KEY')  # API token works
    )
    
    # Generate page title
    if not page_title:
        page_title = f"Sprint Report - {config.sprint_name} - {datetime.now().strftime('%Y-%m-%d')}"
    
    # Check if page exists
    existing_page = confluence.get_page_by_title(
        space=space_key,
        title=page_title
    )
    
    if existing_page:
        # Update existing page
        page_id = existing_page['id']
        result = confluence.update_page(
            page_id=page_id,
            title=page_title,
            body=html_content,
            minor_edit=False
        )
        logger.info(f"✓ Updated Confluence page: {page_id}")
    else:
        # Create new page
        result = confluence.create_page(
            space=space_key,
            title=page_title,
            body=html_content,
            parent_id=parent_page_id
        )
        logger.info(f"✓ Created Confluence page: {result['id']}")
    
    return result

# Usage in main()
if os.getenv('CONFLUENCE_SPACE_KEY'):
    with open('sprint_report.html', 'r') as f:
        html_content = f.read()
    
    publish_to_confluence(
        html_content=html_content,
        space_key=os.getenv('CONFLUENCE_SPACE_KEY'),
        parent_page_id=os.getenv('CONFLUENCE_PARENT_PAGE_ID')
    )
```

---

## 📁 Google Drive Integration

### Setup

```bash
pip install google-auth google-auth-oauthlib google-api-python-client
```

### Upload Report to Google Drive

```python
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def upload_to_google_drive(
    file_path: str,
    folder_id: Optional[str] = None,
    credentials_json: str = 'credentials.json'
) -> str:
    """
    Upload sprint report to Google Drive.
    
    Args:
        file_path: Path to file to upload
        folder_id: Optional Google Drive folder ID
        credentials_json: Path to service account credentials
        
    Returns:
        File ID of uploaded file
    """
    
    # Authenticate
    creds = service_account.Credentials.from_service_account_file(
        credentials_json,
        scopes=['https://www.googleapis.com/auth/drive.file']
    )
    
    service = build('drive', 'v3', credentials=creds)
    
    # Prepare file metadata
    file_metadata = {
        'name': os.path.basename(file_path),
        'mimeType': 'text/html'
    }
    
    if folder_id:
        file_metadata['parents'] = [folder_id]
    
    # Upload file
    media = MediaFileUpload(file_path, mimetype='text/html')
    
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink'
    ).execute()
    
    logger.info(f"✓ Uploaded to Google Drive: {file.get('webViewLink')}")
    
    return file.get('id')
```

---

## 🔔 Custom Webhooks

### Generic Webhook Sender

```python
def send_webhook_notification(
    webhook_url: str,
    data: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None
) -> bool:
    """
    Send data to any webhook endpoint.
    
    Args:
        webhook_url: Webhook URL
        data: Data to send
        headers: Optional custom headers
        
    Returns:
        True if successful
    """
    
    default_headers = {
        'Content-Type': 'application/json'
    }
    
    if headers:
        default_headers.update(headers)
    
    try:
        response = requests.post(
            webhook_url,
            json=data,
            headers=default_headers,
            timeout=30
        )
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Webhook failed: {e}")
        return False
```

---

## 🗄️ Database Integration

### PostgreSQL Example

```python
import psycopg2
from psycopg2.extras import execute_values

def store_sprint_data_postgres(
    df: pd.DataFrame,
    table_name: str = 'sprint_issues'
):
    """Store sprint data in PostgreSQL database."""
    
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    
    cursor = conn.cursor()
    
    # Create table if not exists
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            task_id VARCHAR(50) PRIMARY KEY,
            task_name TEXT,
            status VARCHAR(100),
            assigned_to VARCHAR(200),
            issue_type VARCHAR(50),
            priority VARCHAR(50),
            created_date DATE,
            last_updated TIMESTAMP,
            sprint_id INTEGER,
            sprint_name VARCHAR(200),
            report_date DATE
        )
    """)
    
    # Prepare data
    df['sprint_id'] = config.sprint_id
    df['sprint_name'] = config.sprint_name
    df['report_date'] = datetime.now().date()
    
    # Insert data
    columns = df.columns.tolist()
    values = [tuple(row) for row in df.values]
    
    execute_values(
        cursor,
        f"""
        INSERT INTO {table_name} ({','.join(columns)})
        VALUES %s
        ON CONFLICT (task_id) DO UPDATE SET
            status = EXCLUDED.status,
            last_updated = EXCLUDED.last_updated
        """,
        values
    )
    
    conn.commit()
    cursor.close()
    conn.close()
    
    logger.info(f"✓ Stored {len(df)} records in PostgreSQL")
```

---

## 🚀 Advanced Examples

### Multi-Platform Notification

```python
class NotificationManager:
    """Manage notifications across multiple platforms."""
    
    def __init__(self, config: JIRAConfig):
        self.config = config
        self.platforms = []
        
        # Auto-detect configured platforms
        if os.getenv('SLACK_WEBHOOK_URL'):
            self.platforms.append('slack')
        if os.getenv('TEAMS_WEBHOOK_URL'):
            self.platforms.append('teams')
        if os.getenv('CONFLUENCE_SPACE_KEY'):
            self.platforms.append('confluence')
    
    def notify_all(self, stats: Dict, report_path: str):
        """Send notifications to all configured platforms."""
        
        results = {}
        
        if 'slack' in self.platforms:
            results['slack'] = send_slack_notification(
                os.getenv('SLACK_WEBHOOK_URL'),
                self.config.sprint_name,
                stats
            )
        
        if 'teams' in self.platforms:
            results['teams'] = send_teams_notification(
                os.getenv('TEAMS_WEBHOOK_URL'),
                self.config.sprint_name,
                stats
            )
        
        if 'confluence' in self.platforms:
            with open(report_path, 'r') as f:
                html = f.read()
            results['confluence'] = publish_to_confluence(
                html,
                os.getenv('CONFLUENCE_SPACE_KEY')
            )
        
        return results
```

---

## 📚 Additional Resources

- **JIRA Cloud REST API**: https://developer.atlassian.com/cloud/jira/platform/rest/v3/
- **Slack API**: https://api.slack.com/
- **Microsoft Teams Webhooks**: https://docs.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/
- **Confluence API**: https://developer.atlassian.com/cloud/confluence/rest/
- **Google Drive API**: https://developers.google.com/drive/api/v3/about-sdk

---

**Need help with integration? Open an issue on GitHub!**
