# AGENTS.md

Notes for AI coding assistants working on FRIDAY.

## Project

FRIDAY is a fork of [Momentum Firmware](https://github.com/Next-Flip/Momentum-Firmware) for Flipper Zero.

- Work happens on `dev`. `upstream` points to Next-Flip/Momentum-Firmware; Momentum's `dev` is merged in regularly.
- Keep diffs against upstream small so merges stay painless:
  - Do not rename internal identifiers (`mntm_*`, `momentum_app`, `FW_ORIGIN_Momentum`, setting keys, file paths). Only change user-facing strings and assets.
  - `FIRMWARE_ORIGIN` stays `"Momentum"` — external apps use `FW_ORIGIN_Momentum` to select APIs, and FRIDAY is API-compatible.
  - Put FRIDAY-specific code in new files or new apps where possible instead of editing upstream files.
- FRIDAY design sources and helper tools live in `friday/`:
  - `friday/designs/` — generators for FRIDAY graphics (run with a Python that has Pillow); they write into `assets/`
  - `friday/tools/` — `fgfx.py` (pixel fonts, wordmark), `preview.py` (upscaled previews), `flipper_cli.py` (USB CLI)
  - Never commit Flipper Devices press-kit files; they are not GPL.
- Follow [CODING_STYLE.md](CODING_STYLE.md).

## Upstream policy

Momentum does not accept AI-generated contributions. Never open pull requests, issues or comments against Next-Flip repositories from this fork.

## Build

```sh
./fbt                  # firmware
./fbt updater_package  # installable package in dist/
./fbt fap_<appid>      # single external app
./fbt lint_all format  # style checks
```
