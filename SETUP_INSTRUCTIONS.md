# 🚀 Factory Setup Instructions - Super Simple!

## What You Need to Do (15 minutes total)

### Part 1: GitHub Setup (5 minutes)

1. **Go to your Factory repo settings**
   ```
   https://github.com/YOUR_ORG/Factory/settings/secrets/actions
   ```

2. **Add these secrets** (click "New repository secret" for each):
   
   **SECRET #1: `ORG_ADMIN_TOKEN`**
   - Go to: https://github.com/settings/tokens/new
   - Name: "Factory Admin Token"
   - Expiration: 90 days (or longer)
   - Check these boxes:
     ✅ repo (all)
     ✅ workflow
     ✅ admin:org (if creating repos in an org)
   - Click "Generate token"
   - Copy the token and save as `ORG_ADMIN_TOKEN` secret

   **SECRET #2: `ORG_LOGIN`**
   - Value: Your GitHub username or organization name
   - Example: `seanr87` or `my-org-name`

   **SECRET #3: `TEMPLATE_REPO`**
   - Value: `study-template`
   - This is the name of your template repository

3. **Add this variable** (Go to Settings → Variables → New repository variable):
   
   **VARIABLE: `FACTORY_PROJECT_NUMBER`**
   - Value: Your Factory Portfolio project number (see Part 2.5 below)
   - This enables automatic issue tracking in your portfolio

### Part 2: Create Template Repository (3 minutes)

1. **Create a new repo called `study-template`** in your organization
   
2. **Add a basic README.md** with this content:
   ```markdown
   # [Study Name]
   
   ## Overview
   Study description here
   
   ## Status
   - [ ] Protocol Development
   - [ ] Data Collection
   - [ ] Analysis
   - [ ] Results
   
   ## Team
   - Lead: [Name]
   - Site: [Institution]
   ```

3. **Go to Settings → Make it a template**
   - Check "Template repository" box

### Part 2.5: Create Factory Portfolio Project (2 minutes)

1. **Go to your organization or user profile**
   - Click "Projects" tab
   - Click "New project"
   
2. **Create the project**
   - Name: `Factory Portfolio` 
   - Description: `Tracks all OHDSI studies`
   - Template: `Table` or `Board` (your choice)
   
3. **Get the project number**
   - After creating, look at the URL: `https://github.com/users/USERNAME/projects/NUMBER`
   - The NUMBER is what you need for `FACTORY_PROJECT_NUMBER` variable
   - Example: if URL is `/projects/3`, then set variable to `3`

### Part 3: Test It! (2 minutes)

1. **Go to Actions tab** in your Factory repo
   
2. **Click "Provision New Study"** workflow
   
3. **Click "Run workflow"** and fill in:
   - Study title: `Test Study 2025`
   - Lead name: `Your Name`
   - Lead GitHub: `your-github-username`
   - Target date: `2025-12-31`
   
4. **Click green "Run workflow" button**

5. **Wait 30 seconds** - you should see:
   - New private repository created: `study-test-study-2025`
   - New issue in Factory repo tracking the study
   - You're added as admin to the new study repo

## That's It! 🎉

### What's Working Now:
- ✅ Create new studies with one click
- ✅ Automatic tracking in Factory repo
- ✅ Daily sync of study activity (runs at 9 AM UTC)

### Optional: GitHub App (Advanced - 30 minutes)

If you want automatic stage tracking when issues are labeled:

1. **Create GitHub App**:
   - Go to: Organization Settings → Developer settings → GitHub Apps → New
   - Name: `Factory Sync Bot`
   - Homepage: `https://github.com/YOUR_ORG/Factory`
   - Webhook URL: `https://your-app.herokuapp.com/webhook` (deploy first)
   - Permissions: Issues (Read & Write)
   - Subscribe to: Issues events
   - Create and download private key

2. **Deploy the App** (easiest with Heroku):
   ```bash
   cd app
   heroku create factory-sync-app
   heroku config:set GITHUB_APP_ID=your_app_id
   heroku config:set GITHUB_APP_WEBHOOK_SECRET=your_secret
   git push heroku main
   ```

3. **Install App** on your Factory and study repos

## Troubleshooting

**"Repository creation failed"**
- Check your `ORG_ADMIN_TOKEN` has `repo` and `admin:org` permissions
- Make sure `study-template` repository exists and is set as template

**"Workflow not showing up"**
- Go to Actions tab → Look for "Provision New Study"
- If not there, check the workflow file exists: `.github/workflows/provision-study.yml`

**"Can't push to GitHub"**
- You need to configure git credentials:
  ```bash
  git config --global user.name "Your Name"
  git config --global user.email "your-email@example.com"
  ```
- Then use GitHub CLI or personal access token to push

## Need Help?

1. Check the workflow logs in Actions tab
2. Look at `README_MVP.md` for architecture details
3. Test locally with: `make validate`

## Next Steps

Once working:
1. Create your first real study
2. Add team members as admins
3. Start tracking progress with issue labels
4. Consider deploying the GitHub App for automation