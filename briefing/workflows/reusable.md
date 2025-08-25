# Reusable Workflows

## Overview
Reusable workflows enable DRY principles in GitHub Actions. Define once, call many times with different inputs.

## Defining a Reusable Workflow

```yaml
# .github/workflows/reusable-provision.yml
name: Reusable Study Provision

on:
  workflow_call:
    inputs:
      study_title:
        required: true
        type: string
      lead:
        required: true
        type: string
    secrets:
      ORG_TOKEN:
        required: true

jobs:
  provision:
    runs-on: ubuntu-latest
    steps:
      - name: Create repository
        env:
          GH_TOKEN: ${{ secrets.ORG_TOKEN }}
        run: |
          gh repo create "${{ inputs.study_title }}" \
            --template study-template \
            --public
```

## Calling a Reusable Workflow

```yaml
# .github/workflows/new-study.yml
name: Create New Study

on:
  workflow_dispatch:
    inputs:
      study_title:
        required: true
        type: string

jobs:
  call-provision:
    uses: ./.github/workflows/reusable-provision.yml
    with:
      study_title: ${{ inputs.study_title }}
      lead: ${{ github.actor }}
    secrets:
      ORG_TOKEN: ${{ secrets.ORG_ADMIN_TOKEN }}
```

## Factory Reusable Workflows

### Study Lifecycle
- `provision-study.yml` - Create new study repo
- `advance-stage.yml` - Progress study stages
- `sync-portfolio.yml` - Update Factory project

### Maintenance
- `validate-study.yml` - Check study health
- `archive-study.yml` - Archive completed studies

## Best Practices

1. **Inputs**: Use structured inputs with validation
2. **Outputs**: Return job outputs for chaining
3. **Secrets**: Pass explicitly, never inherit
4. **Permissions**: Define at job level
5. **Documentation**: Include usage examples

## Versioning

Tag reusable workflows for stability:
```yaml
uses: ./.github/workflows/provision@v1.0.0
```

## Limitations
- Max 4 levels of nesting
- 20 unique workflows per run
- Same-repo or public repos only
- Cannot call from forked repos