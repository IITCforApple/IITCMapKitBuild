# Required release pipeline

This repository builds and publishes the private source repository
`git@github.com:chewnglow/iitc_mapkit.git`. Follow the source repository's
`AGENTS.md` for implementation, validation, installation and version metadata.

When the user requests a versioned release or version-tag push:

1. Complete and validate source changes. Build/package and install the macOS app
   and the connected physical iPhone app as required by source instructions,
   preserving application data. Never start a simulator as a substitute.
2. Commit the source changes and release metadata on source `main`, create its
   unused matching `vMAJOR.MINOR.PATCH` tag, and push both to the source remote.
   Verify their remote commit IDs before updating this repository.
3. Initialize `iitc_mapkit`, fetch its source remote, and check out the exact
   newly pushed source `origin/main` commit. Confirm its `VERSION` matches the
   requested tag. Preserve `.gitmodules` and private-source access boundaries;
   any SSH URL substitution belongs in local Git configuration only.
4. Commit the updated `iitc_mapkit` gitlink and related delivery instructions on
   this repository's `main`. Run the existing release safeguards. Verify the
   gitlink equals source remote `main`, then push build `main`.
5. Create the same unused `vMAJOR.MINOR.PATCH` tag in this repository and finally
   push tags, for example `git push origin --tags`. The tag is a Git ref, not the
   remote argument. Never overwrite an existing published tag.
6. Verify the remote build branch/tag, its gitlink and the dispatched tag
   workflow. Report the actual workflow state. If following publication through
   completion, verify its ZIP, DMG and SHA-256 assets on the matching release.

Pushing a source tag alone does not complete delivery. This repository's version
tag triggers the existing notarized macOS release workflow. Keep signing,
notarization, secret handling, encrypted private logs and asset publication in
that workflow. Do not upload private source or local development-signed packages
as public release replacements. No simulator, TestFlight upload, credential
changes or unrelated workflow changes are implied by a tag push.

Routine edits require focused commits; a new version/tag is only created when
the user requests version finalization, a versioned package or a version tag.
