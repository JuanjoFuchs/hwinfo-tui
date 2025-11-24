# GitHub Issue for microsoft/winget-create

## Title
Add `--upgrade-behavior` parameter to `update` command

## Labels
- enhancement
- update-command

## Description

### Problem

The `wingetcreate update` command does not support setting the `UpgradeBehavior` field in installer manifests via command-line parameters. This forces users to either:
1. Manually edit generated manifests after running `wingetcreate update`, or
2. Use interactive mode (which breaks automation)

This is particularly problematic for **portable apps**, which should typically use `UpgradeBehavior: uninstallPrevious` to avoid leaving duplicate tracking entries (see [related winget-cli issue](link to first issue)).

### Current Limitation

```bash
# This works:
wingetcreate update JuanjoFuchs.hwinfo-tui \
  --version 1.0.3 \
  --urls https://github.com/.../hwinfo-tui-1.0.3.exe \
  --token $GITHUB_TOKEN \
  --submit

# But there's no way to set UpgradeBehavior!
# Users must manually edit the generated manifest and update the PR
```

### Proposed Solution

Add a `--upgrade-behavior` (or `-b`) parameter to the `update` command:

```bash
wingetcreate update JuanjoFuchs.hwinfo-tui \
  --version 1.0.3 \
  --urls https://github.com/.../hwinfo-tui-1.0.3.exe \
  --upgrade-behavior uninstallPrevious \
  --token $GITHUB_TOKEN \
  --submit
```

### Parameter Specification

**Name**: `--upgrade-behavior` or `-b`
**Type**: String (enum)
**Valid Values**:
- `install` - Install over existing version
- `uninstallPrevious` - Uninstall previous version first
- `deny` - Prevent upgrades

**Default**: No change to existing manifest (or omit field if creating new)

**Scope**: Can be set at root level or per-installer

### Example Usage

**Simple case (root level):**
```bash
wingetcreate update Package.Id \
  --version 2.0.0 \
  --urls https://example.com/app.exe \
  --upgrade-behavior uninstallPrevious
```

**Multiple installers (per-installer):**
```bash
wingetcreate update Package.Id \
  --version 2.0.0 \
  --urls "https://example.com/x64.exe|x64" "https://example.com/arm64.exe|ARM64" \
  --upgrade-behavior "uninstallPrevious|uninstallPrevious"
```

### Generated Manifest

The command would generate/update:

```yaml
PackageIdentifier: Package.Id
PackageVersion: 2.0.0
InstallerType: portable
UpgradeBehavior: uninstallPrevious  # <-- NEW FIELD
Commands:
- app
Installers:
- Architecture: x64
  InstallerUrl: https://example.com/x64.exe
  InstallerSha256: <hash>
```

### Benefits

1. **Automation-friendly**: CI/CD pipelines can set `UpgradeBehavior` without manual intervention
2. **Consistency**: All manifest fields can be set via CLI
3. **Portable app best practices**: Easy to follow the recommendation of using `uninstallPrevious` for portable apps
4. **Time-saving**: No need to manually edit generated PRs

### Use Case: GitHub Actions

Many projects use GitHub Actions to automatically update WinGet packages:

```yaml
- name: Update WinGet package
  run: |
    wingetcreate update ${{ env.PACKAGE_ID }} \
      --version ${{ github.ref_name }} \
      --urls ${{ steps.build.outputs.installer_url }} \
      --upgrade-behavior uninstallPrevious \
      --token ${{ secrets.WINGET_TOKEN }} \
      --submit
```

Without this parameter, users must either:
- Add a post-processing step to modify manifests (complex)
- Manually edit the PR after automation creates it (defeats the purpose of automation)
- Skip `UpgradeBehavior` entirely (leaves duplicate tracking entries for portable apps)

### Implementation Considerations

1. **Backward Compatibility**: Parameter is optional, existing behavior unchanged
2. **Validation**: Should validate against enum values (`install`, `uninstallPrevious`, `deny`)
3. **Persistence**: If updating an existing manifest that already has `UpgradeBehavior`, decide whether to:
   - Preserve existing value (unless overridden)
   - Use new parameter value
4. **Interactive Mode**: Should be prompted in `--interactive` mode
5. **Schema Version**: Available in manifest schema v1.0.0+

### Alternative Names Considered

- `--upgrade-behavior` (proposed - matches manifest field name exactly)
- `--upgrade-mode`
- `-b` (short form)
- `--uninstall-previous` (too specific, doesn't cover all values)

### Documentation Impact

Would need updates to:
- `doc/update.md` - Parameter documentation
- `README.md` - Usage examples
- Command help text (`wingetcreate update --help`)

### Related Issues/Discussions

- microsoft/winget-cli#1865 - Upgrading an application does not remove the existing version
- microsoft/winget-cli#2727 - Switch for --uninstallPrevious for upgrade
- microsoft/winget-cli#5615 - Winget doesn't remove older version when upgrading

### Testing

Test cases should cover:
- Setting `UpgradeBehavior` in new manifests
- Updating existing manifests with `UpgradeBehavior`
- Updating existing manifests without `UpgradeBehavior`
- Invalid values (should show error)
- Per-installer vs root-level behavior
- Interaction with `--interactive` mode

---

**Environment:**
- wingetcreate Version: 1.10.3.0
- Use Case: Automated package updates for portable apps

**Workaround (Current):**
Manually edit generated manifest after `wingetcreate update` completes, then commit to PR branch.
