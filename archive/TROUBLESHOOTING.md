# Factory Troubleshooting Guide

## Setup Checklist

### 1. GitHub Project Configuration
Ensure your Factory project has these fields:
- [ ] **Stage** (single-select) with options:
  - Initiation
  - Protocol development  
  - Data diagnostics
  - Phenotype development
  - Phenotype evaluation
  - Analysis specifications
  - Network execution
  - Study diagnostics
  - Evidence synthesis
  - Results evaluation
- [ ] **Lead** (text)
- [ ] **Lead Site** (text)
- [ ] **Partner Sites** (text)
- [ ] **Partner Count** (number)
- [ ] **Target Date** (date)
- [ ] **Study Repo** or **Repo** (text/URL) - either name works

### 2. Factory Repository Settings

Navigate to: `https://github.com/seanr87/Factory/settings/secrets/actions`

#### Required Secrets:
- [ ] `ORG_ADMIN_TOKEN` - Personal Access Token with permissions:
  - Repository: Read, Write, Create
  - Project: Read, Write
  - Issues: Read, Write
  - Actions: Read, Write (optional)
- [ ] `ORG_LOGIN` - Your GitHub username (e.g., `seanr87`)
- [ ] `TEMPLATE_REPO` - Path to template repository (e.g., `seanr87/study-template`)

#### Required Variables:
- [ ] `FACTORY_PROJECT_NUMBER` - The number from your Factory project URL
  - Find it at: `https://github.com/users/seanr87/projects/X` where X is the number

### 3. Study Template Repository

Ensure `https://github.com/seanr87/study-template` contains:
- [ ] `.github/workflows/` directory with:
  - stage-sync.yml
  - partner-sync.yml
  - weekly-partner-nudge.yml
- [ ] `.github/ISSUE_TEMPLATE/` directory with:
  - Stage checklist templates (9 files)
  - add_data_partner.yml
  - bulk_add_data_partners.yml
- [ ] README.md with OHDSI conventions

## Common Issues and Solutions

### Issue: "FACTORY_PROJECT_NUMBER is not set"
**Solution:** 
1. Go to Factory repo → Settings → Secrets and variables → Actions → Variables
2. Click "New repository variable"
3. Name: `FACTORY_PROJECT_NUMBER`
4. Value: Your project number (e.g., `1` or `2`)

### Issue: "Factory project not found"
**Possible causes:**
1. Wrong project number
2. Project is private and token lacks permissions
3. Wrong ORG_LOGIN value

**Solution:**
- Verify project number from URL
- Check token has project:read permission
- Ensure ORG_LOGIN matches your GitHub username

### Issue: "Factory must have fields: Study Repo or Repo"
**Solution:**
1. Go to your Factory project
2. Click ⚙️ Settings
3. Add a field named "Study Repo" (text type)
4. Save changes

### Issue: "No Stage option named 'X' found in Factory"
**Solution:**
1. Go to Factory project settings
2. Edit the Stage field
3. Add all required stage options (see list above)
4. Ensure spelling matches exactly

### Issue: Provision workflow fails at "Create repository from template"
**Possible causes:**
1. Template repo doesn't exist
2. Token lacks repo creation permission
3. Repository name already exists

**Solution:**
- Verify template exists at specified path
- Check token has repo:write permission
- Try a different study title

### Issue: Stage sync not updating Factory
**Possible causes:**
1. FACTORY_PROJECT_NUMBER not set in study repo
2. Token lacks project:write permission
3. Study repo not linked to Factory item

**Solution:**
1. In study repo, go to Settings → Variables
2. Add FACTORY_PROJECT_NUMBER variable
3. Ensure Factory item has Study Repo field matching the repository URL

## Testing the System

### 1. Test Provision Workflow
```bash
# Go to Factory repo → Actions → Provision New Study
# Run with test values:
Study title: Test Study 2025
Lead: John Doe
Lead username: seanr87
Lead site: Test University
Partner sites: Site A, Site B, Site C
Target date: 2025-12-31
```

### 2. Test Stage Sync
1. Go to created study repository
2. Close one of the stage checklist issues
3. Check Factory project - stage should update

### 3. Test Partner Sync
1. In study repo, create new issue
2. Add label "partner-site" or "data-partner"
3. Check Factory - Partner Count should update

### 4. Test Factory Health
```bash
# Go to Factory repo → Actions → Factory Health Digest
# Click "Run workflow"
# Check for new issue with health report
```

## Debug Commands

### Check GitHub CLI authentication
```bash
gh auth status
```

### Test GraphQL queries
```bash
# Get project info
gh api graphql -f query='
  query($login: String!, $number: Int!) {
    user(login: $login) {
      projectV2(number: $number) {
        id
        title
      }
    }
  }' -f login="seanr87" -f number=1
```

### Check repository secrets
```bash
gh secret list --repo seanr87/Factory
```

### Check repository variables
```bash
gh variable list --repo seanr87/Factory
```

## Workflow Logs

To debug failed workflows:
1. Go to repository → Actions tab
2. Click on failed workflow run
3. Click on job name
4. Expand failed step
5. Look for error messages

Common error patterns:
- `Resource not accessible by integration` - Token permission issue
- `Not Found` - Wrong repository/project reference
- `Validation Failed` - Missing required field or invalid value
- `Bad credentials` - Token expired or incorrect

## Getting Help

If issues persist:
1. Check workflow run logs for specific error messages
2. Verify all configuration items in this checklist
3. Ensure your PAT token hasn't expired
4. Try running workflows with debug logging enabled

## Quick Reset

If everything is broken, here's how to start fresh:

1. Delete all test study repositories
2. Clear Factory project items
3. Regenerate PAT token with correct permissions
4. Update secrets in Factory repo
5. Run provision workflow with simple test values
6. Verify each component works before adding complexity