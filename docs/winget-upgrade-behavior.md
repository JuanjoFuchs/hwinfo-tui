# WinGet UpgradeBehavior for Portable Apps

## Issue Overview

WinGet portable apps that don't explicitly specify `UpgradeBehavior` can leave duplicate entries in the WinGet database after upgrades. While the actual executable gets replaced correctly, the old version remains tracked in `winget list`, leading to confusion and potential PATH conflicts.

## Root Cause

When upgrading a portable app, WinGet's default behavior is to:
1. Download the new executable
2. Replace the file in the installation directory
3. Update the tracking database

However, without explicit `UpgradeBehavior: uninstallPrevious`, the old version's database entry **is not removed**, resulting in both versions appearing in `winget list`.

## The Fix: Add UpgradeBehavior to Manifests

### Required Manifest Change

Add the `UpgradeBehavior: uninstallPrevious` field to your installer manifest:

```yaml
# JuanjoFuchs.hwinfo-tui.installer.yaml
PackageIdentifier: JuanjoFuchs.hwinfo-tui
PackageVersion: 1.0.3
InstallerType: portable
UpgradeBehavior: uninstallPrevious  # <-- ADD THIS LINE
Commands:
- hwinfo-tui
Installers:
- Architecture: x64
  InstallerUrl: https://github.com/JuanjoFuchs/hwinfo-tui/releases/download/v1.0.3/hwinfo-tui-1.0.3-windows-x64.exe
  InstallerSha256: <hash>
ManifestType: installer
ManifestVersion: 1.10.0
ReleaseDate: 2025-10-31
```

### Valid UpgradeBehavior Values

According to the [WinGet manifest schema](https://aka.ms/winget-manifest.installer.1.10.0.schema.json):

- `install` - Install over the existing version (default for most installers)
- `uninstallPrevious` - Uninstall the previous version before installing the new one
- `deny` - Prevent upgrades entirely

### Why `uninstallPrevious` for Portable Apps?

The [WinGet Portable Apps specification](https://github.com/microsoft/winget-cli/blob/master/doc/specs/%23182%20-%20Support%20for%20installation%20of%20portable%20standalone%20apps.md) explicitly states:

> "There will be no support for installing multiple 'side by side' versions of portable packages."

Since portable apps **cannot** install side-by-side, the old version should always be removed during upgrade.

## User Workarounds

### For Users Experiencing This Issue

If you've upgraded and see duplicate entries:

**Option 1: Uninstall old version manually**
```powershell
winget uninstall --id JuanjoFuchs.hwinfo-tui --version 1.0.2
```

**Option 2: Clean reinstall**
```powershell
winget uninstall JuanjoFuchs.hwinfo-tui
winget install JuanjoFuchs.hwinfo-tui
```

**Option 3: Use the --uninstall-previous flag (WinGet 1.5+)**
```powershell
winget upgrade JuanjoFuchs.hwinfo-tui --uninstall-previous
```

### Verifying the Fix

After upgrade, verify only one version is installed:
```powershell
winget list --id JuanjoFuchs.hwinfo-tui
```

Expected output (single entry):
```
Name       Id                     Version Source
-------------------------------------------------
hwinfo-tui JuanjoFuchs.hwinfo-tui 1.0.3   winget
```

## Automated Workflow Integration

**Current Limitation**: The `wingetcreate update` command does not support setting `UpgradeBehavior` via command-line parameters (as of version 1.10.3).

### Manual Process

**Note:** This manual step was only required **once** for version 1.0.3. After adding `UpgradeBehavior` to the manifest, `wingetcreate` automatically preserves this field when updating to subsequent versions since it uses the previous version's manifest as a template.

**For the first time** (or if starting from a manifest without UpgradeBehavior):

1. Go to the created PR in [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs/pulls)
2. Edit the `JuanjoFuchs.hwinfo-tui.installer.yaml` file
3. Add `UpgradeBehavior: uninstallPrevious` after the `InstallerType` line
4. Commit the change to the PR branch

Example:
```yaml
PackageIdentifier: JuanjoFuchs.hwinfo-tui
PackageVersion: 1.0.3
InstallerType: portable
UpgradeBehavior: uninstallPrevious  # <-- ADD THIS LINE
Commands:
- hwinfo-tui
```

**For subsequent versions**: No manual action needed - the field is automatically preserved.

### Future Automation

A GitHub issue has been filed with microsoft/winget-create requesting support for setting `UpgradeBehavior` via command-line: [microsoft/winget-create#632](https://github.com/microsoft/winget-create/issues/632)

Once this feature is available, the workflow can be updated to include:
```bash
wingetcreate update JuanjoFuchs.hwinfo-tui \
  --version 1.0.3 \
  --urls https://... \
  --upgrade-behavior uninstallPrevious \  # Future flag
  --token $WINGET_TOKEN \
  --submit
```

## Related WinGet Issues

**Issues Filed by This Project:**
- [microsoft/winget-cli#5851 - Portable apps should default to UpgradeBehavior: uninstallPrevious](https://github.com/microsoft/winget-cli/issues/5851)
- [microsoft/winget-create#632 - Add --upgrade-behavior parameter to update command](https://github.com/microsoft/winget-create/issues/632)

**Related Existing Issues:**
- [#1865 - Upgrading an application does not remove the existing version](https://github.com/microsoft/winget-cli/issues/1865)
- [#2727 - Switch for --uninstallPrevious for upgrade](https://github.com/microsoft/winget-cli/issues/2727)
- [#5615 - Winget doesn't remove older version when upgrading certain packages](https://github.com/microsoft/winget-cli/issues/5615)
- [#5800 - winget upgrade installs a second copy instead of upgrading it](https://github.com/microsoft/winget-cli/issues/5800)
- [Discussion #5620 - Duplicate versions after upgrade](https://github.com/microsoft/winget-cli/discussions/5620)

## References

- [WinGet Portable Apps Specification](https://github.com/microsoft/winget-cli/blob/master/doc/specs/%23182%20-%20Support%20for%20installation%20of%20portable%20standalone%20apps.md)
- [WinGet Installer Manifest Schema v1.10.0](https://aka.ms/winget-manifest.installer.1.10.0.schema.json)
- [WinGet Upgrade Command Documentation](https://learn.microsoft.com/en-us/windows/package-manager/winget/upgrade)
