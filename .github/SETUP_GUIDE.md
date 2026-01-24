# 🔧 VariDex GitHub Configuration Setup Guide

**Last Updated:** January 24, 2026  
**Estimated Time:** 30 minutes  
**Required Access:** Repository Admin

---

## 🎯 Overview

This guide walks you through the one-time configuration needed to activate VariDex's full CI/CD pipeline.

**What you'll configure:**
- ✅ GitHub Secrets (PyPI tokens, Codecov)
- ✅ GitHub Environments (production & testing)
- ✅ Branch Protection Rules
- ✅ Verification & Testing

---

## 📝 Prerequisites

### Required Accounts

1. **PyPI Account** (for production releases)
   - Create at: https://pypi.org/account/register/
   - Verify email address
   - Enable 2FA (recommended)

2. **Test PyPI Account** (for testing releases)
   - Create at: https://test.pypi.org/account/register/
   - Verify email address
   - Note: Separate from production PyPI

3. **Codecov Account** (optional, for coverage reports)
   - Sign up at: https://codecov.io
   - Connect GitHub account
   - Enable VariDex repository

---

## 🔑 Step 1: Create PyPI API Tokens

### A. Production PyPI Token

1. **Login to PyPI**
   - Go to: https://pypi.org/
   - Click "Log in" (top right)

2. **Navigate to Account Settings**
   - Click your username (top right)
   - Select "Account settings"

3. **Create API Token**
   - Scroll to "API tokens" section
   - Click "Add API token"
   - Fill in:
     ```
     Token name: GitHub Actions - VariDex
     Scope: Entire account (or "Project: varidex" if already published)
     ```
   - Click "Add token"

4. **Copy Token**
   - ⚠️ **IMPORTANT:** Copy the token immediately
   - It starts with `pypi-`
   - You won't be able to see it again!
   - Store temporarily in a secure location

### B. Test PyPI Token

1. **Login to Test PyPI**
   - Go to: https://test.pypi.org/
   - Click "Log in" (top right)

2. **Repeat the same process**
   - Navigate to Account settings
   - Create API token
   - Name: `GitHub Actions - VariDex Test`
   - Scope: Entire account
   - Copy and store the token

### C. Codecov Token (Optional)

1. **Login to Codecov**
   - Go to: https://codecov.io
   - Sign in with GitHub

2. **Add Repository**
   - Click "Add new repository"
   - Find and enable "Plantucha/VariDex"

3. **Get Upload Token**
   - Click on VariDex repository
   - Go to "Settings" → "General"
   - Copy the "Repository Upload Token"

---

## 🔐 Step 2: Add GitHub Secrets

### Navigate to Secrets Settings

1. Go to your VariDex repository: https://github.com/Plantucha/VariDex
2. Click **"Settings"** tab (top menu)
3. In left sidebar, click **"Secrets and variables"** → **"Actions"**

### Add Each Secret

For each secret below, click **"New repository secret"**:

#### Secret 1: PYPI_API_TOKEN

```yaml
Name: PYPI_API_TOKEN
Secret: [paste your production PyPI token here]
       (starts with pypi-)
```

**Click "Add secret"**

#### Secret 2: TEST_PYPI_API_TOKEN

```yaml
Name: TEST_PYPI_API_TOKEN
Secret: [paste your test PyPI token here]
       (starts with pypi-)
```

**Click "Add secret"**

#### Secret 3: CODECOV_TOKEN (Optional)

```yaml
Name: CODECOV_TOKEN
Secret: [paste your Codecov token here]
```

**Click "Add secret"**

### Verify Secrets Added

You should now see:
- ✅ PYPI_API_TOKEN
- ✅ TEST_PYPI_API_TOKEN
- ✅ CODECOV_TOKEN (if added)

⚠️ **Note:** You won't be able to view secret values after adding them (security feature)

---

## 🌎 Step 3: Create GitHub Environments

### Navigate to Environments Settings

1. Still in **Settings** tab
2. In left sidebar, click **"Environments"**

### Create Production Environment

1. Click **"New environment"**

2. **Configuration:**
   ```yaml
   Name: pypi
   ```

3. Click **"Configure environment"**

4. **Deployment protection rules:**
   - ☑️ Enable "Required reviewers"
   - Add yourself as reviewer
   - ☑️ Enable "Wait timer" (optional): 0 minutes

5. **Deployment branches:**
   - Select: **"Protected branches only"**
   - Or: **"Selected branches"** → Add rule: `refs/tags/v*`

6. **Environment secrets:**
   - Click "Add secret"
   - Name: `PYPI_API_TOKEN`
   - Value: [paste production PyPI token]
   - Click "Add secret"

7. **Save changes**

### Create Test Environment

1. Click **"New environment"** again

2. **Configuration:**
   ```yaml
   Name: test-pypi
   ```

3. Click **"Configure environment"**

4. **Deployment protection rules:**
   - Leave unchecked (no reviewers needed for testing)

5. **Deployment branches:**
   - Select: **"All branches"**

6. **Environment secrets:**
   - Click "Add secret"
   - Name: `TEST_PYPI_API_TOKEN`
   - Value: [paste test PyPI token]
   - Click "Add secret"

7. **Save changes**

### Verify Environments

You should now see:
- ✅ `pypi` environment (with reviewer)
- ✅ `test-pypi` environment (no reviewer)

---

## 🛡️ Step 4: Configure Branch Protection

### Navigate to Branch Settings

1. Still in **Settings** tab
2. In left sidebar, click **"Branches"**
3. Under "Branch protection rules", click **"Add rule"**

### Configure Protection for Main Branch

#### Branch name pattern:
```
main
```

#### Protection Rules:

**Status Checks:**
- ☑️ **Require status checks to pass before merging**
  - ☑️ Require branches to be up to date before merging
  - **Search and add these status checks:**
    - `code-quality`
    - `test (ubuntu-latest, 3.11)`
    - `security / codeql`
    - `build`

  ⚠️ **Note:** Status checks will appear after first CI run

**Pull Request Reviews:**
- ☑️ **Require a pull request before merging** (recommended)
  - Required approving reviews: 1
  - ☑️ Dismiss stale reviews

**Additional Rules:**
- ☑️ **Require linear history**
- ☑️ **Require deployments to succeed** (optional)
- ☑️ **Do not allow bypassing the above settings**
- ☐️ Allow force pushes (keep unchecked)
- ☐️ Allow deletions (keep unchecked)

**Optional (Enhanced Security):**
- ☑️ **Require signed commits** (if you use GPG signing)
- ☑️ **Require conversation resolution before merging**

#### Save Rule

Click **"Create"** at the bottom

### Verify Branch Protection

1. Go to repository main page
2. Look for shield icon next to "main" branch
3. Branch should show as "Protected"

---

## ✅ Step 5: Verification & Testing

### A. Verify Configuration

**Check Secrets:**
1. Settings → Secrets and variables → Actions
2. Should see: PYPI_API_TOKEN, TEST_PYPI_API_TOKEN, CODECOV_TOKEN

**Check Environments:**
1. Settings → Environments
2. Should see: pypi, test-pypi

**Check Branch Protection:**
1. Settings → Branches
2. Should see rule for "main" branch

### B. Test CI/CD Pipeline

**Create a test branch and PR:**

```bash
# Clone repository (if not already)
git clone https://github.com/Plantucha/VariDex.git
cd VariDex

# Create test branch
git checkout -b test/verify-ci-setup

# Make a small change
echo "\n## CI/CD Status\n\nCI/CD pipeline is now active!" >> README.md

# Commit and push
git add README.md
git commit -m "test: Verify CI/CD pipeline configuration"
git push origin test/verify-ci-setup
```

**Create Pull Request:**
1. Go to: https://github.com/Plantucha/VariDex/pulls
2. Click "New pull request"
3. Select: base: `main` ← compare: `test/verify-ci-setup`
4. Click "Create pull request"
5. Title: "Test: Verify CI/CD Configuration"
6. Click "Create pull request"

**Watch CI Run:**
1. In the PR, you'll see checks starting
2. Click "Details" on any check to see logs
3. Wait for all checks to complete (~8 minutes)

**Expected Results:**
- ✅ code-quality (Black, Flake8, mypy)
- ✅ test (multiple jobs for different platforms)
- ✅ security (CodeQL, vulnerability scans)
- ✅ build (package validation)
- ✅ docs (documentation checks)

**If all pass:**
- 🎉 Configuration successful!
- You can merge the PR
- Delete the test branch

**If any fail:**
- Check the logs in "Details"
- See troubleshooting section below

### C. Test Release Workflow (Optional)

**Only do this after main CI passes!**

```bash
# Update version to beta
vim varidex/__version__.py
# Change to: __version__ = "6.5.0-beta1"

# Commit
git add varidex/__version__.py
git commit -m "chore: Bump version to 6.5.0-beta1"
git push origin main

# Create tag
git tag v6.5.0-beta1
git push origin v6.5.0-beta1
```

**Or use manual workflow:**
1. Go to: Actions → Release & Publish
2. Click "Run workflow"
3. Enter version: `v6.5.0-beta1`
4. Select: `test` (for Test PyPI)
5. Click "Run workflow"

**Check Results:**
- Package should appear on Test PyPI
- GitHub release should be created
- Artifacts should be uploaded

---

## 🔧 Troubleshooting

### Issue: Status Checks Not Appearing

**Problem:** Can't select status checks in branch protection

**Solution:**
- Status checks only appear after first CI run
- Create and merge a PR first
- Then add status checks to branch protection
- Edit the branch protection rule after first CI run

### Issue: CI Fails with "Secret not found"

**Problem:** Workflow can't access secrets

**Solution:**
- Verify secret names are exact: `PYPI_API_TOKEN` (case-sensitive)
- Check secrets are in correct location (repository secrets, not environment)
- For environment secrets, verify environment name matches workflow

### Issue: PyPI Upload Fails

**Problem:** "Invalid or non-existent authentication information"

**Solution:**
- Verify token is correct (starts with `pypi-`)
- Check token hasn't expired
- Ensure token has correct scope (entire account or project)
- For first upload, use "Entire account" scope

### Issue: Branch Protection Blocks Merge

**Problem:** Can't merge even though checks pass

**Solution:**
- Ensure all required checks are passing
- Check if "Require branches to be up to date" is enabled
- If so, update branch with: `git pull origin main` then push
- Verify you have merge permissions

### Issue: CodeQL Fails

**Problem:** Security scanning fails

**Solution:**
- Usually first-run initialization
- Check logs for specific error
- Re-run the check
- If persistent, disable temporarily and investigate

---

## 📊 Post-Setup Checklist

### Configuration Complete:
- [ ] PyPI production token created and added
- [ ] Test PyPI token created and added
- [ ] Codecov token added (optional)
- [ ] Production environment (`pypi`) configured
- [ ] Test environment (`test-pypi`) configured
- [ ] Branch protection enabled on `main`
- [ ] Test PR created and CI passed
- [ ] All status checks passing
- [ ] Branch protection enforcing checks

### Verification Complete:
- [ ] Created test PR successfully
- [ ] All CI checks passed
- [ ] Merged test PR
- [ ] Confirmed branch protection works
- [ ] (Optional) Test release workflow works

### Documentation Updated:
- [ ] README badges added (optional)
- [ ] Team notified of new workflow
- [ ] Reviewed CI/CD documentation

---

## 📚 Additional Resources

**VariDex Documentation:**
- [CI/CD Pipeline Guide](../docs/CI_CD_PIPELINE.md)
- [CI/CD Completion Summary](../CI_CD_COMPLETION_SUMMARY.md)
- [Testing Quick Reference](../TESTING_QUICK_REFERENCE.md)
- [Project Status Summary](../PROJECT_STATUS_SUMMARY.md)

**GitHub Documentation:**
- [Encrypted Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [Using Environments](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment)
- [Branch Protection Rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/defining-the-mergeability-of-pull-requests/about-protected-branches)

**PyPI Documentation:**
- [PyPI API Tokens](https://pypi.org/help/#apitoken)
- [Publishing Packages](https://packaging.python.org/tutorials/packaging-projects/)

---

## ❓ Need Help?

**Issues with setup:**
- Check troubleshooting section above
- Review GitHub Actions logs for specific errors
- See [CI/CD Pipeline Guide](../docs/CI_CD_PIPELINE.md)

**Questions:**
- [GitHub Discussions](https://github.com/Plantucha/VariDex/discussions)
- [GitHub Issues](https://github.com/Plantucha/VariDex/issues)

---

**Setup Time:** ~30 minutes  
**Difficulty:** Beginner-friendly  
**One-time setup:** Yes, never needed again!

✅ **After completion, your CI/CD pipeline will be fully operational!** 🚀
