<h1 align="center">F.R.I.D.A.Y.</h1>

<p align="center"><b>Firmware for Radio, Infrared, Digital Access & You</b></p>

<p align="center">
  <a href="#install">Install</a> · <a href="#features">Features</a> · <a href="#building">Building</a> · <a href="#credits">Credits</a>
</p>

---

FRIDAY is a custom firmware for [Flipper Zero](https://flipper.net/), built on top of [Momentum Firmware](https://github.com/Next-Flip/Momentum-Firmware). It keeps everything Momentum offers — the settings app, asset packs, extended Sub-GHz, the full app collection — and adds its own features, apps and a distinct look on top.

FRIDAY stays **API-compatible with Momentum**: every app built for Momentum runs on FRIDAY, and new Momentum releases are merged regularly.

## Install

Releases will be published on the [Releases page](https://github.com/Bossaln/FRIDAY-Firmware/releases).

1. Download the latest `friday-*.tgz` update package.
2. Copy it to your Flipper's SD card (e.g. with qFlipper's file manager) and extract it, or install it directly via qFlipper → *Install from file*.
3. On the Flipper, open the extracted folder and run `update.fuf`.

## Features

- Everything from Momentum — see the [Momentum feature list](https://github.com/Next-Flip/Momentum-Firmware#list-of-changes).
- FRIDAY boot and desktop graphics.
- More to come — see the [changelog](CHANGELOG.md).

## Building

Requirements: macOS, Linux or Windows with Git and Python 3. The build toolchain is downloaded automatically on first run.

```sh
git clone --recursive https://github.com/Bossaln/FRIDAY-Firmware.git
cd FRIDAY-Firmware
./fbt                    # build firmware
./fbt updater_package    # build an installable update package (dist/)
./fbt flash_usb_full     # build and flash to a USB-connected Flipper
```

See [documentation/fbt.md](documentation/fbt.md) for all build targets.

## AI disclosure

FRIDAY is developed with the help of AI coding assistants. Changes made in this fork are **not** submitted upstream: Momentum does not accept AI-generated contributions, and we respect that policy.

## Credits

FRIDAY would not exist without the work of:

- [Momentum Firmware](https://github.com/Next-Flip/Momentum-Firmware) — the base of this firmware
- [Unleashed Firmware](https://github.com/DarkFlippers/unleashed-firmware) — many of the features Momentum includes
- [Flipper Devices](https://github.com/flipperdevices/flipperzero-firmware) — the official firmware and the Flipper Zero itself
- All authors of the included applications — see `applications/external`

The name is a nod to the AI assistant from the Iron Man films. FRIDAY is an independent community project and is not affiliated with or endorsed by Marvel, Disney, Flipper Devices or the Momentum team.

## License

[GNU General Public License v3.0](LICENSE), like the projects it is based on.
