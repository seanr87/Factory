# Migration Plan: Factory & Study-Template to Johns Hopkins Enterprise

## Overview

This document outlines the steps to migrate the OHDSI Study Factory system from a personal GitHub account to the Johns Hopkins GitHub Enterprise (OHDSI-JHU organization). The system consists of two repositories that work together:

- **Factory** - Main system that creates and manages study repositories
- **study-template** - Template used to create new study repositories

## Prerequisites

- Access to Johns Hopkins GitHub Enterprise
- Admin permissions in the OHDSI-JHU organization
- Personal access token with organization admin privileges

## Migration Steps

### Phase 1: Fork Both Repositories

#### Step 1.1: Fork Factory Repository
1. Go to the current Factory repository: `https://github.com/seanr87/Factory`
2. Click the **"Fork"** button in the top-right corner
3. Select **"OHDSI-JHU"** as the destination organization
4. Keep the repository name as **"Factory"**
5. Click **"Create fork"**

#### Step 1.2: Fork Study-Template Repository
1. Go to the study-template repository: `https://github.com/seanr87/study-template`
2. Click the **"Fork"** button in the top-right corner
3. Select **"OHDSI-JHU"** as the destination organization
4. Keep the repository name as **"study-template"**
5. Click **"Create fork"**

#### Step 1.3: Configure Study-Template as Template
1. Go to `https://github.com/OHDSI-JHU/study-template`
2. Click **"Settings"** tab
3. Scroll down to **"Template repository"** section
4. Check the box **"Template repository"**
5. Click **"Update"**

### Phase 2: Set Up GitHub App (Required for Token Generation)

#### Step 2.1: Create GitHub App
1. Go to `https://github.com/organizations/OHDSI-JHU/settings/apps`
2. Click **"New GitHub App"**
3. Fill in the form:
   - **GitHub App name**: `Factory Study Bot`
   - **Homepage URL**: `https://github.com/OHDSI-JHU/Factory`
   - **Webhook URL**: `https://example.com` (not used, but required)
   - **Webhook secret**: Leave blank
4. **Permissions** (Repository permissions):
   - Contents: **Read and write**
   - Issues: **Read and write**
   - Metadata: **Read**
   - Projects: **Read and write**
   - Pull requests: **Read and write**
5. **Organization permissions**:
   - Projects: **Read and write**
6. **Where can this GitHub App be installed?**: **Only on this account**
7. Click **"Create GitHub App"**

#### Step 2.2: Generate Private Key
1. After creating the app, scroll down to **"Private keys"**
2. Click **"Generate a private key"**
3. Download the `.pem` file and save it securely

#### Step 2.3: Install GitHub App
1. On the same page, click **"Install App"** in the left sidebar
2. Click **"Install"** next to OHDSI-JHU
3. Select **"Selected repositories"**
4. Choose both:
   - `OHDSI-JHU/Factory`
   - `OHDSI-JHU/study-template`
5. Click **"Install"**

### Phase 3: Create Factory Portfolio Project

#### Step 3.1: Create Project Board
1. Go to `https://github.com/orgs/OHDSI-JHU/projects`
2. Click **"New project"**
3. Choose **"Table"** template
4. Name: `Factory Portfolio`
5. Description: `Tracks all OHDSI studies`
6. Click **"Create project"**

#### Step 3.2: Add Required Fields
The project needs these fields (some may already exist):
1. Click **"+ Add field"** to add:
   - **Objective** (Single select) with options:
     - Protocol
     - Data Collection
     - Analysis
     - Results
     - Complete
   - **Lead** (Text)
   - **Study Repo** (Text)
   - **Start Date** (Date)
   - **Target Date** (Date)

#### Step 3.3: Get Project Information
1. Note the project URL (e.g., `https://github.com/orgs/OHDSI-JHU/projects/1`)
2. The number at the end is your **project number** (e.g., `1`)

### Phase 4: Configure Repository Secrets and Variables

## 🏭 Factory Repository Configuration

**Location**: `https://github.com/OHDSI-JHU/Factory/settings`

### Secrets (Factory Repository Only)
Go to **Settings → Secrets and variables → Actions → Secrets tab**

**SECRET 1: APP_ID**
- Name: `APP_ID`
- Value: The App ID from your GitHub App (found on the app's main page)

**SECRET 2: APP_PRIVATE_KEY**
- Name: `APP_PRIVATE_KEY`
- Value: Copy and paste the entire contents of the `.pem` file you downloaded (including the `-----BEGIN RSA PRIVATE KEY-----` and `-----END RSA PRIVATE KEY-----` lines)

**SECRET 3: ORG_ADMIN_TOKEN**
- Name: `ORG_ADMIN_TOKEN`
- Value: Create a personal access token:
  1. Go to `https://github.com/settings/tokens/new`
  2. Name: "Factory Admin Token"
  3. Expiration: 90 days (or longer)
  4. Select scopes:
     - ✅ **repo** (Full control of private repositories)
     - ✅ **workflow** (Update GitHub Action workflows)
     - ✅ **admin:org** (Full control of orgs and teams)
     - ✅ **project** (Full control of projects)
  5. Click **"Generate token"**
  6. Copy the token immediately (you won't see it again)

### Variables (Factory Repository Only)
Go to **Settings → Secrets and variables → Actions → Variables tab**

**VARIABLE 1: FACTORY_PROJECT_NUMBER**
- Name: `FACTORY_PROJECT_NUMBER`
- Value: The project number from Phase 3.3 (e.g., `1`)

**VARIABLE 2: FACTORY_PROJECT_URL**
- Name: `FACTORY_PROJECT_URL`
- Value: The full project URL from Phase 3.3 (e.g., `https://github.com/orgs/OHDSI-JHU/projects/1`)

## 📚 Study-Template Repository Configuration

**Location**: `https://github.com/OHDSI-JHU/study-template/settings`

### Variables (Study-Template Repository Only)
Go to **Settings → Secrets and variables → Actions → Variables tab**

**VARIABLE: FACTORY_PROJECT_URL**
- Name: `FACTORY_PROJECT_URL`
- Value: The same project URL as above (e.g., `https://github.com/orgs/OHDSI-JHU/projects/1`)

### Phase 5: Testing

#### Step 5.1: Test Study Creation
1. Go to `https://github.com/OHDSI-JHU/Factory/actions`
2. Click **"Provision New Study"** workflow
3. Click **"Run workflow"**
4. Fill in test values:
   - Study title: `Migration Test Study`
   - Target date: `2025-12-31`
   - Study lead: Select or add a test lead
5. Click **"Run workflow"**

#### Step 5.2: Verify Results
After the workflow completes, check:
- ✅ New repository created: `OHDSI-JHU/study-migration-test-study`
- ✅ Factory Portfolio Project has new row with study details
- ✅ Factory repository has new tracking issue
- ✅ Study repository has status tracking issues

## Configuration Summary

### What Gets Configured Automatically
When a new study is created, the Factory system automatically:
- Creates the new study repository from the template
- Adds the `ORG_ADMIN_TOKEN` secret to the new study repository
- Adds the `FACTORY_PROJECT_URL` variable to the new study repository

### Manual Configuration Required

| Repository | Secrets | Variables |
|------------|---------|-----------|
| **OHDSI-JHU/Factory** | `APP_ID`<br>`APP_PRIVATE_KEY`<br>`ORG_ADMIN_TOKEN` | `FACTORY_PROJECT_NUMBER`<br>`FACTORY_PROJECT_URL` |
| **OHDSI-JHU/study-template** | None | `FACTORY_PROJECT_URL` |
| **Generated Study Repos** | `ORG_ADMIN_TOKEN` (automatic) | `FACTORY_PROJECT_URL` (automatic) |

## Important Configuration Notes

### Automatic Organization Detection
The system uses `github.repository_owner` which will automatically resolve to `OHDSI-JHU` when running in the OHDSI-JHU organization. No code changes are needed for this.

### Template Repository Reference
The system is currently configured to use the template at line 38 in `.github/actions/create-study-repository/action.yml`:
```yaml
--template "${{ github.repository_owner }}/study-template"
```
This will automatically use `OHDSI-JHU/study-template` when running in the OHDSI-JHU organization.

### Status Feedback System
Study repositories automatically send status updates back to the Factory repository. This requires:
- Study repositories have the `ORG_ADMIN_TOKEN` secret configured (done automatically during provisioning)
- The `FACTORY_PROJECT_URL` variable is set in both the study-template and generated study repositories

## Post-Migration Cleanup

Once the migration is complete and tested:
1. Archive or delete the original personal repositories
2. Update any documentation that references the old repository locations
3. Notify team members of the new repository locations
4. Consider setting up branch protection rules on the Factory repository