# Pi OCI

[![Build and test](https://github.com/kengbailey/pi-oci/actions/workflows/ci.yml/badge.svg)](https://github.com/kengbailey/pi-oci/actions/workflows/ci.yml)

**The Pi coding agent, packaged for small ARMv7 Linux devices.** Run it directly
with **runc**, without a Docker daemon, or use the standard OCI image.

This is an independent distribution of [Pi](https://github.com/earendil-works/pi),
not a new agent or an inference server. Your model runs at the provider or
OpenAI-compatible endpoint you configure. No account or model weights are included.

## Two editions

| | Standard | Minimal |
|---|---|---|
| Pi runtime | Upstream JavaScript unchanged | Explicit, version-guarded optimizations |
| Providers | All mandatory upstream provider SDKs | OpenAI SDK only; compatible endpoints supported |
| Updates | Automatic, after acceptance tests | Maintainer-reviewed and manually released |
| Aim | Compatibility and low maintenance | Lower RAM, storage, and startup cost |

Both include the interactive TUI, built-in tools, session storage, Bash, fd,
ripgrep, and image/WASM handling. Neither includes npm, compilers, Git, optional
native accelerators, or Amazon firmware. Standard removes only source maps and
TypeScript declaration files; runtime code and assets are preserved.

**Initial target: `linux/arm/v7`.** ARM64/x86 images are not currently published.
An ARMv7 build does not imply support for every old kernel. See
[compatibility](docs/COMPATIBILITY.md).

## Get it

- [Versioned downloads](https://github.com/kengbailey/pi-oci/releases): complete
  rootfs, runc setup helper, SHA-256 checksums, dependency inventory, and source archive.
- OCI images: `ghcr.io/kengbailey/pi-oci:standard` and
  `ghcr.io/kengbailey/pi-oci:minimal` once the corresponding release passes CI.
- Prefer immutable tags such as `standard-v0.86.0-r1` to the moving edition tags.

[**Install and run with runc →**](docs/USAGE.md)

Nothing starts at boot, updates a device automatically, or mounts a Docker socket.
The default runtime runs Pi as UID 1000, with no capabilities, seccomp, a read-only
root, one CPU core worth of quota, and a 192 MiB container memory limit. Only your
chosen home and workspace are writable. Networking uses the host network.

## Measured on a small ARMv7 device

Pi 0.86.0, Alpine 3.24.2, Node 24.18.1, direct runc:

| | Standard | Minimal |
|---|---:|---:|
| Cached interactive startup | 3.66–3.71 s | 2.85–2.89 s |
| Fresh-idle Pi RAM (PSS) | 56–58 MiB | 45.4 MiB |
| Pi RAM after a small tool/model exchange | 65.7 MiB | 56–57 MiB |
| Complete runtime file payload | 119.3 MiB | 77.8 MiB |

runc added about 6 MiB PSS. These are **prototype hardware measurements**, not
universal promises or newly measured results for every automated release.
Deferred work increases memory after first use. [Method, limits, CPU results](docs/BENCHMARKS.md).

## Build locally

Requirements: Node 24, npm, Python 3.9+, Docker with Buildx and ARMv7 emulation
(or a native ARMv7 builder). Docker is a **build tool**, not a runtime requirement.

```sh
python3 scripts/build.py standard
python3 tests/run.py standard
# Or substitute minimal. Its patches are pinned to reviewed source hashes.
```

Artifacts land in `out/<edition>/`. `scripts/sources.py` and `scripts/finalize.py`
complete the redistributable release set after tests. See [release policy](docs/RELEASES.md).

## How it stays maintainable

- Separate lockfiles, version pins, and CI jobs. Minimal cannot block Standard.
- Daily Standard update detection for Pi, the selected Alpine series, and runtime
  packages. A candidate must build and pass tests before it is committed/released.
- Minimal's source guards fail closed when patched upstream modules change.
- Deterministic model tests need no API credentials; they exercise real streaming
  responses, all seven tools, extensions, sessions, and failure handling.
- Complete source materials are a required binary-publication gate.

[Minimal patches](docs/MINIMAL.md) · [Test coverage](docs/TESTING.md) ·
[Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)

Packaging/launcher code is MIT. Dependencies retain their own licenses; see
[NOTICE](NOTICE). Pi is copyright Mario Zechner and contributors.
