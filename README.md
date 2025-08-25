# OHDSI Study Factory 🏭

> Simple system for creating and tracking OHDSI network studies

## Currently Built Functions ✅

- **Study Provisioning**: Automated study repository creation with GitHub Actions
- **Dynamic Study Lead Management**: Dropdown selection with automatic database updates
- **Template-Based Repository Creation**: New study repos created from predefined template
- **Study Lead Admin Access**: Automatic admin privileges assignment to study leads
- **Central Factory Tracking**: Issues created in Factory repo for each study
- **Project Board Integration**: Per-study project boards linked to repositories
- **Activity Monitoring**: Automated daily checks for inactive studies
- **Study Lead Database**: JSON-based storage with GitHub App workflow modification
- **Validation System**: Input validation for study titles, dates, and GitHub usernames
- **Modular GitHub Actions**: Reusable actions for study management operations

## Next Functions to Implement 🚧

Based on SPEC-001 requirements, these functions should be incorporated next:

- [ ] **Factory Portfolio Auto-Updates**: Central project updates based on individual study progress
- [ ] **Last Activity Tracking**: Display last updated date and file/issue links for each study  
- [ ] **Delinquent Study Detection**: Automatic "delinquent" tags for studies inactive >30 days
- [ ] **Study Start Date Recording**: Automatic timestamp capture during repo creation
- [ ] **Data Partner Progress Tracking**: Charts/lists showing individual data partner status
- [ ] **Project Board Links**: Direct links from portfolio issues to study project boards
- [ ] **Study Phase Ordering**: Issues displayed in order of study phases (Protocol → Results)
- [ ] **Data Partner View**: Separate view for tracking data partner progress across studies
- [ ] **Status Color Coding**: Appropriately colored statuses for studies and data partners
- [ ] **Real-time Portfolio Updates**: GitHub App integration for live status synchronization

## Quick Start (15 minutes)

See **[SETUP_INSTRUCTIONS.md](SETUP_INSTRUCTIONS.md)** for step-by-step setup guide.

## What It Does

1. **Creates new study repositories** from a template with one click
2. **Tracks all studies** in a central Factory repository  
3. **Monitors activity** and flags inactive studies
4. **Updates progress** as studies advance through stages

## How to Use

### Create a New Study

1. Go to **Actions** → **Provision New Study**
2. Click **Run workflow**
3. Fill in study details
4. Click **Run**

Done! You'll get:
- New private study repository
- Study lead added as admin
- Tracking issue in Factory repo

### Track Studies

All studies are tracked as issues in this repo with:
- Current stage (Protocol → Results)
- Last activity date
- Status (🟢 Active, 🟡 Low Activity, 🔴 Inactive)

### Architecture

```
Factory/
├── .github/workflows/
│   ├── provision-study.yml    # Creates new studies
│   └── factory-sync.yml       # Daily activity check
├── app/                       # Optional GitHub App
└── study-template/            # Template for new studies
```

## Documentation

- **[Setup Instructions](SETUP_INSTRUCTIONS.md)** - Start here!
- **[MVP Overview](README_MVP.md)** - Technical details
- **[Implementation Plan](IMPLEMENTATION_PLAN.md)** - Roadmap
- **[App Documentation](app/README.md)** - GitHub App details

## Status

✅ **MVP Complete** - Core functionality working
- Study provisioning in <2 minutes
- Automatic activity tracking
- Simple issue-based portfolio

## Support

- Check workflow logs in Actions tab
- See troubleshooting in [SETUP_INSTRUCTIONS.md](SETUP_INSTRUCTIONS.md)
- Review architecture in [README_MVP.md](README_MVP.md)