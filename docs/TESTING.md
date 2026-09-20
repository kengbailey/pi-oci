# Acceptance gates

`python3 scripts/build.py <edition>` verifies locks, builds the image and exports
a single rootfs. Standard hashes every retained file against the npm install.
Minimal checks exact patch inputs, provider exclusions, grammar parity and HTTP
behavior. No private config or prebuilt prototype binary is copied into releases.

`python3 tests/run.py <edition>` uses a deterministic local OpenAI-compatible
streaming server, **with external networking disabled**, to exercise real Pi:

- all seven tools: ls, find, grep, read, edit, Bash and write;
- resulting file contents and a passing child-process test;
- session resume and a real TypeScript extension;
- PTY/TUI rendering and clean exit;
- WASM image creation, non-root identity, empty capabilities, seccomp and read-only root;
- structured connection errors (Pi may exit 0 even when a model call fails);
- mandatory provider-module imports in Standard, without pretending to authenticate
  to every vendor.

QEMU plus the fixture server requires a **512 MiB / two-core CI allowance**.
The device launcher defaults to 192 MiB / one core; hardware figures are recorded
separately. Automated tests do not verify every OAuth flow, arbitrary extension,
long-context session, or old-kernel behavior.

Source collection, license notices and checksum assembly must also pass before
binary publication. Tests use no live account secrets and never run on a home
device or self-hosted runner. Public pull requests cannot publish releases.
