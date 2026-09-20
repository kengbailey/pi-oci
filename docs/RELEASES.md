# Release and update policy

Tags are independent: `standard-v<pi>-r<revision>` and
`minimal-v<pi>-r<revision>`. A runtime dependency rebuild increments the packaging
revision even if Pi itself is unchanged. Published release tags/assets are not
silently replaced. Keep the old download for rollback.

## Standard

`Update Standard` runs daily. It detects the latest stable Pi npm package,
refreshes the pinned base-image digest within the selected Alpine series, and
checks exact runtime package versions. It builds and runs acceptance tests,
collects corresponding source materials, and only then commits the changed
Standard inputs and publishes a release. A concurrent main-branch change aborts
promotion. A failure leaves the last release intact; inspect Actions for details.

The job never updates Minimal, your devices, credentials, or sessions. It does not
automatically move to a new Alpine release series. Source unavailability or an
ARMv7 dependency break is a maintenance task, not permission to bypass a gate.

## Minimal

Upgrade its lock independently, review `scripts/build-minimal.mjs`, compare every
guarded source change, update the patch-input hashes only after review, and run
tests and same-version hardware benchmarks. Increment its packaging revision.
Then dispatch **Build and test → release_minimal=true** on main. Standard builds
and publishes independently; Minimal failure does not block it.

## Artifacts

Every release has a complete ARMv7 rootfs, runc setup tools, SHA256SUMS,
build-info, dependency inventory and source archive. The image on GHCR is a
single flattened layer to avoid repeated VFS copies. Source collection archives
the exact Alpine aports recipe/patch directory for each installed package's
commit and verifies every source distfile against that recipe's SHA-512 digest.
It also retains integrity-checked npm inputs and upstream Pi source.

Base and direct package versions plus npm locks are pinned. Alpine feeds can
retire packages; this is **not a claim of bit-for-bit reproducibility forever**.
Installed inventories, input hashes and source archives preserve provenance.
Checksums are published; release signing/independent reproducibility verification
is not yet implemented.

GitHub-hosted public CI is used; no paid runners or home-device runner is required.
Scheduled workflows can be disabled by GitHub after repository inactivity;
check the Actions status if expected updates stop.
