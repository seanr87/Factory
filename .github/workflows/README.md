# Factory Workflows

## Active Workflows

### provision-new-study.yaml
Creates a new study repository from template with:
- Repository creation from study-template
- Project board setup with stages
- Factory portfolio issue creation
- Team permissions configuration

**Required Secrets:**
- `ORG_ADMIN_TOKEN` - GitHub PAT with org admin permissions
- `ORG_LOGIN` - Organization name
- `TEMPLATE_REPO` - Template repository name

**Required Variables:**
- `FACTORY_PROJECT_NUMBER` - Factory project board number

### factory-health.yml
Monitors and updates Factory portfolio health:
- Syncs study progress to portfolio
- Flags inactive studies (>30 days)
- Updates last activity timestamps
- Maintains stage status

**Schedule:** Daily at 00:00 UTC

## Workflow Security

All workflows follow security best practices:
- Minimal permissions (read by default)
- SHA-pinned actions
- Secret validation
- No hardcoded values

## Local Testing

Test workflows locally with `act`:
```bash
act workflow_dispatch -W .github/workflows/provision-new-study.yaml \
  --input study_title="Test Study" \
  --input lead="John Doe" \
  --input lead_site="Johns Hopkins" \
  --input partner_sites="Site1,Site2" \
  --input target_date="2025-12-31"
```

## Maintenance

Before modifying workflows:
1. Review briefing packet guidance
2. Test changes locally with `act`
3. Run `actionlint` validation
4. Update this README if needed