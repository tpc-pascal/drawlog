# Changelog

All notable changes to Drawlog are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Add ticket entry and validation for Power 6/55, Lotto 5/35, Bingo18,
  Max 3D Pro, and Keno, while retaining historical Mega 6/55 CSV imports.
- Add an hourly Vietlott results workflow and a read-only latest-results panel.

## [v0.0.1] - 2026-11-09

First release of **Drawlog**, a private-by-design Vietlott ticket ledger that
runs locally or on Hugging Face Spaces.

### Added

- Add a responsive ticket ledger for Mega 6/55, Mega 6/45, and Max 3D.
- Add validated CSV import, in-session editing, summaries, and new-file export.
- Add a Gradio Hugging Face Space that serves the browser-only app; ticket
  records and imported CSV contents remain in the browser.
- Add CI, changelog-based release publishing, Space deployment, scheduled
  keep-alive, and manual Space hardware workflows.
- Add project documentation, contribution and security policies, and Drawlog
  branding.

### Changed

- Switch the Hugging Face Space from Docker to Gradio so it can run on the
  Space's existing ZeroGPU hardware without changing its hardware plan.

### Removed
