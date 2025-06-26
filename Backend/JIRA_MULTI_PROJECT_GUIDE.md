# Jira Multi-Project Story Sync Guide

This guide explains how to sync user stories from multiple Jira projects into your Test Case Generator system.

## 🚀 Quick Start

### 1. Environment Setup

Set up your Jira credentials in environment variables:

```bash
# Required Jira credentials
export JIRA_BASE_URL="https://your-company.atlassian.net"
export JIRA_EMAIL="your-email@company.com"
export JIRA_API_TOKEN="your-api-token"

# Optional: Enable Jira sync in scheduler
export JIRA_SYNC_ENABLED="true"
```

### 2. Discover Available Projects

First, discover what projects you have access to:

```bash
cd Backend
python sync_multiple_projects.py
```

Choose option `1` to discover available projects. This will show you all project keys and names.

## 📋 Methods to Get Stories from Multiple Projects

### Method 1: Sync Specific Projects

Edit the `sync_multiple_projects.py` script and modify the `project_keys` list:

```python
# In sync_multiple_projects.py
project_keys = ["PROJ1", "PROJ2", "PROJ3"]  # Replace with your actual project keys
```

Then run:
```bash
python sync_multiple_projects.py
# Choose option 2
```

### Method 2: Sync All Available Projects

Automatically sync from all projects you have access to:

```bash
python sync_multiple_projects.py
# Choose option 3
```

### Method 3: Use Environment Variables

Set specific project keys in environment variables:

```bash
export JIRA_PROJECT_KEYS="PROJ1,PROJ2,PROJ3"
export JIRA_SYNC_ENABLED="true"
```

Then use the enhanced scheduler:
```bash
python scheduler_with_jira.py
```

### Method 4: Sync All Projects Automatically

```bash
export JIRA_SYNC_ALL_PROJECTS="true"
export JIRA_SYNC_ENABLED="true"
python scheduler_with_jira.py
```

## 🔧 Advanced Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `JIRA_SYNC_ENABLED` | Enable/disable Jira sync | `false` |
| `JIRA_PROJECT_KEYS` | Comma-separated list of project keys | `""` |
| `JIRA_SYNC_ALL_PROJECTS` | Sync all available projects | `false` |
| `JIRA_MAX_RESULTS` | Max results per API call | `100` |
| `JIRA_BATCH_SIZE` | Batch size for processing | `50` |
| `JIRA_RATE_LIMIT_DELAY` | Delay between API calls (seconds) | `1.0` |

### JQL Query Customization

The system uses these default filters:
- **Status**: "Selected for Development" OR "In Progress"
- **Issue Type**: "Story"

You can modify these in the code:

```python
# In jira_integration_improved.py
stats = await integration.sync_stories_from_multiple_projects(
    project_keys=["PROJ1", "PROJ2"],
    statuses=[JiraStatus.SELECTED_FOR_DEV, JiraStatus.IN_PROGRESS, JiraStatus.TO_DO],
    issue_types=[JiraIssueType.STORY, JiraIssueType.EPIC]
)
```

## 📊 Available Status and Issue Types

### Status Types
- `JiraStatus.SELECTED_FOR_DEV` - "Selected for Development"
- `JiraStatus.IN_PROGRESS` - "In Progress"
- `JiraStatus.DONE` - "Done"
- `JiraStatus.TO_DO` - "To Do"

### Issue Types
- `JiraIssueType.STORY` - "Story"
- `JiraIssueType.EPIC` - "Epic"
- `JiraIssueType.BUG` - "Bug"
- `JiraIssueType.TASK` - "Task"

## 🔍 Troubleshooting

### Common Issues

1. **No projects found**
   - Check your Jira credentials
   - Verify you have access to projects
   - Run the discovery script first

2. **Rate limiting errors**
   - Increase `JIRA_RATE_LIMIT_DELAY`
   - Reduce `JIRA_BATCH_SIZE`

3. **Authentication errors**
   - Verify your API token is correct
   - Check if your email has the right permissions

### Debug Mode

Enable debug logging by modifying the logging level in `jira_integration_improved.py`:

```python
logging.basicConfig(level=logging.DEBUG)
```

## 📈 Performance Tips

1. **Start with a few projects** to test the setup
2. **Use specific project keys** instead of "all projects" for better performance
3. **Adjust batch sizes** based on your Jira instance performance
4. **Monitor rate limits** and adjust delays accordingly

## 🔄 Integration with Scheduler

The enhanced scheduler (`scheduler_with_jira.py`) automatically:

1. Syncs stories from Jira (if enabled)
2. Processes local project folders
3. Generates embeddings
4. Creates test cases
5. Runs every 5 minutes

### Scheduler Configuration

```bash
# Sync specific projects
export JIRA_SYNC_ENABLED="true"
export JIRA_PROJECT_KEYS="PROJ1,PROJ2,PROJ3"

# OR sync all projects
export JIRA_SYNC_ENABLED="true"
export JIRA_SYNC_ALL_PROJECTS="true"

# Run the enhanced scheduler
python scheduler_with_jira.py
```

## 📝 Example Workflows

### Workflow 1: Manual Sync
```bash
# 1. Discover projects
python sync_multiple_projects.py
# Choose option 1

# 2. Sync specific projects
# Edit the script with your project keys
python sync_multiple_projects.py
# Choose option 2
```

### Workflow 2: Automated Sync
```bash
# 1. Set environment variables
export JIRA_SYNC_ENABLED="true"
export JIRA_PROJECT_KEYS="PROJ1,PROJ2"

# 2. Run enhanced scheduler
python scheduler_with_jira.py
```

### Workflow 3: All Projects Sync
```bash
# 1. Set environment variables
export JIRA_SYNC_ENABLED="true"
export JIRA_SYNC_ALL_PROJECTS="true"

# 2. Run enhanced scheduler
python scheduler_with_jira.py
```

## 🎯 Best Practices

1. **Test with one project first** before syncing multiple
2. **Monitor the logs** for any errors or rate limiting
3. **Use specific project keys** for better performance
4. **Set appropriate rate limits** to avoid overwhelming Jira
5. **Regularly check sync results** to ensure data quality

## 📞 Support

If you encounter issues:

1. Check the logs for error messages
2. Verify your Jira credentials and permissions
3. Test with the discovery script first
4. Ensure your Jira instance allows API access

The system will automatically handle:
- Rate limiting
- Retry logic
- Error recovery
- Duplicate detection
- Data validation 