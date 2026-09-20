# Security

Pi is a coding agent: it can run commands and modify files within its workspace.
Do not mount private home directories or system paths unintentionally. Treat
untrusted prompts, repositories, extensions and downloaded code accordingly.

The default runc profile uses root to create namespaces but runs Pi as UID 1000,
with no capabilities, no-new-privileges, seccomp and a read-only rootfs. It shares
host networking to support small/old hosts without bridge/firewall management.
This is not network isolation or a boundary against an exploited host kernel.

Keep the host kernel and runc maintained where possible. Supporting an old
device does not make its kernel vulnerabilities disappear. No remote daemon or
management API is opened by this distribution.

Use GitHub private vulnerability reporting for sensitive reports. Never post
keys or private model/session data in a public issue. Ordinary compatibility
issues belong in public issues with sanitized reproduction steps.
