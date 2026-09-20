# Contributing

Keep Standard runtime bytes unchanged. Propose optimizations in Minimal with a
patch explanation, regression coverage and measurements against same-version
Standard. Never trade away working functionality just to report a smaller idle
number. Keep the tracks independently buildable.

Use synthetic fixtures and generic model configuration. Do not commit credentials,
auth files, session transcripts, device backups, firmware or home-network details.
Report the Pi/runtime versions, architecture, kernel, runtime, cache state and
exact command when filing a bug. Remove private paths and keys from logs.

Run the Python static tests and the appropriate build/runtime suite. Changes to
the release workflows need careful review because main can publish Standard.
Actions are pinned by commit; update those pins deliberately.
