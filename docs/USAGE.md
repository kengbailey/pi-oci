# Running Pi OCI

## Direct runc (recommended for one small device)

You need Linux, a working container-capable kernel, **runc with seccomp support**,
and mounted cgroup controllers for CPU, memory and device isolation. Use your
distribution's cgroup setup; this project does not modify host boot/configuration.
Python 3 is needed once to generate the OCI bundle, not for normal launches.

Download one edition's `*-armv7-rootfs.tar.gz`, `pi-runc-tools.tar.gz`, and
`SHA256SUMS` from the same [release](https://github.com/kengbailey/pi-oci/releases).
Verify the files against the published SHA-256 values before extraction. The
checksums detect corruption; they are not independent release signatures.

```sh
# Example names: use the files from your selected release.
sha256sum --ignore-missing -c SHA256SUMS
mkdir runtime
sudo tar -xzf pi-minimal-0.86.0-r1-armv7-rootfs.tar.gz -C runtime
tar -xzf pi-runc-tools.tar.gz
sudo install -d -o 1000 -g 1000 pi-home work
sudo python3 pi-oci/scripts/prepare-runc.py \
  --rootfs "$PWD/runtime" --home "$PWD/pi-home" \
  --workspace "$PWD/work" --bundle "$PWD/bundle"
sudo ./bundle/pi-runc
```

Create dedicated directories. The setup helper refuses existing bundle paths and
does not recursively change ownership of your files. If UID 1000 is not your user,
arrange access to these directories deliberately. The runtime must remain outside
both writable mounts. Keep its extracted files and the OCI bundle root-owned.

The helper generates `config.json` and a small POSIX-shell launcher. No daemon,
Docker service, package manager, or Python interpreter is used by that launcher.
It takes no additional arguments: set Pi arguments during setup, for example:

```sh
sudo python3 pi-oci/scripts/prepare-runc.py \
  --rootfs "$PWD/runtime" --home "$PWD/pi-home" \
  --workspace "$PWD/work" --bundle "$PWD/cli-bundle" --no-terminal \
  -- /usr/local/bin/pi --provider openai --model gpt-4o-mini -p 'Explain this workspace'
```

Ctrl+D exits the interactive UI. Nothing starts at boot. Separate versioned
runtime and bundle directories make rollback straightforward; back up your Pi
home before switching versions because session/settings formats can evolve.

### Android-derived ARMv7 kernels

Some kernels require membership in the Android `inet` group (GID **3003**) for
non-root sockets. Use `--android-inet` when generating the bundle on such hosts.
Old cgroup-v1 kernels without a pids controller also need `--legacy-cgroup-v1`.
The tested 3.18 kernel was rebuilt with namespaces and required controllers;
an unmodified stock device is **not** supported just because its CPU is ARMv7.

## Providers and persistent state

In Pi, use `/login` where supported, or configure its normal files under
`pi-home/.pi/agent/`. Credentials belong in your private state, never in the image.

For an OpenAI-compatible server, create `pi-home/.pi/agent/models.json` using
upstream's [custom model configuration](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/models.md).
Example (replace the URL/model and supply authentication as appropriate):

```json
{
  "providers": {
    "my-server": {
      "baseUrl": "https://example.com/v1",
      "api": "openai-completions",
      "apiKey": "YOUR_PROVIDER_KEY_ENV_NAME",
      "models": [{"id": "your-model", "name": "Your model"}]
    }
  }
}
```

The generated OCI config intentionally does not inherit your shell environment.
Use Pi's private auth storage, or explicitly add the necessary environment
variable to `config.json` and protect that file. Avoid putting literal keys in
shell history. Minimal retains OpenAI Chat Completions, Responses and Codex code,
but cloud account/OAuth flows are not all tested by this distribution.

## Docker or Podman

The OCI image contains the same complete runtime. For Docker:

```sh
docker run --rm -it --platform linux/arm/v7 \
  --read-only --cap-drop ALL --security-opt no-new-privileges \
  --memory 192m --memory-swap 192m --cpus 1 --pids-limit 64 \
  --network host --tmpfs /tmp:rw,nosuid,nodev,size=32m \
  -v "$PWD/pi-home:/home/pi" -v "$PWD/work:/workspace" \
  ghcr.io/kengbailey/pi-oci:minimal
```

Use `--group-add 3003` only on kernels that need it. On old kernels without the
pids controller, omit `--pids-limit`. No port is published, but **host networking
lets the agent reach your host/LAN**; it is not network isolation. Standard
includes additional providers, not additional host permissions. Only mount work
you intend the coding agent to read/write.
