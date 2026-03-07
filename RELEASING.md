# Releasing assgen

## Versioning

assgen follows [Semantic Versioning](https://semver.org):

| Change type | Bump | Example |
|---|---|---|
| Breaking API / behaviour change | **Major** | `1.0.0 → 2.0.0` |
| New backwards-compatible feature | **Minor** | `0.1.0 → 0.2.0` |
| Bug fix, dependency update | **Patch** | `0.1.0 → 0.1.1` |

Tags **must** be valid semver — the release workflow validates the format and
aborts before doing any work if the tag is malformed (e.g. `v0.1` will fail).

The version is derived automatically from Git tags by `hatch-vcs` —
there is no version field to edit manually.

## Pre-release checklist

- [ ] All CI checks pass on `main` (lint, tests, docker build)
- [ ] Manually smoke-test the fix or feature:
  ```bash
  assgen --version
  assgen gen --help
  ```
- [ ] Update docs if the change affects user-facing behaviour

## Cut a release

```bash
# Annotated tag — the message becomes the basis for release notes
git tag -a v0.1.0 -m "Release v0.1.0"
git push origin v0.1.0
```

## What the release workflow does automatically

1. **Validates** the tag is proper semver — aborts if malformed
2. **Lints + tests** (offline tests only; integration tests run separately)
3. Builds the Python **wheel and sdist** via `hatch build`
4. Builds the **MkDocs site** and zips it as `assgen-docs-v*.zip`
5. Creates a **GitHub Release** with wheel, sdist, docs zip, and binaries attached
6. Builds standalone **client binaries** with PyInstaller in parallel on 3 platforms:
   - `assgen-v*-linux-x64`
   - `assgen-v*-windows-x64.exe`
   - `assgen-v*-macos-x64`
7. Builds CPU server + client **Docker images** and pushes to `ghcr.io` with full
   semver tags (e.g. `:1.2.3`, `:1.2`, `:1`, `:latest`).
   Pre-release tags (e.g. `v1.2.3-rc.1`) get only `:1.2.3-rc.1` — no `:latest`.

## Pre-release tags

```bash
git tag -a v0.2.0-rc.1 -m "Release candidate 1 for v0.2.0"
git push origin v0.2.0-rc.1
```

Pre-releases get a GitHub Release marked as pre-release but **no `:latest` Docker tag**
and no `:major` / `:major.minor` shortcuts.

## After the release

```bash
# Verify Docker images
docker pull ghcr.io/aallbrig/assgen-server:v0.1.0   # specific
docker pull ghcr.io/aallbrig/assgen-server:0.1       # minor alias
docker pull ghcr.io/aallbrig/assgen-server:latest    # latest stable

# Test the standalone binary (Linux)
curl -LO https://github.com/aallbrig/assgen/releases/latest/download/assgen-v0.1.0-linux-x64
chmod +x assgen-v0.1.0-linux-x64 && ./assgen-v0.1.0-linux-x64 --version

# Check the GitHub Release page
gh release view v0.1.0

# Confirm the upgrade command detects the new release
assgen upgrade --check
```

## Patch release workflow

Same as above — just bump the patch segment:

```bash
git tag -a v0.1.1 -m "Fix: <short description>"
git push origin v0.1.1
```

## Notes

- The CUDA server image (`Dockerfile.server-cuda`) is **not** built in CI
  (it requires a GPU runner and pulls ~6 GB).  Build and push it manually
  when needed:
  ```bash
  VERSION=v0.1.0
  docker build -f docker/Dockerfile.server-cuda \
               --build-arg VERSION=${VERSION#v} \
               -t ghcr.io/aallbrig/assgen-server-cuda:$VERSION .
  docker push ghcr.io/aallbrig/assgen-server-cuda:$VERSION
  docker tag  ghcr.io/aallbrig/assgen-server-cuda:$VERSION \
              ghcr.io/aallbrig/assgen-server-cuda:latest
  docker push ghcr.io/aallbrig/assgen-server-cuda:latest
  ```
- PyPI publishing is not yet automated.  Add a `Publish to PyPI` step to
  `release.yml` using OIDC trusted publishing once you are ready to make
  the package public on PyPI.
