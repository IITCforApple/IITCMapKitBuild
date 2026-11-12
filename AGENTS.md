# Required release pipeline

Review release notes, announcements, tag annotations, commit messages and other public copy for confidential project names, service URLs, features and implementation details before publishing. Describe confidential changes with a neutral maintenance summary.

This repository builds and publishes the private source repository
`git@github.com:IITCforApple/iitc_mapkit.git`. Follow the source repository's
`AGENTS.md` for implementation, validation, installation and version metadata.

Use the same user-facing version from `VERSION` for the macOS, iOS, and iPadOS
apps. When finalizing a version, update and verify the app version metadata for
all three platforms together.

When the user requests a versioned release or version-tag push:

1. Prepare and commit the source release metadata on source `main`. Push
   `main` and its new matching `vMAJOR.MINOR.PATCH` tag to the source remote.
   Never move a published tag.
2. Fetch the private source branch into the `iitc_mapkit` submodule and pin
   the exact source `main` commit just pushed. Preserve `.gitmodules` and
   private-source access.
3. Commit the gitlink and any related delivery instructions on build `main`
   and push that branch to `git@github.com:IITCforApple/IITCMapKitBuild.git`.
   Then create and push the matching version tag to start the release workflow.

For a release push, skip duplicate local validation, release builds, packaging
and installation. After Git accepts the build tag, finish without querying
workflow status, waiting for completion, or checking published assets. Perform
those steps only if the user explicitly asks. GitHub Actions runs its existing
release safeguards.

Pushing a source tag alone does not complete delivery. This repository's version
tag triggers the existing notarized macOS release workflow. Keep signing,
notarization, secret handling, encrypted private logs and asset publication in
that workflow. Do not upload private source or local development-signed packages
as public release replacements. No simulator, TestFlight upload, credential
changes or unrelated workflow changes are implied by a tag push.

Routine edits require focused commits; a new version/tag is only created when
the user requests version finalization, a versioned package or a version tag.

Use the source `Scripts/package-mac-dmg.command` for the IITC MapKit disk image.
It owns the link-themed artwork, Retina background and Finder item layout. Do not
recreate a plain DMG in this repository. The source installer migrates the former
`~/Applications/IITC Native.app` to `~/Applications/IITC MapKit.app` while retaining
bundle identities and saved-data paths.
