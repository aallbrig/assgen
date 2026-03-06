# Installation & Upgrade

## Install

### From PyPI *(coming soon)*

```bash
pip install assgen

# With GPU inference support
pip install "assgen[inference]"
```

### From a GitHub Release

Each tagged release publishes a `.whl` wheel file on the
[Releases page](https://github.com/aallbrig/assgen/releases).

1. Go to [github.com/aallbrig/assgen/releases](https://github.com/aallbrig/assgen/releases)
2. Find the latest release (or the version you want)
3. Download the `.whl` file under **Assets**
4. Install it:

```bash
pip install assgen-<version>-py3-none-any.whl

# With inference extras
pip install "assgen-<version>-py3-none-any.whl[inference]"
```

### From source (development install)

```bash
git clone https://github.com/aallbrig/assgen.git
cd assgen
pip install -e ".[dev]"
```

---

## Upgrade

The easiest way to stay current is the built-in `upgrade` command:

```bash
# Check if a newer version exists, then prompt to upgrade
assgen upgrade

# Just check — exit 0 if up-to-date, exit 1 if outdated (useful in scripts)
assgen upgrade --check

# Upgrade without a confirmation prompt
assgen upgrade --yes

# Include pre-releases
assgen upgrade --pre
```

The `upgrade` command:

1. Fetches the latest release info from the GitHub Releases API
2. Compares it against the running version
3. If newer, shows a summary of the release notes
4. Runs `pip install assgen==<version>` in the same Python environment

!!! tip "Keeping inference extras"
    If you installed with `pip install "assgen[inference]"`, re-run with
    `pip install "assgen[inference]==<new-version>"` after upgrading, or add
    `--inference` support to the upgrade workflow in a future release.

---

## Verify installation

```bash
assgen version
# assgen  version: 0.0.1  python: 3.12.3  platform: Linux

assgen --help
```

---

## Hardware recommendations

| GPU | VRAM | Suitable models |
|-----|------|----------------|
| RTX 4070 / 3080 | 12 GB | SDXL, TripoSR, AudioGen-Medium, MusicGen-Small |
| RTX 4090 / 3090 | 24 GB | All catalog models |
| Any CPU | — | Orchestration, job queue, text models |

Set the inference device in `~/.config/assgen/server.yaml`:

```yaml
device: "cuda"   # auto | cuda | cpu | mps (Apple Silicon)
```
