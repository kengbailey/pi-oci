# Compatibility and scope

- Runtime: Alpine/musl ARMv7 hard-float, Node 24, Pi 0.86.0 initially.
- Hardware-tested prototype: ARMv7 Echo Dot 2nd generation with custom 3.18
  container-capable kernel, cgroup v1, seccomp, namespaces, and runc. This repository
  does not supply firmware, kernel patches, rooting, or device-repartition tools.
- CI: real ARMv7 binaries under QEMU on a modern Linux host. It does **not** emulate
  the old kernel. Future automated releases are CI-tested, not automatically
  re-certified on the original hardware.
- Other ARMv7 hosts with working runc may work; not all boards are hardware-tested.
- No ARM64 or x86 downloads yet. Do not mistake architecture emulation for a native
  image or use the old-kernel measurements as benchmarks for another machine.

Standard preserves mandatory provider dependencies; optional native clipboard,
terminal accelerators and native addon dependencies are omitted. An arbitrary
extension can require absent tools/packages or unsupported APIs. The included
TypeScript extension test is useful coverage, not an ecosystem guarantee.

Minimal removes non-OpenAI provider implementations/catalogs. Compatible servers
must be configured explicitly. Image-file reading/resizing remains; non-OpenAI
image-generation providers do not. Minified names can change stack traces and
code that relies on function names. See the [patch list](MINIMAL.md).

Neither image contains a local LLM. Memory limits cover the container; V8's
96 MiB old-space setting is not a total process-RAM limit. Long sessions and large
child builds can exceed the 192 MiB profile. Adjust limits only with real headroom.
