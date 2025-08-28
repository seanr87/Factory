# Study Status Feedback System

This system provides automated status updates from Study Repositories back to the Factory Portfolio when study milestones are completed.

## How It Works

1. **Status Issues Creation**: When a new study is provisioned, 3 placeholder status tracking issues are automatically created in the study repository
2. **Project Assignment**: These issues are assigned to the study's project and ordered by priority
3. **Status Monitoring**: When a status issue is closed, the Factory tracking issue is automatically updated
4. **Feedback Loop**: The Factory issue status and activity log are updated in real-time

## Status Issues Configuration

Status issues are defined in `.github/data/study-status-issues.json`. This file can be easily edited to:
- Change issue titles and descriptions
- Modify the number of status milestones  
- Update Factory status mappings
- Add or remove status tracking points

### Current Default Status Issues

1. **📋 Protocol Development Complete** → Updates Factory status to "Protocol Development"
2. **📊 Analysis Specifications Finalized** → Updates Factory status to "Analysis Specifications"  
3. **🚀 Network Execution Started** → Updates Factory status to "Network Execution"

## Editing Status Issues

To customize the status issues:

1. Edit `.github/data/study-status-issues.json`
2. Modify the `issues` array to add/remove/change status milestones
3. Update `factory_status_mapping` for the corresponding status names
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
      "factory_status": "Custom Status Name"
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
  - Assigns issues to study project
  - Sets up webhook workflow in study repo

### 2. Factory Status Updates  
- **Workflow**: `.github/workflows/update-factory-status.yml`
- **Trigger**: Repository dispatch from study repositories
- **Purpose**: Updates Factory issue status when study milestones are completed

### 3. Study Repository Webhooks
- **Reusable Workflow**: `.github/workflows/reusable/study-status-webhook.yml`
- **Trigger Action**: `.github/actions/trigger-factory-status-update/action.yml`
- **Purpose**: Monitors study repository for closed status issues and triggers Factory updates

## Testing the System

### Manual Test Process

1. **Create a test study** using the provision workflow
2. **Verify status issues** are created in the study repository
3. **Check project assignment** - issues should appear in study project
4. **Close a status issue** to test the feedback loop
5. **Verify Factory update** - check that the Factory issue status updated

### What to Verify

- ✅ Status issues created with correct titles and content
- ✅ Issues assigned to study project in correct order
- ✅ Webhook workflow created in study repository  
- ✅ Closing status issue triggers Factory status update
- ✅ Factory issue body and activity log updated correctly
- ✅ Status update comment added to Factory issue

## Troubleshooting

### Common Issues

1. **Webhook not triggering**: Check that `FACTORY_ORG_TOKEN` secret is set in study repository
2. **Status not updating**: Verify issue has `status-tracking` label
3. **Wrong status mapping**: Check configuration in `study-status-issues.json`
4. **Project assignment failing**: Verify study project permissions

### Logs and Debugging

- Check workflow runs in both study and Factory repositories
- Look for error messages in action outputs
- Verify repository dispatch events are being sent
- Check issue labels and Factory issue number references

## Demo Scenario

**For demonstrating to colleagues:**

1. Create a new study with placeholder data
2. Show the 3 status issues in the study repository
3. Show them in the study project (ordered correctly)  
4. Close the first status issue
5. Show the Factory issue updated automatically with new status
6. Show the activity comment on the Factory issue
7. Explain how easy it is to edit the status issue content via JSON config

This provides a complete status feedback loop from study repositories back to the Factory portfolio management system.