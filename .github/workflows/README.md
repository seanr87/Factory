# Factory Workflows

## Active Workflows

### provision-study.yml
Creates a new study repository with complete automation:
- Repository creation from study-template using `create-study-repository` action
- Study lead invitation and permissions using `invite-collaborator` action
- Factory tracking issue creation using `create-factory-tracking` action
- Factory Portfolio Project integration using `add-to-factory-project` action
- Status tracking issues creation using `create-status-issues` action
- Study project board setup using `setup-study-project` action

**Required Secrets:**
- `ORG_ADMIN_TOKEN` - GitHub PAT with repo, admin:org, and project permissions

**Required Variables:**
- `FACTORY_PROJECT_NUMBER` - Factory Portfolio Project number

### activity-check.yml  
Monitors study activity and updates Factory issues:
- Daily monitoring of all study repositories
- Status emoji updates (🟢 Active, 🟡 Low Activity, 🔴 Inactive)
- Activity-based classification (>30 days = Inactive, >14 days = Low Activity)
- GraphQL-based bulk issue updates
- Factory issue body timestamp updates

**Schedule:** Daily at 09:00 UTC

### factory-issue-updater.yml
Updates Factory tracking issues based on study repository changes:
- Triggered by repository dispatch from study repositories
- Updates Factory issue status based on study milestone completion
- Maintains Factory issue body with current study progress

### update-study-leads-dropdown.yml
Maintains the study lead dropdown in provision workflow:
- Updates workflow with current study leads from database
- Triggered when study-leads.json changes

## Workflow Security

All workflows follow security best practices:
- Minimal permissions (read by default)
- SHA-pinned actions
- Secret validation
- No hardcoded values

## Local Testing

Test workflows locally with `act` or GitHub CLI:

```bash
# Test provision workflow with GitHub CLI
gh workflow run provision-study.yml \
  -f study_title="Test Study" \
  -f study_lead_selection="Add new study lead" \
  -f new_lead_name="Test Lead" \
  -f new_lead_github="testuser" \
  -f target_date="2025-12-31"

# Test activity check workflow
gh workflow run activity-check.yml

# Validate workflow syntax
yamllint .github/workflows/*.yml
actionlint .github/workflows/*.yml
```

## Maintenance

Before modifying workflows:
1. Review briefing packet guidance in `briefing/` directory
2. Test changes locally with GitHub CLI or `act`
3. Run `actionlint` and `yamllint` validation
4. Update documentation (this README, main README.md, status-feedback-system.md)
5. Test end-to-end: provision → verify Factory Portfolio → check status tracking

## Configuration Files

- **`.github/data/study-status-issues.json`** - Configure status tracking milestones
- **`.github/data/study-leads.json`** - Manage study lead dropdown options

## GitHub Actions

All workflows use modular, reusable actions in `.github/actions/`:
- `create-study-repository` - Repository creation from template
- `invite-collaborator` - Manage study lead permissions  
- `create-factory-tracking` - Create Factory tracking issues
- `add-to-factory-project` - Populate Factory Portfolio Project fields
- `create-status-issues` - Create configurable status milestones
- `setup-study-project` - Set up study project boards