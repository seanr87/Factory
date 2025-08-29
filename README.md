# OHDSI Study Factory 🏭

> Simple system for creating and tracking OHDSI network studies

## Conventions
### Study Lead Management
When Provisioning, you can assign a Study Lead in 2 ways.
#### 1. Existing Study Lead
Simply select the Study Lead's name & GitHub name from the list. The Study Lead will receive Admin permissions on the Study Project* and Study Repo, and will be both assigned and tagged in the study's Factory Issue to be displayed in Factory Portfolio.
#### 2. Add New Study Lead
* Leave the "Select Existing Study Lead" dropdown on "Add New Study Lead".
* In the following fields, enter the new Study Lead's name and GitHub username.
* The Study Lead will receive Admin permissions on the Study Project* and Study Repo.
> If the Study Lead is an existing Collaborator, they'll be assigned to the study's Factory Issue.
> If the Study Lead is _not_ an existing Collaborator, they'll receive a Collaborator invitation. Once they accept it, **Coordinator must manually assign Study Lead to the study's Factory Issue.**
### Study Status Syncing
Upon creation, each Study Repository is populated with `status-tracking` Issues designed to guide the Study Lead through the process. When a Study Lead closes a `status-tracking` Issue, a GitHub Action modifies the study's `study-tracking` Factory Issue, providing Factory Portfolio with the study's updated status.

## Currently Built Functions ✅

- **Study Provisioning**: Automated study repository creation with GitHub Actions
- **Dynamic Study Lead Management**: Dropdown selection with automatic database updates
- **Template-Based Repository Creation**: New study repos created from predefined template
- **Study Lead Admin Access**: Automatic admin privileges assignment to study leads
- **Central Factory Tracking**: Issues created in Factory repo for each study
- **Factory Portfolio Integration**: Automatic population of Factory Portfolio Project with Lead, Study Repo, and Objective fields
- **Project Board Integration**: Per-study project boards linked to repositories  
- **Status Tracking Issues**: Configurable milestone issues created in study repositories
- **Activity Monitoring**: Automated daily checks for inactive studies with emoji status indicators
- **Study Lead Database**: JSON-based storage with GitHub App workflow modification
- **Validation System**: Input validation for study titles, dates, and GitHub usernames
- **Modular GitHub Actions**: Reusable actions for study management operations

## Next Functions to Implement 🚧

Based on SPEC-001 requirements, these functions should be incorporated next:

- [x] **Factory Portfolio Auto-Updates**: Central project updates based on individual study progress ✅
- [x] **Last Activity Tracking**: Display last updated date and file/issue links for each study ✅  
- [x] **Delinquent Study Detection**: Automatic "delinquent" tags for studies inactive >30 days ✅
- [x] **Study Start Date Recording**: Automatic timestamp capture during repo creation ✅
- [ ] **Data Partner Progress Tracking**: Charts/lists showing individual data partner status
- [x] **Project Board Links**: Direct links from portfolio issues to study project boards ✅
- [x] **Study Phase Ordering**: Issues displayed in order of study phases (Protocol → Results) ✅
- [ ] **Data Partner View**: Separate view for tracking data partner progress across studies
- [x] **Status Color Coding**: Appropriately colored statuses for studies and data partners ✅
- [x] **Real-time Portfolio Updates**: GitHub App integration for live status synchronization ✅

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
- Factory Portfolio Project updated with study details
- Status tracking issues created in study repository

### Track Studies

All studies are tracked as issues in this repo with:
- Current stage (Protocol → Results)
- Last activity date
- Status (🟢 Active, 🟡 Low Activity, 🔴 Inactive)

### Architecture

```
Factory/
├── .github/workflows/
│   ├── provision-study.yml       # Creates new studies
│   ├── activity-check.yml        # Daily activity monitoring
│   └── factory-issue-updater.yml # Updates Factory issues
├── .github/actions/              # Reusable actions
├── .github/data/                # Configuration files
└── study-template/              # Template for new studies
```

## Documentation

- **[Setup Instructions](SETUP_INSTRUCTIONS.md)** - Start here!
- **[Status Feedback System](.github/docs/status-feedback-system.md)** - How status tracking works
- **[MVP Overview](README_MVP.md)** - Technical details
- **[Implementation Plan](IMPLEMENTATION_PLAN.md)** - Roadmap

## Status

✅ **MVP Complete** - Core functionality working
- Study provisioning in <2 minutes
- Automatic activity tracking
- Simple issue-based portfolio

## Support

- Check workflow logs in Actions tab
- See troubleshooting in [SETUP_INSTRUCTIONS.md](SETUP_INSTRUCTIONS.md)
- Review architecture in [README_MVP.md](README_MVP.md)