# xBloom Studio for Home Assistant

**Unofficial**, local-only [Home Assistant](https://www.home-assistant.io/) custom integration for the **xBloom Studio** coffee machine, communicating over Bluetooth Low Energy (BLE).

It gives you full control of the machine from Home Assistant — brew monitoring, recipe management, and standalone grinder / brewer / scale control — as entities, services, and automation blueprints. Brewing and machine control are BLE-only: the machine is contacted over BLE on demand and released again so the official iOS app can still connect. An **optional** xBloom account login adds cloud recipe sync and a firmware-update check on top — everything works without it.

## Features

- **Live brew monitoring** — brew status, machine status, scale weight, and per-pour progress stream over BLE while a brew is running.
- **Recipe library** — store recipes locally in Home Assistant, import them from an xBloom share link, and create / edit / delete them from the integration's options flow.
- **Optional cloud sync** — log in with your xBloom account to make the cloud the single source of truth for recipes: your account's recipes appear in Home Assistant — both your own ("My Recipes") and ones you saved from shared links ("Shared Recipes", tagged with a `shared` attribute) — and create / edit / delete write straight back to the cloud (so they show up in the iOS app too). On first login, choose to upload your existing local recipes or discard them. Log out any time to fall back to the local library.
- **Firmware update** *(cloud + Bluetooth)* — when logged in, a Firmware entity compares your machine's installed firmware (read from the machine over Bluetooth) against the latest version xBloom publishes, with release notes. Pressing **Install** downloads the firmware from xBloom's servers, verifies its MD5, and flashes it to the machine over Bluetooth (the transfer is validated byte-for-byte against a real captured update and is acknowledged block-by-block). ⚠️ Firmware flashing is inherently risky — a dropped Bluetooth link mid-update can brick the machine. Keep the machine close and powered, and don't run it while brewing.
- **One-tap brewing** — start, pause, resume, or cancel a brew; brew with pre-ground coffee; write a recipe to one of the machine's on-device slots.
- **Standalone control** — run the grinder or brewer on their own, tare the scale, switch water source, and change on-screen units.
- **Announcement blueprints** — ready-made automation blueprints that speak brew progress, live-control feedback, and machine faults through any TTS or notify service (e.g. Alexa).

## Requirements

- Home Assistant **2025.x** or newer.
- A Bluetooth adapter local to your Home Assistant host, **or** an [ESPHome Bluetooth proxy](https://esphome.io/components/bluetooth_proxy.html) within range of the machine. The integration routes through Home Assistant's built-in Bluetooth so either works.
- The xBloom Studio powered on and in BLE range during setup and while sending commands.

## Installation

### HACS (recommended)

This repository is installed as a HACS **custom repository**:

1. In Home Assistant, open **HACS**.
2. Open the menu (three dots, top right) → **Custom repositories**.
3. Add the URL `https://github.com/Alshekhi/xbloom-studio` and choose the category **Integration**.
4. Install **xBloom Studio**, then restart Home Assistant.

### Manual

Copy `custom_components/xbloom/` into your Home Assistant `config/custom_components/` directory, then restart Home Assistant.

## Configuration

With the machine powered on and in range, Home Assistant discovers it automatically over Bluetooth (it advertises as `XBLOOM …`). You will see a discovered device under **Settings → Devices & Services** — confirm it to finish setup. If it is not discovered, use **Add Integration → xBloom Studio**.

Recipes are managed after setup from the integration's **Configure** (options) menu: add from an xBloom share URL or share ID, or create, edit, and delete recipes by hand. The **Recipe** select entity always reflects the current library.

### Optional: xBloom cloud login

The same **Configure** menu has **Log in to xBloom cloud**. Sign in with your xBloom account email and password to sync recipes with the cloud — once logged in, the cloud becomes the single source of truth and every create / edit / delete is written back to your account. If you already have local recipes, you'll be asked whether to upload them to the cloud or discard them.

Tick **Remember my credentials** to store your password locally (in `.storage`, alongside the session token) so the session refreshes itself automatically when the token expires — it's only ever sent to xBloom's login endpoint. Leave it unticked for more privacy: only the token is kept, and when it expires you'll be prompted to log in again. Use **Log out of xBloom cloud** to clear everything and return to the local library (your synced recipes stay cached locally). The cloud is entirely optional — leaving it out keeps the integration BLE-only.

Recipe sync is event-driven, not polled: changes you make in Home Assistant apply immediately, and the options-flow recipe lists pull fresh from the cloud each time you open them. A recipe added or edited on your phone shows up on dashboard dropdowns after you press the **Refresh Recipes** button (Home Assistant has no way to fetch on a dropdown opening).

## Entities

- **Sensors** — Brew Status, Machine Status, Scale Weight, and live readings: Current Recipe, Current Pour, Current Module, Grind Size, Grind Speed, Pour Pattern, Brew Temperature, Brew Ratio, Last Recipe Card.
- **Event** — Brew Event, fired for brew lifecycle changes (useful as an automation trigger).
- **Selects** — Recipe, Mode (auto / pro), Water Source (tank / tap), Temperature Unit (°C / °F), Weight Unit (g / oz / ml), Brew Pattern.
- **Numbers** — Grind Size, Grind Speed, Brew Volume, Brew Temperature, Brew Flow Rate.
- **Buttons** — Start Brew, Cancel Brew, Pause Brew, Resume Brew, Tare Scale, Back to Home, Grind, Brew (standalone), Refresh Recipes, plus BLE Connect / BLE Disconnect diagnostics.
- **Switches** — Use Grinder, Live Control.
- **Update** — Firmware (installed vs latest, with an Install button; available when logged in to the xBloom cloud).

## Services

The integration registers services under the `xbloom.` domain. Highlights:

- Brewing: `start_brew`, `stop_brew`, `brew_pause`, `brew_resume`, `brew_standalone`, `write_slot`.
- Machine control: `grind`, `tare`, `back_to_home`, `set_mode`, `set_water_source`, `set_temp_unit`, `set_weight_unit`.
- Recipe library: `list_recipes`, `get_recipe`, `add_recipe`, `update_recipe`, `delete_recipe`.
- Diagnostics: `ble_connect`, `ble_disconnect`, `dump_notifications`.

Each service, its parameters, and its BLE command are documented in `custom_components/xbloom/services.yaml` and appear in **Developer Tools → Actions**.

## Blueprints

Three automation blueprints live in `blueprints/automation/xbloom/`:

- `brew_announce.yaml` — announces brew progress and completion.
- `live_control_announce.yaml` — speaks feedback while you adjust the machine.
- `machine_fault_announce.yaml` — announces machine faults.

They target any TTS or notify service, so they work with Alexa, Google, or a local speaker. Import them from **Settings → Automations & Scenes → Blueprints → Import Blueprint** using the raw file URL, or copy them into your `config/blueprints/automation/` directory.

## Disclaimer

This is an unofficial, community project. It is **not affiliated with, authorized, or endorsed by xBloom**. It talks to the machine over its local BLE protocol, which may change with firmware updates. Use at your own risk.

## License

Released under the [MIT License](LICENSE).
