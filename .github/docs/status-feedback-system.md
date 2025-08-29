# Study Status Feedback System

This system creates status tracking issues in study repositories and updates the Factory Portfolio Project when study milestones are completed.

## How It Works

1. **Status Issues Creation**: When a new study is provisioned, status tracking issues are automatically created in the study repository
2. **Project Assignment**: These issues are assigned to the study's project and ordered by priority  
3. **Factory Project Updates**: When status issues are updated, the Factory Portfolio Project "Objective" field is automatically updated
4. **Activity Monitoring**: The daily activity check workflow monitors all studies and updates Factory issue status based on repository activity

## Status Issues Configuration

Status issues are defined in `.github/data/study-status-issues.json`. This file controls:
- Issue titles, descriptions, and labels
- Number of status milestones
- Factory Project "Objective" field mappings
- Initial status for each issue

### Current Default Status Issues

1. **1) Analysis Package Prototype** → Updates Factory Project Objective to "Analysis Package Prototype" (starts "In Progress")
2. **2) Network Execution** → Updates Factory Project Objective to "Network Execution" (starts "Todo")
3. **3) Journal Submission** → Updates Factory Project Objective to "Journal Submission" (starts "Todo")

## Editing Status Issues

To customize the status issues:

1. Edit `.github/data/study-status-issues.json`
2. Modify the `issues` array to add/remove/change status milestones
3. Update `factory_objective` mapping for corresponding Project field values
4. New studies will use the updated configuration

### Example Configuration Change

```json
{
  "issues": [
    {
      "order": 1,
      "title": "🎯 New Milestone Title",
      "body": "Custom milestone description...",
      "labels": ["status-tracking", "custom-label"],
      "factory_objective": "Custom Objective Name",
      "initial_status": "In Progress"
    }
  ]
}
```

## Components

### 1. Status Issues Creation
- **Action**: `.github/actions/create-status-issues/action.yml`
- **Purpose**: Creates status tracking issues in study repositories
- **Features**: 
  - Reads configuration from `study-status-issues.json`
  - Creates issues with proper labels and assignments
  - Assigns issues to study project with correct priority order
  - Links issues back to Factory tracking issue

### 2. Factory Project Updates  
- **Action**: `.github/actions/add-to-factory-project/action.yml`
- **Purpose**: Adds Factory tracking issues to the Factory Portfolio Project
- **Features**:
  - Populates "Lead" field with study lead name
  - Populates "Study Repo" field with repository URL
  - Sets initial "Objective" field to "Analysis Package Prototype"

### 3. Activity Monitoring
- **Workflow**: `.github/workflows/activity-check.yml`
- **Schedule**: Daily at 9 AM UTC
- **Purpose**: Monitors all study repositories and updates Factory issue status based on activity
- **Features**:
  - Updates issue titles with status emojis (🟢 Active, 🟡 Low Activity, 🔴 Inactive)
  - Calculates days since last repository activity
  - Updates Factory issue body with timestamp and status

## Testing the System

### Manual Test Process

1. **Create a test study** using the provision workflow
2. **Verify status issues** are created in the study repository with correct titles
3. **Check Factory Project** - verify issue was added with "Lead", "Study Repo", and "Objective" fields populated
4. **Check project assignment** - status issues should appear in study project in correct order
5. **Wait for daily activity check** or manually run activity-check workflow to see status updates

### What to Verify

- ✅ Status issues created with correct titles and content from JSON config
- ✅ Issues assigned to study project in priority order (1, 2, 3)
- ✅ Factory issue added to Factory Portfolio Project
- ✅ Factory Project fields populated: Lead, Study Repo, Objective
- ✅ Activity check updates Factory issue titles with status emojis
- ✅ Repository activity dates reflected in Factory issue body

## Troubleshooting

### Common Issues

1. **Status issues not created**: Check that `study-status-issues.json` file is valid JSON
2. **Project assignment failing**: Verify study project permissions and that project exists
3. **Factory Project not updating**: Check `FACTORY_PROJECT_NUMBER` variable is set correctly
4. **Activity check not running**: Verify `ORG_ADMIN_TOKEN` secret has necessary permissions

### Logs and Debugging

- Check workflow runs in Actions tab for detailed error messages
- Look for GraphQL errors in action outputs
- Verify repository dispatch events in workflow logs
- Check issue labels and Factory issue references

## Demo Scenario

**For demonstrating to colleagues:**

1. Create a new study using the provision workflow
2. Show the 3 status issues created in the study repository
3. Show them assigned to the study project in correct order  
4. Show the Factory issue added to Factory Portfolio Project with populated fields
5. Show how daily activity check updates Factory issue status with emojis
6. Explain how the JSON configuration makes it easy to customize status milestones

This provides automated status tracking from study repositories to the Factory portfolio management system through GitHub Projects integration.