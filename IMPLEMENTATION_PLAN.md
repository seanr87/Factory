# Minimalist Implementation Plan - OHDSI Study Factory

## Overview
This plan implements the Factory system per SPEC-001 requirements, following SPEC-002's briefing packet approach for GitHub Actions and App development.

## Current State Analysis
- **Study Template**: Basic OHDSI study template exists at `/mnt/c/Users/soreill5/study-template`
- **Workflows**: Archived workflows exist for provisioning, stage management, and partner tracking
- **Factory Repo**: Current repo with minimal structure, needs GitHub Actions and App setup

## Phase 1: Core Infrastructure (Week 1)
### 1.1 Briefing Packet Setup (SPEC-002 Compliant)
- [ ] Create `/briefing/` directory structure
  - `actions/` - GitHub Actions concepts and permissions
  - `workflows/` - Reusable workflow patterns
  - `apps/` - GitHub App authentication model
  - `security/` - Least-privilege patterns
  - `prompting/` - LLM contract templates
- [ ] Vendor critical GitHub docs to `/vendor/docs/`
- [ ] Create `briefing.zip` packaging script

### 1.2 GitHub Actions Foundation
- [ ] Move workflows from archive to `.github/workflows/`:
  - `provision-new-study.yaml` - Study repo creation
  - `factory-health.yml` - Portfolio status updates
  - `stage-sync.yml` - Stage progression tracking
- [ ] Implement SHA-pinning for all third-party actions
- [ ] Add `actionlint` and `yamllint` validation

## Phase 2: Study Provisioning (Week 2)
### 2.1 Template Repository Setup
- [ ] Configure `study-template` as GitHub template repository
- [ ] Add stage issue templates (10 stages from Initiation to Evidence Synthesis)
- [ ] Create project board template with stage columns

### 2.2 Provision Workflow Enhancement
- [ ] Add repository creation via GitHub API
- [ ] Auto-generate initial project board
- [ ] Create Factory portfolio issue for new study
- [ ] Set up team permissions (admins, maintainers)
- [ ] Configure branch protection rules

## Phase 3: GitHub App Development (Week 3)
### 3.1 Python App Setup (FastAPI)
- [ ] Create `/app/` directory with FastAPI structure
- [ ] Implement webhook receiver with HMAC verification
- [ ] JWT authentication for App → Installation token flow
- [ ] Use `githubkit` for GitHub API interactions

### 3.2 Portfolio Synchronization
- [ ] Listen for issue state changes in study repos
- [ ] Update Factory project columns based on stage progression
- [ ] Track last activity timestamps
- [ ] Flag studies inactive >30 days as "delinquent"

## Phase 4: Project Board Automation (Week 4)
### 4.1 Factory Portfolio Project
- [ ] Create columns: Active Studies, By Stage, Partners, Health Status
- [ ] Implement issue cards with study metadata
- [ ] Add progress visualization (stage completion %)
- [ ] Link to study repos and project boards

### 4.2 Study Project Boards
- [ ] Auto-create boards with stage columns
- [ ] Add partner tracking view
- [ ] Implement stage transition automation
- [ ] Color-coded status indicators

## Phase 5: Testing & Documentation (Week 5)
### 5.1 Local Testing Infrastructure
- [ ] Set up `act` for local workflow testing
- [ ] Create test fixtures for common scenarios
- [ ] Implement guardrails validation suite
- [ ] Add GHES compatibility checks

### 5.2 Documentation
- [ ] User guide for study leads
- [ ] Admin guide for Factory operators
- [ ] API documentation for GitHub App
- [ ] Troubleshooting playbook

## Minimal Viable Product (MVP) Deliverables
1. **GitHub Action** that provisions new study repos from template
2. **GitHub App** that syncs study progress to Factory portfolio
3. **Project boards** auto-created with stage tracking
4. **Briefing packet** for LLM-assisted maintenance
5. **Test suite** with local validation via `act`

## Technical Stack
- **Languages**: Python (App), YAML (Workflows)
- **Frameworks**: FastAPI, PyJWT, githubkit
- **Tools**: actionlint, act, yamllint
- **Storage**: Stateless (no DB required for MVP)

## Success Criteria
- [ ] Study lead can provision new study in <5 minutes
- [ ] Portfolio automatically reflects study stage changes
- [ ] All workflows pass actionlint validation
- [ ] App handles webhooks with <1s response time
- [ ] Documentation enables self-service troubleshooting

## Risk Mitigation
- **API Rate Limits**: Implement caching and batch operations
- **Permission Errors**: Use least-privilege tokens with explicit scopes
- **GHES Compatibility**: Test on both GitHub.com and GHES environments
- **Maintenance**: Briefing packet enables LLM-assisted updates

## Next Steps
1. Set up development environment with devcontainer
2. Initialize briefing packet structure
3. Port archived workflows to active `.github/workflows/`
4. Begin FastAPI app scaffolding
5. Create initial test fixtures