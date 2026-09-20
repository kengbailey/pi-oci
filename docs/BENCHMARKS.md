# Prototype benchmark record

Measured on actual ARMv7 hardware on 2026-09-20, before this public repository was
assembled. Both Pi 0.86.0 editions used Alpine 3.24.2, Node 24.18.1, a one-core
quota, 192 MiB container limit and 96 MiB V8 old-space setting. A separate native
voice service remained active. Runtime launches used runc, not Docker management.

| Measurement | Standard | Minimal |
|---|---:|---:|
| Runtime file payload | 119.28 MiB | 77.79 MiB |
| Cached TUI launch | 3.66–3.71 s | 2.85–2.89 s |
| Empty Node compile cache | 5.49 s | 3.35 s |
| Fresh-idle Pi PSS | 56.1–58.3 MiB | 45.4 MiB |
| Pi PSS after read/Bash/model exchange | 65.7 MiB | 55.6–57.0 MiB |
| Additional runc PSS | ~6.2 MiB | ~6.1 MiB |

Startup includes an SSH/PTY harness through first usable TUI render. These are
not physical cold boots, globally cold filesystem-cache measurements, or a large
statistical sample. Public release notices/source inventories add some packaging
bytes. Compare downloaded build-info/inventory rather than assuming exact sizes.

Minimal's seven-tool code-repair run sampled **58.43 MiB peak Pi PSS**. That is not
a total memory ceiling, long-session result, or all-child-process peak.

| Minimal tool | Wall time | Pi CPU | Container CPU including children |
|---|---:|---:|---:|
| ls | 278 ms | 272 ms | 273 ms |
| find | 72 ms | 52 ms | 78 ms |
| grep | 54 ms | 56 ms | 68 ms |
| read | 21 ms | 28 ms | 28 ms |
| read again | 12 ms | 12 ms | 13 ms |
| edit | 44 ms | 48 ms | 48 ms |
| Bash / Node test | 328 ms | 60 ms | 324 ms |
| write | 12 ms | 16 ms | 17 ms |

Total tool windows: **0.544 CPU-seconds in Pi**, **0.849 including children**.
Short intervals include tick/accounting noise. A CPU-heavy command remains CPU
heavy; Pi waiting for it is not the same workload. Remote inference CPU is not
included, and these numbers do not establish lower active CPU than Standard.

For future comparisons, fix upstream/runtime versions, limits, model/server,
fixture and compile-cache state; measure PSS for Pi and its supervisor separately;
record child CPU via cgroups; report first render, first request, and post-request
memory. Do not use QEMU timing or CI memory usage as hardware benchmarks.
