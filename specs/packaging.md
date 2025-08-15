# Spec: Packaging HWInfo TUI

This document defines how to build and distribute HWInfo TUI.

Repository: https://github.com/JuanjoFuchs/hwinfo-tui

## Goals

- Publish a Python package (sdist + wheel) to PyPI.
- Provide a standalone Windows executable for users without Python.
- Distribute via Windows Package Manager (winget) using the portable EXE.
- Automate builds, tests, and publishing via GitHub Actions.

## Package metadata (source of truth)

- Project name: `hwinfo-tui` (from `pyproject.toml`)
- Entry point: console script `hwinfo-tui` -> `hwinfo_tui.main:app`
- Python: >= 3.8
- License: MIT
- Classifiers: Console environment; Python 3.8–3.12; OS Independent

Versioning note:
- Today, version appears both in `pyproject.toml` and `src/hwinfo_tui/__init__.py`.
- To avoid drift, prefer one source of truth:
  - Option A (recommended): keep `project.version` in `pyproject.toml` and compute `__version__` at runtime using `importlib.metadata.version("hwinfo-tui")`.
  - Option B: mark `dynamic = ["version"]` in `pyproject.toml` and use `setuptools-scm` or a single `__version__` in the package.
  - CI enforces that git tag `vX.Y.Z` equals the package version.

## Build artifacts

1) PyPI
- sdist: `hwinfo-tui-<version>.tar.gz`
- wheel: `hwinfo_tui-<version>-py3-none-any.whl`

2) Windows standalone executable (portable)
- Built with PyInstaller
- Filename: `hwinfo-tui-<version>-windows-x64.exe` (console app)
- Target: Windows x64 (primary). Additional architectures optional.

## Local build and publish (manual)

Prereqs:
- Python 3.8–3.12, virtualenv activated (scripts present: `activate.ps1`)
- Tools: build, twine, pyinstaller

PowerShell (pwsh) commands:

```powershell
# Activate venv (provided by the repo)
. ./activate.ps1

# Install project + dev tools
python -m pip install --upgrade pip
pip install -e .[dev]
pip install build twine pyinstaller

# Lint / typecheck / test
ruff check .
mypy src
pytest -q

# Build sdist + wheel
python -m build

# Check metadata and long description
python -m twine check dist/*

# Publish to PyPI (requires a token)
# Create a PyPI token and set TWINE_USERNAME="__token__" and TWINE_PASSWORD="pypi-..."
$env:TWINE_USERNAME="__token__"
$env:TWINE_PASSWORD="<your-pypi-token>"
twine upload dist/*

# Build Windows portable EXE
pyinstaller --name hwinfo-tui --onefile --console --paths src src/hwinfo_tui/main.py

# Optionally rename the EXE for release consumption
$ver = (Select-String -Path pyproject.toml -Pattern 'version\s*=\s*"([^"]+)' -AllMatches).Matches.Groups[1].Value
Rename-Item -Path dist/hwinfo-tui.exe -NewName "hwinfo-tui-$ver-windows-x64.exe"

# Run the EXE smoke tests
./dist/hwinfo-tui-$ver-windows-x64.exe --help
./dist/hwinfo-tui-$ver-windows-x64.exe --version
```

Notes:
- Typer/Click/Rich typically work without extra hooks for console apps. If hidden imports are missed, add `--hidden-import` flags or a `.spec` file.
- Ensure the `--paths src` option so PyInstaller finds the `src/` layout.

## PyPI publishing (CI)

- Build with `python -m build` (PEP 517) to produce sdist and wheel.
- Upload using the official action `pypa/gh-action-pypi-publish` with a PyPI API token.
- Version comes from `project.version` in `pyproject.toml` and must match tag `v<version>`.

Example GitHub Actions workflow (build + test):

```yaml
name: ci
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.8", "3.9", "3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'
      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          pip install -e .[dev]
      - name: Lint
        run: |
          ruff check .
      - name: Typecheck
        run: |
          mypy src
      - name: Test
        run: |
          pytest -q
```

Release workflow (on tag) builds artifacts, publishes to PyPI, and attaches the EXE to the GitHub Release:

```yaml
name: release
on:
  push:
    tags:
      - 'v*'

jobs:
  build-release:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      - name: Verify tag matches version
        shell: pwsh
        run: |
          $tag = $env:GITHUB_REF -replace 'refs/tags/',''
          $pyproj = Get-Content pyproject.toml -Raw
          if ($pyproj -match 'version\s*=\s*"([^"]+)"') { $ver = $Matches[1] } else { throw 'Version not found' }
          if ($tag -ne "v$ver") { throw "Tag $tag does not match version v$ver" }
      - name: Install build tools
        run: |
          python -m pip install --upgrade pip
          pip install build twine pyinstaller
          pip install -e .
      - name: Build sdist/wheel
        run: python -m build
      - name: Build Windows EXE (PyInstaller)
        run: pyinstaller --name hwinfo-tui --onefile --console --paths src src/hwinfo_tui/main.py
      - name: Rename EXE with version
        shell: pwsh
        run: |
          if ($env:GITHUB_REF -match 'refs/tags/v(.+)') { $ver = $Matches[1] } else { throw 'No version tag' }
          Rename-Item -Path dist/hwinfo-tui.exe -NewName "hwinfo-tui-$ver-windows-x64.exe"
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: dist
          path: |
            dist/*
            !dist/*.spec
      - name: Publish to PyPI
        if: startsWith(github.ref, 'refs/tags/')
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          password: ${{ secrets.PYPI_TOKEN }}
      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          files: |
            dist/*.whl
            dist/*.tar.gz
            dist/hwinfo-tui-*-windows-x64.exe
          generate_release_notes: true
```

Secrets required:
- `PYPI_TOKEN` (PyPI API token for the project)
- Optional for winget automation: `GH_PAT` with repo scope to submit PR to winget-pkgs

## Windows executable (PyInstaller)

- One-file console binary with PyInstaller.
- Baseline command (Windows runner and local dev):

```powershell
pyinstaller --name hwinfo-tui --onefile --console --paths src src/hwinfo_tui/main.py
```

Tips:
- If Typer/Click or Rich assets are missing at runtime, add hidden imports, e.g.:
  `--hidden-import click.termui --hidden-import click._winconsole`
- For consistent results, pin PyInstaller in CI (e.g., `pyinstaller==6.*`).
- Verify `--help` and `--version` work in a clean Windows environment.

## Winget distribution

Distribution: Portable EXE, x64.

Choose a `PackageIdentifier` as `Publisher.Package` (e.g., `JuanjoFuchs.hwinfo-tui`).

Winget requires a set of manifests (version, installer, defaultLocale). Minimal example for portable EXE installer:

```yaml
# <identifier>/<version>/<files>.yaml — schematic example
PackageIdentifier: JuanjoFuchs.hwinfo-tui
PackageVersion: 1.0.0
PackageName: HWInfo TUI
Publisher: Juanjo Fuchs
License: MIT
ShortDescription: CLI TUI for HWInfo CSV sensors
Moniker: hwinfo-tui
Installers:
  - Architecture: x64
    InstallerType: portable
    InstallerUrl: https://github.com/JuanjoFuchs/hwinfo-tui/releases/download/v1.0.0/hwinfo-tui-1.0.0-windows-x64.exe
    InstallerSha256: <SHA256>
Commands:
  - hwinfo-tui
```

Submission:
- Compute SHA256 of the release asset and set `InstallerUrl` to the GitHub Release EXE.
- Submit a PR to `microsoft/winget-pkgs` (manually or via automation).
- Automation option: run `wingetcreate` in CI after creating the Release, or use a community action to open the PR. Requires a `GH_PAT`.

## Versioning and release process

- Maintain the version in a single source (see Versioning note above).
- Release by creating a git tag `v<version>` that matches the package version.
- CI builds artifacts, uploads to PyPI, and attaches the Windows EXE to the GitHub Release.

## Verification

- PyPI: `pip install hwinfo-tui` then `hwinfo-tui --version`.
- Windows EXE: run `hwinfo-tui.exe --help` on a clean Windows machine.
- Winget: `winget install hwinfo-tui` once the manifest PR is merged and indexed.

## Notes

- The package entry point is declared in `pyproject.toml` under `[project.scripts]` and should be preserved.
- The source layout uses `src/`; PyInstaller must include `--paths src`.
- Keep repository URLs in `pyproject.toml` aligned with the actual GitHub repo (`https://github.com/JuanjoFuchs/hwinfo-tui`).
