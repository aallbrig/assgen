# Releasing assgen

## Versioning

assgen follows [Semantic Versioning](https://semver.org):

| Change type | Bump | Example |
|---|---|---|
| Breaking API / behaviour change | **Major** | `1.0.0 → 2.0.0` |
| New backwards-compatible feature | **Minor** | `0.1.0 → 0.2.0` |
| Bug fix, dependency update | **Patch** | `0.1.0 → 0.1.1` |

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

That's it. The `release` workflow triggers automatically and:

1. Runs ruff lint + pytest
2. Builds the Python wheel and sdist via `hatch build`
3. Builds the MkDocs site and zips it as `assgen-docs-v*.zip`
4. Creates a GitHub Release with the wheel, sdist, and docs zip attached
5. Builds CPU server and client Docker images and pushes them to `ghcr.io`:
   - `ghcr.io/aallbrig/assgen-server:v0.1.0` (and `:latest`)
   - `ghcr.io/aallbrig/assgen-client:v0.1.0` (and `:latest`)

## After the release

```bash
# Verify Docker images
docker pull ghcr.io/aallbrig/assgen-server:v0.1.0

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
