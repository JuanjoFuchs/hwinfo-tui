# GitHub Issue for microsoft/winget-cli

## Title
Portable apps should default to `UpgradeBehavior: uninstallPrevious`

## Labels
- Area-Manifests
- Issue-Feature
- Priority-3

## Description

### Problem

Portable apps upgraded via `winget upgrade` leave duplicate entries in the WinGet tracking database when the manifest doesn't explicitly specify `UpgradeBehavior: uninstallPrevious`. This creates confusion for users and wastes disk space tracking ghost versions.

### Example

```powershell
PS> winget upgrade JuanjoFuchs.hwinfo-tui
# Upgrade completes successfully

PS> winget list --id JuanjoFuchs.hwinfo-tui
Name       Id                     Version Source
-------------------------------------------------
hwinfo-tui JuanjoFuchs.hwinfo-tui 1.0.3   winget
hwinfo-tui JuanjoFuchs.hwinfo-tui 1.0.2   winget  # OLD VERSION STILL TRACKED
```

The physical file was correctly replaced with v1.0.3, but the database entry for v1.0.2 remains.

### Why This Matters for Portable Apps

The [Portable Apps Specification](https://github.com/microsoft/winget-cli/blob/master/doc/specs/%23182%20-%20Support%20for%20installation%20of%20portable%20standalone%20apps.md) explicitly states:

> "There will be no support for installing multiple 'side by side' versions of portable packages."

Since portable apps **cannot** install side-by-side by design, there is no valid use case for leaving the old version in the tracking database during an upgrade.

### Current Workarounds

**For Users:**
```powershell
# Option 1: Manual cleanup
winget uninstall --id Package.Id --version 1.0.2

# Option 2: Use --uninstall-previous flag (WinGet 1.5+)
winget upgrade Package.Id --uninstall-previous

# Option 3: Clean reinstall
winget uninstall Package.Id && winget install Package.Id
```

**For Package Maintainers:**
Manually add `UpgradeBehavior: uninstallPrevious` to every manifest version:
```yaml
InstallerType: portable
UpgradeBehavior: uninstallPrevious
```

### Proposed Solution

**Make `UpgradeBehavior: uninstallPrevious` the default for `InstallerType: portable`**

When a manifest specifies `InstallerType: portable` without an explicit `UpgradeBehavior` field, WinGet should:
1. Default to `UpgradeBehavior: uninstallPrevious`
2. Remove the old version's tracking entry before/after installing the new version
3. Only allow explicit override if package maintainer specifies a different `UpgradeBehavior`

### Benefits

1. **Aligns with spec**: Matches the documented behavior that portable apps don't support side-by-side installations
2. **Better UX**: Users see clean `winget list` output without duplicate entries
3. **Reduces support burden**: Fewer "why do I have two versions installed?" questions
4. **Backwards compatible**: Existing manifests with explicit `UpgradeBehavior` are unaffected

### Implementation Notes

This could be implemented in the upgrade flow by checking:
```cpp
if (installerType == InstallerType::Portable && upgradeBehavior == UpgradeBehavior::Unspecified) {
    upgradeBehavior = UpgradeBehavior::UninstallPrevious;
}
```

### Related Issues

- #1865 - Upgrading an application does not remove the existing version
- #2727 - Switch for --uninstallPrevious for upgrade
- #5615 - Winget doesn't remove older version when upgrading certain packages
- #5800 - winget upgrade installs a second copy instead of upgrading it
- Discussion #5620 - Duplicate versions after upgrade

### Test Case

Package: `JuanjoFuchs.hwinfo-tui` (portable app)
- Install v1.0.2
- Upgrade to v1.0.3 (manifest has no UpgradeBehavior)
- Run `winget list --id JuanjoFuchs.hwinfo-tui`
- **Expected**: Only v1.0.3 appears
- **Current**: Both v1.0.2 and v1.0.3 appear

### Additional Context

- This issue affects all portable apps that don't explicitly set `UpgradeBehavior`
- The WinGet Community Repository has hundreds of portable apps
- Package maintainers are not consistently aware of this requirement
- The `--uninstall-previous` flag exists but requires user intervention

---

**Environment:**
- WinGet Version: 1.9.1571 (and later)
- Windows Version: Windows 11 24H2
- Installer Type: portable
