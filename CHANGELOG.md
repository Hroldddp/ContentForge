# Changelog

## [1.1.0] — 2026-06-26

### Added
- Docker image published to ghcr.io for container users
- pyproject.toml so it can actually be published as a package
- Publish workflow to GitHub Actions — builds wheel, uploads to GitHub Packages
- Build artifacts saved as workflow artifacts even when publish fails

### Fixed
- Setuptools backend was pointing to the wrong module path
- YouTube clip trimming was keeping the full-length original when trim failed
- Stock clips now sorted by duration so short clips fill the timeline first
- Twine auth for GitHub Packages needed a PAT with packages:write scope

### Changed
- AGENTS.md now enforces every element of the repo surface is updated on every change
- Readme has badges now. Lots of badges.

## [1.0.0] — 2026-06-26

### Added
- Complete rewrite of the pipeline — no more gradient backgrounds
- Multi-tier stock fallback: Pexels → Pixabay → Commons → YouTube
- Keeps searching until enough clips fill the whole script duration
- Live FFmpeg progress with percentage and time remaining
- Audio/resolution detection for clips
- --clips flag auto-defaults to ./clips folder

### Changed
- User clips play first, stock fills the rest
- Uses `-t duration` instead of `-shortest` (fixes subtitle conflicts)
- Audio normalized to 44.1kHz stereo so concat doesn't crash
- YouTube clips trimmed to exactly 25s via re-encode
- Assembly uses `-preset veryfast` (way faster than `medium`)
- Font is now DejaVu Sans, auto-sized
- All temp files get cleaned even if the script crashes

### Fixed
- Video was extending past the target duration
- Concat crashed with mixed-format user clips and stock footage
- YouTube trimming was inconsistent because of keyframe boundaries
- Commons downloads had broken filenames
- Python 3.14 RuntimeWarning about subprocess

### Removed
- All gradient/animated background code
- All clip-looping code
- Zoompan (was a bottleneck for slideshows)

## [0.9.0] — 2026-06-25

### Added
- Interactive wizard (wizard.py)
- Adjustable background volume
- Sample script for testing

### Fixed
- Caption sync was wrong — now uses SentenceBoundary events from edge-tts directly
- Migrated from kokoro to edge-tts (Python 3.14 compatibility)
- Background audio mixing now works correctly

## [0.1.0] — 2026-06-24

- Initial release. Basic text-to-video. It worked, barely.

## 1.0.0

- First stable release
- Video assembly pipeline
- TTS voiceover with edge-tts
- Stock footage from multiple sources
- Local AI integration

## 1.1.0-alpha.1

- Improved stock query diversity
- Better error handling
- Tutorial videos enabled by default
