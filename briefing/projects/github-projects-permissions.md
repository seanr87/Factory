# GitHub Actions Projects Permissions - Critical Issues & Workarounds

## TL;DR - Major Limitation ⚠️

**GITHUB_TOKEN cannot access Projects v2 directly.** This is a significant gap in GitHub Actions as of 2024-2025.

## The Problem

### Projects v2 vs Classic Projects
- **Classic Projects**: Old project system, being phased out
- **Projects v2**: New project system (current default), but limited API access
- **GitHub Actions**: Still designed for Classic Projects only

### Permission Confusion
```yaml
# ❌ WRONG - This doesn't exist
permissions:
  projects: write

# ⚠️ LIMITED - Only works for Classic Projects  
permissions:
  repository-projects: write
```

## Available Permission Scopes (2024-2025)

```yaml
permissions:
  actions: read|write|none
  checks: read|write|none
  contents: read|write|none
  deployments: read|write|none
  issues: read|write|none
  packages: read|write|none
  pull-requests: read|write|none
  repository-projects: read|write|none  # Classic Projects only!
  security-events: read|write|none
  statuses: read|write|none
```

## Key Limitations

### 1. GITHUB_TOKEN Limitations
- `repository-projects: write` only works with Classic Projects
- No direct permission for Projects v2
- Fine-grained PATs cannot access user-owned Projects v2

### 2. Organization vs User Projects
- **Organization Projects v2**: Can be accessed with GitHub Apps
- **User Projects v2**: Very limited API access
- **Repository Classic Projects**: Deprecated but still accessible

### 3. API Access Patterns
- **REST API**: Works with Classic Projects only
- **GraphQL API**: Required for Projects v2, but token limitations apply
- **GitHub CLI**: Uses same token limitations as direct API calls

## Workarounds & Solutions

### Option 1: GitHub App (Recommended for Organizations)
```yaml
# Use GitHub App tokens instead of GITHUB_TOKEN
steps:
  - name: Generate token
    id: generate_token
    uses: actions/create-github-app-token@v1
    with:
      app-id: ${{ secrets.APP_ID }}
      private-key: ${{ secrets.PRIVATE_KEY }}
  
  - name: Add to project
    env:
      GH_TOKEN: ${{ steps.generate_token.outputs.token }}
    run: |
      gh project item-add --project-number=$PROJECT_NUMBER --url=$ISSUE_URL
```

### Option 2: Personal Access Token
```yaml
# Use PAT with appropriate scopes
steps:
  - name: Add to project
    env:
      GH_TOKEN: ${{ secrets.PROJECTS_PAT }}
    run: |
      gh project item-add --project-number=$PROJECT_NUMBER --url=$ISSUE_URL
```

### Option 3: Manual Fallback
```yaml
# Graceful failure with manual instructions
- name: Add to project
  run: |
    gh project item-add --project-number=$PROJECT_NUMBER --url=$ISSUE_URL || {
      echo "❌ Automated project add failed"
      echo "🔧 Manual steps:"
      echo "1. Go to your project: https://github.com/users/$OWNER/projects/$NUMBER"
      echo "2. Click 'Add items'"
      echo "3. Add this issue: $ISSUE_URL"
    }
```

## Best Practices

### 1. Principle of Least Privilege
```yaml
# Be specific about what you need
permissions:
  contents: read
  issues: write
  repository-projects: write  # If using Classic Projects
```

### 2. Job-Level Permissions
```yaml
jobs:
  provision:
    permissions:
      issues: write
    runs-on: ubuntu-latest
    steps:
      # Only this job gets issue write access
```

### 3. Organization Settings
- Check organization-level permission restrictions
- May override repository-level settings
- Contact org admins if permissions are locked

## GitHub Actions Permission Hierarchy

1. **Enterprise Level** (if applicable)
   - Can lock permissions for all organizations
2. **Organization Level** 
   - Can restrict repository permissions
   - Affects all repos in the org
3. **Repository Level**
   - Final permissions for workflows
   - Cannot exceed org restrictions

## Debugging Permission Issues

### Check Current Permissions
```bash
# In a workflow step
env:
  GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
run: |
  echo "Current token permissions:"
  gh auth status
  
  # Try the operation
  gh project item-add ... || echo "Permission denied or project not found"
```

### Common Error Messages
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Project doesn't exist or no access
- `GraphQL error`: Often means Projects v2 access issue

## Factory-Specific Implementation

### Current Approach
```yaml
# What we're doing now (limited)
permissions:
  repository-projects: write

# This will work IF:
# - Using Classic Projects (deprecated)
# - Project is repository-scoped
# - Organization allows it
```

### Recommended Approach
```yaml
# Better approach for Factory system
env:
  GH_TOKEN: ${{ secrets.ORG_ADMIN_TOKEN }}  # Use PAT with project access

# Or use GitHub App token
# Or provide manual fallback
```

## Future Considerations

### GitHub's Direction
- Classic Projects being phased out
- Projects v2 becoming standard
- API access still catching up

### Recommendations
1. **Use GitHub Apps** for organization projects
2. **Use PATs** for user projects (with rotation)
3. **Always provide manual fallbacks**
4. **Monitor GitHub's roadmap** for permission improvements

## References
- [GitHub Actions Permissions](https://docs.github.com/en/actions/using-jobs/assigning-permissions-to-jobs)
- [Projects v2 GraphQL API](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-api-to-manage-projects)
- [GitHub Apps Authentication](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app)