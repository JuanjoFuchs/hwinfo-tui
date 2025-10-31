# WinGet Package Automation

This document explains how to set up and use the automated WinGet package publishing workflow.

## Overview

The `.github/workflows/winget-publish.yml` workflow automatically submits package updates to the Windows Package Manager Community Repository when you publish a new release on GitHub.

## Prerequisites

1. **Initial package submission**: Your package (`JuanjoFuchs.hwinfo-tui`) must already exist in the [winget-pkgs repository](https://github.com/microsoft/winget-pkgs)
2. **GitHub Personal Access Token (PAT)**: Required for submitting pull requests to the winget-pkgs repository

## Setup Instructions

### Step 1: Create a GitHub Personal Access Token (Classic)

1. Go to GitHub Settings → Developer settings → Personal access tokens → [Tokens (classic)](https://github.com/settings/tokens)
2. Click **Generate new token** → **Generate new token (classic)**
3. Configure the token:
   - **Note**: `WinGet Package Automation for hwinfo-tui`
   - **Expiration**: Choose your preferred expiration (90 days, 1 year, or no expiration)
   - **Scopes**: Check these permissions:
     - ✅ `public_repo` (required - access to public repositories)
     - ✅ `delete_repo` (optional - auto-cleanup failed forks)
4. Click **Generate token**
5. **IMPORTANT**: Copy the token immediately - you won't be able to see it again!

### Step 2: Add Token to Repository Secrets

1. Go to your hwinfo-tui repository on GitHub
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Configure the secret:
   - **Name**: `WINGET_TOKEN`
   - **Secret**: Paste the token you copied in Step 1
5. Click **Add secret**

### Step 3: Verify Workflow Configuration

The workflow is already configured in `.github/workflows/winget-publish.yml`. It will:

1. Trigger automatically when you publish a release
2. Extract the version from your release tag (e.g., `v1.0.2` → `1.0.2`)
3. Find the Windows x64 executable in your release assets
4. Download `wingetcreate.exe`
5. Update the WinGet manifest with the new version and installer URL
6. Submit a pull request to the winget-pkgs repository

## How to Use

### Automated Publishing (Recommended)

1. Create and push a new version tag:
   ```bash
   git tag v1.0.2
   git push origin v1.0.2
   ```

2. The release workflow (`.github/workflows/release.yml`) will automatically:
   - Build Python packages
   - Build Windows executable
   - Create a GitHub release with the assets

3. The winget-publish workflow will automatically:
   - Detect the new release
   - Submit an update to WinGet

4. Check the **Actions** tab to monitor progress

5. Once complete, a PR will be created in [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs/pulls)

### Manual Trigger

You can also manually trigger the workflow:

1. Go to **Actions** → **Publish to WinGet**
2. Click **Run workflow**
3. Select the branch and release

### Local Testing

If you have `wingetcreate` installed locally, you can test updates manually:

```powershell
# Update the package (without submitting)
wingetcreate update JuanjoFuchs.hwinfo-tui `
  --version 1.0.2 `
  --urls https://github.com/JuanjoFuchs/hwinfo-tui/releases/download/v1.0.2/hwinfo-tui-1.0.2-windows-x64.exe

# To submit (requires GITHUB_TOKEN environment variable)
$env:GITHUB_TOKEN = "your_token_here"
wingetcreate update JuanjoFuchs.hwinfo-tui `
  --version 1.0.2 `
  --urls https://github.com/JuanjoFuchs/hwinfo-tui/releases/download/v1.0.2/hwinfo-tui-1.0.2-windows-x64.exe `
  --token $env:GITHUB_TOKEN `
  --submit
```

## Troubleshooting

### Workflow fails with "Windows x64 executable not found"

**Cause**: The release asset name doesn't match the expected pattern `hwinfo-tui-*-windows-x64.exe`

**Solution**: Verify your release workflow creates assets with the correct naming format (see `.github/workflows/release.yml` lines 84-92)

### Workflow fails with "Authentication failed"

**Cause**: Missing or invalid `WINGET_TOKEN` secret

**Solution**:
- Verify the secret exists in repository settings
- Check the token hasn't expired
- Regenerate the token if needed

### PR to winget-pkgs is rejected

**Cause**: Various validation failures (incorrect hash, malformed manifest, etc.)

**Solution**:
- Check the PR comments for specific validation errors
- Common issues:
  - Installer URL returns 404 (release not fully published yet)
  - Version already exists
  - Manifest schema violations

### Fork out of sync

**Cause**: If you have a fork of microsoft/winget-pkgs, it might be out of sync

**Solution**: You can add a sync step before the update (similar to DevHome's approach):

```yaml
- name: Sync winget-pkgs fork
  shell: pwsh
  run: |
    gh repo sync YOUR_USERNAME/winget-pkgs -b master
  env:
    GH_TOKEN: ${{ secrets.WINGET_TOKEN }}
```

## Advanced Configuration

### Update Multiple Installers

If you add ARM64 or other architectures in the future:

```powershell
wingetcreate update JuanjoFuchs.hwinfo-tui `
  --version 1.0.2 `
  --urls "https://...x64.exe|x64" "https://...arm64.exe|ARM64" `
  --token $env:WINGET_TOKEN `
  --submit
```

### Test Without Submitting

Remove the `--submit` flag to generate manifests locally without creating a PR:

```powershell
wingetcreate update JuanjoFuchs.hwinfo-tui `
  --version 1.0.2 `
  --urls https://...exe
```

## References

- [WinGet Create Documentation](https://github.com/microsoft/winget-create)
- [WinGet Packages Repository](https://github.com/microsoft/winget-pkgs)
- [Package Submission Guidelines](https://github.com/microsoft/winget-pkgs/blob/master/CONTRIBUTING.md)
