# Changelog

This file documents all changes made to Corflow when a new version is released.

* The most recent version and changes will appear at the top.
* Changes are sorted by (1) version and release date, and (2) type.
* Dates are given in the format YEAR-MONTH-DAY.
* The version of the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
* The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

Please note that versions prior to version 3.3.0 were not tracked.

## [3.3.0] -- 2025-02-14

### Added

* CHANGELOG.md
* LICENSE

### Changed

* Transcription.py: Conteneur and Tier class: Parents are
automatically set for all Segments of a new, copied Tier.
* toElan: ID of Segments are by default renamed. Using
`rename_segs=False` avoids this.
* Updating README including new information.

### Fixed

* Improved fromElan importing .eaf files.
* Transcription.py: Conteneur class: Having a deepcopy of metadata
instead of a shallow copy. This fixed the issue, where fromElan
would overwrite metadata for a new, copied Tier object.