# Minimal patch contract

Minimal is deliberately not the no-modification edition. The nine patched Pi
0.86.0 input files are hashed in `tracks/minimal/patch-inputs.json`. A mismatch
stops the build until a maintainer reviews the source and revalidates behavior.

1. Keep only OpenAI/OpenAI-Codex provider and model registries, with Chat
   Completions, Responses and Codex Responses API support. Prune other SDKs from
   the bundled dependency graph, and reject known unwanted SDK inputs.
2. Fold Bun-only detection for a Node runtime and bundle/minify with esbuild.
   Reuse upstream's lazy Jiti approach; retain the compiler for actual extensions.
3. Initialize syntax grammars on demand, preserving all 191 language definitions,
   aliases and embedded-language dependencies. Build-time comparisons check 1,092
   language/sample pairs against upstream output.
4. Defer the **complete upstream** HTTP implementation until first fetch. Preserve
   gzip handling, proxy CONNECT behavior, timeouts, cancellation and custom fetch.
   Do not transplant the older prototype's private Undici imports.
5. Drop function-name preservation in the main bundle. This reduces metadata but
   can make stack traces less descriptive and affect name-sensitive extensions.

The agent loop, built-in tool behavior and wire protocols are not rewritten.
HTTP and grammar initialization are deferred, not made free: fresh-idle memory
is lower than post-request memory. Semi-space and V8 size-optimization flags did
not improve the tested build and are not enabled. JIT-less mode breaks retained
WASM functionality and is not used.

Review a new upstream version against same-version Standard. Retire patches that
upstream incorporates; never update guard hashes merely to make a build pass.
Minimal's release button is deliberately separate from automated Standard updates.
